@echo off
chcp 65001 >nul
title Video Analyzer v5.6 Intrant

echo.
echo ==============================================
echo   VIDEO ANALYZER v5.6 Intrant
echo   http://localhost:8501
echo ==============================================
echo.

cd /d "%~dp0"

REM === BLINDAJE: restaurar app/.env/clientes/terminos si Cursor los vacio ===
if exist "venv_new\Scripts\python.exe" (
    "venv_new\Scripts\python.exe" proteger_integridad.py
) else if exist "venv_video\Scripts\python.exe" (
    "venv_video\Scripts\python.exe" proteger_integridad.py
) else (
    python proteger_integridad.py
)

if exist "venv_new\Scripts\activate.bat" (
    call "venv_new\Scripts\activate.bat"
    goto RUN
)
if exist "venv_video\Scripts\activate.bat" (
    call "venv_video\Scripts\activate.bat"
    goto RUN
)
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
    goto RUN
)

echo ERROR: No se encontro entorno virtual (venv_new, venv_video o .venv).
pause
exit /b 1

:RUN
for %%A in ("appMonitoreo.py") do set APPSZ=%%~zA
if not defined APPSZ set APPSZ=0
if %APPSZ% LSS 50000 (
    echo ERROR: appMonitoreo.py sigue vacio/corrupto tras blindaje.
    echo Restaura manualmente: copy /Y backups\appMonitoreo_v55_backup.py appMonitoreo.py
    pause
    exit /b 1
)

echo Entorno activado. App OK (%APPSZ% bytes).
echo Ejecutando: python -m streamlit run appMonitoreo.py
echo.

netstat -ano | findstr ":8501" | findstr "LISTENING" >nul
if %ERRORLEVEL%==0 (
    echo Streamlit ya esta corriendo en el puerto 8501.
    echo Abriendo http://localhost:8501 ...
    echo Si ves pantalla en blanco: Ctrl+F5
    start "" "http://localhost:8501/?v=55"
    pause
    exit /b 0
)

python -m streamlit run appMonitoreo.py --server.port 8501 --browser.gatherUsageStats false

echo.
echo Aplicacion cerrada.
pause
