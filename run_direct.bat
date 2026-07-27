@echo off
cd /d "C:\Users\Administrador\Desktop\grabaciones"

echo Ejecutando transmistral2.py directamente...
echo.

REM Intentar ejecutar directamente el archivo Python
if exist "venv_video\Scripts\python.exe" (
    echo Usando Python del entorno virtual...
    venv_video\Scripts\python.exe transmistral2.py
) else (
    echo ERROR: No se encuentra el entorno virtual
    echo.
    echo Intentando con Python del sistema...
    python transmistral2.py
)

echo.
echo Presiona cualquier tecla para cerrar...
pause >nul

