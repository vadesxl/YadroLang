# -*- coding: utf-8 -*-
"""Run many helper jobs in parallel (each job asks glm + deepseek).

    python tools/helpers/swarm.py tools/helpers/jobs_release.json [--parallel 6] [--wait] [--redo]

--wait: first wait (up to 6 h) until the gateway really answers; --redo: rerun jobs that already have answers.

jobs file: [{"id": "rt_actions", "role": "redteam", "files": ["src/runtime/actions.py"], "question": "..."}]
Answers: tools/helpers/out/<id>_<model>.md, progress: tools/helpers/out/swarm.log.
All safety rules of ask.py apply (secret scan before sending, repo files only).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"


def run(job: dict) -> str:
    started = time.time()
    cmd = [sys.executable, str(HERE / "ask.py"), "--role", job.get("role", "reviewer"),
           "--model", job.get("model", "both"), "--question", job["question"],
           "--out", str(OUT / f"{job['id']}.md"), "--files", *job.get("files", [])]
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=900)
        res = (r.stdout + r.stderr).strip().replace("\n", " | ")
    except subprocess.TimeoutExpired:
        res = "TIMEOUT"
    line = f"{time.strftime('%H:%M:%S')} {job['id']} {int(time.time() - started)}s {res}"
    with open(OUT / "swarm.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return line


def gateway_up() -> bool:
    """Real (uncached) request: the gateway serves cached answers even when inference is down,
    so a fixed 'hi' ping can lie. A unique text forces a real model call."""
    sys.path.insert(0, str(HERE))
    import ask
    try:
        ask.call("deepseek", "Reply with one word.", f"Say ok. nonce {time.time_ns()}")
        return True
    except SystemExit:
        return False


def done(job: dict) -> bool:
    return any(OUT.glob(f"{job['id']}_*.md"))


def main() -> int:
    jobs = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    par = int(sys.argv[sys.argv.index("--parallel") + 1]) if "--parallel" in sys.argv else 6
    OUT.mkdir(exist_ok=True)
    jobs = [j for j in jobs if "--redo" in sys.argv or not done(j)]     # keep answers we already have
    if "--wait" in sys.argv:                                            # wait up to 6 h for the gateway
        for _ in range(72):
            if gateway_up():
                break
            with open(OUT / "swarm.log", "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%H:%M:%S')} gateway down (HTTP 502), retry in 5 min\n")
            time.sleep(300)
    with open(OUT / "swarm.log", "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} START {len(jobs)} jobs, parallel={par}\n")
    with ThreadPoolExecutor(max_workers=par) as pool:
        for line in pool.map(run, jobs):
            print(line, flush=True)
    with open(OUT / "swarm.log", "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} DONE\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
