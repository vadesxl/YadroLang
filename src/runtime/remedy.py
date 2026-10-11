# -*- coding: utf-8 -*-
"""Exposure remedies: what the user can DO about an open port, from the Guard tab.

Safety rules (enforced here, not in the UI):
- The client sends only (proto, port, pid). Process name and hosted services are looked
  up again right now; a request for a listener that no longer exists is refused.
- Every change to the system runs in a separate elevated PowerShell, so Windows shows
  its own UAC prompt: the user confirms each change outside the browser and the agent.
  Scripts come from fixed templates; only validated integers and whitelisted service
  names are inserted.
- Every change is journaled with an exact undo (rule name, previous service start type).
  Guard's firewall rules live in their own group "Yadro Guard".
- "Trust" and "open settings" change nothing in the system and need no elevation.
"""
from __future__ import annotations

import base64
import json
import os
import re
import secrets
import subprocess
import time
from typing import Dict, List, Optional

from . import exposure as E
from .policy import home

RULE_GROUP = "Yadro Guard"
ELEVATED_TIMEOUT = 180
CRITICAL_PROCESSES = {"system", "svchost", "lsass", "services", "wininit", "csrss", "smss", "winlogon",
                      "spoolsv", "dwm", "explorer", "unknown"}

# Windows services that are safe to switch off when the user does not need them.
# key (lowercase) -> (exact service name, what stops working)
SAFE_TO_DISABLE = {
    "lanmanserver": ("LanmanServer", "Other computers will no longer open shared folders or printers on this PC."),
    "asusupdatecheck": ("AsusUpdateCheck", "ASUS software will stop checking for updates automatically."),
    "termservice": ("TermService", "Remote Desktop to this PC will stop working."),
    "winrm": ("WinRM", "PowerShell remoting to this PC will stop working."),
    "ssdpsrv": ("SSDPSRV", "Some devices (TVs, media players) may not find this PC."),
    "upnphost": ("upnphost", "This PC will stop offering UPnP devices to the network."),
    "fdrespub": ("FDResPub", "Other computers will not see this PC in the Network folder."),
}
PORT_OWNER_SERVICE = {445: "lanmanserver"}      # kernel (pid 4) ports owned by a service
SETTINGS = {                                    # fixed commands, no user input
    "firewall": ["mmc.exe", "wf.msc"],
    "sharing": ["control.exe", "/name", "Microsoft.NetworkAndSharingCenter", "/page", "Advanced"],
    "services": ["mmc.exe", "services.msc"],
    "delivery": ["explorer.exe", "ms-settings:delivery-optimization"],
}
_SETTINGS_FOR = {"share": "sharing", "vendor": "services", "remote": "services"}


class RemedyError(Exception):
    pass


