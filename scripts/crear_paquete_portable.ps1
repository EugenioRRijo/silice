<#
.SYNOPSIS
    Empaqueta el prototipo en una carpeta y archivo .zip portable listo para transferir a otra maquina o memoria USB.
.DESCRIPTION
    Copia el codigo fuente, datos esenciales (incluyendo data/apu.db sembrado),
    lanzadores .bat y documentacion en una carpeta limpia 'dist_portable\APU_System_Portable'
    y genera un archivo 'APU_System_Portable.zip'.
#>

[CmdletBinding()]
param(
    [string]$Destino = "dist_portable",
    [switch]$IncluirVenv = $false
)

$ErrorActionPreference = "Stop"
$Raiz = Split-Path -Parent $PSScriptRoot
Set-Location $Raiz

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "     PREPARANDO PAQUETE PORTABLE: SISTEMA APU - AREN.IA   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Asegurar que data/apu.db exista
if (-not (Test-Path "data/apu.db")) {
    Write-Host "[INFO] Sembrando data/apu.db con el caso de demostracion..." -ForegroundColor Yellow
    uv run python scripts/seed_demo.py
}

# 2. Crear directorio de destino
$CarpetaBase = Join-Path $Raiz $Destino
$CarpetaApp = Join-Path $CarpetaBase "APU_System_Portable"
$ZipDestino = Join-Path $CarpetaBase "APU_System_Portable.zip"

if (Test-Path $CarpetaBase) {
    Write-Host "[INFO] Limpiando carpeta temporal de distribucion previa..." -ForegroundColor Gray
    Remove-Item -Recurse -Force $CarpetaBase
}
New-Item -ItemType Directory -Path $CarpetaApp -Force | Out-Null

# 3. Lista de carpetas y archivos a incluir
$Carpetas = @("core", "adapters", "ml", "ui", "api", "data", "scripts")
$Archivos = @(
    "pyproject.toml",
    "requirements.txt",
    "README.md",
    "INICIAR_PROTOTIPO.bat",
    "COMPARTIR_ONLINE.bat"
)

Write-Host "[INFO] Copiando componentes del proyecto..." -ForegroundColor Green
foreach ($c in $Carpetas) {
    if (Test-Path $c) {
        Write-Host "  -> Copiando $c..." -ForegroundColor Gray
        Copy-Item -Path $c -Destination (Join-Path $CarpetaApp $c) -Recurse -Force
    }
}

foreach ($a in $Archivos) {
    if (Test-Path $a) {
        Write-Host "  -> Copiando $a..." -ForegroundColor Gray
        Copy-Item -Path $a -Destination (Join-Path $CarpetaApp $a) -Force
    }
}

# 4. Crear archivo de instrucciones LEEME_PORTABLE.txt
$LeemeContenido = @"
========================================================================
             SISTEMA APU - AREN.IA (PROTOTIPO PORTABLE)
========================================================================

INSTRUCCIONES PARA OTRA MAQUINA:

1. MODO LOCAL (En esta maquina):
   - Haga doble clic sobre 'INICIAR_PROTOTIPO.bat'.
   - El script preparara el entorno automaticamente y abrira el navegador
     en http://localhost:8501 con el caso listo para operar.

2. MODO ONLINE (Compartir por internet a cualquier persona):
   - Haga doble clic sobre 'COMPARTIR_ONLINE.bat'.
   - Se abrira una ventana que generara un enlace publico seguro (HTTPS)
     terminado en '.trycloudflare.com'.
   - Comparta ese enlace con el evaluador, profesor o jurado para que
     puedan usar el sistema directamente desde su navegador o celular.

3. MODO NUBE (Streamlit Cloud):
   - Si prefiere tenerlo alojado permanentemente en la nube de forma gratuita,
     conecte este repositorio con https://share.streamlit.io usando 'ui/app.py'
     como archivo principal.

Requisitos minimos en la otra maquina:
- Windows 10 o Windows 11.
- Conexion a internet la primera vez que se ejecute (para descargar dependencias).
========================================================================
"@
Set-Content -Path (Join-Path $CarpetaApp "LEEME_PORTABLE.txt") -Value $LeemeContenido -Encoding UTF8

# 5. Opcional: incluir el .venv si se solicito expresamente (offline completo)
if ($IncluirVenv -and (Test-Path ".venv")) {
    Write-Host "[INFO] Copiando .venv para modo 100% offline (esto puede tomar varios minutos)..." -ForegroundColor Yellow
    Copy-Item -Path ".venv" -Destination (Join-Path $CarpetaApp ".venv") -Recurse -Force
}

# 6. Comprimir en archivo .zip
Write-Host "[INFO] Generando archivo comprimido $ZipDestino..." -ForegroundColor Cyan
Compress-Archive -Path "$CarpetaApp\*" -DestinationPath $ZipDestino -Force

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "               ¡PAQUETE PORTABLE CREADO CON EXITO!        " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Carpeta: $CarpetaApp"
Write-Host "Archivo ZIP listo para compartir: $ZipDestino"
Write-Host ""
