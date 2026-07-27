@echo off
echo Buscando Python instalado...
echo.

for %%i in (C:\Python313 C:\Python312 C:\Python311 C:\Python310 "C:\Program Files\Python313" "C:\Program Files\Python312" "%LOCALAPPDATA%\Programs\Python\Python313" "%LOCALAPPDATA%\Programs\Python\Python312") do (
    if exist "%%i\python.exe" (
        echo ENCONTRADO: %%i\python.exe
        "%%i\python.exe" --version
        echo.
    )
)

echo.
echo Verificando instalaciones via MS Store...
where python.exe 2>nul
if errorlevel 1 (
    echo No se encontro python.exe en PATH
) else (
    echo Python encontrado en PATH
)

echo.
pause







