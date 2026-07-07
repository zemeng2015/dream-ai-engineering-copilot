# SPDX-License-Identifier: Apache-2.0

param(
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [string]$EnvFile = "",
    [Parameter(Mandatory = $false)]
    [string]$EnvExamplePath = ".env.qwencloud.local.example",
    [Parameter(Mandatory = $false)]
    [string]$WorkflowPath = ".github/workflows/qwencloud-release.yml",
    [Parameter(Mandatory = $false)]
    [string]$GitHubSecretsHandoffPath = "scripts/qwencloud-github-secrets-handoff.ps1",
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
. (Join-Path $PSScriptRoot "qwencloud-env.ps1")

$reportJson = Join-Path $OutputDir "release-config-audit-$timestamp.json"
$reportMd = Join-Path $OutputDir "release-config-audit-$timestamp.md"
$checks = @()
$importedEnvNames = @()

$requiredRuntimeEnv = @(
    "DASHSCOPE_API_KEY",
    "ALIBABA_CLOUD_REGION",
    "ALIBABA_CLOUD_CONTAINER_IMAGE",
    "ALIBABA_CONTAINER_REGISTRY_USERNAME",
    "ALIBABA_CONTAINER_REGISTRY_PASSWORD"
)
$optionalRuntimeEnv = @(
    "QWEN_BASE_URL",
    "QWEN_MODEL"
)
$requiredGitHubSecrets = @(
    "ALIBABA_CLOUD_ACCESS_KEY_ID",
    "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
    "ALIBABA_CLOUD_REGION",
    "ALIBABA_CLOUD_CONTAINER_IMAGE",
    "ALIBABA_CONTAINER_REGISTRY_USERNAME",
    "ALIBABA_CONTAINER_REGISTRY_PASSWORD",
    "DASHSCOPE_API_KEY"
)
$optionalGitHubSecrets = @(
    "ALIBABA_CLOUD_ACCOUNT_ID",
    "QWEN_BASE_URL",
    "QWEN_MODEL"
)
$allTemplateNames = @($requiredGitHubSecrets + $optionalGitHubSecrets | Select-Object -Unique)

function Add-Check([string]$Name, [bool]$Ok, [string]$Details, [bool]$Required = $true) {
    $script:checks += [ordered]@{
        name = $Name
        ok = $Ok
        required = $Required
        details = $Details
    }
}

function Read-TextOrEmpty([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path)) {
        return ""
    }

    return Get-Content -LiteralPath $Path -Raw
}

function Has-Env([string]$Name) {
    return Test-QwenCloudEnvValuePresent -Name $Name
}

function Test-RegionFormat([string]$Region) {
    if ([string]::IsNullOrWhiteSpace($Region)) {
        return [pscustomobject]@{ ok = $false; details = "missing" }
    }
    if ($Region -match "[<>]") {
        return [pscustomobject]@{ ok = $false; details = "placeholder" }
    }

    return [pscustomobject]@{
        ok = ($Region -match "^[a-z]+-[a-z]+-\d+$")
        details = "region=$Region"
    }
}

function Test-ContainerImageFormat([string]$Image) {
    if ([string]::IsNullOrWhiteSpace($Image)) {
        return [pscustomobject]@{ ok = $false; details = "missing" }
    }
    if ($Image -match "\s|[<>]" -or $Image -match "^https?://") {
        return [pscustomobject]@{ ok = $false; details = "invalid characters or placeholder" }
    }

    $parts = @($Image -split "/")
    $registryHost = if ($parts.Count -gt 0) { $parts[0] } else { "" }
    $last = if ($parts.Count -gt 0) { $parts[$parts.Count - 1] } else { "" }
    $hostOk = $registryHost -match "\." -and $registryHost -notmatch "[:]"
    $pathOk = $parts.Count -ge 3
    $tagOk = $last -match "^[^:]+:[^:]+$"
    return [pscustomobject]@{
        ok = ($hostOk -and $pathOk -and $tagOk)
        details = "registryHost=$(if ($registryHost) { $registryHost } else { '<missing>' }); pathParts=$($parts.Count); tagPresent=$tagOk"
    }
}

