param([string]$Version = '', [string]$CompilerPath = '')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path -LiteralPath 'dist/AwayGuard/AwayGuard.exe')) { throw 'Build the portable app first.' }
if (-not $Version) {
    $match = [regex]::Match((Get-Content -LiteralPath 'pyproject.toml' -Raw), '(?m)^version\s*=\s*"([0-9.]+)"')
    if (-not $match.Success) { throw 'Cannot read app version.' }
    $Version = $match.Groups[1].Value
}
$Version = $Version -replace '^v', ''
if ($Version -notmatch '^\d+\.\d+\.\d+(\.\d+)?$') { throw 'Installer version must use numeric major.minor.patch format.' }
if (-not $CompilerPath) { $CompilerPath = Join-Path (Get-Location) '.tools/inno/ISCC.exe' }
if (-not (Test-Path -LiteralPath $CompilerPath)) { throw 'Run scripts/setup-installer-tool.ps1 first.' }
& $CompilerPath "/DAppVersion=$Version" 'installer/AwayGuard.iss'
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
$lines = foreach ($file in @('AwayGuard-Windows-x64.zip','AwayGuard-Setup-x64.exe')) {
    $digest = (Get-FileHash -LiteralPath (Join-Path 'dist' $file) -Algorithm SHA256).Hash.ToLowerInvariant()
    "$digest  $file"
}
Set-Content -LiteralPath 'dist/SHA256SUMS.txt' -Value $lines -Encoding ascii
Write-Host 'Installer ready: dist/AwayGuard-Setup-x64.exe'
