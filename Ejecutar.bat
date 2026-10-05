@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: no se encontro "python" en el PATH. Instalar Python 3.12 desde python.org.
    pause
    exit /b 1
)
python -c "import openseespy, numpy, pytest" 2>nul
if errorlevel 1 (
    echo Instalando dependencias de requirements.txt...
    python -m pip install -r requirements.txt || (pause & exit /b 1)
)

:menu
echo.
echo ================================================
echo  MCOC P1_G4 - Analisis OpenSees + Unity
echo ================================================
echo  1. Analizar y exportar resultados a Unity
echo  2. Ejecutar los tests (pytest)
echo  3. QA de verificacion (resultados\qa_semana06.json)
echo  4. Reconstruir el modelo desde los planos y exportar
echo  5. Abrir el viewer de Windows (Builds\Windows\P1G4_Viewer.exe)
echo  6. Abrir el proyecto Unity
echo  0. Salir
echo.
set "op="
set /p op="Opcion: "
if "%op%"=="1" python -X utf8 Proyecto1\scripts\exportar_resultados_unity.py
if "%op%"=="2" python -m pytest
if "%op%"=="3" python -X utf8 Proyecto1\scripts\qa_semana06.py
if "%op%"=="4" python -X utf8 Proyecto1\scripts\ajustar_modelo_planos.py
if "%op%"=="5" (
    if exist "Proyecto1\edificio_G4\Builds\Windows\P1G4_Viewer.exe" (
        start "" "Proyecto1\edificio_G4\Builds\Windows\P1G4_Viewer.exe"
    ) else (
        echo No hay build de Windows: compilar en Unity con MCOC/Build Windows ^(viewer^) o descargarlo de la release.
    )
)
if "%op%"=="6" call "%~dp0Abrir_Unity.bat"
if "%op%"=="0" exit /b 0
goto menu
