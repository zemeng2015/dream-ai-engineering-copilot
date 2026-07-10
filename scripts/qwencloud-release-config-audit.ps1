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
    [Parameter(Mandatory = $false)]
    [string]$RuntimeServerlessTemplatePath = "deploy/alibaba/serverless-devs-runtime.yaml",
    [Parameter(Mandatory = $false)]
    [string]$RuntimePackageScriptPath = "scripts/qwencloud-build-fc-code-package.ps1",
    [switch]$UseCodePackage,
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
$deploymentMode = if ($UseCodePackage) { "custom-runtime-code-package" } else { "custom-container" }

if ($UseCodePackage) {
    $requiredRuntimeEnv = @(
        "DASHSCOPE_API_KEY",
        "QWEN_BASE_URL",
        "QWEN_MODEL"
    )
    $optionalRuntimeEnv = @(
        "ALIBABA_CLOUD_REGION",
        "ALIBABA_CLOUD_RUNTIME_REGION"
    )
    $requiredGitHubSecrets = @(
        "ALIBABA_CLOUD_ACCESS_KEY_ID",
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
        "DASHSCOPE_API_KEY",
        "QWEN_BASE_URL",
        "QWEN_MODEL"
    )
    $optionalGitHubSecrets = @(
        "ALIBABA_CLOUD_ACCOUNT_ID",
        "ALIBABA_CLOUD_REGION",
        "ALIBABA_CLOUD_RUNTIME_REGION"
    )
}
else {
    $requiredRuntimeEnv = @(
        "DASHSCOPE_API_KEY",
        "ALIBABA_CLOUD_REGION",
        "ALIBABA_CLOUD_CONTAINER_IMAGE",
        "ALIBABA_CONTAINER_REGISTRY_USERNAME",
        "ALIBABA_CONTAINER_REGISTRY_PASSWORD",
        "QWEN_BASE_URL",
        "QWEN_MODEL"
    )
    $optionalRuntimeEnv = @()
    $requiredGitHubSecrets = @(
        "ALIBABA_CLOUD_ACCESS_KEY_ID",
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
        "DASHSCOPE_API_KEY",
        "QWEN_BASE_URL",
        "QWEN_MODEL"
    )
    $optionalGitHubSecrets = @(
        "ALIBABA_CLOUD_ACCOUNT_ID",
        "ALIBABA_CLOUD_REGION",
        "ALIBABA_CLOUD_RUNTIME_REGION"
    )
}
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
        ok = ($Region -match "^[a-z]+-[a-z0-9]+(?:-[a-z0-9]+)*$")
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

function Test-QwenBaseUrl {
    $value = [Environment]::GetEnvironmentVariable("QWEN_BASE_URL")
    $apiKey = [Environment]::GetEnvironmentVariable("DASHSCOPE_API_KEY")
    if ([string]::IsNullOrWhiteSpace($value)) {
        return [pscustomobject]@{ ok = $false; details = "missing" }
    }

    $validUrl = $value -match "^https://" -and $value -notmatch "[<>]"
    $workspaceKey = -not [string]::IsNullOrWhiteSpace($apiKey) -and $apiKey.StartsWith("sk-ws")
    $workspaceDomain = $value -match "^https://[a-z0-9-]+\.ap-southeast-1\.maas\.aliyuncs\.com/compatible-mode/v1/?$"
    $legacyDomain = $value -match "^https://dashscope(?:-intl)?\.aliyuncs\.com/compatible-mode/v1/?$"
    $officialDomain = $workspaceDomain -or $legacyDomain
    return [pscustomobject]@{
        ok = ($validUrl -and $officialDomain)
        details = if (-not $validUrl) {
            "invalid HTTPS URL"
        }
        elseif (-not $officialDomain) {
            "URL must use an allowlisted Alibaba Model Studio compatible-mode endpoint"
        }
        elseif ($workspaceKey) {
            if ($workspaceDomain) {
                "workspace key and dedicated Singapore URL are aligned"
            }
            else {
                "workspace key uses an official DashScope domain; the FC template selects the Singapore endpoint"
            }
        }
        else {
            "legacy key URL is valid"
        }
    }
}

function Test-QwenModel {
    $value = [Environment]::GetEnvironmentVariable("QWEN_MODEL")
    return [pscustomobject]@{
        ok = $value -ceq "qwen3.7-plus"
        details = if ($value -ceq "qwen3.7-plus") {
            "model=qwen3.7-plus"
        }
        elseif ([string]::IsNullOrWhiteSpace($value)) {
            "missing"
        }
        else {
            "model must be qwen3.7-plus for the submitted benchmark and runtime attestation"
        }
    }
}

