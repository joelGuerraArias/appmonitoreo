@echo off
echo Buscando FFmpeg...
echo.

echo === Verificando PATH ===
where ffmpeg 2>nul
if errorlevel 1 (
    echo ❌ FFmpeg NO esta en el PATH
) else (
    echo ✅ FFmpeg encontrado en PATH
    ffmpeg -version | findstr "ffmpeg version"
)

echo.
echo === Buscando en ubicaciones comunes ===

for %%p in (
    "C:\ffmpeg\bin\ffmpeg.exe"
    "C:\Program Files\ffmpeg\bin\ffmpeg.exe"
    "C:\ProgramData\chocolatey\bin\ffmpeg.exe"
    "%LOCALAPPDATA%\Programs\ffmpeg\bin\ffmpeg.exe"
) do (
    if exist %%p (
        echo ✅ ENCONTRADO: %%p
        %%p -version | findstr "ffmpeg version"
    )
)

echo.
echo === Buscando en todo el disco C: (puede tardar) ===
dir C:\ffmpeg.exe /s /b 2>nul | findstr /v "Windows\WinSxS"

echo.
pause


















