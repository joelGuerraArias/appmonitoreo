@echo off
title Video Analyzer IA - Iniciando...
cd /d "C:\Users\Administrador\Desktop\grabaciones"

echo ========================================
echo 🎬 VIDEO ANALYZER IA v2.0
echo ========================================
echo.
echo 🚀 Iniciando aplicacion Streamlit...
echo 📁 Directorio: %CD%
echo 🌐 URL: http://localhost:8501
echo.

REM Activar entorno virtual si existe
if exist "venv_video\Scripts\activate.bat" (
    echo 🔧 Activando entorno virtual...
    call venv_video\Scripts\activate.bat
    echo ✅ Entorno virtual activado
) else (
    echo ⚠️ No se encontro entorno virtual, usando Python del sistema
)

echo.
echo 🔄 Ejecutando: streamlit run transmistral2.py --server.port 8501 --server.headless false
echo.

REM Abrir navegador después de 3 segundos
start /min cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8501"

REM Ejecutar Streamlit
streamlit run transmistral2.py --server.port 8501 --server.headless false

echo.
echo ========================================
echo 🛑 Aplicacion detenida
echo ========================================
pause

