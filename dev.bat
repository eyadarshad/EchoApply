@echo off
title SmartApply AI - Dev Server Launcher
echo ==========================================================
echo  Starting SmartApply AI (Backend + Frontend)
echo ==========================================================
echo.

cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0dev.ps1"
pause
