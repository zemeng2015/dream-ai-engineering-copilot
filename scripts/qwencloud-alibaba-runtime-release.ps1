# SPDX-License-Identifier: Apache-2.0

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
    [string]$ServerlessTemplate = "deploy/alibaba/serverless-devs-runtime.yaml",
    [Parameter(Mandatory = $false)]
    [string]$CodeDir = "artifacts/qwencloud-fc-code",
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [string]$EnvFile = "",
    [switch]$PlanOnly,
    [switch]$SkipPackage,
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

$releaseJson = Join-Path $OutputDir "alibaba-runtime-release-$timestamp.json"
$releaseMd = Join-Path $OutputDir "alibaba-runtime-release-$timestamp.md"
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

function Get-PowerShellExe {
    $pwsh = Get-Command "pwsh" -ErrorAction SilentlyContinue
    if ($pwsh) { return $pwsh.Source }

    $powershell = Get-Command "powershell" -ErrorAction SilentlyContinue
    if ($powershell) { return $powershell.Source }

    throw "PowerShell executable not found."
}

function Quote-ProcessArg([string]$Value) {
    if ($null -eq $Value) {
        return '""'
    }

    return '"' + ($Value -replace '"', '\"') + '"'
}

function Protect-SensitiveLogText([string]$Text) {
    if ([string]::IsNullOrEmpty($Text)) {
        return $Text
    }

    $protected = $Text
    foreach ($name in @(
        "ALIBABA_CLOUD_ACCESS_KEY_ID",
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
        "ALIBABA_CONTAINER_REGISTRY_PASSWORD",
        "DASHSCOPE_API_KEY",
        "QWEN_API_KEY",
        "QWEN_BASE_URL"
    )) {
        $value = [Environment]::GetEnvironmentVariable($name)
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            $protected = $protected.Replace($value, "[REDACTED:$name]")
        }
    }
    return $protected
}

function Protect-ServerlessDevsLogs {
    $logsRoot = Join-Path $HOME ".s/logs"
    if (-not (Test-Path -LiteralPath $logsRoot -PathType Container)) {
        return
    }

    foreach ($path in Get-ChildItem -LiteralPath $logsRoot -Recurse -File | Where-Object {
        $_.Extension -in @(".log", ".json", ".out", ".err")
    }) {
        try {
            $text = Get-Content -LiteralPath $path.FullName -Raw -ErrorAction Stop
            $protected = Protect-SensitiveLogText $text
            if ($protected -cne $text) {
                Set-Content -LiteralPath $path.FullName -Value $protected -Encoding UTF8
            }
        }
        catch {
            continue
        }
    }
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
    $startArguments = @($resolvedArguments | ForEach-Object { Quote-ProcessArg $_ })
    $proc = Start-Process -FilePath $resolvedFilePath -ArgumentList $startArguments -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($Name -like "serverless-*") {
        Protect-ServerlessDevsLogs
    }
    $stdoutText = Protect-SensitiveLogText $(if (Test-Path $stdout) { Get-Content -Raw $stdout } else { "" })
    $stderrText = Protect-SensitiveLogText $(if (Test-Path $stderr) { Get-Content -Raw $stderr } else { "" })
    Set-Content -Path $stdout -Value $stdoutText -Encoding UTF8
    Set-Content -Path $stderr -Value $stderrText -Encoding UTF8
    $details = "$resolvedFilePath $($resolvedArguments -join ' ')"
    if ($proc.ExitCode -ne 0) {
        Add-Step -Name $Name -Status "fail" -Details "$details; stdout=$stdout; stderr=$stderr"
        throw "$Name failed with exit code $($proc.ExitCode). See $stderr"
    }
    Add-Step -Name $Name -Status "pass" -Details "$details; stdout=$stdout; stderr=$stderr"
    return [pscustomobject]@{
        stdout = $stdout
        stderr = $stderr
        text = $stdoutText
    }
}

function Try-Extract-BackendUrl([string]$Text) {
    $plainText = [regex]::Replace($Text, "`e\[[0-9;]*[A-Za-z]", "")
    $systemUrl = [regex]::Match(
        $plainText,
        "(?m)^\s*system_url:\s*(https://[^\s'""<>]+\.fcapp\.run)\s*$"
    )
    if ($systemUrl.Success) {
        return $systemUrl.Groups[1].Value
    }

    $matches = [regex]::Matches($plainText, "https?://[^\s'""<>]+")
    $urls = @($matches | ForEach-Object { $_.Value.TrimEnd(".", ",", ";", ")") })
    $strong = $urls | Where-Object { $_ -match "\.fcapp\.run(?:/|$)" } | Select-Object -First 1
    if ($strong) {
        return $strong
    }
    return $null
}

