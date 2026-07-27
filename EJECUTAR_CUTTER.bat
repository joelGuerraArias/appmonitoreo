@echo off
echo ========================================
echo    EJECUTANDO VIDEO CUTTER
echo ========================================
echo.

REM Navegar al directorio del script
cd /d "%~dp0"

REM Configurar PATH para incluir FFmpeg de Chocolatey
set PATH=C:\ProgramData\chocolatey\lib\ffmpeg\tools\ffmpeg-8.0-essentials_build\bin;%PATH%

REM Verificar FFmpeg
echo Verificando FFmpeg...
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] FFmpeg no encontrado en el PATH
    echo Por favor instala FFmpeg con: choco install ffmpeg
    pause
    exit /b 1
)

where ffprobe >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] FFprobe no encontrado en el PATH
    pause
    exit /b 1
)

echo [OK] FFmpeg encontrado
echo [OK] FFprobe encontrado
echo.

REM Ejecutar la aplicación con el entorno virtual
echo Iniciando Video Cutter...
echo.
venv_video\Scripts\python.exe cutter.py

REM Si el script falla, mantener la ventana abierta
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] La aplicacion termino con errores
    pause
)

















