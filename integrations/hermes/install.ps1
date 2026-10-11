# Устанавливает плагин Yadro Guard в дашборд Hermes.
# Запуск: powershell -ExecutionPolicy Bypass -File integrations\hermes\install.ps1
# Что делает: копирует плагин в %LOCALAPPDATA%\hermes\plugins\yadro-guard,
# пишет config.json (путь к движку и к Python с llvmlite), включает плагин.
# Чужие плагины (home-dashboard и др.) не трогает.
$ErrorActionPreference = "Stop"
$EngineHome = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$HermesHome = if ($env:HERMES_HOME) { $env:HERMES_HOME } else { Join-Path $env:LOCALAPPDATA "hermes" }
$Target = Join-Path $HermesHome "plugins\yadro-guard"
$Python = (Get-Command python -ErrorAction Stop).Source

& $Python -c "import llvmlite" 2>$null
if ($LASTEXITCODE -ne 0) { throw "У $Python нет llvmlite: pip install -r requirements.txt" }

New-Item -ItemType Directory -Force $Target | Out-Null
Copy-Item -Recurse -Force (Join-Path $PSScriptRoot "yadro-guard\*") $Target
$cfg = @{ engine_home = $EngineHome; python = $Python } | ConvertTo-Json
[IO.File]::WriteAllText((Join-Path $Target "config.json"), $cfg, (New-Object Text.UTF8Encoding($false)))

$hermes = Join-Path $HermesHome "bin\hermes.exe"
if (Test-Path $hermes) { & $hermes plugins enable yadro-guard }
Write-Host "Готово: $Target"
Write-Host "Перезапустите дашборд Hermes или нажмите Re-scan на странице Plugins."
