param(
    [Parameter(Mandatory = $false)]
    [string]$Repo = "zemeng2015/dream-ai-engineering-copilot",
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [string]$EnvFile = "",
    [switch]$SetFromEnv,
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
. (Join-Path $PSScriptRoot "qwencloud-env.ps1")
$importedEnvNames = @()
if (-not [string]::IsNullOrWhiteSpace($EnvFile)) {
    $importedEnvNames = @(Import-QwenCloudEnvFile -Path $EnvFile)
}

$reportJson = Join-Path $OutputDir "github-secrets-handoff-$timestamp.json"
$reportMd = Join-Path $OutputDir "github-secrets-handoff-$timestamp.md"
$templateEnv = Join-Path $OutputDir "github-secrets-template-$timestamp.env"

$requiredSecrets = @(
    "ALIBABA_CLOUD_ACCESS_KEY_ID",
    "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
    "DASHSCOPE_API_KEY",
    "QWEN_BASE_URL",
    "QWEN_MODEL"
)

$optionalSecrets = @(
    "ALIBABA_CLOUD_ACCOUNT_ID",
    "ALIBABA_CLOUD_REGION",
    "ALIBABA_CLOUD_RUNTIME_REGION"
)

function Has-Command([string]$Name) {
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Has-Env([string]$Name) {
    return Test-QwenCloudEnvValuePresent -Name $Name
}

function Get-SecretNames([string]$RepoName) {
    if (-not (Has-Command "gh")) {
        throw "GitHub CLI `gh` is required."
    }

    $output = (& gh secret list --repo $RepoName 2>&1) -join "`n"
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to list GitHub secrets for ${RepoName}: $output"
    }

    return @(
        $output -split "`r?`n" |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
            ForEach-Object { ($_ -split "\s+")[0] }
    )
}

function Set-SecretFromEnv([string]$Name, [string]$RepoName) {
    if (-not (Has-Env $Name)) {
        return [ordered]@{
            name = $Name
            attempted = $false
            ok = $false
            details = "env missing"
        }
    }

    $value = [Environment]::GetEnvironmentVariable($Name)
    $output = ($value | & gh secret set $Name --repo $RepoName 2>&1) -join "`n"
    return [ordered]@{
        name = $Name
        attempted = $true
        ok = ($LASTEXITCODE -eq 0)
        details = if ($LASTEXITCODE -eq 0) { "stored from env via stdin" } else { $output }
    }
}

$templateLines = @(
    "# SPDX-License-Identifier: Apache-2.0",
    "# Fill locally, then either source values into your shell or run:",
    "# scripts/qwencloud-github-secrets-handoff.ps1 -SetFromEnv",
    "# scripts/qwencloud-github-secrets-handoff.ps1 -EnvFile .env.qwencloud.local -SetFromEnv",
    "# Do not commit real secrets.",
    "ALIBABA_CLOUD_ACCESS_KEY_ID=<alibaba-access-key-id>",
    "ALIBABA_CLOUD_ACCESS_KEY_SECRET=<alibaba-access-key-secret>",
    "ALIBABA_CLOUD_REGION=ap-southeast-1",
    "ALIBABA_CLOUD_RUNTIME_REGION=ap-southeast-1",
    "DASHSCOPE_API_KEY=<qwen-cloud-api-key>",
    "ALIBABA_CLOUD_ACCOUNT_ID=<optional-account-id>",
    "QWEN_BASE_URL=https://<workspace-id>.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
    "QWEN_MODEL=qwen3.7-plus"
)
Set-Content -Path $templateEnv -Value ($templateLines -join "`r`n") -Encoding UTF8

$beforeNames = Get-SecretNames -RepoName $Repo
$setResults = @()
if ($SetFromEnv) {
    foreach ($name in ($requiredSecrets + $optionalSecrets)) {
        $setResults += Set-SecretFromEnv -Name $name -RepoName $Repo
    }
}
$afterNames = Get-SecretNames -RepoName $Repo

$secretRows = @()
foreach ($name in $requiredSecrets) {
    $secretRows += [ordered]@{
        name = $name
        required = $true
        presentBefore = $beforeNames -contains $name
        presentAfter = $afterNames -contains $name
        envSet = Has-Env $name
    }
}
foreach ($name in $optionalSecrets) {
    $secretRows += [ordered]@{
        name = $name
        required = $false
        presentBefore = $beforeNames -contains $name
        presentAfter = $afterNames -contains $name
        envSet = Has-Env $name
    }
}

$missingRequired = @($secretRows | Where-Object { $_.required -and -not $_.presentAfter } | ForEach-Object { $_.name })
$failedSet = @($setResults | Where-Object { $_.attempted -and -not $_.ok } | ForEach-Object { $_.name })
$ready = $missingRequired.Count -eq 0 -and $failedSet.Count -eq 0
$status = if ($ready) { "READY" } else { "DRAFT" }

$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    repo = $Repo
    status = $status
    readyForGitHubReleaseWorkflow = $ready
    setFromEnv = [bool]$SetFromEnv
    envFile = $EnvFile
    importedEnvNames = $importedEnvNames
    requiredSecrets = $requiredSecrets
    optionalSecrets = $optionalSecrets
    missingRequiredSecrets = $missingRequired
    failedSetSecrets = $failedSet
    secrets = $secretRows
    setResults = $setResults
    template = $templateEnv
    markdown = $reportMd
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud GitHub Secrets Handoff ($timestamp)",
    "",
    "- Status: $status",
    "- Ready for `Qwen Cloud Release` workflow: $ready",
    "- Repo: $Repo",
    "- Set from env: $([bool]$SetFromEnv)",
    "- Env file imported: $(if ($EnvFile) { $EnvFile } else { '<none>' })",
    "- Template: $templateEnv",
    "",
    "## Safety",
    "",
    "- This report never writes secret values.",
    "- `-EnvFile` imports local dotenv-style values into this PowerShell process only.",
    "- `-SetFromEnv` sends same-named local environment variables to GitHub secrets through stdin.",
    "- GitHub CLI encrypts secret values before storing them on GitHub.",
    "",
    "## Secrets",
    "",
    "| Secret | Required | Present Before | Present After | Local Env Set |",
    "|---|---:|---:|---:|---:|"
)
foreach ($row in $secretRows) {
    $lines += "| $($row.name) | $(if ($row.required) { 'yes' } else { 'no' }) | $(if ($row.presentBefore) { 'yes' } else { 'no' }) | $(if ($row.presentAfter) { 'yes' } else { 'no' }) | $(if ($row.envSet) { 'yes' } else { 'no' }) |"
}

