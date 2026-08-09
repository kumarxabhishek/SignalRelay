#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="$root/.vendor/NSE-MCP"
commit="8fe76bc51fc2beb5013eb252592b285be8e1b5c0"

if [[ ! -d "$target/.git" ]]; then
  git clone https://github.com/manitgupta/NSE-MCP.git "$target"
fi
git -C "$target" fetch --depth 1 origin "$commit"
git -C "$target" checkout --detach "$commit"
corepack pnpm --dir "$target" install --frozen-lockfile=false
corepack pnpm --dir "$target" run build
