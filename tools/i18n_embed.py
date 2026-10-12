# -*- coding: utf-8 -*-
"""Embed the Russian UI dictionary into the Guard page (between I18N_RU markers).

    python tools/i18n_embed.py tools/i18n/ru.json

Keys with numbers are also stored with every number replaced by '#', so texts like
"Exposure score 86/100" translate too. Re-run tools/build_desktop_plugin.py afterwards.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "integrations" / "hermes" / "yadro-guard" / "dashboard" / "dist" / "index.js"
BEGIN, END = "/* I18N_RU_BEGIN */", "/* I18N_RU_END */"


def main() -> int:
    d = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    over = Path(sys.argv[1]).with_name("ru_overrides.json")      # hand-picked wording wins
    if over.exists():
        d.update(json.loads(over.read_text(encoding="utf-8")))
    out = {}
    for k, v in d.items():
        if not (isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip()):
            continue
        out[k] = v
        if re.search(r"\d", k) and len(re.findall(r"\d+", k)) == len(re.findall(r"\d+", v)):
            out.setdefault(re.sub(r"\d+", "#", k), re.sub(r"\d+", "#", v))
    js = PAGE.read_text(encoding="utf-8")
    i, j = js.index(BEGIN) + len(BEGIN), js.index(END)
    body = "\n  const I18N_RU = " + json.dumps(out, ensure_ascii=False, indent=0, sort_keys=True) \
        .replace("\n", "\n    ") + ";\n  "
    PAGE.write_text(js[:i] + body + js[j:], encoding="utf-8", newline="\n")
    print(f"embedded {len(out)} strings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
