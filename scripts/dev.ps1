$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& npm.cmd run build --prefix frontend
if ($LASTEXITCODE -ne 0) { throw 'Falló la compilación frontend.' }
& .\.venv\Scripts\python.exe launcher.py
