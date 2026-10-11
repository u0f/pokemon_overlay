param([string]$Python='python')
$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    & $Python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Instala Python 3.12 o posterior, o indica -Python con su ruta.' }
}
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias Python.' }
& npm.cmd ci --prefix frontend
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias frontend.' }
& npm.cmd run build --prefix frontend
if ($LASTEXITCODE -ne 0) { throw 'Falló la compilación frontend.' }
Write-Host 'Instalación terminada. Abre Iniciar PokeStream.cmd.'
