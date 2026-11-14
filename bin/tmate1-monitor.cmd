@echo off
rem TMate 1.0 diagnostic monitor (Windows). Same options as bin/tmate1-monitor.
setlocal
set "PYTHONPATH=%~dp0..;%PYTHONPATH%"
py -3 -m tmate1.monitor %*
