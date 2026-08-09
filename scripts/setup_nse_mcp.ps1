$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$target = Join-Path $root ".vendor\\NSE-MCP"
$commit = "8fe76bc51fc2beb5013eb252592b285be8e1b5c0"

if (-not (Test-Path $target)) {
    git clone https://github.com/manitgupta/NSE-MCP.git $target
}

Push-Location $target
try {
    git checkout $commit
    pnpm install --frozen-lockfile=false
    pnpm run build
} finally {
    Pop-Location
}

