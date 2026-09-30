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
$destMsi = Join-Path $Installer "CivicLedgerSetup.msi"
try {
    Copy-Item $msi.FullName $destMsi -Force
} catch {
    Write-Host "Note: could not overwrite $destMsi (file in use). Using $($msi.FullName)"
    $destMsi = $msi.FullName
}
Write-Host "MSI: $($msi.FullName) ($([math]::Round($msi.Length/1MB,1)) MB)"

Write-Host "Publishing setup wizard (Docker + Ollama checks)..."
$setupOut = Join-Path $Installer "setup-pub"
dotnet publish (Join-Path $Installer "setup\CivicLedgerSetup.csproj") `
    -c Release -r win-x64 --self-contained true `
    -p:PublishSingleFile=true `
    -p:EnableCompressionInSingleFile=true `
    -p:IncludeNativeLibrariesForSelfExtract=true `
    -p:DebugType=none `
    -o $setupOut
$dist = Join-Path $Installer "dist"
New-Item -ItemType Directory -Force -Path $dist | Out-Null
Copy-Item (Join-Path $setupOut "CivicLedgerSetup.exe") (Join-Path $dist "CivicLedgerSetup.exe") -Force
Copy-Item $msi.FullName (Join-Path $dist "CivicLedgerSetup.msi") -Force
Copy-Item (Join-Path $dist "CivicLedgerSetup.exe") (Join-Path $Installer "CivicLedgerSetup.exe") -Force
Copy-Item $msi.FullName (Join-Path $setupOut "CivicLedgerSetup.msi") -Force
Write-Host "Setup: $(Join-Path $dist 'CivicLedgerSetup.exe')"
Write-Host "New PCs: run dist\CivicLedgerSetup.exe (asks for Docker and Ollama, then the MSI)."
