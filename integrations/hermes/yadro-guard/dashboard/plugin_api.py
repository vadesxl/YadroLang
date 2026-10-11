"""Yadro Guard — backend плагина для дашборда Hermes.

Монтируется Hermes по адресу /api/plugins/yadro-guard/.
Движок запускается ОТДЕЛЬНЫМ процессом (свой Python с llvmlite), поэтому:
- Hermes не зависит от зависимостей движка;
- сбой/зависание движка не роняет Hermes (жёсткий таймаут);
- наружу отдаётся только JSON движка.

Безопасность:
- только файлы .яд/.yad/.yd (проверяет и движок);
- секреты из сейфа через веб НИКОГДА не выдаются — только метаданные;
- история сканов хранит лишь путь, вердикт и время.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

try:
    from fastapi import APIRouter
    from pydantic import BaseModel
except Exception:  # pragma: no cover - для локальных тестов без FastAPI
    class APIRouter:  # type: ignore
        def get(self, *_a, **_k):
            return lambda fn: fn

        def post(self, *_a, **_k):
            return lambda fn: fn

    class BaseModel:  # type: ignore
        def __init__(self, **kw):
            self.__dict__.update(kw)

router = APIRouter()

PLUGIN_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = PLUGIN_DIR / "config.json"
HISTORY_FILE = PLUGIN_DIR / "history.json"
TIMEOUT_S = 60
ALLOWED = {".яд", ".yad", ".yd"}
MAX_HISTORY = 30


def _config() -> Dict[str, str]:
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _engine(*args: str) -> Dict[str, Any]:
    cfg = _config()
    home, python = cfg.get("engine_home"), cfg.get("python")
    if not home or not python:
        return {"status": "error", "message": "плагин не настроен: запустите install.ps1"}
    env = {"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    import os
    full_env = {**os.environ, **env}
    try:
        res = subprocess.run([python, "-m", *args], cwd=home, env=full_env, capture_output=True,
                             text=True, encoding="utf-8", timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": f"движок не ответил за {TIMEOUT_S}s"}
    except OSError as e:
        return {"status": "error", "message": f"не удалось запустить движок: {e.strerror}"}
    try:
        return json.loads(res.stdout.strip().splitlines()[-1]) if res.stdout.strip() else \
            {"status": "error", "message": "движок вернул пустой ответ"}
    except (json.JSONDecodeError, IndexError):
        return {"status": "error", "message": "движок вернул не-JSON"}


def _check_path(path: str) -> str | None:
    p = Path(path)
    if not p.is_absolute():
        return "укажите полный путь к файлу"
    if p.suffix.lower() not in ALLOWED:
        return f"поддерживаются только {sorted(ALLOWED)}"
    return None


def _history() -> list:
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _remember(path: str, result: Dict[str, Any]) -> None:
    item = {"path": path, "status": result.get("status"), "code": result.get("code"),
            "labels": [l.get("label") for l in result.get("labels", [])], "at": int(time.time())}
    items = [h for h in _history() if h.get("path") != path]
    items.insert(0, item)
    HISTORY_FILE.write_text(json.dumps(items[:MAX_HISTORY], ensure_ascii=False), encoding="utf-8")


class PathBody(BaseModel):
    path: str


async def _run(cmd: str, path: str) -> Dict[str, Any]:
    err = _check_path(path)
    if err:
        return {"status": "error", "message": err}
    return await asyncio.to_thread(_engine, "src.guard_api", cmd, path)


@router.post("/scan")
async def scan(body: "PathBody") -> Dict[str, Any]:
    result = await _run("scan", body.path)
    if result.get("status") in ("ok", "leak"):
        _remember(body.path, result)
    return result


@router.post("/fix")
async def fix(body: "PathBody") -> Dict[str, Any]:
    return await _run("fix", body.path)


@router.post("/report")
async def report(body: "PathBody") -> Dict[str, Any]:
    return await _run("report", body.path)


@router.get("/history")
async def history() -> Dict[str, Any]:
    return {"items": _history()}


@router.get("/vault")
async def vault() -> Dict[str, Any]:
    """Только метаданные сейфа (токен, метка, время). Значения не выдаются."""
    cfg = _config()
    if not cfg.get("engine_home"):
        return {"status": "error", "message": "плагин не настроен"}

    def _list():
        import os
        try:
            res = subprocess.run([cfg["python"], "-m", "src.vault", "list"], cwd=cfg["engine_home"],
                                 env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
                                 capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT_S)
            return {"status": "ok", "items": json.loads(res.stdout or "[]")}
        except Exception:
            return {"status": "error", "message": "сейф недоступен"}

    return await asyncio.to_thread(_list)


@router.get("/health")
async def health() -> Dict[str, Any]:
    cfg = _config()
    ok = bool(cfg.get("engine_home")) and Path(cfg.get("engine_home", "")).is_dir()
    return {"status": "ok" if ok else "error", "configured": ok}
