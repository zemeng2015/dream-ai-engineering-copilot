param(
    [Parameter(Mandatory = $false)]
    [string]$DemoVideoUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$BackendUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [string]$Region = "",
    [Parameter(Mandatory = $false)]
    [string]$ContainerImage = "",
    [Parameter(Mandatory = $false)]
    [string]$EnvFile = "",
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
. (Join-Path $PSScriptRoot "qwencloud-env.ps1")
$importedEnvNames = @()
$envFileExists = $true
$envFileImportIssue = ""
if (-not [string]::IsNullOrWhiteSpace($EnvFile)) {
    $envFileExists = Test-Path -LiteralPath $EnvFile
    if ($envFileExists) {
        $importedEnvNames = @(Import-QwenCloudEnvFile -Path $EnvFile)
    }
    elseif ($AllowDraft) {
        $envFileImportIssue = "missing env file: $EnvFile"
    }
    else {
        throw "Env file not found: $EnvFile"
    }
}

$handoffJson = Join-Path $OutputDir "cloud-credentials-handoff-$timestamp.json"
$handoffMd = Join-Path $OutputDir "cloud-credentials-handoff-$timestamp.md"
$handoffPs1 = Join-Path $OutputDir "cloud-credentials-template-$timestamp.ps1"

function Has-Env([string]$Name) {
    return Test-QwenCloudEnvValuePresent -Name $Name
}

function Env-State([string]$Name, [bool]$Required = $true) {
    return [ordered]@{
        name = $Name
        required = $Required
        set = Has-Env $Name
        details = if (Has-Env $Name) { "set" } elseif ($Required) { "missing" } else { "optional default available" }
    }
}

function Test-ServerlessDevsDefaultAccess {
    if (-not (Get-Command "s" -ErrorAction SilentlyContinue)) {
        return [ordered]@{ ok = $false; details = "s command missing" }
    }

    try {
        $output = (& s config get -a default 2>&1) -join "`n"
        $ok = $output -notmatch "not yet|not found|not.*configured|configured key information"
        return [ordered]@{
            ok = $ok
            details = if ($ok) { "default access configured" } else { "default access not configured" }
        }
    }
    catch {
        return [ordered]@{ ok = $false; details = $_.Exception.Message }
    }
}

function Get-RegistryHost([string]$Image) {
    if ([string]::IsNullOrWhiteSpace($Image)) {
        return "<registry-host>"
    }
    $first = ($Image -split "/")[0]
    if ($first -and $first -match "\.") {
        return $first
    }
    return "<registry-host>"
}

if ([string]::IsNullOrWhiteSpace($Region)) {
    $Region = [Environment]::GetEnvironmentVariable("ALIBABA_CLOUD_REGION")
}
if ([string]::IsNullOrWhiteSpace($ContainerImage)) {
    $ContainerImage = [Environment]::GetEnvironmentVariable("ALIBABA_CLOUD_CONTAINER_IMAGE")
}
if ([string]::IsNullOrWhiteSpace($Region)) {
    $Region = "ap-southeast-1"
}
if ([string]::IsNullOrWhiteSpace($ContainerImage)) {
    $ContainerImage = "<registry>/<namespace>/dream-qwencloud-memoryagent:latest"
}

$registryHost = Get-RegistryHost -Image $ContainerImage
$sAccess = Test-ServerlessDevsDefaultAccess
$envChecks = @(
    Env-State -Name "DASHSCOPE_API_KEY"
    Env-State -Name "ALIBABA_CLOUD_REGION"
    Env-State -Name "ALIBABA_CLOUD_CONTAINER_IMAGE"
    Env-State -Name "QWEN_BASE_URL" -Required $false
    Env-State -Name "QWEN_MODEL" -Required $false
)

$blockers = @()
if (-not $envFileExists) {
    $blockers += "env_file_missing"
}
if (-not $sAccess.ok) {
    $blockers += "serverless_devs_default_access"
}
foreach ($check in $envChecks) {
    if ($check.required -and -not $check.set) {
        $blockers += "env.$($check.name)"
    }
}

$ready = $blockers.Count -eq 0
$status = if ($ready) { "READY" } else { "DRAFT" }
$videoValue = if ($DemoVideoUrl) { $DemoVideoUrl } else { "<public-video-url>" }
$backendValue = if ($BackendUrl) { $BackendUrl } else { "<deployed-url>" }

$setupCommands = @(
    '$env:DASHSCOPE_API_KEY="<qwen-cloud-api-key>"',
    "`$env:ALIBABA_CLOUD_REGION=`"$Region`"",
    "`$env:ALIBABA_CLOUD_CONTAINER_IMAGE=`"$ContainerImage`"",
    '$env:QWEN_BASE_URL="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"',
    '$env:QWEN_MODEL="qwen3.7-plus"',
    's config add -a default --AccessKeyID "<alibaba-access-key-id>" --AccessKeySecret "<alibaba-access-key-secret>" --force',
    's config get -a default',
    "docker login $registryHost",
    'scripts/qwencloud-deploy-preflight.ps1 -EnvFile .env.qwencloud.local -BuildImage -SmokeContainer',
    "scripts/qwencloud-alibaba-release.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl `"$videoValue`"",
    "scripts/qwencloud-final-readiness.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl `"$videoValue`" -BackendUrl `"$backendValue`"",
    "scripts/qwencloud-final-upload-bundle.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl `"$videoValue`" -BackendUrl `"$backendValue`""
)

$templateLines = @(
    "# SPDX-License-Identifier: Apache-2.0",
    "# Fill this template locally. Do not commit real secrets.",
    "# Generated: $timestamp",
    ""
) + $setupCommands
Set-Content -Path $handoffPs1 -Value ($templateLines -join "`r`n") -Encoding UTF8

$handoff = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = $status
    readyForCloudRelease = $ready
    blockers = $blockers
    serverlessDevsDefaultAccess = $sAccess
    envFileExists = $envFileExists
    envFileImportIssue = $envFileImportIssue
    envChecks = $envChecks
    region = $Region
    containerImage = $ContainerImage
    registryHost = $registryHost
    envFile = $EnvFile
    importedEnvNames = $importedEnvNames
    template = $handoffPs1
    markdown = $handoffMd
    nextCommands = $setupCommands
}
Set-Content -Path $handoffJson -Value ($handoff | ConvertTo-Json -Depth 12) -Encoding UTF8

