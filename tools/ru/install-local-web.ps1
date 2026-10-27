# User-run setup for the local WebTiles compatibility environment.
# No administrator privileges, Windows features, shortcuts or PATH changes.
param([string]$Workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..')))
$ErrorActionPreference = 'Stop'
$runtimeRoot = Join-Path $Workspace '.tools/cygwin'
$cacheRoot = Join-Path $Workspace '.tools/cygwin-cache'
$setupPath = Join-Path $Workspace '.tools/setup-x86_64.exe'
New-Item -ItemType Directory -Force $cacheRoot | Out-Null
Invoke-WebRequest -Uri 'https://cygwin.com/setup-x86_64.exe' -OutFile $setupPath
$packages = 'gcc-g++,make,python3,python3-pip,python3-devel,liblua5.4-devel,libncurses-devel,libsqlite3-devel,zlib-devel,libpng-devel,flex,bison,pkg-config,git,unzip'
$process = Start-Process -FilePath $setupPath -WindowStyle Hidden -Wait -PassThru -ArgumentList @(
    '--quiet-mode', '--no-admin', '--no-shortcuts', '--root', $runtimeRoot,
    '--local-package-dir', $cacheRoot,
    '--site', 'https://mirrors.kernel.org/sourceware/cygwin/', '--packages', $packages
)
if ($process.ExitCode -ne 0) { throw "Cygwin setup exited with $($process.ExitCode)" }
Write-Host "Cygwin ready: $runtimeRoot"