function Test-OptionalUrlEnv([string]$Name) {
    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) {
        return [pscustomobject]@{ ok = $true; details = "optional default available" }
    }

    return [pscustomobject]@{
        ok = ($value -match "^https?://" -and $value -notmatch "[<>]")
        details = if ($value -match "^https?://" -and $value -notmatch "[<>]") { "set" } else { "invalid optional URL" }
    }
}

if (-not [string]::IsNullOrWhiteSpace($EnvFile)) {
    $envFileExists = Test-Path -LiteralPath $EnvFile
    Add-Check -Name "env_file_present" -Ok $envFileExists -Details $(if ($envFileExists) { $EnvFile } else { "missing: $EnvFile" })
    if ($envFileExists) {
        try {
            $importedEnvNames = @(Import-QwenCloudEnvFile -Path $EnvFile)
            Add-Check -Name "env_file_importable" -Ok $true -Details "imported=$($importedEnvNames.Count)"
        }
        catch {
            Add-Check -Name "env_file_importable" -Ok $false -Details $_.Exception.Message
        }
    }
    else {
        Add-Check -Name "env_file_importable" -Ok $false -Details "env file missing"
    }
}
else {
    Add-Check -Name "env_file_optional" -Ok $true -Details "not provided; using process environment" -Required $false
}

foreach ($name in $requiredRuntimeEnv) {
    Add-Check -Name "env.$name.present" -Ok (Has-Env $name) -Details $(if (Has-Env $name) { "set" } else { "missing or placeholder" })
}
foreach ($name in $optionalRuntimeEnv) {
    Add-Check -Name "env.$name.optional" -Ok $true -Details $(if (Has-Env $name) { "set" } else { "optional default available" }) -Required $false
}

$regionCheck = Test-RegionFormat -Region ([Environment]::GetEnvironmentVariable("ALIBABA_CLOUD_REGION"))
Add-Check -Name "env.ALIBABA_CLOUD_REGION.format" -Ok $regionCheck.ok -Details $regionCheck.details

$imageCheck = Test-ContainerImageFormat -Image ([Environment]::GetEnvironmentVariable("ALIBABA_CLOUD_CONTAINER_IMAGE"))
Add-Check -Name "env.ALIBABA_CLOUD_CONTAINER_IMAGE.format" -Ok $imageCheck.ok -Details $imageCheck.details

$baseUrlCheck = Test-OptionalUrlEnv -Name "QWEN_BASE_URL"
Add-Check -Name "env.QWEN_BASE_URL.url_or_default" -Ok $baseUrlCheck.ok -Details $baseUrlCheck.details -Required $false

$workflowText = Read-TextOrEmpty -Path $WorkflowPath
Add-Check -Name "workflow_present" -Ok (-not [string]::IsNullOrWhiteSpace($workflowText)) -Details $(if ($workflowText) { $WorkflowPath } else { "missing: $WorkflowPath" })
foreach ($name in $requiredGitHubSecrets) {
    Add-Check -Name "workflow.secret.$name" -Ok ($workflowText -match [regex]::Escape("secrets.$name")) -Details "required workflow secret mapping"
}
foreach ($name in $optionalGitHubSecrets) {
    Add-Check -Name "workflow.secret.$name" -Ok ($workflowText -match [regex]::Escape("secrets.$name")) -Details "optional workflow secret mapping" -Required $false
}
Add-Check -Name "workflow.validates_public_demo_video" -Ok ($workflowText -match "qwencloud-video-upload-status\.ps1") -Details "workflow validates Devpost video URL"
Add-Check -Name "workflow.generates_release_summary_after_bundle" -Ok ($workflowText.IndexOf("qwencloud-final-upload-bundle.ps1") -ge 0 -and $workflowText.IndexOf("qwencloud-release-summary.ps1") -gt $workflowText.IndexOf("qwencloud-final-upload-bundle.ps1")) -Details "release summary runs after final upload bundle"

