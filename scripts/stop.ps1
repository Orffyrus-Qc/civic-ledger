$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose down
Write-Host "Canadian Political Leak sandbox stopped."
