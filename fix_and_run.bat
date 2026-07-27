@echo off
echo ========================================
echo    CORRIGIENDO Y EJECUTANDO APP
echo ========================================
echo.

cd /d "C:\Users\Administrador\Desktop\grabaciones"

echo Verificando archivos...
if not exist "transmistral2.py" (
    echo ERROR: No se encuentra transmistral2.py
    pause
    exit /b 1
)

echo Archivo principal encontrado: transmistral2.py

echo.
echo Intentando ejecutar con Python del sistema...
python --version 2>nul
if %errorlevel% equ 0 (
    echo Python encontrado en el sistema
    echo Instalando Streamlit...
    python -m pip install streamlit --user
    echo.
    echo Ejecutando aplicacion...
    python -m streamlit run transmistral2.py
) else (
    echo Python no encontrado en el sistema
    echo.
    echo Intentando con Python del entorno virtual...
    if exist "venv_video\Scripts\python.exe" (
        echo Usando Python del entorno virtual...
        venv_video\Scripts\python.exe -m pip install streamlit
        echo.
        echo Ejecutando aplicacion...
        venv_video\Scripts\python.exe -m streamlit run transmistral2.py
    ) else (
        echo ERROR: No se puede encontrar Python
        echo.
        echo SOLUCIONES:
        echo 1. Instalar Python desde https://python.org
        echo 2. O usar Microsoft Store para instalar Python
        echo.
        pause
    )
)

echo.
echo Aplicacion cerrada
pause

