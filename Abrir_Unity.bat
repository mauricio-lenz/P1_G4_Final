@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ================================================
echo  Abriendo el proyecto Unity del repositorio
echo ================================================
echo.

rem Proyecto Unity real (Assets con escena + ProjectSettings)
set "projDir=%~dp0Proyecto1\edificio_G4"

if not exist "%projDir%\ProjectSettings\ProjectVersion.txt" (
    echo ERROR: No encontre el proyecto Unity en:
    echo   %projDir%
    pause
    exit /b 1
)

echo Proyecto Unity:
echo %projDir%
echo.

rem Lee la version de editor requerida
set "ver="
for /f "tokens=2 delims= " %%A in ('type "%projDir%\ProjectSettings\ProjectVersion.txt" ^| findstr /c:"m_EditorVersion:"') do (
    if not defined ver set "ver=%%A"
)

rem Localiza el ejecutable de Unity para esa version (Hub la instala en Program Files o LOCALAPPDATA)
set "unityExe="
if defined ver if exist "C:\Program Files\Unity\Hub\Editor\%ver%\Editor\Unity.exe" (
    set "unityExe=C:\Program Files\Unity\Hub\Editor\%ver%\Editor\Unity.exe"
)
if defined ver if not defined unityExe if exist "%LOCALAPPDATA%\Unity\Editor\%ver%\Editor\Unity.exe" (
    set "unityExe=%LOCALAPPDATA%\Unity\Editor\%ver%\Editor\Unity.exe"
)

if defined unityExe (
    echo Version requerida: %ver%
    echo Ejecutable: %unityExe%
    echo Abriendo Unity...
    start "" "%unityExe%" -projectPath "%projDir%"
) else (
    echo No encontre Unity.exe para la version %ver%.
    echo Abriendo la carpeta del proyecto para abrirlo desde Unity Hub...
    start "" "%projDir%"
)

echo.
pause