# ---------- journal and trust list ----------
def _read(name: str, default):
    try:
        return json.loads((home() / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write(name: str, data) -> None:
    p = home() / name
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)


def trust_key(proto: str, port: int, process: str) -> str:
    return f"{proto.upper()}:{int(port)}:{(process or '').lower()}"


def trusted() -> Dict[str, int]:
    d = _read("exposure_trust.json", {})
    return d if isinstance(d, dict) else {}


def journal() -> List[dict]:
    j = _read("remedies.json", [])
    return j if isinstance(j, list) else []


def _log(kind: str, title: str, undo: Optional[dict], l: "E.Listener") -> dict:
    entry = {"id": "FX-" + secrets.token_hex(3).upper(), "at": int(time.time()), "kind": kind, "title": title,
             "proto": l.proto, "port": l.port, "process": l.process, "undo": undo, "undone": False}
    _write("remedies.json", ([entry] + journal())[:200])
    return entry


def _mark_undone(fix_id: str) -> None:
    j = journal()
    for e in j:
        if e.get("id") == fix_id:
            e["undone"], e["undone_at"] = True, int(time.time())
    _write("remedies.json", j)


def guard_rules() -> set:
    """Rule names Guard created and has not undone (from the journal; no system query)."""
    return {(e.get("undo") or {}).get("rule") for e in journal()
            if not e.get("undone") and (e.get("undo") or {}).get("rule")}


# ---------- which actions make sense for a listener ----------
def rule_name(proto: str, port: int) -> str:
    return f"YadroGuard-Block-{proto.upper()}-{int(port)}"


def service_for(l: "E.Listener") -> Optional[str]:
    names = {s.lower() for s in l.services}
    if l.pid == 4 and l.port in PORT_OWNER_SERVICE:
        names.add(PORT_OWNER_SERVICE[l.port])
    return next((n for n in sorted(names) if n in SAFE_TO_DISABLE), None)


def actions_for(l: "E.Listener", guard_blocked: bool, is_trusted: bool) -> List[str]:
    acts = []
    if l.reach != "this_computer":
        acts.append("unblock" if guard_blocked else "block_port")
    svc = service_for(l)
    if svc:
        acts.append("disable_service")
    elif E._proc_key(l.process) not in CRITICAL_PROCESSES and l.pid > 4:
        acts.append("stop_program")
        acts.append("show_file")
    acts.append("untrust" if is_trusted else "trust")
    return acts


def settings_for(l: "E.Listener") -> Optional[str]:
    if any(s.lower() == "dosvc" for s in l.services):
        return "delivery"
    if l.category in _SETTINGS_FOR:
        return _SETTINGS_FOR[l.category]
    return "firewall" if l.reach != "this_computer" else None


def what_breaks(l: "E.Listener") -> str:
    key = service_for(l)
    return SAFE_TO_DISABLE[key][1] if key else ""


# ---------- the live listener the request is about ----------
def _live(proto: str, port: int, pid: int) -> "E.Listener":
    proto = str(proto).upper()
    try:
        port, pid = int(port), int(pid)
    except (TypeError, ValueError):
        raise RemedyError("bad request")
    if proto not in ("TCP", "UDP") or not (0 < port < 65536) or pid < 0:
        raise RemedyError("bad request")
    for l in E.parse_netstat(E._run(["netstat", "-ano"])):
        if l.proto == proto and l.port == port and l.pid == pid:
            flt = ["/FI", f"PID eq {pid}"]
            l.process = E.parse_tasklist(E._run(["tasklist", "/FO", "CSV", "/NH", *flt])).get(
                pid, "System" if pid == 4 else "unknown")
            l.services = E.parse_services(E._run(["tasklist", "/SVC", "/FO", "CSV", "/NH", *flt])).get(pid, [])
            l.reach = E.classify_reach(l.address)
            return l
    raise RemedyError("This program is no longer listening on that port. Run the check again.")


def _proc_path(pid: int) -> str:
    out = E._run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                  f"(Get-Process -Id {int(pid)} -ErrorAction SilentlyContinue).Path"]).strip()
    return out if re.fullmatch(r"[A-Za-z]:\\[^\r\n<>\"|?*]+", out or "") else ""


# ---------- elevated execution (UAC) ----------
def _elevated(script: str) -> None:
    """Run a fixed script in an elevated PowerShell. Windows asks the user (UAC)."""
    inner = "$ErrorActionPreference = 'Stop'\n" + script + "\nexit 0\n"
    enc = base64.b64encode(inner.encode("utf-16-le")).decode("ascii")
    outer = ("try { $p = Start-Process powershell -Verb RunAs -Wait -PassThru -WindowStyle Hidden "
             f"-ArgumentList '-NoProfile','-NonInteractive','-EncodedCommand','{enc}'; exit $p.ExitCode }} "
             "catch { exit 1223 }")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", outer],
                           capture_output=True, text=True, timeout=ELEVATED_TIMEOUT,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired):
        raise RemedyError("Windows did not finish the change in time. Nothing was confirmed.")
    if r.returncode == 1223:
        raise RemedyError("You cancelled the Windows confirmation. Nothing was changed.")
    if r.returncode != 0:
        raise RemedyError("Windows refused the change. Nothing was changed.")


def _service_start_type(name: str) -> str:
    out = E._run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                  f"(Get-Service -Name '{name}' -ErrorAction SilentlyContinue).StartType"]).strip()
    return out if out in ("Automatic", "Manual") else "Manual"


