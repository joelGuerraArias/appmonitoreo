@echo off
chcp 65001 >nul
title 🎬 Analizador de Videos - Iniciando...

echo.
echo ========================================
echo      🎬 ANALIZADOR DE VIDEOS AUTO      
echo         Iniciando aplicacion...        
echo ========================================
echo.

cd /d "C:\grabaciones"

if not exist "venv_video\Scripts\activate.bat" (
    echo ❌ Error: Entorno virtual no encontrado
    pause
    exit /b 1
)

echo ⚙️ Activando entorno virtual...
call venv_video\Scripts\activate.bat

if "%VIRTUAL_ENV%"=="" (
    echo ❌ Error activando entorno virtual
    pause
    exit /b 1
)

echo ✅ Entorno activado: %VIRTUAL_ENV%

if not exist "transmistral2.py" (
    echo ❌ Error: Archivo principal no encontrado
    pause
    exit /b 1
)

echo ✅ Archivo principal encontrado
echo.
echo 🚀 Iniciando Streamlit...
echo 🌐 Se abrira automaticamente en tu navegador
echo 📱 URL: http://localhost:8501
echo.
echo 💡 Para detener: Cierra esta ventana o presiona Ctrl+C
echo.

streamlit run transmistral2.py

echo.
echo 🛑 Aplicacion cerrada
timeout /t 3
exit

