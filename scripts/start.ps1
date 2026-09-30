$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
Write-Host "Starting Civic Ledger sandbox (no model download)..."
docker compose up -d --build
Write-Host ""
Write-Host "UI:     http://127.0.0.1:8088"
Write-Host "Search: http://127.0.0.1:8888"
Write-Host "Pick a model in the Civic Ledger launcher, or: docker exec cpl-llm ollama pull qwen3:8b"
Write-Host "Logs:   docker compose logs -f app"
