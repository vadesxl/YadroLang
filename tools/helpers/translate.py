# -*- coding: utf-8 -*-
"""Translate UI strings with helper models, in small chunks, spread over all helpers.

    python tools/helpers/translate.py tools/helpers/out/strings_ui.txt tools/helpers/out/ru.json

Lines already in the output JSON are skipped, so it can be re-run after failures.
"""
from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ask  # noqa: E402

SYSTEM = ("You translate English UI strings of a Windows security app into short, natural Russian for "
          "non-technical users. Keep product names, commands, code, flags, ports, file names and env "
          "variables unchanged (e.g. --host 127.0.0.1, OLLAMA_HOST, SMB, RDP). Do not think aloud. "
          "Answer with ONE JSON object only: {\"<english>\": \"<russian>\", ...}.")
CHUNK = 40


def parse(text: str) -> dict:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        return {}
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return {}
    return {k: v for k, v in d.items() if isinstance(k, str) and isinstance(v, str) and v.strip()}


def main() -> int:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    lines = [l.strip() for l in src.read_text(encoding="utf-8-sig").splitlines() if l.strip()]
    done = json.loads(dst.read_text(encoding="utf-8")) if dst.exists() else {}
    todo = [l for l in lines if l not in done]
    chunks = [todo[i:i + CHUNK] for i in range(0, len(todo), CHUNK)]
    team = [p for p in ask.TEAM + ask.TEAM2 if p in ask.available() and not p.startswith("minimax")]

    def work(i_chunk):
        i, chunk = i_chunk
        for attempt in range(len(team)):
            provider = team[(i + attempt) % len(team)]
            try:
                got = parse(ask.call(provider, SYSTEM, json.dumps(chunk, ensure_ascii=False)))
            except SystemExit:
                continue
            got = {k: v for k, v in got.items() if k in chunk}
            if len(got) >= len(chunk) * 0.8:
                return got
        return {}

    with ThreadPoolExecutor(max_workers=max(1, len(team))) as pool:
        for got in pool.map(work, enumerate(chunks)):
            done.update(got)
            dst.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"translated {len(done)}/{len(lines)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
