param([switch]$OpenBrowser)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
Set-Location -LiteralPath $projectRoot
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot '.env'))) {
    throw 'Missing .env. Follow the Docker setup in README.md before starting Smart Sales.'
}
$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCommand) { throw 'Docker Desktop is required. Install it before starting Smart Sales.' }
$dockerExecutable = $dockerCommand.Source
$env:DOCKER_CONFIG = Join-Path $projectRoot '.local\docker'
$env:DOCKER_HOST = 'npipe:////./pipe/docker_engine'
New-Item -ItemType Directory -Path $env:DOCKER_CONFIG -Force | Out-Null

function Test-LocalDocker {
    try {
        & $dockerExecutable info --format '{{.ServerVersion}}' *> $null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

if (-not (Test-LocalDocker)) {
    $desktopExecutable = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
    if (-not (Test-Path -LiteralPath $desktopExecutable)) { throw 'Docker Desktop executable was not found.' }
    Write-Host 'Starting Docker Desktop. Waiting for the local engine...'
    Start-Process -FilePath $desktopExecutable -WindowStyle Hidden
    $engineReady = $false
    for ($attempt = 0; $attempt -lt 45; $attempt++) {
        if (Test-LocalDocker) { $engineReady = $true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $engineReady) { throw 'Docker engine did not become ready. Open Docker Desktop and resolve its startup error, then retry.' }
}

Write-Host 'Starting Smart Sales with the existing Docker database...'
& $dockerExecutable compose up -d --build --wait --wait-timeout 120
if ($LASTEXITCODE -ne 0) { throw 'Smart Sales did not start. Read the Docker error above; existing volumes were preserved.' }

$appReady = $false
for ($attempt = 0; $attempt -lt 15; $attempt++) {
    try {
        $health = Invoke-WebRequest -Uri 'http://127.0.0.1:8002/health/' -UseBasicParsing -TimeoutSec 5
        if ($health.StatusCode -eq 200 -and (($health.Content | ConvertFrom-Json).status -eq 'ok')) {
            $login = Invoke-WebRequest -Uri 'http://127.0.0.1:8002/login/' -UseBasicParsing -TimeoutSec 5
            if ($login.StatusCode -eq 200) { $appReady = $true; break }
        }
    } catch { }
    Start-Sleep -Seconds 2
}
if (-not $appReady) { throw 'Containers started, but the website readiness check failed. Run docker compose logs web to inspect the error.' }

Write-Host 'Smart Sales is ready: http://127.0.0.1:8002'
Write-Host 'Demo username: demo_admin. The local password stays in .local/demo-password.txt.'
Write-Host 'The application keeps running when this window closes. Use docker compose stop to stop it.'
if ($OpenBrowser) { Start-Process -FilePath 'http://127.0.0.1:8002/login/' }
