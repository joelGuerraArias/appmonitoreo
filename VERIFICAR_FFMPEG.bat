@echo off
echo ========================================
echo   🔧 VERIFICANDO FFMPEG
echo ========================================
echo.

set PATH=C:\ProgramData\chocolatey\lib\ffmpeg\tools\ffmpeg-8.0-essentials_build\bin;%PATH%

echo Verificando FFmpeg...
ffmpeg -version | findstr "ffmpeg version"
if errorlevel 1 (
    echo ❌ FFmpeg NO funciona
) else (
    echo ✅ FFmpeg OK
)

echo.
echo Verificando FFprobe...
ffprobe -version | findstr "ffprobe version"
if errorlevel 1 (
    echo ❌ FFprobe NO funciona
) else (
    echo ✅ FFprobe OK
)

echo.
echo ========================================
echo   ✅ VERIFICACION COMPLETA
echo ========================================
echo.
pause


















