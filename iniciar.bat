@echo off
chcp 65001 >nul
title Cristocentricos
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo No existe el entorno de Python. Sigue la seccion "Instalacion" del README.md
  pause
  exit /b 1
)
if not exist ".env" (
  echo Falta el archivo .env. Copia .env.example como .env y llena SECRET_KEY.
  pause
  exit /b 1
)
if not exist "frontend\dist\index.html" (
  echo Compilando la interfaz por primera vez...
  pushd frontend
  call npm run build
  popd
)

start "Cristocentricos - Servidor (no cerrar)" cmd /k ".venv\Scripts\python.exe servidor.py"
REM La ventana de agentes se activa en la fase 3:
REM start "Cristocentricos - Agentes (no cerrar)" cmd /k ".venv\Scripts\python.exe -m agentes.worker"

timeout /t 3 /nobreak >nul
start "" http://localhost:5000
