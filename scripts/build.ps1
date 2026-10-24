param([string]$PythonExe = 'python')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
& $PythonExe -c "import sys; assert sys.prefix != sys.base_prefix, 'Build inside a virtual environment; use build.bat'"
if ($LASTEXITCODE -ne 0) { throw 'An isolated build environment is required.' }
& $PythonExe -m unittest discover -s tests -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed; build stopped.' }
& $PythonExe -m PyInstaller --noconfirm --clean --onedir --noupx --windowed --add-data "awayguard/assets;awayguard/assets" --name AwayGuard launch.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
Copy-Item -LiteralPath 'README.md','LICENSE','awayguard/assets/SOURCE.md','scripts/enable-audit.ps1' -Destination 'dist/AwayGuard' -Force
Copy-Item -LiteralPath 'docs' -Destination 'dist/AwayGuard' -Recurse -Force
& $PythonExe -m pip freeze | Set-Content -LiteralPath 'dist/AwayGuard/BUILD-DEPENDENCIES.txt' -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw 'Could not record build dependencies.' }
for ($attempt = 1; $attempt -le 3; $attempt++) {
    try {
        Compress-Archive -LiteralPath 'dist/AwayGuard' -DestinationPath 'dist/AwayGuard-Windows-x64.zip' -Force -ErrorAction Stop
        break
    } catch {
        if ($attempt -eq 3) { throw }
        Write-Host 'A build file is temporarily locked. Retrying ZIP creation...'
        Start-Sleep -Seconds 2
    }
}
$digest = (Get-FileHash -LiteralPath 'dist/AwayGuard-Windows-x64.zip' -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath 'dist/SHA256SUMS.txt' -Value "$digest  AwayGuard-Windows-x64.zip" -Encoding ascii
Write-Host 'Built dist/AwayGuard/AwayGuard.exe and dist/AwayGuard-Windows-x64.zip. Keep the entire folder together.'
