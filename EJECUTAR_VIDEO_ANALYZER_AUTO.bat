@echo off
title 🎬 Video Analyzer v2 - Auto Start
echo ==================================================
echo   🚀 INICIANDO VIDEO ANALYZER v2
echo ==================================================
echo.

cd /d "%~dp0"
if exist "venv_new\Scripts\activate.bat" call venv_new\Scripts\activate.bat
if exist "venv_new\Scripts\activate.bat" goto RUN

if exist "venv_video\Scripts\activate.bat" call venv_video\Scripts\activate.bat
if exist "venv_video\Scripts\activate.bat" goto RUN

echo ❌ No se encontro entorno virtual.
pause
exit /b 1

:RUN
echo ✅ Entorno activado.
echo 📂 Directorio: %CD%
echo 🏃 Ejecutando videoAnalizerv2.py con Streamlit...
echo.

:LOOP
echo [%date% %time%] Iniciando Streamlit...
streamlit run videoAnalizerv2.py
echo.
echo ==================================================
echo   ⚠️ Streamlit se cerro. Reiniciando en 5s...
echo   (Cierra esta ventana para detener)
echo ==================================================
timeout /t 5 /nobreak >nul
goto LOOP
