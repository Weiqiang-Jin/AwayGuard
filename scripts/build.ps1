param([string]$PythonExe = 'python')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
& $PythonExe -m unittest discover -s tests -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed; build stopped.' }
& $PythonExe -m PyInstaller --noconfirm --clean --onefile --windowed --add-data "awayguard/assets;awayguard/assets" --name AwayGuard launch.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
Compress-Archive -LiteralPath 'dist/AwayGuard.exe','README.md','LICENSE','awayguard/assets/SOURCE.md','scripts/enable-audit.ps1' -DestinationPath 'dist/AwayGuard-Windows-x64.zip' -Force
$digest = (Get-FileHash -LiteralPath 'dist/AwayGuard-Windows-x64.zip' -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath 'dist/SHA256SUMS.txt' -Value "$digest  AwayGuard-Windows-x64.zip" -Encoding ascii
Write-Host 'Built dist/AwayGuard.exe and dist/AwayGuard-Windows-x64.zip'
