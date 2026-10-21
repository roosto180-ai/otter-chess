param([int]$Port = 3000)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Join-Path $PSScriptRoot 'docs')
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Install Node.js 22.18+ or 24 LTS, then run this script again.' }
if (-not (Test-Path -LiteralPath node_modules/next)) { & npm.cmd ci; if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' } }
$env:NEXT_TELEMETRY_DISABLED='1'
$env:NEXT_PUBLIC_BASE_PATH=''
$env:NEXT_PUBLIC_SITE_URL="http://127.0.0.1:$Port"
& npm.cmd run build
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
$env:PORT="$Port"
& npm.cmd run serve
