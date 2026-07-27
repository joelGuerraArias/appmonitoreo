@echo off
title Video Analyzer Next.js (sin Streamlit)
cd /d "%~dp0"

echo ============================================
echo  Video Analyzer - Next.js STANDALONE
echo  No hace falta abrir Streamlit (8501)
echo ============================================
echo.

REM Preferir venv_new del repo
if exist "%~dp0venv_new\Scripts\python.exe" (
  set "VA_PYTHON=%~dp0venv_new\Scripts\python.exe"
  echo Python: %VA_PYTHON%
) else (
  echo AVISO: no se encontro venv_new\Scripts\python.exe
)

REM Auto-arrancar worker al levantar el server
set NEXT_AUTO_START_WORKER=true

cd /d "%~dp0app-monitoreo-next"
if not exist "node_modules\" (
  echo Instalando dependencias npm...
  call npm install
  if errorlevel 1 (
    echo Error en npm install
    pause
    exit /b 1
  )
)

echo.
echo Abriendo http://localhost:3000 en unos segundos...
echo El worker Python arranca solo (pipeline completo).
echo Para detener: cierra esta ventana o pulsa Detener en la UI.
echo.

start "" cmd /c "timeout /t 4 /nobreak >nul & start http://localhost:3000"

call npm run dev
pause