$md = @(
    "# Qwen Cloud Cloud Credentials Handoff ($timestamp)",
    "",
    "- Status: $status",
    "- Ready for cloud release: $ready",
    "- Region: $Region",
    "- Container image: $ContainerImage",
    "- Registry host: $registryHost",
    "- Env file imported: $(if ($EnvFile -and $envFileExists) { $EnvFile } elseif ($EnvFile) { '<missing: ' + $EnvFile + '>' } else { '<none>' })",
    "- Template: $handoffPs1",
    "",
    "## Safety",
    "",
    "- This handoff never stores real `DASHSCOPE_API_KEY`, Alibaba AccessKeyID, or AccessKeySecret values.",
    "- Fill the generated PowerShell template locally and keep it out of git.",
    "- Or create a local `.env.qwencloud.local` file and pass `-EnvFile .env.qwencloud.local`.",
    "- The public repo should only contain placeholders and deployment code.",
    "",
    "## Current Checks",
    "",
    "| Check | Required | Result | Details |",
    "|---|---:|---:|---|",
    "| env_file | $(if ($EnvFile) { 'yes' } else { 'no' }) | $(if ($envFileExists) { 'PASS' } elseif ($EnvFile) { 'FAIL' } else { 'WARN' }) | $(if ($EnvFile) { if ($envFileExists) { 'found' } else { $envFileImportIssue } } else { 'not requested' }) |",
    "| serverless_devs_default_access | yes | $(if ($sAccess.ok) { 'PASS' } else { 'FAIL' }) | $($sAccess.details -replace '\|', '/') |"
)
foreach ($check in $envChecks) {
    $required = if ($check.required) { "yes" } else { "no" }
    $result = if ($check.set) { "PASS" } elseif ($check.required) { "FAIL" } else { "WARN" }
    $md += "| env.$($check.name) | $required | $result | $($check.details) |"
}

$md += @(
    "",
    "## Blockers",
    ""
)
if ($blockers.Count -eq 0) {
    $md += "- None"
}
else {
    foreach ($blocker in $blockers) {
        $md += "- $blocker"
    }
}

$md += @(
    "",
    "## Setup Commands",
    "",
    '```powershell'
) + $setupCommands + @(
    '```',
    "",
    "## Final Expected Artifacts",
    "",
    "- Alibaba deployment screenshot: artifacts/qwencloud-proof/alibaba-deployment-screenshot.png",
    "- Alibaba backend proof recording: artifacts/qwencloud-proof/alibaba-deployment-proof.mp4",
    "- Public demo video URL: $videoValue",
    "- Deployed backend URL: $backendValue"
)
Set-Content -Path $handoffMd -Value ($md -join "`r`n") -Encoding UTF8

if ($ready) {
    Write-Host "Cloud credentials handoff READY: $handoffMd"
}
else {
    Write-Host "Cloud credentials handoff DRAFT: $handoffMd" -ForegroundColor Yellow
    Write-Host "Missing required items: $($blockers -join ', ')"
}
Write-Host "Template: $handoffPs1"
Write-Host "JSON: $handoffJson"

if (-not $ready -and -not $AllowDraft) {
    exit 1
}
