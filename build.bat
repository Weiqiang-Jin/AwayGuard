@echo off
setlocal
cd /d "%~dp0"
echo Building AwayGuard. Python 3.10+ and internet access are needed for the first build.
if not exist ".build-venv\Scripts\python.exe" (
    python -m venv .build-venv
    if errorlevel 1 goto fail
)
".build-venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto fail
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build.ps1 -PythonExe "%~dp0.build-venv\Scripts\python.exe"
if errorlevel 1 goto fail
echo Done. Double-click dist\AwayGuard\AwayGuard.exe to run. Keep its _internal folder beside it.
pause
exit /b 0
:fail
echo Build failed. See the error above.
pause
exit /b 1
