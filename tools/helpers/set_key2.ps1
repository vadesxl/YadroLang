# Сохраняет ВТОРОЙ ключ Dahl в переменную Windows DAHL_API_KEY_2.
# Ключ вводится в СКРЫТОМ поле: не попадает в чат, в файлы и в историю команд.
$secure = Read-Host "Вставьте ВТОРОЙ ключ Dahl (символы не видны) и нажмите Enter" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $key = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr).Trim()
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}
if ($key.Length -lt 10) { Write-Host "Ключ слишком короткий, ничего не сохранено." -ForegroundColor Red; Read-Host "Enter для выхода"; exit 1 }
[Environment]::SetEnvironmentVariable("DAHL_API_KEY_2", $key, "User")
$env:DAHL_API_KEY_2 = $key
Remove-Variable key
Write-Host "Второй ключ сохранён (длина скрыта). Проверяю помощников..." -ForegroundColor Green
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$env:PYTHONUTF8 = "1"
python (Join-Path $root "tools\helpers\ask.py") --list
Write-Host ""
Write-Host "Готово. Окно можно закрыть и написать в Cline: 'ключ вставил'." -ForegroundColor Cyan
Read-Host "Enter для выхода"
