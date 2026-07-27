@echo off
echo ========================================
echo   📦 INSTALANDO DEPENDENCIAS
echo ========================================
echo.

cd /d "%~dp0"

echo 📂 Directorio: %CD%
echo.

echo 🔧 Instalando todas las dependencias...
echo    (Esto puede tomar 3-5 minutos)
echo.

venv_video\Scripts\python.exe -m pip install --upgrade pip
venv_video\Scripts\python.exe -m pip install -r requirements.txt

echo.
echo ========================================
if errorlevel 1 (
    echo ❌ Hubo errores en la instalación
    echo.
    echo Revisa los mensajes arriba para ver qué falló
) else (
    echo ✅ TODAS LAS DEPENDENCIAS INSTALADAS
    echo.
    echo Ahora puedes ejecutar: EJECUTAR_APP_SIMPLE.bat
)
echo ========================================
echo.
pause


















