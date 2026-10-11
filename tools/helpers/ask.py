# -*- coding: utf-8 -*-
"""Conductor -> helper models. The conductor (Cline) calls cheaper/free models for
independent review, second opinions, drafts and test ideas.

    python tools/helpers/ask.py --list
    python tools/helpers/ask.py --role reviewer --files src/runtime/policy.py --question "..."
    python tools/helpers/ask.py --role redteam --model openrouter --files a.py b.py --out review.md

Providers (first available is used unless --model is given):
    openrouter   OPENROUTER_API_KEY   free models with the ":free" suffix
    gemini       GEMINI_API_KEY       Google AI Studio free tier
    groq         GROQ_API_KEY         fast free tier
    local        LOCAL_LLM_URL (+ LOCAL_LLM_KEY)  OpenAI-compatible server, e.g. llama-server

Safety rules (enforced, not just documented):
- Files are scanned with our own secret detectors BEFORE sending. Any finding aborts.
- Only files inside this repository can be sent; .env, vault and key files never.
- API keys come from environment variables only and are never printed.
- Answers are written to tools/helpers/out/ (git-ignored) for the conductor to read.
Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "out"
MAX_CHARS = 40_000      # big prompts time out on gateways (HTTP 524); send focused files
TIMEOUT = 240
FORBIDDEN = {".env", "vault.json", "decisions.json", "incidents.json", "config.json"}
FORBIDDEN_SUFFIX = {".pem", ".key", ".pfx", ".p12", ".kdbx", ".dat"}

ROLES = {
    "reviewer": ("You are a senior security engineer doing an independent code review. Be concrete and "
                 "skeptical. List real bugs and security weaknesses with file/line references, ordered by "
                 "severity. Say explicitly what is fine. No flattery, no generic advice. Max 600 words."),
    "redteam": ("You are an attacker trying to bypass this security tool. List concrete bypasses: inputs, "
                "encodings, tool-call shapes or sequences that would get a secret or a risky action past it. "
                "For each, give a minimal example input and why it works. Max 600 words."),
    "architect": ("You are a product security architect. Assess the design and threat model: what threats are "
                  "missing, which assumptions are wrong, what to build next and why. Be direct. Max 600 words."),
    "tester": ("You write test cases. Produce concrete unit-test inputs (positive and negative) that would expose "
               "false negatives and false positives in the code shown. Output a compact list. Max 600 words."),
}

_DAHL_URL = "https://inference.dahl.global/v1/chat/completions"
TEAM = ("glm", "deepseek", "minimax")   # helper models on the Dahl key; --model both/all asks every one
TEAM2 = ("glm2", "deepseek2", "minimax2")  # same models on the second key; used by --model all
PROVIDERS = {
    "glm": {"env": "DAHL_API_KEY", "url": _DAHL_URL,
            "model": os.environ.get("DAHL_GLM_MODEL", "zai-org/GLM-5.3-Flash")},
    "deepseek": {"env": "DAHL_API_KEY", "url": _DAHL_URL,
                 "model": os.environ.get("DAHL_DEEPSEEK_MODEL", "deepseek-ai/DeepSeek-V4-Flash-0731")},
    "minimax": {"env": "DAHL_API_KEY", "url": _DAHL_URL,
                "model": os.environ.get("DAHL_MINIMAX_MODEL", "MiniMaxAI/MiniMax-M2.7")},
    # same three models on the SECOND Dahl key (own concurrency limit -> twice the helpers)
    "glm2": {"env": "DAHL_API_KEY_2", "url": _DAHL_URL,
             "model": os.environ.get("DAHL_GLM_MODEL", "zai-org/GLM-5.3-Flash")},
    "deepseek2": {"env": "DAHL_API_KEY_2", "url": _DAHL_URL,
                  "model": os.environ.get("DAHL_DEEPSEEK_MODEL", "deepseek-ai/DeepSeek-V4-Flash-0731")},
    "minimax2": {"env": "DAHL_API_KEY_2", "url": _DAHL_URL,
                 "model": os.environ.get("DAHL_MINIMAX_MODEL", "MiniMaxAI/MiniMax-M2.7")},
    "openrouter": {"env": "OPENROUTER_API_KEY", "url": "https://openrouter.ai/api/v1/chat/completions",
                   "model": os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free")},
    "gemini": {"env": "GEMINI_API_KEY",
               "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
               "model": os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")},
    "groq": {"env": "GROQ_API_KEY", "url": "https://api.groq.com/openai/v1/chat/completions",
             "model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")},
    "local": {"env": "LOCAL_LLM_KEY", "url": (os.environ.get("LOCAL_LLM_URL", "http://127.0.0.1:18434/v1").rstrip("/")
                                              + "/chat/completions"),
              "model": os.environ.get("LOCAL_LLM_MODEL", "local"), "optional_key": True},
}


def _env(name: str) -> str:
    v = os.environ.get(name)
    if v:
        return v
    if os.name == "nt":  # user-level variables set via SetEnvironmentVariable(..., "User")
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                return winreg.QueryValueEx(k, name)[0]
        except OSError:
            return ""
    return ""


def available():
    out = []
    for name, p in PROVIDERS.items():
        if _env(p["env"]) or (p.get("optional_key") and _env("LOCAL_LLM_URL")):
            out.append(name)
    return out


def _load_detectors():
    sys.path.insert(0, str(ROOT))
    from src.runtime import detectors  # noqa: E402
    return detectors


def collect(files) -> str:
    """Read repo files for the prompt. Refuses secrets-bearing files and any detector hit."""
    det = _load_detectors()
    parts, total = [], 0
    for f in files:
        p = (ROOT / f).resolve() if not Path(f).is_absolute() else Path(f).resolve()
        if ROOT not in p.parents and p != ROOT:
            raise SystemExit(f"refused: {f} is outside the repository")
        if p.name in FORBIDDEN or p.suffix.lower() in FORBIDDEN_SUFFIX:
            raise SystemExit(f"refused: {p.name} may contain secrets")
        text = p.read_text(encoding="utf-8", errors="replace")
        hits = [h for h in det.scan_text(text) if h.confidence in ("high", "certain")]
        if hits:
            raise SystemExit(f"refused: {f} contains what looks like a secret ({hits[0].title}, {hits[0].preview})")
        chunk = f"\n\n===== FILE: {p.relative_to(ROOT).as_posix()} =====\n{text}"
        total += len(chunk)
        if total > MAX_CHARS:
            raise SystemExit(f"refused: prompt too large ({total} chars > {MAX_CHARS}); send fewer files")
        parts.append(chunk)
    return "".join(parts)


def call(provider: str, system: str, user: str) -> str:
    p = PROVIDERS[provider]
    headers = {"Content-Type": "application/json"}
    key = _env(p["env"])
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if provider == "openrouter":
        headers["X-Title"] = "Yadro Guard review"
    body = json.dumps({"model": p["model"], "temperature": 0.2, "max_tokens": 2500,
                       "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
    last = ""
    for attempt in range(4):                       # gateways (524/502/503/429, resets) are often transient
        req = urllib.request.Request(p["url"], data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                data = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:200]}"
            if e.code in (429, 502, 503, 504, 524) and attempt < 3:
                time.sleep(10 * (attempt + 1))
                continue
            raise SystemExit(f"{provider} {last}")
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            last = f"unreachable: {type(e).__name__}"
            if attempt < 3:
                time.sleep(10 * (attempt + 1))
                continue
            raise SystemExit(f"{provider} {last}")
        try:
            msg = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            raise SystemExit(f"{provider}: unexpected answer shape")
        u = data.get("usage") or {}
        try:  # proof that the helper really answered + token accounting
            OUT.mkdir(exist_ok=True)
            with open(OUT / "usage.log", "a", encoding="utf-8") as f:
                f.write(f"{int(time.time())} {provider} {data.get('model', p['model'])} "
                        f"in={u.get('prompt_tokens')} out={u.get('completion_tokens')} id={data.get('id')}\n")
        except OSError:
            pass
        content = (msg.get("content") or "").strip()
        if not content:                                # some reasoning models put text elsewhere
            content = (msg.get("reasoning_content") or msg.get("reasoning") or "").strip()
        if content:
            return content
        last = "empty answer"
        time.sleep(3)
    raise SystemExit(f"{provider} {last}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--role", choices=sorted(ROLES), default="reviewer")
    ap.add_argument("--model", choices=sorted(PROVIDERS) + ["both", "all"],
                    help="'both' asks glm and deepseek in parallel for two independent opinions")
    ap.add_argument("--ping", action="store_true", help="tiny request to check that helpers answer")
    ap.add_argument("--files", nargs="*", default=[])
    ap.add_argument("--question", default="Review this code.")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.list:
        av = available()
        for name, p in PROVIDERS.items():
            print(f"{name:11} {'READY' if name in av else 'no key':7} model={p['model']}  ({p['env']})")
        return 0
    if a.ping:
        targets = [p for p in (TEAM if a.model in (None, "both", "all") else [a.model]) if p in available()]
        if not targets:
            raise SystemExit("no helper configured")
        for p in targets:
            t = time.time()
            try:
                txt = call(p, "Answer with one short word.", "Reply with: ready")
                print(f"{p:9} OK   {int((time.time() - t) * 1000)} ms  model={PROVIDERS[p]['model']}  answer={txt.strip()[:30]!r}")
            except SystemExit as e:
                print(f"{p:9} FAIL {e}")
        return 0
    if a.model in ("both", "all"):
        providers = [p for p in (TEAM + TEAM2 if a.model == "all" else TEAM) if p in available()]
    else:
        providers = [a.model or (available() or [None])[0]]
    if not providers or not providers[0]:
        raise SystemExit("no helper model configured: run tools/helpers/set_key.ps1")
    prompt = a.question + collect(a.files)
    OUT.mkdir(exist_ok=True)

    def run(provider):
        started = time.time()
        try:
            answer = call(provider, ROLES[a.role], prompt)
        except SystemExit as e:
            return f"FAIL {provider}: {e}"
        out = (Path(a.out).with_name(f"{Path(a.out).stem}_{provider}.md") if a.out and len(providers) > 1
               else Path(a.out) if a.out else OUT / f"{int(started)}_{a.role}_{provider}.md")
        out.write_text(f"# {a.role} via {provider} ({PROVIDERS[provider]['model']})\n\n"
                       f"Question: {a.question}\nFiles: {', '.join(a.files) or '-'}\n\n{answer}\n", encoding="utf-8")
        return f"ok {provider} {int(time.time() - started)}s -> {out}"

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=len(providers)) as pool:
        for line in pool.map(run, providers):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
