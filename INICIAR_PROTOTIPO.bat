@echo off
setlocal enabledelayedexpansion
title Sistema APU - AREN.IA (Prototipo Portable)

cd /d "%~dp0"

echo ====================================================================
echo               SISTEMA APU - AREN.IA (PROTOTIPO)
echo ====================================================================
echo.

:: 1. Verificar si existe uv en el sistema o en el entorno del usuario
set "UV_CMD="
where uv >nul 2>&1
if %errorlevel% equ 0 (
    set "UV_CMD=uv"
) else if exist "%USERPROFILE%\.cargo\bin\uv.exe" (
    set "UV_CMD=%USERPROFILE%\.cargo\bin\uv.exe"
) else if exist "%LOCALAPPDATA%\bin\uv.exe" (
    set "UV_CMD=%LOCALAPPDATA%\bin\uv.exe"
)

:: 2. Si no hay uv ni entorno, comprobar si existe python
if not defined UV_CMD (
    echo [INFO] No se encontro 'uv' en la maquina.
    echo [INFO] Verificando instalacion de Python...
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        echo [INFO] Python detectado en el sistema.
        if not exist ".venv" (
            echo [INFO] Creando entorno virtual local...
            python -m venv .venv
            echo [INFO] Instalando dependencias (esto toma unos momentos)...
            call .venv\Scripts\activate.bat
            python -m pip install --upgrade pip
            pip install -r requirements.txt
        )
        goto :iniciar_con_venv
    ) else (
        echo [INFO] Descargando herramienta portable ultrarrapida 'uv' (15 MB)...
        powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
        if exist "%USERPROFILE%\.cargo\bin\uv.exe" (
            set "UV_CMD=%USERPROFILE%\.cargo\bin\uv.exe"
        ) else if exist "%LOCALAPPDATA%\bin\uv.exe" (
            set "UV_CMD=%LOCALAPPDATA%\bin\uv.exe"
        )
    )
)

:: 3. Si se dispone de uv, sincronizar y arrancar
if defined UV_CMD (
    echo [INFO] Preparando entorno con uv...
    if not exist ".venv" (
        "%UV_CMD%" sync --all-extras
    )
    if not exist "data\apu.db" (
        echo [INFO] Inicializando base de datos con caso de demostracion...
        "%UV_CMD%" run python scripts/seed_demo.py
    )
    echo.
    echo ====================================================================
    echo  Iniciando aplicacion en http://localhost:8501
    echo  Para cerrar el programa, cierre esta ventana.
    echo ====================================================================
    echo.
    start http://localhost:8501
    "%UV_CMD%" run python -m streamlit run ui/app.py
    goto :fin
)

:iniciar_con_venv
if exist ".venv" (
    if not exist "data\apu.db" (
        echo [INFO] Inicializando base de datos con caso de demostracion...
        .venv\Scripts\python.exe scripts/seed_demo.py
    )
    echo.
    echo ====================================================================
    echo  Iniciando aplicacion en http://localhost:8501
    echo  Para cerrar el programa, cierre esta ventana.
    echo ====================================================================
    echo.
    start http://localhost:8501
    .venv\Scripts\python.exe -m streamlit run ui/app.py
    goto :fin
)

echo [ERROR] No se pudo preparar el entorno de ejecucion.
echo Por favor asegurese de tener conexion a internet o Python instalado.
pause

:fin
