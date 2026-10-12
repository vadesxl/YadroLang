# -*- coding: utf-8 -*-
"""Collect every user-visible English string of the Guard UI and engine messages.

    python tools/i18n_extract.py > tools/helpers/out/strings_all.txt

JS: every "..." literal that looks like human text (has a space or starts with a capital
letter and has lowercase letters), minus code-ish strings. Python: user-facing strings
from the runtime knowledge base and API error messages.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "integrations" / "hermes" / "yadro-guard" / "dashboard" / "dist" / "index.js"
PY = ["src/runtime/services.py", "src/runtime/actions.py", "src/runtime/exposure.py", "src/runtime/remedy.py",
      "src/runtime/policy.py", "src/runtime/detectors.py", "src/runtime/crypto_detect.py",
      "integrations/hermes/yadro-guard/dashboard/plugin_api.py"]
CODEISH = re.compile(r"^(yg-|/|\.|#|[a-z_]+$|[A-Z_]+$|application/|Content-Type|X-Yadro|POST|use strict)|[{}<>=;]|\\u")


def human(s: str) -> bool:
    s = s.strip()
    if len(s) < 2 or CODEISH.search(s) or not re.search(r"[a-z]{2}", s):
        return False
    return " " in s or s[0].isupper()


def main() -> int:
    seen = []
    js = JS.read_text(encoding="utf-8")
    js = js[js.index("/* I18N_RU_END */"):]                     # skip the embedded dictionary
    for m in re.finditer(r'"((?:[^"\\\n]|\\.)*)"', js):
        s = m.group(1).replace('\\"', '"')
        if human(s) and s not in seen:
            seen.append(s)
    for f in PY:
        t = (ROOT / f).read_text(encoding="utf-8")
        t = re.sub(r'"""[\s\S]*?"""', "", t)                         # no docstrings
        t = "\n".join(l for l in t.splitlines() if not l.lstrip().startswith("#"))
        for m in re.finditer(r'(?<![\w])f?"((?:[^"\\\n]|\\.){3,240})"', t):
            s = m.group(1)
            if "{" in s or not human(s) or s.startswith(("Get-", "New-", "Remove-", "Set-", "Stop-")):
                continue
            if s not in seen:
                seen.append(s)
    sys.stdout.write("\n".join(seen) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
