#Requires -Version 5.1
<#
.SYNOPSIS
Sincroniza los Issues reales de S1/S2/S3/S4 con GitHub Project #1 del Grupo 5.
Requiere gh CLI autenticado como usuario con permiso para editar el Project y scope project.
Solo asigna estados documentados; no fabrica responsables ni marca S1/S2 como Done.
Uso: .\scripts\sync_github_project_s1_s2.ps1 -HacerPublico
#>
param([switch]$HacerPublico)
$ErrorActionPreference = 'Stop'
$Owner = 'sebastins18'
$Repo = 'sebastins18/Control_Finanzas_Familiares'
$ProjectNumber = 1

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw 'Falta GitHub CLI. Instalar con: winget install --id GitHub.cli -e'
}
gh auth status
if ($LASTEXITCODE -ne 0) { throw 'Iniciar sesion con: gh auth login; conceder proyecto con gh auth refresh -s project' }
gh project view $ProjectNumber --owner $Owner --format json | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Sin acceso al Project. Ejecutar: gh auth refresh -s project' }

# Asociar repositorio existente al Project (si ya esta enlazado, no interrumpir).
gh project link $ProjectNumber --owner $Owner --repo $Repo 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host 'Project link: ya asociado o requiere permisos; revisar manualmente.' }

if ($HacerPublico) {
    gh project edit $ProjectNumber --owner $Owner --visibility PUBLIC | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo hacer publico el Project (requiere owner).' }
    Write-Host 'Visibilidad publica configurada; revisar acceso del profesor.'
}

function Get-Fields {
    $result = gh project field-list $ProjectNumber --owner $Owner --format json | ConvertFrom-Json
    return @($result.fields)
}
$fields = Get-Fields
foreach ($definition in @(
    @{ Name = 'Seguimiento'; Options = 'S1,S2,S3,S4' },
    @{ Name = 'Prioridad'; Options = 'Critica,Alta,Media' }
)) {
    if (-not ($fields | Where-Object { $_.name -eq $definition.Name })) {
        gh project field-create $ProjectNumber --owner $Owner --name $definition.Name --data-type SINGLE_SELECT --single-select-options $definition.Options | Out-Null
        if ($LASTEXITCODE -ne 0) { Write-Warning "No se pudo crear campo $($definition.Name)" }
        else { Write-Host "Campo creado: $($definition.Name)" }
    }
}
$fields = Get-Fields
$statusField = $fields | Where-Object { $_.name -eq 'Status' } | Select-Object -First 1

$items = @(
    @{No=1; Seguimiento='S1'; Prioridad='Critica'; Status='progress'},
    @{No=2; Seguimiento='S2'; Prioridad='Critica'; Status='progress'},
    @{No=3; Seguimiento='S3'; Prioridad='Alta'; Status='todo'},
    @{No=4; Seguimiento='S4'; Prioridad='Media'; Status='todo'},
    @{No=5; Seguimiento='S2'; Prioridad='Alta'; Status='done'; IsPR=$true},
    @{No=6; Seguimiento='S1'; Prioridad='Critica'; Status='progress'},
    @{No=7; Seguimiento='S2'; Prioridad='Critica'; Status='progress'},
    @{No=8; Seguimiento='S2'; Prioridad='Alta'; Status='progress'},
    @{No=9; Seguimiento='S1'; Prioridad='Critica'; Status='progress'},
    @{No=10; Seguimiento='S3'; Prioridad='Alta'; Status='todo'},
    @{No=11; Seguimiento='S1'; Prioridad='Alta'; Status='todo'}
)

function Set-ProjectOption([string]$url,[string]$fieldName,[string]$requested) {
    $field = $fields | Where-Object { $_.name -eq $fieldName } | Select-Object -First 1
    if (-not $field) { Write-Warning "Campo no encontrado: $fieldName"; return }
    $available = @($field.options | ForEach-Object { $_.name })
    $chosen = $available | Where-Object { $_ -eq $requested } | Select-Object -First 1
    if (-not $chosen) { Write-Warning "Opcion $requested no existe para $fieldName"; return }
    gh project item-edit $ProjectNumber --owner $Owner --url $url --field $fieldName --value $chosen | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Warning "No se pudo asignar $fieldName a $url" }
}
foreach ($item in $items) {
    $kind = if ($item.IsPR) { 'pull' } else { 'issues' }
    $url = "https://github.com/$Repo/$kind/$($item.No)"
    gh project item-add $ProjectNumber --owner $Owner --url $url --format json | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Warning "Revisar si ya esta agregado: $url" }
    Set-ProjectOption $url 'Seguimiento' $item.Seguimiento
    Set-ProjectOption $url 'Prioridad' $item.Prioridad
    if ($statusField) {
        $variants = switch ($item.Status) {
            'done'     { @('Done','Completed','Hecho','Terminado') }
            'progress' { @('In Progress','In progress','En progreso','En curso') }
            default    { @('Todo','To Do','Backlog','Por hacer') }
        }
        $candidate = $variants | Where-Object { $_ -in @($statusField.options | ForEach-Object name) } | Select-Object -First 1
        if ($candidate) { Set-ProjectOption $url 'Status' $candidate }
        else { Write-Warning "Status sin opcion equivalente para $url; editarlo manualmente." }
    }
    Write-Host "Revisado $url"
}

Write-Host '--- ESTADO FINAL DEL PROJECT ---'
gh project item-list $ProjectNumber --owner $Owner --limit 100 --format json
Write-Host 'Revisar campos, visibilidad y responsables reales desde https://github.com/users/sebastins18/projects/1'
