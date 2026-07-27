@echo off
echo ========================================
echo   🚀 INICIANDO VIDEO ANALYZER IA v2.0
echo ========================================
echo.

cd /d "%~dp0"

echo 📂 Directorio: %CD%
echo.

echo 🔧 Configurando FFmpeg...
set PATH=C:\ProgramData\chocolatey\lib\ffmpeg\tools\ffmpeg-8.0-essentials_build\bin;%PATH%
echo    ✅ PATH actualizado con FFmpeg
echo.

echo 🐍 Usando Python del entorno virtual...
echo.
echo 🌐 Iniciando Streamlit...
echo    Abriendo navegador automáticamente...
echo.

venv_video\Scripts\python.exe -m streamlit run transmistral2.py --server.headless=false

echo.
echo ❌ La aplicación se cerró
pause

