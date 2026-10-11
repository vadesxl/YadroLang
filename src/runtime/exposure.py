# -*- coding: utf-8 -*-
"""Exposure scan: which programs listen on network ports, and who can reach them.

Levels of certainty (shown to the user, never mixed up):
  1. listening + bind address  -> exact (netstat)
  2. Windows firewall verdict   -> exact for the active profile (netsh / Get-NetFirewall*)
  3. router port forwarding     -> not checked here (needs UPnP query)
  4. reachable from the internet-> NOT checked: requires an external probe the user opts into

Reach classes:
  this_computer   127.0.0.0/8, ::1          safe
  local_network   a specific LAN address      reachable by devices on the same network
  all_networks    0.0.0.0 / ::                reachable by every network this PC joins
                                              (home Wi-Fi, café Wi-Fi, VPN, internet if forwarded)
Read-only: this module never changes ports, services or the firewall.
"""
from __future__ import annotations

import csv
import io
import ipaddress
import json
import ntpath
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import services as S

TIMEOUT = 20


@dataclass
class Listener:
    proto: str
    address: str
    port: int
    pid: int
    process: str = ""
    path: str = ""
    reach: str = ""
    service: str = ""
    category: str = ""
    severity: str = S.INFO
    why: str = ""
    fix: str = ""
    firewall: str = "unknown"      # allowed / blocked / off / not verified / not needed
    firewall_rule: str = ""        # name of the deciding rule, if one decided it
    firewall_scope: str = ""       # everyone / local network / some addresses / default / ...
    services: List[str] = field(default_factory=list)     # Windows services in this process
    addresses: List[str] = field(default_factory=list)    # 0.0.0.0 and :: merged into one row
    tags: List[str] = field(default_factory=list)

    def public(self) -> dict:
        return dict(self.__dict__)


def _run(cmd: List[str]) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT,
                           encoding="utf-8", errors="replace",
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return r.stdout or ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


_NETSTAT = re.compile(r"^\s*(TCP|UDP)\s+(\S+):(\d+)\s+(\S+)\s+(?:(LISTENING)\s+)?(\d+)\s*$", re.I)


def parse_netstat(text: str) -> List[Listener]:
    out, seen = [], set()
    for line in text.splitlines():
        m = _NETSTAT.match(line)
        if not m:
            continue
        proto, addr, port, _remote, state, pid = m.groups()
        if proto.upper() == "TCP" and not state:
            continue                       # only LISTENING sockets for TCP
        addr = addr.strip("[]")
        key = (proto.upper(), addr, int(port), int(pid))
        if key in seen:
            continue
        seen.add(key)
        out.append(Listener(proto.upper(), addr, int(port), int(pid)))
    return out


def classify_reach(address: str) -> str:
    if address in ("0.0.0.0", "::", "*"):
        return "all_networks"
    try:
        ip = ipaddress.ip_address(address.split("%")[0])
    except ValueError:
        return "all_networks"
    if ip.is_loopback:
        return "this_computer"
    return "local_network" if ip.is_private or ip.is_link_local else "all_networks"


def parse_tasklist(text: str) -> Dict[int, str]:
    names = {}
    for row in csv.reader(io.StringIO(text)):
        if len(row) >= 2 and row[1].isdigit():
            names[int(row[1])] = row[0]
    return names


def _proc_key(name: str) -> str:
    return re.sub(r"\.exe$", "", (name or "").lower())


