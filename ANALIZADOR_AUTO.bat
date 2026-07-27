@echo off
REM ===== ANALIZADOR DE VIDEOS - LAUNCHER AUTOMÁTICO =====
REM Un solo clic y todo funciona automáticamente

title 🎬 Analizador de Videos - Iniciando...

REM Ir a la carpeta del proyecto
cd /d "C:\grabaciones"

REM Activar entorno virtual silenciosamente
call venv_video\Scripts\activate.bat >nul 2>&1

REM Verificar que se activó
if "%VIRTUAL_ENV%"=="" (
    echo ❌ Error activando entorno virtual
    pause
    exit /b 1
)

REM Verificar dependencias críticas e instalar si faltan
python -c "import streamlit" >nul 2>&1 || pip install streamlit >nul 2>&1
python -c "import openai" >nul 2>&1 || pip install openai >nul 2>&1

REM Mostrar mensaje de inicio
echo.
echo ╔════════════════════════════════════════╗
echo ║     🎬 ANALIZADOR DE VIDEOS AUTO       ║
echo ║          Iniciando aplicación...       ║
echo ╚════════════════════════════════════════╝
echo.
echo ✅ Entorno virtual: ACTIVADO
echo ✅ Dependencias: VERIFICADAS  
echo 🚀 Abriendo en navegador...
echo.
echo 💡 Para detener: Cierra esta ventana o presiona Ctrl+C
echo ⏰ Hora de inicio: %time%
echo.

REM Iniciar la aplicación automáticamente (SIN headless para abrir navegador)
streamlit run transmistral2.py --server.port=8501

REM Si llega aquí, la aplicación se cerró
echo.
echo 🛑 Aplicación cerrada
echo 👋 ¡Hasta luego!
timeout /t 3
exit