# ---------- actions ----------
def run(action: str, proto: str, port: int, pid: int) -> dict:
    """Perform one action for one live listener. "message" is a short code the UI translates."""
    if os.name != "nt":
        raise RemedyError("Only Windows is supported.")
    l = _live(proto, port, pid)
    if action in ("trust", "untrust"):
        t = trusted()
        k = trust_key(l.proto, l.port, l.process)
        if action == "trust":
            t[k] = int(time.time())
        else:
            t.pop(k, None)
        _write("exposure_trust.json", t)
        return {"status": "ok", "message": action}
    if action == "block_port":
        if l.reach == "this_computer":
            raise RemedyError("This port is already reachable only from this computer.")
        name = rule_name(l.proto, l.port)
        _elevated(f"Remove-NetFirewallRule -Name '{name}' -ErrorAction SilentlyContinue\n"
                  f"New-NetFirewallRule -Name '{name}' -DisplayName 'Yadro Guard: block {l.proto} {l.port}' "
                  f"-Group '{RULE_GROUP}' -Direction Inbound -Action Block -Protocol {l.proto} "
                  f"-LocalPort {l.port} -Profile Any | Out-Null")
        e = _log("block_port", f"block {l.proto} {l.port}", {"rule": name}, l)
        return {"status": "ok", "message": "blocked", "fix": e["id"]}
    if action == "unblock":
        name = rule_name(l.proto, l.port)
        _elevated(f"Remove-NetFirewallRule -Name '{name}'")
        for e in journal():
            if (e.get("undo") or {}).get("rule") == name and not e.get("undone"):
                _mark_undone(e["id"])
        return {"status": "ok", "message": "unblocked"}
    if action == "disable_service":
        key = service_for(l)
        if not key:
            raise RemedyError("This service cannot be switched off safely from here.")
        svc = SAFE_TO_DISABLE[key][0]
        before = _service_start_type(svc)
        _elevated(f"Stop-Service -Name '{svc}' -Force\nSet-Service -Name '{svc}' -StartupType Disabled")
        e = _log("disable_service", f"service {svc} off", {"service": svc, "start_type": before}, l)
        return {"status": "ok", "message": "service_off", "fix": e["id"]}
    if action == "stop_program":
        if E._proc_key(l.process) in CRITICAL_PROCESSES or l.pid <= 4 or service_for(l):
            raise RemedyError("This is part of Windows and cannot be stopped from here.")
        _elevated(f"Stop-Process -Id {l.pid} -Force")
        _log("stop_program", f"stop {l.process} ({l.pid})", None, l)
        return {"status": "ok", "message": "stopped"}
    if action == "show_file":
        path = _proc_path(l.pid)
        if not path:
            raise RemedyError("The program's file could not be found.")
        subprocess.Popen(["explorer.exe", "/select,", path])
        return {"status": "ok", "message": "shown"}
    raise RemedyError("Unknown action.")


def open_settings(which: str) -> dict:
    if which not in SETTINGS or os.name != "nt":
        raise RemedyError("Unknown settings page.")
    subprocess.Popen(SETTINGS[which])
    return {"status": "ok", "message": "settings"}


def undo(fix_id: str) -> dict:
    e = next((x for x in journal() if x.get("id") == fix_id), None)
    if not e or e.get("undone"):
        raise RemedyError("Nothing to undo.")
    u = e.get("undo") or {}
    rule, svc = str(u.get("rule", "")), str(u.get("service", ""))
    if rule and re.fullmatch(r"YadroGuard-Block-(TCP|UDP)-\d{1,5}", rule):
        _elevated(f"Remove-NetFirewallRule -Name '{rule}'")
    elif svc and SAFE_TO_DISABLE.get(svc.lower(), ("",))[0] == svc:
        start = u.get("start_type") if u.get("start_type") in ("Automatic", "Manual") else "Manual"
        _elevated(f"Set-Service -Name '{svc}' -StartupType {start}\nStart-Service -Name '{svc}'")
    else:
        raise RemedyError("This change cannot be undone automatically.")
    _mark_undone(fix_id)
    return {"status": "ok", "message": "undone"}