function Get-EffectiveRuntimeRegion {
    $requiredRuntimeRegion = "ap-southeast-1"

    $runtimeRegion = [Environment]::GetEnvironmentVariable("ALIBABA_CLOUD_RUNTIME_REGION")
    if (-not [string]::IsNullOrWhiteSpace($runtimeRegion) -and -not ($runtimeRegion -match "[<>]")) {
        return [pscustomobject]@{
            value = $runtimeRegion
            source = "ALIBABA_CLOUD_RUNTIME_REGION"
            requiredRuntimeRegion = $requiredRuntimeRegion
        }
    }

    $region = [Environment]::GetEnvironmentVariable("ALIBABA_CLOUD_REGION")
    if (-not [string]::IsNullOrWhiteSpace($region) -and -not ($region -match "[<>]")) {
        return [pscustomobject]@{
            value = $region
            source = "ALIBABA_CLOUD_REGION"
            requiredRuntimeRegion = $requiredRuntimeRegion
        }
    }

    return [pscustomobject]@{
        value = $requiredRuntimeRegion
        source = "default"
        requiredRuntimeRegion = $requiredRuntimeRegion
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

if ($UseCodePackage) {
    $effectiveRuntimeRegion = Get-EffectiveRuntimeRegion
    $regionCheck = Test-RegionFormat -Region $effectiveRuntimeRegion.value
    $regionSupported = $effectiveRuntimeRegion.value -ceq $effectiveRuntimeRegion.requiredRuntimeRegion
    Add-Check -Name "env.ALIBABA_CLOUD_RUNTIME_REGION.effective" -Ok ($regionCheck.ok -and $regionSupported) -Details "effectiveRegion=$($effectiveRuntimeRegion.value); source=$($effectiveRuntimeRegion.source); sameRegionWithQwenWorkspace=$regionSupported; runtime=custom.debian11"
    Add-Check -Name "env.ALIBABA_CLOUD_CONTAINER_IMAGE.not_required_for_code_package" -Ok $true -Details "custom runtime uses code package, not ACR" -Required $false
}
else {
    $effectiveRuntimeRegion = [pscustomobject]@{
        value = [Environment]::GetEnvironmentVariable("ALIBABA_CLOUD_REGION")
        source = "ALIBABA_CLOUD_REGION"
    }
    $regionCheck = Test-RegionFormat -Region ([Environment]::GetEnvironmentVariable("ALIBABA_CLOUD_REGION"))
    Add-Check -Name "env.ALIBABA_CLOUD_REGION.format" -Ok $regionCheck.ok -Details $regionCheck.details

    $imageCheck = Test-ContainerImageFormat -Image ([Environment]::GetEnvironmentVariable("ALIBABA_CLOUD_CONTAINER_IMAGE"))
    Add-Check -Name "env.ALIBABA_CLOUD_CONTAINER_IMAGE.format" -Ok $imageCheck.ok -Details $imageCheck.details
}

$baseUrlCheck = Test-QwenBaseUrl
Add-Check -Name "env.QWEN_BASE_URL.key_url_alignment" -Ok $baseUrlCheck.ok -Details $baseUrlCheck.details
$modelCheck = Test-QwenModel
Add-Check -Name "env.QWEN_MODEL.submission_alignment" -Ok $modelCheck.ok -Details $modelCheck.details

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

if ($UseCodePackage) {
    $runtimeTemplateText = Read-TextOrEmpty -Path $RuntimeServerlessTemplatePath
    Add-Check -Name "serverless_runtime_template_present" -Ok (-not [string]::IsNullOrWhiteSpace($runtimeTemplateText)) -Details $(if ($runtimeTemplateText) { $RuntimeServerlessTemplatePath } else { "missing: $RuntimeServerlessTemplatePath" })
    Add-Check -Name "serverless_runtime_template.uses_custom_debian11" -Ok ($runtimeTemplateText -match "runtime:\s*custom\.debian11") -Details "Singapore custom runtime provides the required Python 3.12 runtime"
    Add-Check -Name "serverless_runtime_template.uses_code_package" -Ok ($runtimeTemplateText -match "(?m)^\s*code:\s*") -Details "code package path configured"
    Add-Check -Name "serverless_runtime_template.has_custom_runtime_config" -Ok ($runtimeTemplateText -match "customRuntimeConfig:") -Details "startup command and port configured"
    Add-Check -Name "serverless_runtime_template.uses_fc_python312" -Ok ($runtimeTemplateText -match "PYTHON_BIN:\s*/var/fc/lang/python3\.12/bin/python3") -Details "uses the documented Function Compute Python 3.12 binary"
    Add-Check -Name "serverless_runtime_template.uses_bounded_non_thinking_qwen" -Ok ($runtimeTemplateText -match "QWEN_ENABLE_THINKING:\s*`"false`"" -and $runtimeTemplateText -match "QWEN_MAX_COMPLETION_TOKENS:\s*`"1200`"") -Details "interactive public demo disables default deep thinking and caps completion tokens"
    Add-Check -Name "serverless_runtime_template.uses_singapore_dashscope_endpoint" -Ok ($runtimeTemplateText -match "QWEN_BASE_URL:.*https://dashscope-intl\.aliyuncs\.com/compatible-mode/v1") -Details "FC uses the official Singapore shared endpoint after dedicated-domain egress validation timed out"
    Add-Check -Name "serverless_runtime_template.no_unvalidated_endpoint_override" -Ok ($runtimeTemplateText -notmatch "QWEN_RUNTIME_BASE_URL") -Details "public runtime cannot redirect the Qwen bearer token through an unchecked environment override"
    Add-Check -Name "serverless_runtime_template.no_acr_image_dependency" -Ok ($runtimeTemplateText -notmatch "ALIBABA_CLOUD_CONTAINER_IMAGE") -Details "ACR image env is not referenced"
    Add-Check -Name "serverless_runtime_template.uses_writable_ephemeral_paths" -Ok ($runtimeTemplateText -match "DREAM_ARTIFACT_ROOT:\s*/tmp/" -and $runtimeTemplateText -match "DREAM_AUDIT_DB_PATH:\s*/tmp/") -Details "generated artifacts and SQLite use writable /tmp paths"
    Add-Check -Name "serverless_runtime_template.caps_function_concurrency" -Ok ($runtimeTemplateText -match "concurrencyConfig:\s*\r?\n\s*reservedConcurrency:\s*1") -Details "function-level reserved concurrency is capped at one for the anonymous judge demo"

    $runtimePackageScriptText = Read-TextOrEmpty -Path $RuntimePackageScriptPath
    Add-Check -Name "runtime_package_script_present" -Ok (-not [string]::IsNullOrWhiteSpace($runtimePackageScriptText)) -Details $(if ($runtimePackageScriptText) { $RuntimePackageScriptPath } else { "missing: $RuntimePackageScriptPath" })
    Add-Check -Name "runtime_package_script.targets_python312_manylinux" -Ok ($runtimePackageScriptText -match "manylinux2014_x86_64" -and $runtimePackageScriptText -match "PythonVersion = `"3\.12`"" -and $runtimePackageScriptText -match "PythonAbi = `"cp312`"") -Details "builds Linux x86_64 Python 3.12 dependencies"
}

$requiredFailures = @($checks | Where-Object { $_.required -and -not $_.ok })
$ready = $requiredFailures.Count -eq 0
$status = if ($ready) { "READY" } else { "DRAFT" }
$missingRequiredChecks = @($requiredFailures | ForEach-Object { $_.name })

$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = $status
    readyForReleaseConfig = $ready
    deploymentMode = $deploymentMode
    effectiveRuntimeRegion = $effectiveRuntimeRegion.value
    effectiveRuntimeRegionSource = $effectiveRuntimeRegion.source
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
    "- Deployment mode: $deploymentMode",
    "- Effective runtime region: $($effectiveRuntimeRegion.value) ($($effectiveRuntimeRegion.source))",
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

if ($UseCodePackage) {
    $lines += @(
        "",
        "## Next Commands",
        "",
        '```powershell',
        'Copy-Item .env.qwencloud.local.example .env.qwencloud.local',
        '# Fill .env.qwencloud.local locally; do not commit it.',
        'scripts/qwencloud-release-config-audit.ps1 -EnvFile .env.qwencloud.local -UseCodePackage -AllowDraft',
        'scripts/qwencloud-build-fc-code-package.ps1',
        's deploy -t deploy/alibaba/serverless-devs-runtime.yaml -y',
        '```'
    )
}
else {
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
}
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