$handoffText = Read-TextOrEmpty -Path $GitHubSecretsHandoffPath
Add-Check -Name "github_secrets_handoff_present" -Ok (-not [string]::IsNullOrWhiteSpace($handoffText)) -Details $(if ($handoffText) { $GitHubSecretsHandoffPath } else { "missing: $GitHubSecretsHandoffPath" })
foreach ($name in $requiredGitHubSecrets) {
    Add-Check -Name "github_handoff.secret.$name" -Ok ($handoffText -match [regex]::Escape($name)) -Details "required handoff secret name"
}
foreach ($name in $optionalGitHubSecrets) {
    Add-Check -Name "github_handoff.secret.$name" -Ok ($handoffText -match [regex]::Escape($name)) -Details "optional handoff secret name" -Required $false
}

$exampleText = Read-TextOrEmpty -Path $EnvExamplePath
Add-Check -Name "env_example_present" -Ok (-not [string]::IsNullOrWhiteSpace($exampleText)) -Details $(if ($exampleText) { $EnvExamplePath } else { "missing: $EnvExamplePath" })
foreach ($name in $allTemplateNames) {
    Add-Check -Name "env_example.name.$name" -Ok ($exampleText -match "(?m)^$([regex]::Escape($name))=") -Details "template declaration"
}

$requiredFailures = @($checks | Where-Object { $_.required -and -not $_.ok })
$ready = $requiredFailures.Count -eq 0
$status = if ($ready) { "READY" } else { "DRAFT" }
$missingRequiredChecks = @($requiredFailures | ForEach-Object { $_.name })

$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = $status
    readyForReleaseConfig = $ready
    envFile = $EnvFile
    importedEnvNames = $importedEnvNames
    requiredRuntimeEnv = $requiredRuntimeEnv
    optionalRuntimeEnv = $optionalRuntimeEnv
    requiredGitHubSecrets = $requiredGitHubSecrets
    optionalGitHubSecrets = $optionalGitHubSecrets
    missingRequiredChecks = $missingRequiredChecks
    checks = $checks
    reportJson = $reportJson
    reportMarkdown = $reportMd
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Release Config Audit ($timestamp)",
    "",
    "- Status: $status",
    "- Ready for release config: $ready",
    "- Env file: $(if ($EnvFile) { $EnvFile } else { '<process environment>' })",
    "- Workflow: $WorkflowPath",
    "- GitHub secrets handoff: $GitHubSecretsHandoffPath",
    "",
    "## Safety",
    "",
    "- This report records only variable names, presence, and format signals.",
    "- It does not write API keys, access keys, registry passwords, or full environment values.",
    "",
    "## Checks",
    "",
    "| Check | Required | Result | Details |",
    "|---|---:|---:|---|"
)
foreach ($check in $checks) {
    $lines += "| $($check.name) | $(if ($check.required) { 'yes' } else { 'no' }) | $(if ($check.ok) { 'PASS' } else { 'FAIL' }) | $($check.details -replace '\|', '/') |"
}

if ($missingRequiredChecks.Count -gt 0) {
    $lines += @(
        "",
        "## Missing Required Checks",
        ""
    )
    foreach ($name in $missingRequiredChecks) {
        $lines += "- $name"
    }
}

$lines += @(
    "",
    "## Next Commands",
    "",
    '```powershell',
    'Copy-Item .env.qwencloud.local.example .env.qwencloud.local',
    '# Fill .env.qwencloud.local locally; do not commit it.',
    'scripts/qwencloud-release-config-audit.ps1 -EnvFile .env.qwencloud.local -AllowDraft',
    'scripts/qwencloud-github-secrets-handoff.ps1 -EnvFile .env.qwencloud.local -SetFromEnv',
    'scripts/qwencloud-deploy-preflight.ps1 -EnvFile .env.qwencloud.local -BuildImage -SmokeContainer -AllowDraft',
    '```'
)
Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($ready) {
    Write-Host "Release config audit READY: $reportMd"
}
else {
    Write-Host "Release config audit DRAFT: $reportMd" -ForegroundColor Yellow
    Write-Host "Missing required checks: $($missingRequiredChecks -join ', ')"
}
Write-Host "JSON: $reportJson"

if (-not $ready -and -not $AllowDraft) {
    exit 1
}
