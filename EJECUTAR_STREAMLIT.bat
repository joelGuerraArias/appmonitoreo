@echo off
REM ===== ANALIZADOR DE VIDEOS - LAUNCHER CORREGIDO =====
REM Versión corregida que abre automáticamente el navegador

title 🎬 Analizador de Videos - Iniciando...

echo.
echo ╔════════════════════════════════════════╗
echo ║     🎬 ANALIZADOR DE VIDEOS AUTO       ║
echo ║          Iniciando aplicación...       ║
echo ╚════════════════════════════════════════╝
echo.

REM Ir a la carpeta del proyecto
cd /d "C:\grabaciones"

REM Verificar que existe el entorno virtual
if not exist "venv_video\Scripts\activate.bat" (
    echo ❌ Error: No se encuentra el entorno virtual
    echo 📁 Verificar que existe: C:\grabaciones\venv_video\
    pause
    exit /b 1
)

REM Activar entorno virtual
echo ⚙️ Activando entorno virtual...
call venv_video\Scripts\activate.bat

REM Verificar que se activó correctamente
if "%VIRTUAL_ENV%"=="" (
    echo ❌ Error activando entorno virtual
    echo 🔧 Intentar: venv_video\Scripts\activate.bat
    pause
    exit /b 1
)

echo ✅ Entorno virtual: ACTIVADO (%VIRTUAL_ENV%)

REM Verificar dependencias críticas
echo 🔍 Verificando dependencias...
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo 📦 Instalando Streamlit...
    pip install streamlit >nul 2>&1
)

python -c "import openai" 2>nul
if errorlevel 1 (
    echo 📦 Instalando OpenAI...
    pip install openai >nul 2>&1
)

python -c "import mistralai" 2>nul
if errorlevel 1 (
    echo 📦 Instalando Mistral AI...
    pip install mistralai >nul 2>&1
)

echo ✅ Dependencias: VERIFICADAS

REM Verificar que el archivo principal existe
if not exist "transmistral2.py" (
    echo ❌ Error: No se encuentra transmistral2.py
    pause
    exit /b 1
)

echo ✅ Archivo principal: ENCONTRADO

REM Mostrar información de inicio
echo.
echo 🚀 Iniciando Streamlit...
echo 🌐 Se abrirá automáticamente en tu navegador
echo 📱 URL: http://localhost:8501
echo.
echo 💡 Para detener: Cierra esta ventana o presiona Ctrl+C
echo ⏰ Hora de inicio: %time%
echo.

REM Iniciar Streamlit SIN --headless para que abra el navegador automáticamente
streamlit run transmistral2.py

REM Si llega aquí, la aplicación se cerró
echo.
echo 🛑 Aplicación cerrada
echo 👋 ¡Hasta luego!
timeout /t 3
exit

