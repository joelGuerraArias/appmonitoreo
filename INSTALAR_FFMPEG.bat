@echo off
echo ========================================
echo   📦 INSTALANDO FFMPEG
echo ========================================
echo.

cd /d "%~dp0"

echo 🔧 Instalando FFmpeg con pip...
echo.

venv_video\Scripts\python.exe -m pip install ffmpeg-python

echo.
echo ========================================
echo ✅ INSTALACION COMPLETADA
echo ========================================
echo.
echo ⚠️ IMPORTANTE: 
echo.
echo Si aun no funciona, necesitas instalar FFmpeg manualmente:
echo 1. Ve a: https://github.com/BtbN/FFmpeg-Builds/releases
echo 2. Descarga: ffmpeg-master-latest-win64-gpl.zip
echo 3. Extrae el archivo
echo 4. Agrega la carpeta 'bin' al PATH de Windows
echo.
echo O usa Chocolatey (mas facil):
echo    choco install ffmpeg
echo.
pause


















