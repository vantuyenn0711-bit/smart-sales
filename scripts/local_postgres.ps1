param(
    [ValidateSet('start', 'stop', 'status')][string]$Action = 'start',
    [int]$Port = 55432
)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
# PostgreSQL's Windows launcher uses the ANSI API for re-execution. An ASCII
# junction in the temp directory lets it operate on the same project files when
# the checkout name contains Vietnamese characters. No database is moved.
if ($projectRoot -match '[^\x00-\x7F]') {
    $hasher = [Security.Cryptography.SHA256]::Create()
    try { $digest = $hasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($projectRoot)) } finally { $hasher.Dispose() }
    $suffix = ([BitConverter]::ToString($digest).Replace('-','')).Substring(0, 12)
    $junctionPath = Join-Path ([IO.Path]::GetTempPath()) "smart-sales-pg-$suffix"
    if (-not (Test-Path -LiteralPath $junctionPath)) {
        New-Item -ItemType Junction -Path $junctionPath -Target $projectRoot | Out-Null
    } else {
        $junction = Get-Item -LiteralPath $junctionPath
        if ($junction.LinkType -ne 'Junction' -or $junction.Target -notcontains $projectRoot) {
            throw 'The temporary PostgreSQL path is already occupied by an unrelated entry.'
        }
    }
    $projectRoot = $junctionPath
}
$localRoot = Join-Path $projectRoot '.local'
$dataRoot = Join-Path $localRoot 'postgres-data'
$binRoot = Join-Path $projectRoot '.tools\pgsql\bin'
$passwordPath = Join-Path $localRoot 'postgres-password.txt'
$pgCtl = Join-Path $binRoot 'pg_ctl.exe'
if (-not (Test-Path -LiteralPath $pgCtl)) {
    throw 'Portable PostgreSQL is not installed in .tools/pgsql. Use Docker Compose or extract the official PostgreSQL Windows binaries there.'
}
if ($Action -eq 'stop') {
    if (Test-Path -LiteralPath (Join-Path $dataRoot 'postmaster.pid')) {
        & $pgCtl -D $dataRoot -m smart -w stop
        if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL did not stop cleanly.' }
    }
    exit
}
function Test-ProjectCluster {
    param([string]$Password)
    $savedPassword = $env:PGPASSWORD
    $savedTimeout = $env:PGCONNECT_TIMEOUT
    $savedErrorAction = $ErrorActionPreference
    try {
        $env:PGPASSWORD = $Password
        $env:PGCONNECT_TIMEOUT = '2'
        $ErrorActionPreference = 'Continue'
        $runningData = & (Join-Path $binRoot 'psql.exe') -h 127.0.0.1 -p $Port -U smart_sales -d postgres -tAXc 'SHOW data_directory' 2>$null
        $connectStatus = $LASTEXITCODE
        $ErrorActionPreference = $savedErrorAction
        if ($connectStatus -ne 0) { return $false }
        $actualData = [IO.Path]::GetFullPath(([string]$runningData).Trim().Replace('/', '\'))
        if ($actualData.TrimEnd('\') -ne $dataRoot.TrimEnd('\')) {
            throw 'A different PostgreSQL cluster is using this port. No server was started or stopped.'
        }
        return $true
    } finally {
        $ErrorActionPreference = $savedErrorAction
        $env:PGPASSWORD = $savedPassword
        $env:PGCONNECT_TIMEOUT = $savedTimeout
    }
}
if ($Action -eq 'status') {
    if ((Test-Path -LiteralPath $passwordPath) -and (Test-ProjectCluster -Password ([IO.File]::ReadAllText($passwordPath).Trim()))) {
        Write-Host "Project PostgreSQL is ready on 127.0.0.1:$Port (verified cluster)."
        exit 0
    }
    Write-Host 'Project PostgreSQL is not reachable.'
    exit 3
}
New-Item -ItemType Directory -Path $localRoot -Force | Out-Null
if (-not (Test-Path -LiteralPath $passwordPath)) {
    if (Test-Path -LiteralPath (Join-Path $dataRoot 'PG_VERSION')) {
        throw 'Existing PostgreSQL data found without its password file. Nothing was reset. Supply the original credentials.'
    }
    $secretBytes = New-Object byte[] 32
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($secretBytes) } finally { $generator.Dispose() }
    $databasePassword = [Convert]::ToBase64String($secretBytes).TrimEnd('=').Replace('+','-').Replace('/','_')
    [IO.File]::WriteAllText($passwordPath, $databasePassword, [Text.Encoding]::ASCII)
}
$databasePassword = [IO.File]::ReadAllText($passwordPath).Trim()
if (-not (Test-Path -LiteralPath (Join-Path $dataRoot 'PG_VERSION'))) {
    New-Item -ItemType Directory -Path $dataRoot -Force | Out-Null
    & (Join-Path $binRoot 'initdb.exe') -D $dataRoot -U smart_sales --encoding=UTF8 --locale=C --auth-host=scram-sha-256 --auth-local=scram-sha-256 --pwfile=$passwordPath
    if ($LASTEXITCODE -ne 0) { throw 'initdb failed. Existing files were preserved for inspection.' }
}
if (-not (Test-ProjectCluster -Password $databasePassword)) {
    & $pgCtl -D $dataRoot -l (Join-Path $localRoot 'postgres.log') -o "-h 127.0.0.1 -p $Port" -w start
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL failed to start; inspect .local/postgres.log.' }
}
$previousPassword = $env:PGPASSWORD
try {
    $env:PGPASSWORD = $databasePassword
    $databaseExists = & (Join-Path $binRoot 'psql.exe') -h 127.0.0.1 -p $Port -U smart_sales -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='smart_sales'"
    if ($LASTEXITCODE -ne 0) { throw 'Could not connect to local PostgreSQL.' }
    if ($databaseExists -ne '1') {
        & (Join-Path $binRoot 'createdb.exe') -h 127.0.0.1 -p $Port -U smart_sales -E UTF8 smart_sales
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the project database.' }
    }
} finally { $env:PGPASSWORD = $previousPassword }
$environmentPath = Join-Path $projectRoot '.env'
if (-not (Test-Path -LiteralPath $environmentPath)) {
    $keyBytes = New-Object byte[] 48
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($keyBytes) } finally { $generator.Dispose() }
    $djangoKey = [Convert]::ToBase64String($keyBytes)
    $environmentText = "DJANGO_SECRET_KEY=$djangoKey`nDJANGO_DEBUG=true`nDEMO_MODE=true`nDATABASE_URL=postgresql://smart_sales:${databasePassword}@127.0.0.1:$Port/smart_sales`nPOSTGRES_PASSWORD=$databasePassword`n"
    [IO.File]::WriteAllText($environmentPath, $environmentText, (New-Object Text.UTF8Encoding($false)))
}
Write-Host "Project PostgreSQL is ready on 127.0.0.1:$Port. Credentials stay in ignored local files."
