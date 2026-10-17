@echo off
chcp 65001 >nul
title Cristocentricos - EJEMPLO
cd /d "%~dp0"
if not exist "frontend\dist\index.html" (
  pushd frontend
  call npm run build
  popd
)
start "Cristocentricos - EJEMPLO (no cerrar)" cmd /k ".venv\Scripts\python.exe ejemplo.py %*"
timeout /t 3 /nobreak >nul
start "" http://localhost:5022