$lines += @(
    "",
    "## Missing Required Secrets",
    ""
)
if ($missingRequired.Count -eq 0) {
    $lines += "- None"
}
else {
    foreach ($name in $missingRequired) {
        $lines += "- $name"
    }
}

if ($SetFromEnv) {
    $lines += @(
        "",
        "## Set Results",
        "",
        "| Secret | Attempted | Result | Details |",
        "|---|---:|---:|---|"
    )
    foreach ($setResult in $setResults) {
        $lines += "| $($setResult.name) | $(if ($setResult.attempted) { 'yes' } else { 'no' }) | $(if ($setResult.ok) { 'PASS' } else { 'SKIP/FAIL' }) | $($setResult.details -replace '\|', '/') |"
    }
}

$lines += @(
    "",
    "## Next Commands",
    "",
    '```powershell',
    'scripts/qwencloud-github-secrets-handoff.ps1 -EnvFile .env.qwencloud.local -SetFromEnv',
    'gh workflow run "Qwen Cloud Release" --repo zemeng2015/dream-ai-engineering-copilot -f demoVideoUrl="<public-video-url>"',
    '```'
)
Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($ready) {
    Write-Host "GitHub secrets handoff READY: $reportMd"
}
else {
    Write-Host "GitHub secrets handoff DRAFT: $reportMd" -ForegroundColor Yellow
    Write-Host "Missing required secrets: $($missingRequired -join ', ')"
}
Write-Host "Template: $templateEnv"
Write-Host "JSON: $reportJson"

if (-not $ready -and -not $AllowDraft) {
    exit 1
}
