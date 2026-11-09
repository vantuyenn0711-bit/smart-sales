param([int]$Port = 8002, [switch]$SeedDemo)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
Set-Location -LiteralPath $projectRoot
$env:PYTHONUTF8 = '1'
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Create the Python 3.13 environment with uv sync --frozen before running this script. See README.md.'
}
$localLibpq = Join-Path $projectRoot '.tools\pgsql\bin'
if (Test-Path -LiteralPath (Join-Path $localLibpq 'libpq.dll')) {
    # The supported Python adapter uses the official portable libpq on Windows.
    $env:PSYCOPG_IMPL = 'python'
    $env:PATH = $localLibpq + ';' + $env:PATH
}
if (Test-Path -LiteralPath (Join-Path $projectRoot '.local\postgres-data\PG_VERSION')) {
    & (Join-Path $PSScriptRoot 'local_postgres.ps1') start
    if ($LASTEXITCODE -ne 0) { throw 'Project PostgreSQL could not start.' }
}
& $python manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { throw 'Migration failed; the web server was not started.' }
if ($SeedDemo) {
    & $python scripts/create_demo.py
    if ($LASTEXITCODE -ne 0) { throw 'Demo seed failed; existing data was preserved.' }
}
Write-Host "Smart Sales local URL: http://127.0.0.1:$Port"
Write-Host 'Press Ctrl+C to stop the web server. PostgreSQL data stays in .local/postgres-data.'
& $python manage.py runserver "127.0.0.1:$Port" --noreload
exit $LASTEXITCODE
