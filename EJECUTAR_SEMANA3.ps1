$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$scriptAllCandidates = @(
    (Join-Path $scriptDir "Proyecto1\scripts\carga_viva_sismo.py"),
    (Join-Path $scriptDir "scripts\carga_viva_sismo.py"),
    (Join-Path $scriptDir "P1L3\carga_viva_sismo.py")
)

$script = $null
foreach ($candidate in $scriptAllCandidates) {
    if (Test-Path -LiteralPath $candidate) {
        $script = $candidate
        break
    }
}

if ($null -eq $script) {
    Write-Host "ERROR: No encontre carga_viva_sismo.py en el repositorio."
    Write-Host "Ejecuta EJECUTAR_SEMANA3.bat desde la raiz del repositorio."
    return
}

$repo = Split-Path -Parent (Split-Path -Parent $script)
Set-Location $repo

$requirements = Join-Path $scriptDir "requirements.txt"
if (-not (Test-Path -LiteralPath $requirements)) {
    $requirements = Join-Path $scriptDir "Proyecto1\requirements.txt"
}

Write-Host "================================================"
Write-Host " Trabajo MCOP - Analisis estructural (OpenSees)"
Write-Host " Script : $script"
Write-Host "================================================"
Write-Host ""

if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    Write-Host "Creando entorno virtual .venv..."
    python -m venv .venv
}

Write-Host "Instalando/actualizando dependencias necesarias..."
if (Test-Path -LiteralPath $requirements) {
    & ".venv\Scripts\python.exe" -m pip install -r $requirements
} else {
    & ".venv\Scripts\python.exe" -m pip install numpy matplotlib openseespy plotly openpyxl
}

Write-Host ""
Write-Host "Ejecutando analisis..."
& ".venv\Scripts\python.exe" $script

Write-Host ""
Write-Host "Programa terminado. Esta ventana queda abierta."
Write-Host "Para volver a correrlo:"
Write-Host ".\.venv\Scripts\python.exe `"$script`""