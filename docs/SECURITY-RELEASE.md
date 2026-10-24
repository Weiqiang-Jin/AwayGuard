# Antivirus detections and release verification

## Observed report

On 2026-10-24, local Microsoft Defender history reported
`Trojan:Win32/Bearfoos.B!ml` for a downloaded `AwayGuard.exe`.
The exact quarantined download has not been compared with a release checksum.
This is an antivirus detection, not merely an unknown-publisher prompt.
A false positive is possible but has not been confirmed by Microsoft.

## Packaging changes

- Build in a virtual environment using `requirements-build.txt`.
- Distribute PyInstaller's one-folder ZIP, without UPX compression, instead of
  a self-extracting one-file EXE. Keep `AwayGuard.exe` and `_internal` together.
- Include the resolved build dependencies and publish a ZIP SHA-256 checksum.
- Gate GitHub artifact and release uploads on a Defender custom scan. A missing
  Defender service or scan failure blocks upload; do not silently skip it.

These changes improve inspectability and release hygiene, but do not establish
that a binary is safe or guarantee that antivirus vendors will accept it.
Do not rename or repeatedly rebuild a detected binary merely to evade detection.

## If a release is blocked

1. Keep the detection name, Defender definition version, release tag, and hash
   of the exact affected artifact. Do not restore quarantined files just to run them.
2. Review the source and dependencies; compare the download with the published
   checksum where the file is still available. A checksum proves consistency,
   not safety.
3. Submit the affected release to Microsoft's official file-submission portal
   as a **Software developer**, reporting that it appears incorrectly detected.
   Explain its visible, opt-in desktop activity monitoring and local logging.
   Do not include personal activity logs. Submission requires your account and
   approval to share the binary; no submission has been made automatically.
4. Wait for the vendor verdict. If another antivirus blocks it, request review
   from that vendor too. Do not instruct users to disable protection or exclude
   the application.

Portal: https://www.microsoft.com/en-us/wdsi/filesubmission

## Signing and reputation

For public distribution, use Authenticode signing with your verified publisher
identity, for example via a trusted certificate or Microsoft's Artifact Signing.
Sign the final executable before packaging, scanning and hashing it. Keep signing
credentials in a signing service or protected CI secrets, never in the repository.
No publisher certificate has been supplied; current builds remain unsigned.
Signing authenticates the publisher but does not override malware verdicts or
guarantee instant SmartScreen reputation.

References:
- https://pyinstaller.org/en/stable/operating-mode.html
- https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation
- https://learn.microsoft.com/en-us/defender-xdr/submission-guide
