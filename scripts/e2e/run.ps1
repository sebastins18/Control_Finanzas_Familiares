param(
    [string]$Output = ('evidencias/s4-' + (Get-Date -Format 'yyyyMMdd-HHmmss')),
    [switch]$Quick
)
$ErrorActionPreference = 'Stop'
$repoE2E = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Push-Location $repoE2E
try {
    $env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $repoE2E '.venv-e2e\browsers'
    if ($Quick) {
        & '.\.venv-e2e\Scripts\python.exe' scripts/e2e/run_e2e.py --pace 0 --output $Output
    } else {
        & '.\.venv-e2e\Scripts\python.exe' scripts/e2e/run_e2e.py --record --pace 10 --output $Output
    }
    if ($LASTEXITCODE -ne 0) { throw 'La ejecución E2E no terminó aprobada. Consulte los resultados del destino.' }
} finally {
    Pop-Location
}
