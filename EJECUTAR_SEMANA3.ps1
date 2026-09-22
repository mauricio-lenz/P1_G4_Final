$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$semana3Script = "P1L3\carga_viva_sismo.py"
$repoCandidates = @(
    $scriptDir,
    (Join-Path $scriptDir "Trabajo-MCOC-main"),
    (Join-Path $scriptDir "Trabajo-MCOC"),
    (Join-Path $env:USERPROFILE "Downloads\Trabajo-MCOC-main"),
    (Join-Path $env:USERPROFILE "Downloads\Trabajo-MCOC"),
    (Join-Path $env:USERPROFILE "Desktop\Trabajo-MCOC-main"),
    (Join-Path $env:USERPROFILE "Desktop\Trabajo-MCOC")
)

$repo = $null
foreach ($candidate in $repoCandidates) {
    if (Test-Path -LiteralPath (Join-Path $candidate $semana3Script)) {
        $repo = $candidate
        break
    }
}

if ($null -eq $repo) {
    Write-Host "ERROR: No encontre la carpeta del repositorio Trabajo-MCOC."
    Write-Host "Descomprime el ZIP completo y ejecuta EJECUTAR_SEMANA3.bat desde dentro de Trabajo-MCOC-main."
    Write-Host "Ejemplo: Downloads\Trabajo-MCOC-main\EJECUTAR_SEMANA3.bat"
    return
}

Set-Location $repo

Write-Host "================================================"
Write-Host " Trabajo MCOC - Semana 3"
Write-Host " Carga viva, sismo, superposicion y capacidad HA"
Write-Host "================================================"
Write-Host ""

if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    Write-Host "Creando entorno virtual .venv..."
    python -m venv .venv
}

Write-Host "Instalando/actualizando dependencias necesarias..."
& ".venv\Scripts\python.exe" -m pip install openseespy matplotlib

Write-Host ""
Write-Host "Abriendo menu interactivo Semana 3..."
& ".venv\Scripts\python.exe" $semana3Script

Write-Host ""
Write-Host "Programa terminado. Esta ventana queda abierta."
Write-Host "Si quieres correrlo otra vez, escribe:"
Write-Host ".\.venv\Scripts\python.exe 'P1L3\carga_viva_sismo.py'"
