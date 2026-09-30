$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose down
Write-Host "Civic Ledger sandbox stopped."
