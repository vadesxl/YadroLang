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
    firewall: str = "unknown"      # allowed / blocked / unknown
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


def firewall_allowed_ports() -> Optional[set]:
    """Ports with an enabled inbound ALLOW rule for that SPECIFIC port. None if unknown.

    Rules for "any port" of a given program are deliberately ignored: mapping them to
    a listener reliably needs the program path, so we do not claim anything from them.
    Absence from this set therefore means "not verified", never "blocked"."""
    ps = ("Get-NetFirewallRule -Direction Inbound -Enabled True -Action Allow | "
          "Get-NetFirewallPortFilter | Select-Object -ExpandProperty LocalPort")
    out = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps])
    if not out.strip():
        return None
    ports = set()
    for tok in out.split():
        if tok.isdigit():
            ports.add(int(tok))
        elif re.fullmatch(r"\d+-\d+", tok):
            a, b = map(int, tok.split("-"))
            if b - a <= 1000:
                ports.update(range(a, b + 1))
    return ports


def scan(with_firewall: bool = True) -> dict:
    """Full read-only exposure scan of this computer."""
    if os.name != "nt":
        return {"status": "error", "message": "The exposure scan currently supports Windows only."}
    started = time.time()
    listeners = parse_netstat(_run(["netstat", "-ano"]))
    names = parse_tasklist(_run(["tasklist", "/FO", "CSV", "/NH"]))
    allowed = firewall_allowed_ports() if with_firewall else None
    for l in listeners:
        l.process = names.get(l.pid, "System" if l.pid == 4 else "unknown")
        if l.reach != "this_computer":
            l.firewall = "allowed" if (allowed is not None and l.port in allowed) else "not verified"
        else:
            l.firewall = "not needed"
        assess(l)
    listeners = [l for l in listeners if not (l.proto == "UDP" and l.reach == "this_computer")]
    listeners.sort(key=lambda l: (S.SEVERITY_ORDER[l.severity], l.reach != "all_networks", l.port))
    counts = {s: sum(1 for l in listeners if l.severity == s) for s in S.SEVERITY_ORDER}
    score = max(0, 100 - 30 * counts[S.CRITICAL] - 12 * counts[S.HIGH] - 5 * counts[S.MEDIUM]
                - min(10, counts[S.LOW]))
    return {"status": "ok", "scanned_at": int(time.time()), "duration_ms": int((time.time() - started) * 1000),
            "score": score, "counts": counts, "listeners": [l.public() for l in listeners],
            "firewall_checked": allowed is not None,
            "limits": ["This scan sees what listens on this computer and what Windows Firewall allows.",
                       "It cannot see port forwarding on your router. Make sure the router forwards no ports you do not need.",
                       "It does not test from the internet. An external check sends your IP address to an outside service, "
                       "so it is only done when you ask for it."]}