def assess(l: Listener) -> Listener:
    """Fill service, severity, why and fix for one listener."""
    l.reach = classify_reach(l.address)
    proc = _proc_key(l.process)
    info = S.PORTS.get(l.port)
    by_proc = next((v for k, v in S.PROCESSES.items() if proc == k or proc.startswith(k)), None)
    chosen = by_proc if (by_proc and (not info or by_proc[2] != S.LOW)) else info
    by_svc = next((S.WINDOWS_SERVICES[s.lower()] for s in l.services
                   if s.lower() in S.WINDOWS_SERVICES and l.port in S.WINDOWS_SERVICES[s.lower()][0]), None)
    if by_svc and proc == "svchost":            # the hosted service is known for sure: name it
        chosen = by_svc[1:]
    if proc in ("system", "svchost", "lsass", "services", "wininit") and l.port in S.WINDOWS_SYSTEM:
        chosen = None
        l.service, l.category = "Windows system service", "system"
    if chosen:
        l.service, l.category, sev, l.why, l.fix = chosen
    else:
        sev = S.INFO
        l.service = l.service or "Unknown service"
        l.category = l.category or "other"
        l.why = l.why or "A program is waiting for network connections."
        l.fix = l.fix or "If you do not recognise this program, stop it or block it in the firewall."
    if proc in S.TUNNEL_PROCESSES:
        l.tags.append("public-tunnel")
    # severity depends on who can reach it
    udp_noise = l.proto == "UDP" and (l.port in S.DISCOVERY_UDP or l.port >= S.EPHEMERAL_START) \
        and sev in (S.INFO, S.LOW)
    if udp_noise:
        l.severity = S.INFO
        l.service = "Network discovery / app traffic (UDP)"
        l.category = "system"
        l.why = "Used to find devices and for normal app traffic. Not a server others can log into."
        l.fix = "Nothing to do."
    elif l.reach == "this_computer":
        l.severity = S.INFO
        l.why = "Only programs on this computer can connect. This is the safe setting."
        l.fix = "Nothing to do."
    elif l.reach == "local_network":
        l.severity = {S.CRITICAL: S.HIGH, S.HIGH: S.MEDIUM, S.MEDIUM: S.LOW}.get(sev, sev)
    else:
        l.severity = sev if sev != S.INFO else S.LOW
        if l.category == "system":
            l.severity = S.INFO
    if l.firewall == "allowed" and l.severity in (S.CRITICAL, S.HIGH) and l.reach == "all_networks":
        l.tags.append("firewall-allows")
    return l


def parse_services(text: str) -> Dict[int, List[str]]:
    """`tasklist /SVC /FO CSV /NH` -> pid -> Windows service names hosted in that process."""
    out = {}
    for row in csv.reader(io.StringIO(text)):
        if len(row) >= 3 and row[1].isdigit() and row[2] not in ("N/A", ""):
            out[int(row[1])] = [s.strip() for s in row[2].split(",") if s.strip()]
    return out


# One fast, read-only, non-admin query of the local firewall policy (COM HNetCfg.FwPolicy2,
# ~0.2 s; Get-NetFirewall* needs 10-20 s for the same data). Process paths are read only
# for the listening PIDs, to match program rules exactly. Store-app (app container) rules:
# COM hides LocalAppPackageId without admin rights, but such rules have an owner SID and
# no program, so that pair marks them; they do not apply to normal desktop programs.
_FW_PS = r"""
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$f = New-Object -ComObject HNetCfg.FwPolicy2
$rules = foreach ($r in $f.Rules) {
  if ($r.Direction -ne 1 -or -not $r.Enabled) { continue }
  [ordered]@{ name = $r.Name; action = $r.Action; protocol = $r.Protocol; ports = $r.LocalPorts;
    app = $r.ApplicationName; service = $r.serviceName; profiles = $r.Profiles; remote = $r.RemoteAddresses;
    local = $r.LocalAddresses; ifaces = $r.InterfaceTypes; group = $r.Grouping;
    package = [bool]($r.LocalAppPackageId -or ($r.LocalUserOwner -and -not $r.ApplicationName)) }
}
$paths = @{}
foreach ($p in (Get-Process -Id @(__PIDS__) -ErrorAction SilentlyContinue)) { if ($p.Path) { $paths["$($p.Id)"] = $p.Path } }
[ordered]@{ current = $f.CurrentProfileTypes; modify_state = $f.LocalPolicyModifyState;
  enabled = @(1, 2, 4 | ForEach-Object { $f.FirewallEnabled($_) });
  default_in = @(1, 2, 4 | ForEach-Object { $f.DefaultInboundAction($_) });
  block_all = @(1, 2, 4 | ForEach-Object { $f.BlockAllInboundTraffic($_) });
  rules = @($rules); paths = $paths } | ConvertTo-Json -Depth 4 -Compress
"""
_PROFILE_BITS = (1, 2, 4)          # domain, private, public (index in enabled/default_in/block_all)
_TCP, _UDP, _ANY_PROTO = 6, 17, 256
_FW_BLOCK = 0


