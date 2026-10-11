$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& .\.venv\Scripts\python.exe scripts/sync_bridge_profiles.py
if ($LASTEXITCODE -ne 0) { throw 'Falló la sincronización de perfiles Lua.' }
& npm.cmd run build --prefix frontend
if ($LASTEXITCODE -ne 0) { throw 'Falló la compilación frontend.' }
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --onefile --windowed --name PokeStream --icon 'assets/pokestream.ico' --add-data 'frontend/dist;frontend/dist' --add-data 'bridge;bridge' --collect-all uvicorn launcher.py
if ($LASTEXITCODE -ne 0) { throw 'Falló PyInstaller.' }
Write-Host 'Ejecutable: dist\PokeStream.exe. No incluye emuladores, ROMs, partidas ni assets extraídos.'
