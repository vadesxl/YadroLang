# HANDOFF — read this first in a new session

Owner: vadesxl (Ukrainian; answer in Russian, short, honest). Conductor: Cline. Helpers: GLM-5.3 + DeepSeek V4 via Dahl.

## Where the work is
- Worktree: `E:\загрузки\.gemini\antigravity\scratch\wt-ru-security`, branch `security/ethics-gaps`
  (based on `origin/agent/semantic-analysis`). Pushed up to `f5ec4b0`, draft PR #48; the Desktop work below is NOT committed yet. Never push to main.
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

## Session 2026-10-11 (evening): Guard tab in Hermes Desktop — DONE, owner confirmed by screenshots
Why it was invisible: Hermes Desktop does NOT load web-dashboard tabs (`dashboard/dist/index.js`). It needs a
separate ESM file `desktop/plugin.js` (imports only `react` + `@hermes/plugin-sdk`, default-exports HermesPlugin,
registers `routes` / `sidebar.nav` / `palette`). Electron copies `plugins/<name>/desktop/` into
`%LOCALAPPDATA%\hermes\desktop-plugins/<name>/`. Desktop half is opt-in: user flips the Desktop toggle in Plugins.

Done (UNCOMMITTED in worktree):
- `dashboard/dist/index.js` is now a factory `(function (SDK, onReady) {...})(window.__HERMES_PLUGIN_SDK__, ...)`
  so web and Desktop share one page code.
- NEW `tools/build_desktop_plugin.py` generates `integrations/hermes/yadro-guard/desktop/plugin.js`
  (`--check` = verify up to date). fetchJSON goes through `ctx.rest`, limited to `/api/plugins/yadro-guard`.
  ALWAYS re-run it after editing `index.js` or `style.css`.
- NEW test `test_desktop_половина_собрана_и_в_рамках_sdk` in `tests/test_hermes_plugin.py`.
- Copied by hand into `%LOCALAPPDATA%\hermes\plugins\yadro-guard\desktop\plugin.js`. Hermes lint
  `hermes_cli.plugin_validate_desktop.desktop_surface_hits` → clean.
- Owner screenshots: Guard in sidebar; Live protection = Protected; Exposure = 78/100 (0 crit, 0 high, 3 med, 7 low);
  Vault and Check code render.

Not ours (tell owner, do not fix):
- Plugin catalog pane is white: hermes-agent.nousresearch.com sends `X-Frame-Options: DENY` + `frame-ancestors 'none'`.
  Workaround: Install from Git / open the catalog in a browser.
- Home widgets "no data": home-dashboard `plugin_api.py` imports `get_usage_analytics`, `list_cron_jobs` that no longer
  exist in `hermes_cli.web_server`. Fix = update home-dashboard from its repo.

## Session 2026-10-11 (late night) — done, pushed up to 0c562b8 (PR #48), 0e31a6b local
- Desktop commit pushed (git push works through Git Credential Manager = "manager"; no token needed).
- install.ps1 verified: copies `desktop\` (tested with a temp HERMES_HOME).
- Exposure: firewall verdict now real — `firewall_state()` reads local policy via COM `HNetCfg.FwPolicy2`
  (0.2 s, no admin; Get-NetFirewall* took 11-21 s). `firewall_verdict()` matches program path / service / port /
  profile; says "blocked" only when certain. Store-app rules (owner SID + no program) ignored for desktop apps;
  Wi-Fi Direct (`@wlansvc.dll`) and keyword ports (RPC, IPHTTPS) => "not verified". IPv4+IPv6 merged
  (`merge_dual_stack`, keeps the riskier verdict). svchost named by hosted service (`tasklist /SVC`,
  `services.WINDOWS_SERVICES`: W32Time=NTP, DoSvc, CDPSvc). Owner PC: 445/139/1236 stay "not verified" because a
  Codex sandbox block rule (`codex_sandbox_offline_block_inbound`, partial remote range) exists — honest result.
- UI: report shown inline (fixed modal was clipped: backdrop-filter on cards breaks position:fixed); secret kind
  picker = buttons instead of native <select> (white dropdown); code sample prefilled. Reinstalled into Hermes.
- Helpers: `tools/helpers/swarm.py` + `jobs_release.json` (10 jobs: redteam detectors/crypto/actions/policy, review
  vault/api/exposure/UI, architect, tester). Third model MiniMax-M2.7 added (`TEAM`, `--model all`).
  **Dahl gateway returns HTTP 502 for every uncached prompt** (only a cached "hi" returns 200) since ~23:37.
  Swarm runs in background with `--wait` (probes every 5 min up to 6 h). Answers -> `tools/helpers/out/<job>_<model>.md`,
  progress -> `tools/helpers/out/swarm.log`. Read them, turn real findings into tests.

## NEXT (priority order)
1. Run full tests (`$env:PYTHONUTF8='1'; python tests\run_tests.py`) — not run after the Desktop change; the targeted
   run's output was lost. Then commit + push to `security/ethics-gaps` (PR #48).
2. `install.ps1`: copy `desktop\` too (Copy-Item `yadro-guard\*` probably already does — verify) and remind the user
   to enable the Desktop toggle.
3. Check code UX: sample is only a grey placeholder, so the button looks dead. Prefill the sample or make
   "Load example" prominent.
4. Exposure: merge IPv4 `0.0.0.0` + IPv6 `::` rows of the same pid/port into one row.
5. Exposure: "firewall: not verified" everywhere — find out why (admin rights? netsh/Get-NetFirewallRule parsing).
6. Exposure: recognise `svchost` UDP 123 as Windows Time (NTP), not "Unknown service".
7. Russian localisation of the Guard tab (owner speaks Russian/Ukrainian).
8. Old plan still open: disk audit for stealer targets (seed phrases, wallet.dat, MetaMask/Phantom),
   `THREAT_MODEL_PRODUCT.md`, 17 analyzer gaps in `этика_поток.py`, sync EN repo, rotate Gemini key, product name.

Advice given to owner about his PC: SMB 445 open to all networks (turn off sharing if unused, never forward on router);
AsusUpdateCheck on 1236 (update or disable).