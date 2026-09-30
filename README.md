# Civic Ledger

Sandbox watchdog for **public** political finance, lobbying, contracts, campaign promises, and contradictions. Canada has structured feeds (Open Canada, OpenParliament, lobbying dump, mandate scoreboard); other countries use official-domain search.

It does **not** dox private people. Home addresses, personal phones, SINs, people-search sites, and family private data are blocked.

## What it does

- Pulls **structured public tables** (Canada): Open Canada contracts, lobbying communications dump, Carney 2025 mandate letter, OpenParliament bills/votes.
- Auto-searches the web through **SearXNG** (English + French, rotating queries).
- Country switch, bilingual search, promise scoreboard, vendor ↔ lobbyist joins.
- Local **Qwen3 8B** analyzes one story at a time. Extracted table rows are labelled separately from model prose.
- Human **confirm / reject**. SQLite backups under `/data/backups`.

## Stack

| Service | Container | Bind |
|---|---|---|
| Web UI + scanner | `cpl-app` | `127.0.0.1:8088` |
| Web search server | `cpl-searxng` | `127.0.0.1:8888` |
| Local LLM | `cpl-llm` | internal only |

## Start

Needs Docker Desktop with GPU access, then:

```powershell
.\scripts\start.ps1
```

Or the C# launcher: `dotnet run --project launcher -c Release` (Start / Stop, pick an installed model, or confirm before downloading `qwen3:8b`).

**New Windows PC:** run [installer/dist/CivicLedgerSetup.exe](installer/dist/CivicLedgerSetup.exe) with [installer/dist/CivicLedgerSetup.msi](installer/dist/CivicLedgerSetup.msi) in the same folder. The wizard explains and checks **WSL 2** (a major Windows feature Docker needs), **Docker Desktop**, and **Ollama**, then installs Civic Ledger. Reboot if Windows asks after WSL 2. Docker must be running before you click Start.

**Uninstall:** Start menu → Uninstall Civic Ledger, or `CivicLedger.exe /uninstall`. Civic Ledger is selected by default. Docker, Ollama, and WSL 2 are optional and warned separately (WSL 2 requires typing `REMOVE`).

> **Not tested yet.** The Windows installer (setup wizard + MSI) and the full uninstaller have not been verified on a clean PC. Use them at your own risk. Prefer keeping WSL 2 / Docker / Ollama unless you are sure you want those Windows components removed.

Rebuild installers with `installer\build.ps1`.

Open [http://127.0.0.1:8088](http://127.0.0.1:8088)

Country dropdown, EN/FR, Findings, Money, Promises, Entities, Sources tray, Scans.

## Stop

```powershell
.\scripts\stop.ps1
```
