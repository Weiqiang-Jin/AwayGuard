param([string]$TargetPath = 'dist')
$ErrorActionPreference = 'Stop'
$resolvedTarget = (Resolve-Path -LiteralPath $TargetPath).Path
$status = Get-MpComputerStatus -ErrorAction Stop
if (-not $status.AntivirusEnabled -or -not $status.AMServiceEnabled) {
    throw 'Microsoft Defender is not active. Release scan cannot be verified.'
}
$scanStart = Get-Date
Write-Host "Scanning $resolvedTarget with Defender definitions $($status.AntivirusSignatureVersion)"
$appFolder = Join-Path $resolvedTarget 'AwayGuard'
$archivePath = Join-Path $resolvedTarget 'AwayGuard-Windows-x64.zip'
if (-not (Test-Path -LiteralPath $appFolder) -or -not (Test-Path -LiteralPath $archivePath)) {
    throw 'Release folder or ZIP missing; build before scanning.'
}
Start-MpScan -ScanType CustomScan -ScanPath $appFolder -ErrorAction Stop
Start-MpScan -ScanType CustomScan -ScanPath $archivePath -ErrorAction Stop
$detections = @(Get-MpThreatDetection -ErrorAction Stop | Where-Object {
    ($_.InitialDetectionTime -ge $scanStart -or $_.LastThreatStatusChangeTime -ge $scanStart) -and
    (@($_.Resources | Where-Object { $_.IndexOf($resolvedTarget, [StringComparison]::OrdinalIgnoreCase) -ge 0 }).Count -gt 0)
})
if ($detections.Count -gt 0) {
    $detections | Format-List ThreatID,InitialDetectionTime,Resources
    throw 'Defender reported a detection. Do not publish; submit it for vendor review.'
}
if (-not (Test-Path -LiteralPath (Join-Path $resolvedTarget 'AwayGuard/AwayGuard.exe'))) {
    throw 'Expected executable is missing after the scan; release verification failed.'
}
if (-not (Test-Path -LiteralPath $archivePath)) { throw 'Release ZIP missing after scan.' }
Write-Host 'Defender scan completed without a matching new detection. This is not a guarantee against future detections.'
