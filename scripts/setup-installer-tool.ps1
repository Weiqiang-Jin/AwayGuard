$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$toolRoot = Join-Path $repoRoot '.tools'
$compiler = Join-Path $toolRoot 'inno/ISCC.exe'
if (Test-Path -LiteralPath $compiler) { Write-Host "Compiler: $compiler"; exit 0 }
New-Item -ItemType Directory -Path $toolRoot -Force | Out-Null
$download = Join-Path $toolRoot 'innosetup-6.7.3.exe'
Invoke-WebRequest -Uri 'https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe' -OutFile $download -UseBasicParsing
$signature = Get-AuthenticodeSignature -LiteralPath $download
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Pyrsys B\.V\.') {
    throw 'Inno Setup signature or publisher verification failed; refusing to execute.'
}
$installDir = Join-Path $toolRoot 'inno'
$process = Start-Process -FilePath $download -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/CURRENTUSER','/NOICONS',"/DIR=`"$installDir`"") -WindowStyle Hidden -Wait -PassThru
if ($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $compiler)) { throw 'Inno Setup installation failed.' }
Write-Host "Compiler installed: $compiler"
