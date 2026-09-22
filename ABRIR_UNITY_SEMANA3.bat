@echo off
setlocal
cd /d "%~dp0"

echo Abriendo carpeta correcta de Unity para Semana 3...
echo.
echo Proyecto Unity:
echo %cd%\P1L2\unity_visualizador
echo.
start "" "%cd%\P1L2\unity_visualizador"
echo Se abrio la carpeta. En Unity Hub usa Add/Open project y selecciona esa carpeta.
echo No uses la carpeta vieja: edificio completo\unity_visualizador
echo.
pause
