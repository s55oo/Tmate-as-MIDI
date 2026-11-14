@echo off
rem TMate 1.0 - double-click to run the Windows setup/check script.
rem Extra arguments are passed through, e.g.:  setup-windows.cmd -Autostart
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-windows.ps1" %*
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%
