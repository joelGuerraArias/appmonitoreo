@echo off
chcp 65001 >nul
title Video Analyzer 4 - Inicio rapido

echo.
echo ==============================================
echo   INICIANDO VIDEO ANALYZER 4 (mismo script v3, UI v4)
echo ==============================================
echo.

cd /d "%~dp0"

if exist "venv_new\Scripts\activate.bat" (
    call "venv_new\Scripts\activate.bat"
    goto RUN
)

if exist "venv_video\Scripts\activate.bat" (
    call "venv_video\Scripts\activate.bat"
    goto RUN
)

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
    goto RUN
)

echo ERROR: No se encontro entorno virtual (venv_new, venv_video o .venv).
pause
exit /b 1

:RUN
if not exist "appMonitoreo.py" (
    echo ERROR: No se encontro appMonitoreo.py en %CD%
    pause
    exit /b 1
)

echo Entorno activado.
echo Ejecutando: streamlit run appMonitoreo.py
echo URL esperada: http://localhost:8501
echo.

streamlit run appMonitoreo.py

echo.
echo Aplicacion cerrada.
pause
