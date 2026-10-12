# -*- coding: utf-8 -*-
"""Sync the Guard product into the English mirror repo (vadesxl/YadroLang-English).

    python tools/sync_en.py collect <out_dir>          # Russian names/texts that need a translation
    python tools/sync_en.py apply <english_repo_dir>   # copy + translate, using tools/i18n/en_*.json

The mirror is a pure function of this repo: run it again after every change.
- COPY: files that are already English (runtime engine, Hermes plugin, UI, tools).
- TRANSLATE: Python files with Russian identifiers/comments (vault, policy, tests), token by
  token (tokenize): structure and line numbers stay identical. On-disk vault label values are
  NOT translated, so vault files stay compatible between both repos. Test data strings stay.
- The YadroLang compiler and code checker are not synced here: the English repo has its own
  translated compiler. Tests that need the checker skip themselves.
"""
from __future__ import annotations

import io
import json
import re
import shutil
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "tools" / "i18n"
CYR = re.compile(r"[А-Яа-яЁё]")
KEEP_VALUES = {"ПДн", "Финансы", "Здоровье", "УчетныеДанные", "Локация"}   # on-disk vault labels

COPY = ["src/runtime/__init__.py", "src/runtime/actions.py", "src/runtime/crypto_detect.py",
        "src/runtime/detectors.py", "src/runtime/exposure.py", "src/runtime/remedy.py",
        "src/runtime/services.py", "src/runtime/data/bip39_english.txt",
        "integrations/hermes/yadro-guard/__init__.py", "integrations/hermes/yadro-guard/engine_loader.py",
        "integrations/hermes/yadro-guard/plugin.yaml", "integrations/hermes/yadro-guard/dashboard/manifest.json",
        "integrations/hermes/yadro-guard/dashboard/plugin_api.py",
        "integrations/hermes/yadro-guard/dashboard/dist/index.js",
        "integrations/hermes/yadro-guard/desktop/plugin.js",
        "tools/build_desktop_plugin.py", "tools/i18n_embed.py", "tools/i18n_extract.py",
        "tools/i18n/ru.json", "tools/i18n/ru_overrides.json", "tests/js/render_guard_page.mjs"]
TRANSLATE_PY = ["src/vault.py", "src/runtime/policy.py",
                "tests/test_runtime_actions.py", "tests/test_runtime_detectors.py", "tests/test_runtime_policy.py",
                "tests/test_crypto_detect.py", "tests/test_exposure.py", "tests/test_hermes_runtime_hook.py",
                "tests/test_hermes_plugin.py", "tests/test_vault_and_api.py"]
TRANSLATE_LINES = ["integrations/hermes/install.ps1", "integrations/hermes/yadro-guard/dashboard/dist/style.css"]
STRING_RX = re.compile(r"^([rRbBuUfF]*)('''|\"\"\"|'|\")(.*)\2$", re.S)
SKIP = (tokenize.NL, tokenize.COMMENT)


def _items(rel: str, text: str):
    """Yield (kind, start, end, russian, wrap) for every token that needs a translation."""
    toks = list(tokenize.generate_tokens(io.StringIO(text).readline))
    is_test = rel.startswith("tests/")
    for i, t in enumerate(toks):
        if not CYR.search(t.string):
            continue
        if t.type == tokenize.NAME:
            yield "names", t.start, t.end, t.string, None
        elif t.type == tokenize.COMMENT:
            yield "text", t.start, t.end, t.string, None
        elif t.type == tokenize.STRING:
            m = STRING_RX.match(t.string)
            if not m or m.group(3) in KEEP_VALUES:
                continue
            prev = next((x for x in reversed(toks[:i]) if x.type not in SKIP), None)
            nxt = next((x for x in toks[i + 1:] if x.type not in SKIP), None)
            docstring = (prev is None or prev.type in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT,
                                                       tokenize.ENCODING)) \
                and nxt is not None and nxt.type in (tokenize.NEWLINE, tokenize.ENDMARKER)
            if docstring or not is_test:                      # test data strings stay as they are
                yield "text", t.start, t.end, m.group(3), (m.group(1), m.group(2))
        elif t.type == getattr(tokenize, "FSTRING_MIDDLE", -1) and not is_test:
            yield "text", t.start, t.end, t.string, None


