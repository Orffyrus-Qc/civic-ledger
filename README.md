# Canadian Political Leak

Sandbox watchdog for **public** Canadian political finance, lobbying, contracts, campaign promises, and contradictions.

It does **not** dox private people. Home addresses, personal phones, SINs, people-search sites, and family private data are blocked.

## What it does now

- Pulls **structured public tables**: Open Canada contracts datastore, the official lobbying communications dump (live site is Cloudflare-blocked; cached + Internet Archive copy), Carney’s May 2025 mandate letter plus PCO 2015/2021 workbooks, OpenParliament bills/votes.
- Auto-searches the web through **SearXNG** (English + French, rotating queries).
- Dedups stories, hides junk/low-confidence/unverified by default, stamps **source dates**.
- Joins **vendors** that also appear as **lobbyists**.
- Matches findings to ingested **promise** rows.
- Local **Qwen3 8B** (~5.7 GB on GPU 1) analyzes one story at a time. Extracted table rows are labelled separately from model prose.
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

Or the C# launcher: `dotnet run --project launcher -c Release` (Start / Stop only).

Open [http://127.0.0.1:8088](http://127.0.0.1:8088)

Country dropdown, EN/FR, Findings, Money, Promises, Entities, Sources tray, Scans.

## Stop

```powershell
.\scripts\stop.ps1
```
