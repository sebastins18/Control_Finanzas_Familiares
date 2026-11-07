$ErrorActionPreference = 'Stop'
$repoE2E = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Push-Location $repoE2E
try {
    if (-not (Test-Path -LiteralPath '.venv-e2e\Scripts\python.exe')) {
        python -m venv .venv-e2e
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno Python.' }
    }
    & '.\.venv-e2e\Scripts\python.exe' -m pip install --disable-pip-version-check -r scripts/e2e/requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias E2E.' }
    $env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $repoE2E '.venv-e2e\browsers'
    & '.\.venv-e2e\Scripts\python.exe' -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo instalar Chromium.' }
} finally {
    Pop-Location
}
