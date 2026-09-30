$ErrorActionPreference = "Stop"
$Installer = $PSScriptRoot
$Root = (Resolve-Path (Join-Path $Installer "..")).Path
$Payload = Join-Path $Installer "payload"
$OutDir = Join-Path $Installer "bin"

Write-Host "Stack root: $Root"
Write-Host "Publishing launcher (self-contained)..."
dotnet publish (Join-Path $Root "launcher\CivicLedger.csproj") `
    -c Release -r win-x64 --self-contained true `
    -p:PublishSingleFile=true `
    -p:EnableCompressionInSingleFile=true `
    -p:IncludeNativeLibrariesForSelfExtract=true `
    -p:DebugType=none `
    -o (Join-Path $Installer "launcher-pub")

if (Test-Path $Payload) { Remove-Item $Payload -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Payload, (Join-Path $Payload "cache") | Out-Null

Copy-Item (Join-Path $Installer "launcher-pub\CivicLedger.exe") (Join-Path $Payload "CivicLedger.exe")
Copy-Item (Join-Path $Root "docker-compose.yml") $Payload
Copy-Item (Join-Path $Root "README.md") $Payload
Copy-Item (Join-Path $Root "scripts") (Join-Path $Payload "scripts") -Recurse
Copy-Item (Join-Path $Root "searxng") (Join-Path $Payload "searxng") -Recurse
Copy-Item (Join-Path $Root "app") (Join-Path $Payload "app") -Recurse
Get-ChildItem $Payload -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem $Payload -Recurse -Include *.pdb,*.pyc | Remove-Item -Force
Set-Content -Path (Join-Path $Payload "cache\.gitkeep") -Value ""

Write-Host "Building MSI..."
dotnet build (Join-Path $Installer "CplSetup.wixproj") -c Release -p:PayloadDir=$Payload -p:OutputPath=$OutDir\

$msi = Get-ChildItem $OutDir -Filter *.msi -Recurse | Select-Object -First 1
if (-not $msi) { throw "MSI was not produced." }
Write-Host "MSI: $($msi.FullName) ($([math]::Round($msi.Length/1MB,1)) MB)"