def firewall_state(pids: List[int]) -> Optional[dict]:
    """Local Windows Firewall policy + paths of the given PIDs. None if it cannot be read."""
    ids = ",".join(str(int(p)) for p in sorted(set(pids))) or "0"
    out = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", _FW_PS.replace("__PIDS__", ids)])
    try:
        data = json.loads(out.strip() or "null")
    except ValueError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        return None
    return data


def _port_match(spec: Optional[str], port: int) -> Optional[bool]:
    """True/False for numeric port specs; None when a keyword (RPC, Teredo, ...) makes it unknowable."""
    spec = (spec or "*").strip()
    if spec == "*":
        return True
    unknown = False
    for part in (p.strip() for p in spec.split(",")):
        if not part:
            continue
        if part.isdigit():
            if int(part) == port:
                return True
        elif re.fullmatch(r"\d+-\d+", part):
            a, b = map(int, part.split("-"))
            if a <= port <= b:
                return True
        else:
            unknown = True
    return None if unknown else False


def _app_match(rule_app: Optional[str], process: str, path: str) -> Optional[bool]:
    """True = same program, False = other program, None = same file name but the path is unknown."""
    if not rule_app or rule_app.strip().lower() in ("any", "*"):
        return True
    if rule_app.strip().lower() == "system":
        return (process or "").lower() == "system"
    if path:
        return ntpath.normcase(os.path.expandvars(rule_app)) == ntpath.normcase(path)
    return None if ntpath.basename(rule_app).lower() == (process or "").lower() else False


def _service_match(rule_svc: Optional[str], services: List[str]) -> bool:
    if not rule_svc:
        return True
    if rule_svc == "*":
        return bool(services)
    return rule_svc.lower() in {s.lower() for s in services}


def _scope(remote: Optional[str]) -> str:
    r = (remote or "*").strip()
    if r == "*":
        return "everyone"
    if all(p.strip().lower() in ("localsubnet", "local subnet") for p in r.split(",")):
        return "local network"
    return "some addresses"


# Built-in Windows rule groups that look like "System, all ports" but are bound to one
# special interface (Wi-Fi Direct). Their real scope is not visible through the API,
# so they never decide the verdict either way.
_INTERFACE_BOUND_GROUPS = ("@wlansvc.dll",)


def _unrestricted(r: dict) -> bool:
    return (r.get("local") or "*") == "*" and (r.get("ifaces") or "All") == "All" \
        and (r.get("remote") or "*") == "*"


def firewall_verdict(l: Listener, fw: Optional[dict], services: List[str], path: str) -> tuple:
    """(verdict, rule_name, scope) for one listener, from the LOCAL firewall policy.

    verdict: allowed | blocked | off | not verified. "blocked" is claimed only when it
    follows from the policy for sure; anything we cannot map makes it "not verified".
    Allow rules are matched generously: a false "allowed" only overstates risk."""
    if not fw:
        return "not verified", "", ""
    if fw.get("modify_state") not in (0, None):
        return "not verified", "", "group policy"         # GPO rules are not visible here
    current = int(fw.get("current") or 0)
    active = [i for i, bit in enumerate(_PROFILE_BITS) if current & bit]
    if not active:
        return "not verified", "", ""
    enabled, default_in, block_all = fw.get("enabled") or [], fw.get("default_in") or [], fw.get("block_all") or []
    try:
        if not all(enabled[i] for i in active):
            return "off", "", ""
        if all(block_all[i] for i in active):
            return "blocked", "", "all incoming blocked"
        default_block = all(default_in[i] == _FW_BLOCK for i in active)
    except (IndexError, TypeError):
        return "not verified", "", ""
    proto = _TCP if l.proto == "TCP" else _UDP
    allow, uncertain = None, False
    for r in fw["rules"]:
        if not isinstance(r, dict) or r.get("protocol") not in (proto, _ANY_PROTO):
            continue
        if not (int(r.get("profiles") or 0) & current):
            continue
        if r.get("package"):                       # Store-app rule: only for packaged apps
            uncertain = uncertain or "\\windowsapps\\" in (path or "").lower()
            continue
        app = _app_match(r.get("app"), l.process, path)
        if app is False or not _service_match(r.get("service"), services):
            continue
        pm = _port_match(r.get("ports"), l.port)
        if pm is False:
            continue
        if r.get("action") == _FW_BLOCK:
            if pm is True and app is True and _unrestricted(r):
                return "blocked", r.get("name") or "", "rule"
            uncertain = True
            continue
        if pm is None or str(r.get("group") or "").lower().startswith(_INTERFACE_BOUND_GROUPS):
            uncertain = True
            continue
        sc = _scope(r.get("remote"))
        if allow is None or (sc == "everyone" and allow[2] != "everyone"):
            allow = ("allowed", r.get("name") or "", sc)
    if allow:
        return allow
    if uncertain:
        return "not verified", "", ""
    return ("blocked", "", "default") if default_block else ("allowed", "", "default")


