@echo off
title Device Programming DB Manager - BUILD

REM Entrar correctamente aunque la ruta contenga espacios
pushd "%~dp0"

echo =========================
echo DEVICE PROGRAMMING DB MANAGER - BUILD
echo =========================
echo.

echo Directorio actual:
cd
echo.

echo =========================
echo LIMPIANDO COMPILACION ANTERIOR...
echo =========================

if exist build (
    echo Borrando carpeta build...
    rmdir /s /q build
)

if exist dist (
    echo Borrando carpeta dist...
    rmdir /s /q dist
)

if exist __pycache__ (
    echo Borrando carpeta __pycache__...
    rmdir /s /q __pycache__
)

echo.
echo =========================
echo COMPROBANDO ARCHIVOS...
echo =========================

if not exist main_app.py (
    echo ERROR: No existe main_app.py
    pause
    popd
    exit /b
)

if not exist app.spec (
    echo ERROR: No existe app.spec
    pause
    popd
    exit /b
)

if not exist app_icon.ico (
    echo AVISO: No existe app_icon.ico
    echo Se compilara sin icono si el SPEC lo requiere y falla.
    echo Este repositorio no incluye el icono original; añade el tuyo propio.
)

echo Archivos principales encontrados correctamente.
echo.

echo =========================
echo COMPILANDO DEVICE PROGRAMMING DB MANAGER...
echo =========================

pyinstaller app.spec

if errorlevel 1 (
    echo.
    echo =========================
    echo ERROR EN LA COMPILACION
    echo =========================
    pause
    popd
    exit /b
)

echo.
echo =========================
echo COMPILACION CORRECTA
echo =========================

if exist "dist\DeviceProgrammingDBManager.exe" (
    echo EXE generado correctamente:
    echo %cd%\dist\DeviceProgrammingDBManager.exe
) else (
    echo AVISO: No encuentro el EXE esperado en dist.
    echo Revisa el nombre generado dentro de la carpeta dist.
)

echo.
echo Abriendo carpeta dist...
explorer dist

echo.
pause

popd
