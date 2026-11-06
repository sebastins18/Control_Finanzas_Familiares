#Requires -Version 5.1
<#
.SYNOPSIS
Preflight del candidato v0.9.0 desde Windows; no publica nada sin -Publicar.
Requiere git, gh autenticado (con permisos repo) y codigo local sincronizado.
#>
param(
    [string]$Version = "v0.9.0",
    [switch]$Publicar
)
$ErrorActionPreference = "Stop"
$Repo = "sebastins18/Control_Finanzas_Familiares"
if ($Version -notmatch '^v0\.9\.0$') { throw "Este script está limitado a v0.9.0; v1.0.0 requiere revisión final independiente." }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "Falta git" }
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw "Falta gh CLI" }
git rev-parse --show-toplevel | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Ejecutar dentro del repositorio Git" }

# Abortamos si hay modificaciones no confirmadas; los reportes locales S2/S4 deben quedar en .gitignore.
$status = @(git status --porcelain)
if ($LASTEXITCODE -ne 0 -or $status.Count -gt 0) {
    throw "Existen cambios locales sin registrar. Revisar 'git status' antes de versionar."
}
$actual = (git branch --show-current).Trim()
if ($actual -ne "main") { throw "Cambiar primero a main. Rama actual: $actual" }
git fetch origin main --tags
if ($LASTEXITCODE -ne 0) { throw "git fetch falló" }
$localSha = (git rev-parse HEAD).Trim()
$remoteSha = (git rev-parse refs/remotes/origin/main).Trim()
if ($localSha -ne $remoteSha) {
    throw "main local ($localSha) no coincide con origin/main ($remoteSha). Actualizar y revisar cambios."
}
$remoteTag = @(git ls-remote --tags origin "refs/tags/$Version")
if ($LASTEXITCODE -ne 0) { throw "No se pudo verificar tags remotos" }
if ($remoteTag.Count -gt 0) { throw "El tag $Version ya existe en remoto. No se sobrescribe." }
$localTag = @(git tag --list $Version)
if ($localTag.Count -gt 0) { throw "El tag $Version ya existe en local. Revisar antes de continuar." }

$runText = gh api "repos/$Repo/actions/runs?branch=main&per_page=1"
if ($LASTEXITCODE -ne 0) { throw "No se pudo verificar GitHub Actions" }
$data = $runText | ConvertFrom-Json
if (-not $data.workflow_runs -or $data.workflow_runs.Count -eq 0) { throw "GitHub Actions no tiene ejecuciones para main" }
$run = $data.workflow_runs[0]
if ($run.head_sha -ne $localSha -or $run.status -ne "completed" -or $run.conclusion -ne "success") {
    throw "CI no validado para el SHA actual ($localSha). Resultado: $($run.status)/$($run.conclusion), SHA $($run.head_sha)"
}

Write-Host "Preflight APROBADO: $Version -> $localSha; CI run $($run.id)"
if (-not $Publicar) {
    Write-Host "Modo seguro: no se creó ni publicó ningún tag."
    Write-Host "Una vez aprobado por el equipo: powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publicar_rc_s4.ps1 -Publicar"
    exit 0
}
git tag -a $Version -m "S4 - release candidate del Grupo 5"
if ($LASTEXITCODE -ne 0) { throw "No se pudo crear tag local" }
git push origin "refs/tags/$Version"
if ($LASTEXITCODE -ne 0) { throw "No se pudo publicar el tag; revisar situación local antes de reintentar." }
Write-Host "Publicado $Version -> $localSha. No se creó v1.0.0 ni se modificó CRNube."