def merge_dual_stack(listeners: List[Listener]) -> List[Listener]:
    """One row for the same program listening on both 0.0.0.0 and [::] (IPv4 + IPv6)."""
    out, first_of = [], {}
    for l in listeners:
        if l.address not in ("0.0.0.0", "::"):
            out.append(l)
            continue
        key = (l.proto, l.port, l.pid)
        first = first_of.get(key)
        if first is None:
            l.addresses = [l.address]
            first_of[key] = l
            out.append(l)
            continue
        if l.address not in first.addresses:
            first.addresses.append(l.address)
        if S.SEVERITY_ORDER[l.severity] < S.SEVERITY_ORDER[first.severity]:
            first.severity, first.why, first.fix = l.severity, l.why, l.fix
        if _FW_RANK.get(l.firewall, 0) > _FW_RANK.get(first.firewall, 0):   # keep the riskier verdict
            first.firewall, first.firewall_rule, first.firewall_scope = l.firewall, l.firewall_rule, l.firewall_scope
        first.tags.extend(t for t in l.tags if t not in first.tags)
    for l in out:
        l.addresses = sorted(l.addresses or [l.address], key=lambda a: ":" in a)   # IPv4 first
    return out


_FW_RANK = {"not needed": 0, "blocked": 1, "not verified": 2, "allowed": 3, "off": 4}


def scan(with_firewall: bool = True) -> dict:
    """Full read-only exposure scan of this computer."""
    if os.name != "nt":
        return {"status": "error", "message": "The exposure scan currently supports Windows only."}
    started = time.time()
    listeners = parse_netstat(_run(["netstat", "-ano"]))
    names = parse_tasklist(_run(["tasklist", "/FO", "CSV", "/NH"]))
    hosted = parse_services(_run(["tasklist", "/SVC", "/FO", "CSV", "/NH"]))
    fw = firewall_state([l.pid for l in listeners if classify_reach(l.address) != "this_computer"]) \
        if with_firewall else None
    paths = (fw or {}).get("paths") or {}
    for l in listeners:
        l.process = names.get(l.pid, "System" if l.pid == 4 else "unknown")
        l.services = hosted.get(l.pid, [])
        if classify_reach(l.address) != "this_computer":
            l.firewall, l.firewall_rule, l.firewall_scope = firewall_verdict(
                l, fw, l.services, paths.get(str(l.pid), "") if isinstance(paths, dict) else "")
        else:
            l.firewall = "not needed"
        assess(l)
    listeners = [l for l in listeners if not (l.proto == "UDP" and l.reach == "this_computer")]
    listeners = merge_dual_stack(listeners)
    listeners.sort(key=lambda l: (S.SEVERITY_ORDER[l.severity], l.reach != "all_networks", l.port))
    counts = {s: sum(1 for l in listeners if l.severity == s) for s in S.SEVERITY_ORDER}
    score = max(0, 100 - 30 * counts[S.CRITICAL] - 12 * counts[S.HIGH] - 5 * counts[S.MEDIUM]
                - min(10, counts[S.LOW]))
    return {"status": "ok", "scanned_at": int(time.time()), "duration_ms": int((time.time() - started) * 1000),
            "score": score, "counts": counts, "listeners": [l.public() for l in listeners],
            "firewall_checked": fw is not None,
            "limits": ["This scan sees what listens on this computer and what Windows Firewall allows.",
                       "Firewall verdicts come from the local Windows Firewall rules. Rules set by a company "
                       "(group policy) or by other security software are not visible, so those show as 'not verified'.",
                       "It cannot see port forwarding on your router. Make sure the router forwards no ports you do not need.",
                       "It does not test from the internet. An external check sends your IP address to an outside service, "
                       "so it is only done when you ask for it."]}
