$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
Write-Host "Starting Canadian Political Leak sandbox..."
docker compose up -d --build
Write-Host ""
Write-Host "UI:     http://127.0.0.1:8088"
Write-Host "Search: http://127.0.0.1:8888"
Write-Host "Model:  qwen3:8b on GPU 1 (8 GB-class)"
Write-Host "Logs:   docker compose logs -f app llm-pull"
