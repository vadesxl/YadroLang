# HANDOFF — read this first in a new session

Owner: vadesxl (Ukrainian; answer in Russian, short, honest). Conductor: Cline. Helpers: GLM-5.3 + DeepSeek V4 via Dahl.

## Where the work is
- Worktree: `E:\загрузки\.gemini\antigravity\scratch\wt-ru-security`, branch `security/ethics-gaps`
  (based on `origin/agent/semantic-analysis`). **Not pushed yet** — push only with owner's OK, never to main.
- Cleaned old branch: `compiler-fix-working` in `...\scratch\YadroLang`. Private files backup: `...\scratch\backups\yadro_private_2026-10-11`.
- English mirror repo: `...\scratch\YadroLang-English-repo` (52 commits behind RU, needs sync later).
- Installed Hermes plugin: `%LOCALAPPDATA%\hermes\plugins\yadro-guard` (re-install: `powershell -ExecutionPolicy Bypass -File integrations\hermes\install.ps1`).
- Tests: `$env:PYTHONUTF8='1'; python tests\run_tests.py` → 206 tests, only `test_native_link_run` fails (no C compiler on this PC).

## What exists (product "Yadro Guard", final name not chosen; candidate "Oberig")
- `src/runtime/`: detectors (API keys, cards, IBAN, PEM, JWT, crypto seed/WIF/xprv/Solana/keystore),
  actions (bind 0.0.0.0, tunnels, firewall, rm -rf, DROP, force push, curl|bash), policy (incidents:
  Protect & send / Block & quarantine / Allow once; journal never stores raw values), exposure (port scan).
- `src/vault.py`: DPAPI vault, ASCII tokens `yg_tok_<Label>_<hex>`.
- `integrations/hermes/yadro-guard/`: pre_tool_call hook (fail-closed) + English dashboard tab
  (Live protection, Exposure, Check code, Vault). Engine loaded as package `yadro_guard_engine`.
- `src/guard_api.py`, `src/localize.py`, `src/report_html.py`, `src/autofix.py`: YadroLang code check (RU/EN).
- `tools/helpers/ask.py`: helper models. Key: env `DAHL_API_KEY` (set via `tools/helpers/set_key.ps1`).
  Helpers take 1-4 min → always run them in background (`Start-Process ... -RedirectStandardOutput`).
  Token usage proof: `tools/helpers/out/usage.log`.

## Next steps (in order)
1. Push branch + PR (needs owner's "пушь").
2. Disk audit "what a stealer would find" (seed in txt, wallet.dat, wallet folders, MetaMask/Phantom).
3. `THREAT_MODEL_PRODUCT.md` with honest limits (Guard ≠ antivirus vs a running stealer).
4. 17 open analyzer gaps (Check code), then sync English repo.

## Rules
- Never print or commit secrets. Old GitHub token and Gemini key were leaked earlier and rotated.
- Commit after every step; report to owner after every step; warn before long steps.
- Use helpers for review/redteam, but accept only what a test confirms.
