@echo off
:: ============================================================
:: build.bat — Compila DBManager con PyInstaller
::
:: Usa un venv aislado para minimizar el tamaño del ejecutable.
:: Solo instala los paquetes estrictamente necesarios.
::
:: Resultado: dist\DBManager\DBManager.exe
:: ============================================================

setlocal
set VENV_DIR=.venv_build

echo.
echo ========================================
echo   Compilando DBManager con PyInstaller
echo ========================================
echo.

:: ── 1. Verificar Python ──────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado en PATH.
    pause & exit /b 1
)

:: ── 2. Crear venv limpio (solo las dependencias necesarias) ──
if not exist "%VENV_DIR%" (
    echo [1/4] Creando entorno virtual limpio...
    python -m venv %VENV_DIR%
    echo.
    echo [2/4] Instalando dependencias...
    %VENV_DIR%\Scripts\pip install --quiet psycopg2-binary faker pillow pyinstaller
) else (
    echo [1/4] Reutilizando entorno virtual existente.
    echo [2/4] Verificando dependencias...
    %VENV_DIR%\Scripts\pip install --quiet psycopg2-binary faker pillow pyinstaller
)

:: ── 3. Compilar ───────────────────────────────────────────────
echo.
echo [3/4] Ejecutando PyInstaller...
%VENV_DIR%\Scripts\pyinstaller DBManager.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo [ERROR] La compilacion fallo. Revisa los mensajes anteriores.
    pause & exit /b 1
)

:: ── 4. Resultado ──────────────────────────────────────────────
echo.
echo [4/4] Compilacion completada.
echo.
echo Ejecutable: dist\DBManager\DBManager.exe
echo.

:: Mostrar tamaño aproximado del resultado
for /f "tokens=3" %%a in ('dir /s /a "dist\DBManager" ^| find "archivos"') do set SIZE=%%a
if defined SIZE echo Tamanio total: %SIZE% bytes

echo.

:: Abrir carpeta de salida
start "" "dist\DBManager"

pause
