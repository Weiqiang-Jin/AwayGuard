@echo off
cd /d "%~dp0"
python -m awayguard
if errorlevel 1 pause
