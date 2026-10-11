"""Load the Yadro Guard engine package under a UNIQUE module name.

Hermes runs many plugins in one Python process. Importing the engine as a
generic ``src`` package could collide with another package of the same name or
pick up the wrong folder from the working directory. We therefore register the
engine's ``src`` folder as ``yadro_guard_engine`` and only use relative imports
inside ``src/runtime`` and ``src/vault.py`` (pure Python, no llvmlite).
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from pathlib import Path

PACKAGE = "yadro_guard_engine"
_PLUGIN_DIR = Path(__file__).resolve().parent


def engine_home() -> Path | None:
    try:
        home = Path(json.loads((_PLUGIN_DIR / "config.json").read_text(encoding="utf-8"))["engine_home"])
        return home if (home / "src" / "runtime" / "policy.py").is_file() else None
    except Exception:
        return None


def load_policy():
    """Return the engine's runtime.policy module. Raises on failure (callers fail closed)."""
    if f"{PACKAGE}.runtime.policy" in sys.modules:
        return sys.modules[f"{PACKAGE}.runtime.policy"]
    home = engine_home()
    if home is None:
        raise RuntimeError("engine folder not configured or missing")
    if PACKAGE not in sys.modules:
        init = home / "src" / "__init__.py"
        spec = importlib.util.spec_from_file_location(PACKAGE, init, submodule_search_locations=[str(home / "src")])
        module = importlib.util.module_from_spec(spec)
        sys.modules[PACKAGE] = module
        spec.loader.exec_module(module)
    return importlib.import_module(f"{PACKAGE}.runtime.policy")