def collect(out: Path) -> None:
    names, texts = [], []
    for rel in TRANSLATE_PY:
        for kind, _s, _e, ru, _w in _items(rel, (ROOT / rel).read_text(encoding="utf-8")):
            (names if kind == "names" else texts).append(ru)
    for rel in TRANSLATE_LINES:
        texts += [l for l in (ROOT / rel).read_text(encoding="utf-8").splitlines() if CYR.search(l)]
    out.mkdir(parents=True, exist_ok=True)
    for name, data in (("names", names), ("text", texts)):
        uniq = list(dict.fromkeys(x.replace("\n", "\\n") for x in data))
        (out / f"en_{name}_todo.txt").write_text("\n".join(uniq) + "\n", encoding="utf-8")
        print(f"{name}: {len(uniq)}")


def _apply_edits(text: str, edits) -> str:
    offs, n = [], 0
    for l in text.splitlines(keepends=True):
        offs.append(n)
        n += len(l)
    for (sr, sc), (er, ec), new in sorted(edits, key=lambda e: e[0], reverse=True):
        a, b = offs[sr - 1] + sc, offs[er - 1] + ec
        text = text[:a] + new + text[b:]
    return text


def translate_py(rel: str, names: dict, texts: dict) -> str:
    text = (ROOT / rel).read_text(encoding="utf-8")
    edits, missing = [], []
    for kind, s, e, ru, wrap in _items(rel, text):
        table = names if kind == "names" else texts
        en = table.get(ru) or table.get(ru.replace("\n", "\\n"))
        if not en:
            missing.append(ru[:60])
            continue
        en = en.replace("\\n", "\n")
        if wrap:
            q = wrap[1]
            if len(q) == 1:
                en = en.replace("\n", "\\n").replace(q, "\\" + q)
            en = wrap[0] + q + en + q
        edits.append((s, e, en))
    if missing:
        raise SystemExit(f"{rel}: no translation for {len(missing)} items, e.g. {missing[:3]}")
    out = _apply_edits(text, edits)
    compile(out, rel, "exec")                                     # must still be valid Python
    return out


def apply(dst: Path) -> None:
    names = json.loads((I18N / "en_names.json").read_text(encoding="utf-8"))
    texts = json.loads((I18N / "en_text.json").read_text(encoding="utf-8"))
    bad = [v for v in names.values() if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", v)]
    if bad or len(set(names.values())) != len(names):
        raise SystemExit(f"bad or duplicate English identifiers: {bad[:5]}")
    written = []
    for rel in COPY:
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, dst / rel)
        written.append(rel)
    for rel in TRANSLATE_PY:
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        (dst / rel).write_text(translate_py(rel, names, texts), encoding="utf-8", newline="\n")
        written.append(rel)
    for rel in TRANSLATE_LINES:
        out = [texts.get(l, l) for l in (ROOT / rel).read_text(encoding="utf-8").splitlines()]
        left = [l for l in out if CYR.search(l)]
        if left:
            raise SystemExit(f"{rel}: untranslated lines: {left[:2]}")
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        (dst / rel).write_text("\n".join(out) + "\n", encoding="utf-8-sig" if rel.endswith(".ps1") else "utf-8",
                               newline="\n")
        written.append(rel)
    (dst / "SYNC_MANIFEST.json").write_text(json.dumps({"source": "vadesxl/YadroLang", "files": written},
                                                       indent=1), encoding="utf-8")
    print(f"synced {len(written)} files into {dst}")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("collect", "apply"):
        raise SystemExit(__doc__)
    (collect if sys.argv[1] == "collect" else apply)(Path(sys.argv[2]))
