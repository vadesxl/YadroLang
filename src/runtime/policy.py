# -*- coding: utf-8 -*-
"""Runtime Guard policy: what happens when an agent action contains a secret.

Flow for one agent tool call (pre_tool_call):
  1. scan the arguments for secrets (detectors)
  2. nothing found              -> allow (None)
  3. a saved decision matches   -> apply it (protect & send / block)
  4. otherwise                  -> BLOCK, record an incident, wait for the user

User decisions on an incident (made in the Guard tab):
  protect   "Protect & send"      secrets are swapped for vault tokens / masks, the
                                  agent's retried action goes out with the replacements
  block     "Block & quarantine"  the action stays blocked, the secret goes to the vault
  allow     "Allow once"          the exact same action may run one time

Safety rules:
- Raw secret values are NEVER written to the incident journal: only masked
  previews and SHA-256 fingerprints (to recognise the same secret again).
- Unknown errors inside this module result in BLOCK (fail-closed).
- Every state file is written atomically.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import detectors

MAX_INCIDENTS = 500
DECISION_TTL = 7 * 24 * 3600     # a saved decision is valid for a week
ALLOW_ONCE_TTL = 15 * 60         # "allow once" expires after 15 minutes if unused
LABEL_RU = {"PII": "ПДн", "Financial": "Финансы", "Health": "Здоровье",
            "Credentials": "УчетныеДанные", "Location": "Локация"}


def home() -> Path:
    base = os.environ.get("YADRO_GUARD_HOME") or (Path(os.environ.get("LOCALAPPDATA", Path.home())) / "yadro-guard")
    return Path(base)


def _file(name: str) -> Path:
    return home() / name


def _read(name: str, default):
    try:
        return json.loads(_file(name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write(name: str, data) -> None:
    p = _file(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def action_key(tool_name: str, findings: List[detectors.Finding]) -> str:
    """Same tool + same set of secrets = same action (args may differ slightly)."""
    fps = sorted({fingerprint(f.value) for f in findings})
    return hashlib.sha256((tool_name + "|" + "|".join(fps)).encode()).hexdigest()[:32]


def _destination(tool_name: str, args: Any) -> str:
    """Best-effort human description of where the data is going."""
    if isinstance(args, dict):
        for key in ("url", "endpoint", "uri", "to", "recipient", "chat_id", "channel", "path", "file_path"):
            v = args.get(key)
            if isinstance(v, str) and v:
                return v[:160]
        cmd = args.get("command") or args.get("cmd")
        if isinstance(cmd, str) and cmd:
            import re
            url = re.search(r"\b(?:https?|ftp|wss?)://[^\s\"'<>]+", cmd)
            prog = cmd.split()[0][:60]
            return f"{url.group(0)[:140]} (via {prog})" if url else "shell: " + prog
    return tool_name


def _known_secrets():
    """(value, label, title) for secrets in the vault — exact-match detection."""
    try:
        from .. import vault
        return vault.known_values()
    except Exception:
        return []


def _incident_text(inc: Dict[str, Any]) -> str:
    """Message returned to the agent (and shown in Hermes) when an action is blocked."""
    what = ", ".join(f'{f["title"]} ({f["preview"]})' for f in inc["findings"][:4])
    return (f'⛔ Yadro Guard blocked this action. The tool "{inc["tool"]}" was about to send {what} '
            f'to {inc["destination"]}. Incident {inc["id"]}. '
            "The user can choose in the Guard tab: Protect & send, Block & quarantine, or Allow once. "
            "Do not retry until the user has decided, and never try to work around this block.")


def check(tool_name: str, args: Any, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """The pre_tool_call decision. Returns None (allow) or a Hermes directive dict."""
    findings = detectors.scan_args(args, _known_secrets())
    if not findings:
        return None
    key = action_key(tool_name, findings)
    now = int(time.time())
    decisions = _read("decisions.json", {})
    d = decisions.get(key)
    if d and now - d.get("at", 0) <= (ALLOW_ONCE_TTL if d["choice"] == "allow" else DECISION_TTL):
        if d["choice"] == "allow":
            decisions.pop(key, None)          # one time only
            _write("decisions.json", decisions)
            _log_event(d.get("incident"), "allowed once")
            return None
        if d["choice"] == "protect":
            safe = detectors.redact_args(args, findings, _replacement_for(d.get("tokens", {})))
            _log_event(d.get("incident"), "sent with protection")
            return {"action": "modify", "args": safe if isinstance(safe, dict) else {"value": safe}}
        if d["choice"] == "block":
            return {"action": "block", "message": f'⛔ Yadro Guard: this action was blocked by the user '
                                                  f'(incident {d.get("incident")}). Do not retry it.'}
    inc = _new_incident(tool_name, args, findings, key, context or {})
    return {"action": "block", "message": _incident_text(inc)}


def _replacement_for(tokens: Dict[str, str]):
    def repl(f: detectors.Finding) -> str:
        return tokens.get(fingerprint(f.value)) or f"[{f.title} hidden by Yadro Guard]"
    return repl


def _new_incident(tool_name, args, findings, key, ctx) -> Dict[str, Any]:
    incidents = _read("incidents.json", [])
    for inc in incidents:                      # same pending action: don't spam duplicates
        if inc["key"] == key and inc["status"] == "pending":
            inc["attempts"] = inc.get("attempts", 1) + 1
            inc["last_at"] = int(time.time())
            _write("incidents.json", incidents)
            return inc
    import sys
    inc = {"id": "YG-" + secrets.token_hex(3).upper(), "key": key, "status": "pending",
           "at": int(time.time()), "last_at": int(time.time()), "attempts": 1,
           "tool": tool_name, "destination": _destination(tool_name, args),
           "agent": {k: str(ctx.get(k, ""))[:80] for k in ("session_id", "task_id", "turn_id", "tool_call_id")},
           "process": {"pid": os.getpid(), "name": Path(sys.argv[0] if sys.argv and sys.argv[0] else "python").name[:60]},
           "findings": _quarantine(findings),
           "events": [{"at": int(time.time()), "what": "blocked before execution"}]}
    incidents.insert(0, inc)
    _write("incidents.json", incidents[:MAX_INCIDENTS])
    return inc


def _log_event(incident_id: Optional[str], what: str) -> None:
    if not incident_id:
        return
    incidents = _read("incidents.json", [])
    for inc in incidents:
        if inc["id"] == incident_id:
            inc["events"].append({"at": int(time.time()), "what": what})
            break
    _write("incidents.json", incidents)


def list_incidents(limit: int = 100) -> List[Dict[str, Any]]:
    return [{k: v for k, v in inc.items() if k != "key"} for inc in _read("incidents.json", [])[:limit]]


CHOICES = {"protect": "Protect & send", "block": "Block & quarantine", "allow": "Allow once"}


def decide(incident_id: str, choice: str) -> Dict[str, Any]:
    """Apply the user's decision to a pending incident."""
    if choice not in CHOICES:
        return {"status": "error", "message": "Unknown choice."}
    incidents = _read("incidents.json", [])
    inc = next((i for i in incidents if i["id"] == incident_id), None)
    if not inc:
        return {"status": "error", "message": "Incident not found."}
    if inc["status"] != "pending":
        return {"status": "error", "message": "This incident has already been decided."}
    tokens = {f["fingerprint"]: f["token"] for f in inc["findings"] if f.get("token")}
    decisions = _read("decisions.json", {})
    decisions[inc["key"]] = {"choice": choice, "at": int(time.time()), "incident": inc["id"], "tokens": tokens}
    _write("decisions.json", decisions)
    inc["status"] = {"protect": "protected", "block": "quarantined", "allow": "allowed"}[choice]
    inc["decided_at"] = int(time.time())
    inc["events"].append({"at": int(time.time()), "what": f"user chose: {CHOICES[choice]}"})
    _write("incidents.json", incidents)
    hint = {"protect": "Ask the agent to try again: the secret will be replaced with a vault token.",
            "block": "The action stays blocked. The secret is kept encrypted in the vault.",
            "allow": "Ask the agent to try again within 15 minutes. It will be allowed one time."}[choice]
    return {"status": "ok", "incident": {k: v for k, v in inc.items() if k != "key"}, "next": hint}


def _quarantine(findings: List[detectors.Finding]) -> List[Dict[str, Any]]:
    """Store every found secret encrypted in the vault (deduplicated by fingerprint).
    The journal only ever keeps the token, never the value."""
    out = []
    try:
        from .. import vault
    except Exception:
        vault = None
    for f in findings:
        item = {**f.public(), "fingerprint": fingerprint(f.value)}
        if vault is not None:
            try:
                item["token"] = vault.положить_уникально(f.value, LABEL_RU.get(f.label, "УчетныеДанные"),
                                                         fingerprint(f.value), f.title)
            except Exception:
                item["token"] = None    # no encryption available: masked placeholder will be used
        out.append(item)
    return out
