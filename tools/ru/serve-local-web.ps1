# Run the local browser version in this terminal; Ctrl+C stops the server.
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$workspaceRoot = Split-Path -Parent $repoRoot
$bashPath = Join-Path $workspaceRoot '.tools/cygwin/bin/bash.exe'
$sourceRoot = Join-Path $repoRoot 'crawl-ref/source'
if (-not (Test-Path -LiteralPath $bashPath)) { throw 'Install the project Cygwin environment first.' }
if (-not (Test-Path -LiteralPath (Join-Path $sourceRoot 'crawl.exe'))) { throw 'Build the WebTiles engine first with make WEBTILES=y in Cygwin.' }
$configPath = Join-Path $sourceRoot 'webserver/config.yml'
if (-not (Test-Path -LiteralPath $configPath)) {
    @'
dgl_mode: false
bind_address: 127.0.0.1
bind_port: 8080
no_cache: true
'@ | Set-Content -LiteralPath $configPath -Encoding utf8
}
$env:DCSS_RU_SOURCE = $sourceRoot
Write-Host 'DCSS-RU: http://127.0.0.1:8080/ (Ctrl+C to stop)'
& $bashPath -lc 'cd "$(cygpath -u "$DCSS_RU_SOURCE")" && export LANG=C.UTF-8 && exec python3 webserver/server.py'
exit $LASTEXITCODE
