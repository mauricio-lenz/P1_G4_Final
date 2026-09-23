@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ================================================
echo  Abriendo el proyecto Unity del repositorio
echo ================================================
echo.

rem Busca cualquier proyecto Unity (carpeta con ProjectSettings\ProjectVersion.txt)
set "projDir="
for /r "%~dp0" %%F in (ProjectVersion.txt) do (
    if not defined projDir (
        for %%I in ("%%~dpF..\") do set "projDir=%%~fI"
    )
)

if not defined projDir (
    echo ERROR: No encontre ningun proyecto Unity en %~dp0
    echo Coloca este script dentro del repositorio del proyecto.
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

rem Localiza el ejecutable de Unity para esa version
set "unityExe="
if defined ver if exist "%LOCALAPPDATA%\Unity\Editor\%ver%\Editor\Unity.exe" (
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
