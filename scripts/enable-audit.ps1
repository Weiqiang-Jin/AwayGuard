# Run explicitly in an elevated PowerShell. This changes Windows audit policy.
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this script from PowerShell as Administrator.'
}
$backupFolder = Join-Path $env:LOCALAPPDATA 'AwayGuard'
New-Item -ItemType Directory -Force -Path $backupFolder | Out-Null
$backupPath = Join-Path $backupFolder ('audit-policy-' + [Guid]::NewGuid().ToString() + '.csv')
& auditpol.exe /backup "/file:$backupPath"
if ($LASTEXITCODE -ne 0) { throw 'Audit policy backup failed; no policy changes made.' }
Write-Host "Policy backup: $backupPath"
# Stable GUIDs work independently of the Windows display language.
# Logon: success and failure; Other Logon/Logoff Events: success.
& auditpol.exe /set '/subcategory:{0CCE9215-69AE-11D9-BED3-505054503030}' /success:enable /failure:enable
if ($LASTEXITCODE -ne 0) { throw "Logon policy update failed. Backup: $backupPath" }
& auditpol.exe /set '/subcategory:{0CCE921C-69AE-11D9-BED3-505054503030}' /success:enable
if ($LASTEXITCODE -ne 0) { throw "Other Logon/Logoff policy update failed. Backup: $backupPath" }
Write-Host 'Audit policy configured. Domain/organization policy can override these settings.'
Write-Host 'Restore the full previous policy only if appropriate using:'
Write-Host "auditpol.exe /restore /file:`"$backupPath`""
