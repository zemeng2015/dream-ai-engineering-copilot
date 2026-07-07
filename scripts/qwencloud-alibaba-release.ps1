param(
    [Parameter(Mandatory = $false)]
    [string]$RepoUrl = "https://github.com/zemeng2015/dream-ai-engineering-copilot",
    [Parameter(Mandatory = $false)]
    [string]$DemoVideoUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$BackendUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$BlogPostUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$ImageTag = "dream-qwencloud-memoryagent:local",
    [Parameter(Mandatory = $false)]
    [string]$ServerlessTemplate = "deploy/alibaba/serverless-devs.yaml",
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [int]$SmokePort = 8011,
    [Parameter(Mandatory = $false)]
    [string]$EnvFile = "",
    [switch]$PlanOnly,
    [switch]$SkipBuild,
    [switch]$SkipSmoke,
    [switch]$SkipPush,
    [switch]$SkipDeploy,
    [switch]$SkipDraft,
    [switch]$SkipScreenshot,
    [switch]$SkipProofVideo,
    [switch]$AllowDraftPacket
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
. (Join-Path $PSScriptRoot "qwencloud-env.ps1")
$importedEnvNames = @()
if (-not [string]::IsNullOrWhiteSpace($EnvFile)) {
    $importedEnvNames = @(Import-QwenCloudEnvFile -Path $EnvFile)
}
$releaseJson = Join-Path $OutputDir "alibaba-release-$timestamp.json"
$releaseMd = Join-Path $OutputDir "alibaba-release-$timestamp.md"
$steps = @()

function Add-Step([string]$Name, [string]$Status, [string]$Details) {
    $script:steps += [ordered]@{
        name = $Name
        status = $Status
        details = $Details
    }
}

function Has-Command([string]$Name) {
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Has-Env([string]$Name) {
    return Test-QwenCloudEnvValuePresent -Name $Name
}

function Require-Env([string]$Name) {
    if (-not (Has-Env $Name)) {
        throw "Required environment variable is missing: $Name"
    }
}

function Get-PowerShellExe {
    $pwsh = Get-Command "pwsh" -ErrorAction SilentlyContinue
    if ($pwsh) { return $pwsh.Source }

    $powershell = Get-Command "powershell" -ErrorAction SilentlyContinue
    if ($powershell) { return $powershell.Source }

    throw "PowerShell executable not found."
}

function Invoke-Logged {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $command = Get-Command $FilePath -ErrorAction SilentlyContinue
    $resolvedFilePath = if ($command) { $command.Source } else { $FilePath }
    $resolvedArguments = $ArgumentList
    if ($resolvedFilePath -match "\.ps1$") {
        $resolvedArguments = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $resolvedFilePath) + $ArgumentList
        $resolvedFilePath = Get-PowerShellExe
    }

    $stdout = Join-Path $OutputDir "$Name-$timestamp.out"
    $stderr = Join-Path $OutputDir "$Name-$timestamp.err"
    $proc = Start-Process -FilePath $resolvedFilePath -ArgumentList $resolvedArguments -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    $details = "$resolvedFilePath $($resolvedArguments -join ' ')"
    if ($proc.ExitCode -ne 0) {
        Add-Step -Name $Name -Status "fail" -Details "$details; stdout=$stdout; stderr=$stderr"
        throw "$Name failed with exit code $($proc.ExitCode). See $stderr"
    }
    Add-Step -Name $Name -Status "pass" -Details "$details; stdout=$stdout; stderr=$stderr"
    return [pscustomobject]@{
        stdout = $stdout
        stderr = $stderr
        text = if (Test-Path $stdout) { Get-Content -Raw $stdout } else { "" }
    }
}

function Try-Extract-BackendUrl([string]$Text) {
    $matches = [regex]::Matches($Text, "https?://[^\s'""<>]+")
    $urls = @($matches | ForEach-Object { $_.Value.TrimEnd(".", ",", ";", ")") })
    $strong = $urls | Where-Object { $_ -match "aliyun|fc|function|serverless|custom|http" } | Select-Object -First 1
    if ($strong) {
        return $strong
    }
    return $urls | Select-Object -First 1
}

function Write-ReleaseReport([string]$EffectiveBackendUrl) {
    $result = [ordered]@{
        generatedAt = (Get-Date).ToUniversalTime().ToString("o")
        planOnly = [bool]$PlanOnly
        repoUrl = $RepoUrl
        demoVideoUrl = $DemoVideoUrl
        backendUrl = $EffectiveBackendUrl
        blogPostUrl = $BlogPostUrl
        imageTag = $ImageTag
        containerImage = [Environment]::GetEnvironmentVariable("ALIBABA_CLOUD_CONTAINER_IMAGE")
        region = [Environment]::GetEnvironmentVariable("ALIBABA_CLOUD_REGION")
        envFile = $EnvFile
        importedEnvNames = $importedEnvNames
        steps = $steps
    }
    Set-Content -Path $releaseJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

    $lines = @(
        "# Qwen Cloud Alibaba Release ($timestamp)",
        "",
        "- Plan only: $([bool]$PlanOnly)",
        "- Repo: $RepoUrl",
        "- Demo video: $(if ($DemoVideoUrl) { $DemoVideoUrl } else { '<missing>' })",
        "- Backend URL: $(if ($EffectiveBackendUrl) { $EffectiveBackendUrl } else { '<missing>' })",
        "- Blog/social: $(if ($BlogPostUrl) { $BlogPostUrl } else { '<optional>' })",
        "- Container image: $([Environment]::GetEnvironmentVariable('ALIBABA_CLOUD_CONTAINER_IMAGE'))",
        "- Region: $([Environment]::GetEnvironmentVariable('ALIBABA_CLOUD_REGION'))",
        "- Env file imported: $(if ($EnvFile) { $EnvFile } else { '<none>' })",
        "",
        "## Steps",
        "",
        "| Step | Status | Details |",
        "|---|---|---|"
    )
    foreach ($step in $steps) {
        $lines += "| $($step.name) | $($step.status) | $($step.details -replace '\|', '/') |"
    }
    Set-Content -Path $releaseMd -Value ($lines -join "`r`n") -Encoding UTF8
}

try {
    foreach ($path in @("Dockerfile", $ServerlessTemplate, "scripts/qwencloud-deploy-preflight.ps1", "scripts/qwencloud-hackathon-verify.ps1", "scripts/qwencloud-capture-alibaba-proof.ps1", "scripts/qwencloud-render-alibaba-proof-video.ps1", "scripts/qwencloud-validate-alibaba-proof.ps1", "scripts/qwencloud-hackathon-submission-packet.ps1", "scripts/qwencloud-cloud-credentials-handoff.ps1", "scripts/qwencloud-devpost-handoff.ps1")) {
        if (-not (Test-Path $path)) {
            throw "Required release file missing: $path"
        }
    }
    Add-Step -Name "required_files" -Status "pass" -Details "release scripts and deployment template found"

    $requiredTools = @("docker", "s", "python")
    if (-not $SkipProofVideo) {
        $requiredTools += "ffmpeg"
    }
    foreach ($tool in $requiredTools) {
        if (-not (Has-Command $tool)) {
            throw "Required command is missing: $tool"
        }
    }
    Add-Step -Name "tools" -Status "pass" -Details "$($requiredTools -join ', ') available"

    if ($SkipDeploy -and $BackendUrl) {
        Add-Step -Name "required_env" -Status "skipped" -Details "SkipDeploy with explicit BackendUrl"
    }
    else {
        $missingEnv = @("DASHSCOPE_API_KEY", "ALIBABA_CLOUD_REGION", "ALIBABA_CLOUD_CONTAINER_IMAGE") | Where-Object { -not (Has-Env $_) }
        if ($missingEnv.Count -gt 0) {
            if ($PlanOnly) {
                Add-Step -Name "required_env" -Status "missing" -Details "Set before real release: $($missingEnv -join ', ')"
            }
            else {
                throw "Required environment variables are missing: $($missingEnv -join ', ')"
            }
        }
        else {
            Add-Step -Name "required_env" -Status "pass" -Details "DASHSCOPE_API_KEY, ALIBABA_CLOUD_REGION, ALIBABA_CLOUD_CONTAINER_IMAGE present"
        }
    }

    if ($PlanOnly) {
        Add-Step -Name "plan" -Status "pass" -Details "No build, push, deploy, verification, screenshot, proof video, or packet side effects were executed."
        Write-ReleaseReport -EffectiveBackendUrl $BackendUrl
        Write-Host "Plan-only release report: $releaseMd"
        exit 0
    }

    $preflightArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/qwencloud-deploy-preflight.ps1", "-ImageTag", $ImageTag, "-SmokePort", "$SmokePort")
    if ($EnvFile) {
        $preflightArgs += @("-EnvFile", $EnvFile)
    }
    if (-not $SkipBuild) {
        $preflightArgs += "-BuildImage"
    }
    if (-not $SkipSmoke) {
        $preflightArgs += "-SmokeContainer"
    }
    Invoke-Logged -FilePath (Get-PowerShellExe) -ArgumentList $preflightArgs -Name "deploy-preflight" | Out-Null

    if ($SkipBuild) {
        Add-Step -Name "docker_build" -Status "skipped" -Details "handled by preflight skip"
    }
    else {
        Add-Step -Name "docker_build" -Status "pass" -Details "built by deploy preflight as $ImageTag"
    }

    $containerImage = [Environment]::GetEnvironmentVariable("ALIBABA_CLOUD_CONTAINER_IMAGE")
    if ($SkipPush) {
        Add-Step -Name "docker_push" -Status "skipped" -Details "SkipPush set"
    }
    else {
        Invoke-Logged -FilePath "docker" -ArgumentList @("tag", $ImageTag, $containerImage) -Name "docker-tag" | Out-Null
        Invoke-Logged -FilePath "docker" -ArgumentList @("push", $containerImage) -Name "docker-push" | Out-Null
    }

    $effectiveBackendUrl = $BackendUrl
    if ($SkipDeploy) {
        Add-Step -Name "serverless_deploy" -Status "skipped" -Details "SkipDeploy set"
    }
    else {
        $deploy = Invoke-Logged -FilePath "s" -ArgumentList @("deploy", "-t", $ServerlessTemplate, "-y") -Name "serverless-deploy"
        $foundUrl = Try-Extract-BackendUrl -Text $deploy.text
        if ([string]::IsNullOrWhiteSpace($effectiveBackendUrl) -and -not [string]::IsNullOrWhiteSpace($foundUrl)) {
            $effectiveBackendUrl = $foundUrl
            Add-Step -Name "backend_url_detected" -Status "pass" -Details $effectiveBackendUrl
        }
        elseif ([string]::IsNullOrWhiteSpace($effectiveBackendUrl)) {
            Add-Step -Name "backend_url_detected" -Status "manual" -Details "No URL parsed from Serverless Devs output. Re-run with -BackendUrl."
        }
    }

    if ([string]::IsNullOrWhiteSpace($effectiveBackendUrl)) {
        throw "BackendUrl is required after deployment. Pass -BackendUrl if Serverless Devs output did not expose it."
    }

    $verifyArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/qwencloud-hackathon-verify.ps1", "-BaseUrl", $effectiveBackendUrl)
    Invoke-Logged -FilePath (Get-PowerShellExe) -ArgumentList $verifyArgs -Name "verify-backend" | Out-Null

    if ($SkipScreenshot) {
        Add-Step -Name "capture_alibaba_screenshot" -Status "skipped" -Details "SkipScreenshot set"
    }
    else {
        $screenshotArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/qwencloud-capture-alibaba-proof.ps1", "-BaseUrl", $effectiveBackendUrl)
        if (-not $SkipDraft) {
            $screenshotArgs += "-IncludeDraft"
        }
        Invoke-Logged -FilePath (Get-PowerShellExe) -ArgumentList $screenshotArgs -Name "capture-alibaba-proof" | Out-Null
    }

    if ($SkipProofVideo) {
        Add-Step -Name "render_alibaba_proof_video" -Status "skipped" -Details "SkipProofVideo set"
    }
    else {
        $proofVideoArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/qwencloud-render-alibaba-proof-video.ps1", "-BaseUrl", $effectiveBackendUrl)
        if (-not $SkipScreenshot) {
            $proofVideoArgs += "-SkipCapture"
        }
        if (-not $SkipDraft) {
            $proofVideoArgs += "-IncludeDraft"
        }
        Invoke-Logged -FilePath (Get-PowerShellExe) -ArgumentList $proofVideoArgs -Name "render-alibaba-proof-video" | Out-Null
    }

    if ($SkipScreenshot -or $SkipProofVideo) {
        Add-Step -Name "validate_alibaba_proof_integrity" -Status "skipped" -Details "requires screenshot and proof video"
    }
    else {
        $integrityArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/qwencloud-validate-alibaba-proof.ps1", "-BackendUrl", $effectiveBackendUrl)
        Invoke-Logged -FilePath (Get-PowerShellExe) -ArgumentList $integrityArgs -Name "validate-alibaba-proof-integrity" | Out-Null
    }

    $packetArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/qwencloud-hackathon-submission-packet.ps1", "-RepoUrl", $RepoUrl, "-BackendUrl", $effectiveBackendUrl)
    if ($DemoVideoUrl) {
        $packetArgs += @("-DemoVideoUrl", $DemoVideoUrl)
    }
    if ($BlogPostUrl) {
        $packetArgs += @("-BlogPostUrl", $BlogPostUrl)
    }
    if ($SkipDraft) {
        $packetArgs += "-SkipBackendDraft"
    }
    if ($AllowDraftPacket -or [string]::IsNullOrWhiteSpace($DemoVideoUrl)) {
        $packetArgs += "-AllowDraft"
    }
    Invoke-Logged -FilePath (Get-PowerShellExe) -ArgumentList $packetArgs -Name "submission-packet" | Out-Null

    $handoffArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/qwencloud-devpost-handoff.ps1", "-RepoUrl", $RepoUrl, "-BackendUrl", $effectiveBackendUrl)
    if ($DemoVideoUrl) {
        $handoffArgs += @("-DemoVideoUrl", $DemoVideoUrl)
    }
    if ($BlogPostUrl) {
        $handoffArgs += @("-BlogPostUrl", $BlogPostUrl)
    }
    if ($AllowDraftPacket -or [string]::IsNullOrWhiteSpace($DemoVideoUrl)) {
        $handoffArgs += "-AllowDraft"
    }
    Invoke-Logged -FilePath (Get-PowerShellExe) -ArgumentList $handoffArgs -Name "devpost-handoff" | Out-Null

    Write-ReleaseReport -EffectiveBackendUrl $effectiveBackendUrl
    Write-Host "Alibaba release flow completed. Report: $releaseMd"
    Write-Host "JSON: $releaseJson"
}
catch {
    Add-Step -Name "release_error" -Status "fail" -Details $_.Exception.Message
    Write-ReleaseReport -EffectiveBackendUrl $BackendUrl
    Write-Error $_.Exception.Message
    Write-Host "Release report: $releaseMd"
    exit 1
}