function Write-ReleaseReport([string]$EffectiveBackendUrl) {
    $result = [ordered]@{
        generatedAt = (Get-Date).ToUniversalTime().ToString("o")
        planOnly = [bool]$PlanOnly
        repoUrl = $RepoUrl
        demoVideoUrl = $DemoVideoUrl
        backendUrl = $EffectiveBackendUrl
        blogPostUrl = $BlogPostUrl
        serverlessTemplate = $ServerlessTemplate
        codeDir = [Environment]::GetEnvironmentVariable("DREAM_FC_CODE_DIR")
        region = [Environment]::GetEnvironmentVariable("ALIBABA_CLOUD_RUNTIME_REGION")
        envFile = $EnvFile
        importedEnvNames = $importedEnvNames
        steps = $steps
    }
    Set-Content -Path $releaseJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

    $lines = @(
        "# Qwen Cloud Alibaba Runtime Release ($timestamp)",
        "",
        "- Plan only: $([bool]$PlanOnly)",
        "- Repo: $RepoUrl",
        "- Demo video: $(if ($DemoVideoUrl) { $DemoVideoUrl } else { '<missing>' })",
        "- Backend URL: $(if ($EffectiveBackendUrl) { $EffectiveBackendUrl } else { '<missing>' })",
        "- Blog/social: $(if ($BlogPostUrl) { $BlogPostUrl } else { '<optional>' })",
        "- Serverless template: $ServerlessTemplate",
        "- Code dir: $([Environment]::GetEnvironmentVariable('DREAM_FC_CODE_DIR'))",
        "- Runtime region: $([Environment]::GetEnvironmentVariable('ALIBABA_CLOUD_RUNTIME_REGION'))",
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

$effectiveBackendUrl = $BackendUrl
try {
    foreach ($path in @($ServerlessTemplate, "scripts/qwencloud-build-fc-code-package.ps1", "scripts/qwencloud-release-config-audit.ps1", "scripts/qwencloud-hackathon-verify.ps1", "scripts/qwencloud-capture-alibaba-proof.ps1", "scripts/qwencloud-render-alibaba-proof-video.ps1", "scripts/qwencloud-validate-alibaba-proof.ps1", "scripts/qwencloud-hackathon-submission-packet.ps1", "scripts/qwencloud-devpost-handoff.ps1", "scripts/qwencloud-devpost-materials-audit.ps1")) {
        if (-not (Test-Path $path)) {
            throw "Required runtime release file missing: $path"
        }
    }
    Add-Step -Name "required_files" -Status "pass" -Details "runtime release scripts and deployment template found"

    $requiredTools = @("s", "python")
    if (-not $SkipProofVideo) {
        $requiredTools += "ffmpeg"
    }
    foreach ($tool in $requiredTools) {
        if (-not (Has-Command $tool)) {
            throw "Required command is missing: $tool"
        }
    }
    Add-Step -Name "tools" -Status "pass" -Details "$($requiredTools -join ', ') available"

    if (-not (Has-Env "ALIBABA_CLOUD_RUNTIME_REGION")) {
        [Environment]::SetEnvironmentVariable("ALIBABA_CLOUD_RUNTIME_REGION", "ap-southeast-1", "Process")
        $env:ALIBABA_CLOUD_RUNTIME_REGION = "ap-southeast-1"
    }
    if (-not (Has-Env "ALIBABA_CLOUD_REGION")) {
        [Environment]::SetEnvironmentVariable("ALIBABA_CLOUD_REGION", [Environment]::GetEnvironmentVariable("ALIBABA_CLOUD_RUNTIME_REGION"), "Process")
        $env:ALIBABA_CLOUD_REGION = [Environment]::GetEnvironmentVariable("ALIBABA_CLOUD_RUNTIME_REGION")
    }

    $resolvedCodeDir = if ([System.IO.Path]::IsPathRooted($CodeDir)) {
        [System.IO.Path]::GetFullPath($CodeDir)
    }
    else {
        [System.IO.Path]::GetFullPath((Join-Path (Get-Location).Path $CodeDir))
    }
    [Environment]::SetEnvironmentVariable("DREAM_FC_CODE_DIR", $resolvedCodeDir, "Process")
    $env:DREAM_FC_CODE_DIR = $resolvedCodeDir

    if ($SkipDeploy -and $BackendUrl) {
        Add-Step -Name "required_env" -Status "skipped" -Details "SkipDeploy with explicit BackendUrl"
    }
    else {
        $requiredEnv = @("DASHSCOPE_API_KEY", "QWEN_BASE_URL", "QWEN_MODEL")
        $missingEnv = $requiredEnv | Where-Object { -not (Has-Env $_) }
        if ($missingEnv.Count -gt 0) {
            if ($PlanOnly) {
                Add-Step -Name "required_env" -Status "missing" -Details "Set before real release: $($missingEnv -join ', ')"
            }
            else {
                throw "Required environment variables are missing: $($missingEnv -join ', ')"
            }
        }
        else {
            Add-Step -Name "required_env" -Status "pass" -Details "$($requiredEnv -join ', ') present; runtime region=$([Environment]::GetEnvironmentVariable('ALIBABA_CLOUD_RUNTIME_REGION'))"
        }
    }

    if ($PlanOnly) {
        Add-Step -Name "plan" -Status "pass" -Details "No package, deploy, verification, screenshot, proof video, or packet side effects were executed."
        Write-ReleaseReport -EffectiveBackendUrl $BackendUrl
        Write-Host "Plan-only runtime release report: $releaseMd"
        exit 0
    }

    $releaseConfigAuditArgs = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        "scripts/qwencloud-release-config-audit.ps1", "-UseCodePackage"
    )
    if ($EnvFile) {
        $releaseConfigAuditArgs += @("-EnvFile", $EnvFile)
    }
    Invoke-Logged -FilePath (Get-PowerShellExe) -ArgumentList $releaseConfigAuditArgs -Name "release-config-audit" | Out-Null

    if ($SkipPackage) {
        Add-Step -Name "code_package" -Status "skipped" -Details "SkipPackage set; using $resolvedCodeDir"
    }
    else {
        Invoke-Logged -FilePath (Get-PowerShellExe) -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/qwencloud-build-fc-code-package.ps1", "-OutputDir", $resolvedCodeDir) -Name "build-fc-code-package" | Out-Null
    }

    if ($SkipDeploy) {
        Add-Step -Name "serverless_deploy" -Status "skipped" -Details "SkipDeploy set"
    }
    else {
        $deploy = Invoke-Logged -FilePath "s" -ArgumentList @("deploy", "-t", $ServerlessTemplate, "-y") -Name "serverless-deploy-runtime"
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

    Invoke-Logged -FilePath (Get-PowerShellExe) -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/qwencloud-hackathon-verify.ps1", "-BaseUrl", $effectiveBackendUrl) -Name "verify-backend" | Out-Null

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
        Invoke-Logged -FilePath (Get-PowerShellExe) -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/qwencloud-validate-alibaba-proof.ps1", "-BackendUrl", $effectiveBackendUrl) -Name "validate-alibaba-proof-integrity" | Out-Null
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
    if ($AllowDraftPacket) {
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
    if ($EnvFile) {
        $handoffArgs += @("-EnvFile", $EnvFile)
    }
    if ($AllowDraftPacket) {
        $handoffArgs += "-AllowDraft"
    }
    Invoke-Logged -FilePath (Get-PowerShellExe) -ArgumentList $handoffArgs -Name "devpost-handoff" | Out-Null

    $materialsAuditArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/qwencloud-devpost-materials-audit.ps1", "-RepoUrl", $RepoUrl, "-BackendUrl", $effectiveBackendUrl)
    if ($DemoVideoUrl) {
        $materialsAuditArgs += @("-DemoVideoUrl", $DemoVideoUrl)
    }
    if ($BlogPostUrl) {
        $materialsAuditArgs += @("-BlogPostUrl", $BlogPostUrl)
    }
    if ($EnvFile) {
        $materialsAuditArgs += @("-EnvFile", $EnvFile)
    }
    if ($SkipDraft) {
        $materialsAuditArgs += "-SkipBackendDraft"
    }
    if ($AllowDraftPacket) {
        $materialsAuditArgs += "-AllowDraft"
    }
    Invoke-Logged -FilePath (Get-PowerShellExe) -ArgumentList $materialsAuditArgs -Name "devpost-materials-audit" | Out-Null

    Write-ReleaseReport -EffectiveBackendUrl $effectiveBackendUrl
    Write-Host "Alibaba runtime release flow completed. Report: $releaseMd"
    Write-Host "JSON: $releaseJson"
}
catch {
    Add-Step -Name "release_error" -Status "fail" -Details $_.Exception.Message
    Write-ReleaseReport -EffectiveBackendUrl $effectiveBackendUrl
    Write-Error $_.Exception.Message
    Write-Host "Runtime release report: $releaseMd"
    exit 1
}
