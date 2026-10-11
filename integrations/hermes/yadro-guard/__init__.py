"""Yadro Guard runtime hook for Hermes Agent.

Registers a ``pre_tool_call`` hook: before ANY agent tool runs (terminal,
browser, HTTP, file writes, MCP tools, messaging ...), its arguments are scanned
for secrets and sensitive data. A finding blocks the action and opens an
incident in the Guard tab, where the user chooses:
Protect & send / Block & quarantine / Allow once.

Fail-closed: if the guard itself fails, the tool call is BLOCKED, never silently
allowed. (Hermes also blocks on hook timeout for pre_tool_call.)
Kill switch for emergencies: environment variable YADRO_GUARD_DISABLE=1.

The detectors and policy are pure Python (no llvmlite), so they are imported
in-process from the engine folder configured in config.json.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)
_PLUGIN_DIR = Path(__file__).resolve().parent
_policy = None
_load_error = ""

# Read-only / internal tools that cannot exfiltrate data by themselves.
# Everything NOT listed here is scanned (unknown tools are guarded by default).
_SKIP_TOOLS = frozenset({"read_file", "list_dir", "search_files", "glob", "todo_write", "clarify"})


def _load_policy():
    global _policy, _load_error
    if _policy is not None:
        return _policy
    try:
        from .engine_loader import load_policy
        _policy = load_policy()
    except Exception as exc:  # pragma: no cover - reported via fail-closed message
        _load_error = f"{type(exc).__name__}: {exc}"[:200]
        logger.error("yadro-guard: cannot load runtime policy: %s", _load_error)
    return _policy


def _on_pre_tool_call(tool_name: str = "", args: Any = None, **ctx: Any) -> Optional[dict]:
    if os.environ.get("YADRO_GUARD_DISABLE", "").lower() in {"1", "true", "yes"}:
        return None
    if tool_name in _SKIP_TOOLS:
        return None
    policy = _load_policy()
    if policy is None:
        return {"action": "block",
                "message": "⛔ Yadro Guard is installed but its engine could not be loaded, so this action "
                           f"was blocked for safety. Reinstall the plugin. ({_load_error})"}
    try:
        return policy.check(tool_name, args, ctx)
    except Exception as exc:
        logger.exception("yadro-guard: check failed")
        return {"action": "block",
                "message": f"⛔ Yadro Guard could not check this action ({type(exc).__name__}), "
                           "so it was blocked for safety."}


def register(ctx) -> None:
    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
