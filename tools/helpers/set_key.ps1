# Сохраняет API-ключ помощников (Dahl: GLM-5.3 + DeepSeek V4) в переменную Windows.
# Ключ вводится в СКРЫТОМ поле: не попадает в чат, в файлы и в историю команд.
# Запуск: правой кнопкой -> "Выполнить с помощью PowerShell", или:
#   powershell -ExecutionPolicy Bypass -File tools\helpers\set_key.ps1
$secure = Read-Host "Вставьте ключ Dahl (символы не отображаются) и нажмите Enter" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $key = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr).Trim()
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}
if ($key.Length -lt 10) { Write-Host "Ключ слишком короткий, ничего не сохранено." -ForegroundColor Red; exit 1 }
[Environment]::SetEnvironmentVariable("DAHL_API_KEY", $key, "User")
$env:DAHL_API_KEY = $key
Remove-Variable key
Write-Host "Ключ сохранён (длина скрыта). Проверяю помощников..." -ForegroundColor Green
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$env:PYTHONUTF8 = "1"
python (Join-Path $root "tools\helpers\ask.py") --ping
Write-Host ""
Write-Host "Если оба OK - напишите в Cline: 'помощники готовы'. Окно можно закрыть." -ForegroundColor Cyan
Read-Host "Enter для выхода"
