$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$compiler = Join-Path $projectRoot '.tools\tailwindcss.exe'
if (-not (Test-Path -LiteralPath $compiler) -or (Get-Item -LiteralPath $compiler).Length -eq 0) {
    $nodeRoot = Join-Path $projectRoot '.tools\node-v22.15.0-win-x64'
    $node = Join-Path $nodeRoot 'node.exe'
    $cli = Join-Path $projectRoot 'node_modules\@tailwindcss\cli\dist\index.mjs'
    if ((Test-Path -LiteralPath $node) -and (Test-Path -LiteralPath $cli)) {
        & $node $cli -i (Join-Path $projectRoot 'assets\css\tailwind.css') -o (Join-Path $projectRoot 'static\css\tailwind.css') --minify
        if ($LASTEXITCODE -ne 0) { throw 'Tailwind CSS compilation failed.' }
        exit
    }
    $available = Get-Command tailwindcss -ErrorAction SilentlyContinue
    if (-not $available) { throw 'Install the standalone Tailwind CSS CLI or place it at .tools/tailwindcss.exe.' }
    $compiler = $available.Source
}
& $compiler -i (Join-Path $projectRoot 'assets\css\tailwind.css') -o (Join-Path $projectRoot 'static\css\tailwind.css') --minify
if ($LASTEXITCODE -ne 0) { throw 'Tailwind CSS compilation failed.' }
