# SPDX-License-Identifier: Apache-2.0
param(
    [Parameter(Mandatory = $false)]
    [string]$DemoVideoUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$BackendUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$BlogPostUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$DevpostProjectUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$EnvFile = ".env.qwencloud.local",
    [Parameter(Mandatory = $false)]
    [string]$AlibabaScreenshotPath = "artifacts/qwencloud-proof/alibaba-deployment-screenshot.png",
    [Parameter(Mandatory = $false)]
    [string]$AlibabaProofVideoPath = "artifacts/qwencloud-proof/alibaba-deployment-proof.mp4",
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [switch]$SkipExternalUrlChecks,
    [switch]$SkipBackendChecks,
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
. (Join-Path $PSScriptRoot "qwencloud-env.ps1")
. (Join-Path $PSScriptRoot "qwencloud-devpost-video-url.ps1")

$reportJson = Join-Path $OutputDir "live-inputs-intake-$timestamp.json"
$reportMd = Join-Path $OutputDir "live-inputs-intake-$timestamp.md"
$checks = @()
$importedEnvNames = @()

function Add-Check([string]$Name, [bool]$Ok, [string]$Details, [bool]$Required = $true) {
    $script:checks += [ordered]@{
        name = $Name
        ok = $Ok
        required = $Required
        details = $Details
    }
}

function Has-Env([string]$Name) {
    return Test-QwenCloudEnvValuePresent -Name $Name
}

function Is-HttpUrl([string]$Url) {
    if ([string]::IsNullOrWhiteSpace($Url)) { return $false }
    if ($Url -match "[<>]|\.\.\.") { return $false }
    return [bool]($Url -match "^https?://")
}

function Test-UrlReachable([string]$Url) {
    if (-not (Is-HttpUrl $Url)) {
        return [pscustomobject]@{ ok = $false; details = "not an http(s) URL" }
    }

    try {
        $response = Invoke-WebRequest -Method Head -Uri $Url -TimeoutSec 20 -MaximumRedirection 5 -UserAgent "dream-qwencloud-live-inputs-intake/1.0"
        return [pscustomobject]@{ ok = ([int]$response.StatusCode -ge 200 -and [int]$response.StatusCode -lt 400); details = "HEAD status=$([int]$response.StatusCode)" }
    }
    catch {
        try {
            $response = Invoke-WebRequest -Method Get -Uri $Url -TimeoutSec 20 -MaximumRedirection 5 -UserAgent "dream-qwencloud-live-inputs-intake/1.0"
            return [pscustomobject]@{ ok = ([int]$response.StatusCode -ge 200 -and [int]$response.StatusCode -lt 400); details = "GET status=$([int]$response.StatusCode)" }
        }
        catch {
            return [pscustomobject]@{ ok = $false; details = $_.Exception.Message }
        }
    }
}

function Get-PngDimensions([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    $bytes = [System.IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $Path))
    if ($bytes.Length -lt 24) { return $null }
    $pngSignature = @(137, 80, 78, 71, 13, 10, 26, 10)
    for ($i = 0; $i -lt $pngSignature.Count; $i++) {
        if ($bytes[$i] -ne $pngSignature[$i]) { return $null }
    }
    $width = [System.Net.IPAddress]::NetworkToHostOrder([BitConverter]::ToInt32($bytes, 16))
    $height = [System.Net.IPAddress]::NetworkToHostOrder([BitConverter]::ToInt32($bytes, 20))
    return [pscustomobject]@{ width = $width; height = $height }
}

function Get-VideoMetadata([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    if (-not (Get-Command ffprobe -ErrorAction SilentlyContinue)) { return $null }

    $probeJson = & ffprobe -v error -show_entries format=duration,size,format_name -show_streams -of json $Path
    $probe = $probeJson | ConvertFrom-Json
    $stream = @($probe.streams | Where-Object { $_.codec_type -eq "video" } | Select-Object -First 1)
    return [pscustomobject]@{
        duration = [double]$probe.format.duration
        size = [int64]$probe.format.size
        format = [string]$probe.format.format_name
        width = if ($stream) { [int]$stream.width } else { 0 }
        height = if ($stream) { [int]$stream.height } else { 0 }
        codec = if ($stream) { [string]$stream.codec_name } else { "" }
    }
}

function Get-BackendHealth([string]$Url) {
    if (-not (Is-HttpUrl $Url)) {
        return [pscustomobject]@{ ok = $false; details = "BackendUrl missing"; health = $null }
    }

    try {
        $base = $Url.TrimEnd("/")
        $health = Invoke-RestMethod -Uri "$base/health" -TimeoutSec 20
        return [pscustomobject]@{
            ok = ($health.status -eq "ok")
            details = "status=$($health.status); deployment_target=$($health.deployment_target); provider=$($health.llm_provider); track=$($health.track)"
            health = $health
        }
    }
    catch {
        return [pscustomobject]@{ ok = $false; details = $_.Exception.Message; health = $null }
    }
}

function Get-BackendShowcase([string]$Url) {
    if (-not (Is-HttpUrl $Url)) {
        return [pscustomobject]@{ ok = $false; details = "BackendUrl missing"; showcase = $null }
    }

    try {
        $base = $Url.TrimEnd("/")
        $showcase = Invoke-RestMethod -Uri "$base/qwencloud/showcase" -TimeoutSec 20
        return [pscustomobject]@{
            ok = ($showcase.track -eq "Track 1: MemoryAgent" -and $showcase.runtime.status -eq "ok")
            details = "track=$($showcase.track); live_backend_ready=$($showcase.runtime.live_backend_ready); weighted_static_evidence_ready=$($showcase.scorecard.weighted_static_evidence_ready)"
            showcase = $showcase
        }
    }
    catch {
        return [pscustomobject]@{ ok = $false; details = $_.Exception.Message; showcase = $null }
    }
}

$envFileExists = Test-Path -LiteralPath $EnvFile
if ($envFileExists) {
    $importedEnvNames = @(Import-QwenCloudEnvFile -Path $EnvFile)
}

Add-Check -Name "env_file_present" -Ok $envFileExists -Details $(if ($envFileExists) { $EnvFile } else { "missing: $EnvFile" })
Add-Check -Name "env.DASHSCOPE_API_KEY" -Ok (Has-Env "DASHSCOPE_API_KEY") -Details $(if (Has-Env "DASHSCOPE_API_KEY") { "set" } else { "missing" })
$effectiveRuntimeRegion = [Environment]::GetEnvironmentVariable("ALIBABA_CLOUD_RUNTIME_REGION")
if ([string]::IsNullOrWhiteSpace($effectiveRuntimeRegion)) {
    $effectiveRuntimeRegion = "ap-southeast-1"
}
Add-Check -Name "env.ALIBABA_CLOUD_RUNTIME_REGION.effective" -Ok ($effectiveRuntimeRegion -match "^[a-z0-9-]+$") -Details "effective=$effectiveRuntimeRegion"
Add-Check -Name "env.ALIBABA_CLOUD_REGION" -Ok (Has-Env "ALIBABA_CLOUD_REGION") -Details $(if (Has-Env "ALIBABA_CLOUD_REGION") { "set" } else { "optional; runtime region defaults to ap-southeast-1" }) -Required $false

Add-Check -Name "demo_video_url_present" -Ok (-not [string]::IsNullOrWhiteSpace($DemoVideoUrl)) -Details $(if ($DemoVideoUrl) { $DemoVideoUrl } else { "missing" })
$demoVideoPlatformOk = Test-QwenCloudDevpostVideoUrl -Url $DemoVideoUrl
Add-Check -Name "demo_video_url_platform" -Ok $demoVideoPlatformOk -Details $(if ($demoVideoPlatformOk) { "accepted Devpost platform" } else { Get-QwenCloudDevpostVideoPlatformMessage })
if ($demoVideoPlatformOk -and -not $SkipExternalUrlChecks) {
    $videoReachable = Test-UrlReachable -Url $DemoVideoUrl
    Add-Check -Name "demo_video_url_reachable" -Ok $videoReachable.ok -Details $videoReachable.details
}
else {
    Add-Check -Name "demo_video_url_reachable" -Ok $SkipExternalUrlChecks -Details $(if ($SkipExternalUrlChecks) { "skipped by -SkipExternalUrlChecks" } else { "not checked because platform check failed" }) -Required (-not $SkipExternalUrlChecks)
}

Add-Check -Name "backend_url_present" -Ok (Is-HttpUrl $BackendUrl) -Details $(if ($BackendUrl) { $BackendUrl } else { "missing" })
if ((Is-HttpUrl $BackendUrl) -and -not $SkipBackendChecks) {
    $backend = Get-BackendHealth -Url $BackendUrl
    $health = $backend.health
    Add-Check -Name "backend_health_reachable" -Ok $backend.ok -Details $backend.details
    Add-Check -Name "backend_deployment_target_alibaba" -Ok ($backend.ok -and $health -and ([string]$health.deployment_target -match "Alibaba Cloud Function Compute")) -Details $(if ($health) { [string]$health.deployment_target } else { "health missing" })
    Add-Check -Name "backend_provider_qwen_cloud" -Ok ($backend.ok -and $health -and $health.llm_provider -eq "qwen-cloud") -Details $(if ($health) { [string]$health.llm_provider } else { "health missing" })
    Add-Check -Name "backend_track_memoryagent" -Ok ($backend.ok -and $health -and $health.track -eq "Track 1: MemoryAgent") -Details $(if ($health) { [string]$health.track } else { "health missing" })
    Add-Check -Name "backend_proof_file_alibaba" -Ok ($backend.ok -and $health -and $health.proof_file -eq "deploy/alibaba/serverless-devs-runtime.yaml") -Details $(if ($health) { [string]$health.proof_file } else { "health missing" })
    $showcaseResult = Get-BackendShowcase -Url $BackendUrl
    $showcase = $showcaseResult.showcase
    Add-Check -Name "backend_showcase_reachable" -Ok $showcaseResult.ok -Details $showcaseResult.details
    Add-Check -Name "backend_showcase_track_memoryagent" -Ok ($showcaseResult.ok -and $showcase -and $showcase.track -eq "Track 1: MemoryAgent") -Details $(if ($showcase) { [string]$showcase.track } else { "showcase missing" })
    Add-Check -Name "backend_showcase_static_evidence_ready" -Ok ($showcaseResult.ok -and $showcase -and [int]$showcase.scorecard.weighted_static_evidence_ready -eq 100) -Details $(if ($showcase) { "$($showcase.scorecard.weighted_static_evidence_ready)/$($showcase.scorecard.weighted_total)" } else { "showcase missing" })
}
else {
    $skipOk = $SkipBackendChecks
    Add-Check -Name "backend_health_reachable" -Ok $skipOk -Details $(if ($skipOk) { "skipped by -SkipBackendChecks" } else { "BackendUrl missing" }) -Required (-not $skipOk)
    Add-Check -Name "backend_deployment_target_alibaba" -Ok $skipOk -Details $(if ($skipOk) { "skipped by -SkipBackendChecks" } else { "BackendUrl missing" }) -Required (-not $skipOk)
    Add-Check -Name "backend_provider_qwen_cloud" -Ok $skipOk -Details $(if ($skipOk) { "skipped by -SkipBackendChecks" } else { "BackendUrl missing" }) -Required (-not $skipOk)
    Add-Check -Name "backend_track_memoryagent" -Ok $skipOk -Details $(if ($skipOk) { "skipped by -SkipBackendChecks" } else { "BackendUrl missing" }) -Required (-not $skipOk)
    Add-Check -Name "backend_proof_file_alibaba" -Ok $skipOk -Details $(if ($skipOk) { "skipped by -SkipBackendChecks" } else { "BackendUrl missing" }) -Required (-not $skipOk)
    Add-Check -Name "backend_showcase_reachable" -Ok $skipOk -Details $(if ($skipOk) { "skipped by -SkipBackendChecks" } else { "BackendUrl missing" }) -Required (-not $skipOk)
    Add-Check -Name "backend_showcase_track_memoryagent" -Ok $skipOk -Details $(if ($skipOk) { "skipped by -SkipBackendChecks" } else { "BackendUrl missing" }) -Required (-not $skipOk)
    Add-Check -Name "backend_showcase_static_evidence_ready" -Ok $skipOk -Details $(if ($skipOk) { "skipped by -SkipBackendChecks" } else { "BackendUrl missing" }) -Required (-not $skipOk)
}

$screenshotExists = Test-Path -LiteralPath $AlibabaScreenshotPath
$screenshotDims = Get-PngDimensions -Path $AlibabaScreenshotPath
Add-Check -Name "alibaba_screenshot_exists" -Ok $screenshotExists -Details $(if ($screenshotExists) { $AlibabaScreenshotPath } else { "missing: $AlibabaScreenshotPath" })
Add-Check -Name "alibaba_screenshot_png_1280x720" -Ok ($screenshotDims -and $screenshotDims.width -ge 1280 -and $screenshotDims.height -ge 720) -Details $(if ($screenshotDims) { "$($screenshotDims.width)x$($screenshotDims.height)" } else { "not a readable PNG" })

$proofVideoExists = Test-Path -LiteralPath $AlibabaProofVideoPath
$proofVideo = Get-VideoMetadata -Path $AlibabaProofVideoPath
Add-Check -Name "alibaba_proof_video_exists" -Ok $proofVideoExists -Details $(if ($proofVideoExists) { $AlibabaProofVideoPath } else { "missing: $AlibabaProofVideoPath" })
Add-Check -Name "alibaba_proof_video_short_720p_h264" -Ok ($proofVideo -and $proofVideo.duration -ge 5 -and $proofVideo.duration -le 60 -and $proofVideo.width -ge 1280 -and $proofVideo.height -ge 720 -and $proofVideo.codec -eq "h264") -Details $(if ($proofVideo) { "duration=$($proofVideo.duration); resolution=$($proofVideo.width)x$($proofVideo.height); codec=$($proofVideo.codec)" } else { "metadata missing" })

Add-Check -Name "blog_post_url_optional" -Ok ([string]::IsNullOrWhiteSpace($BlogPostUrl) -or (Is-HttpUrl $BlogPostUrl)) -Details $(if ($BlogPostUrl) { $BlogPostUrl } else { "not provided" }) -Required $false
Add-Check -Name "devpost_project_url_optional" -Ok ([string]::IsNullOrWhiteSpace($DevpostProjectUrl) -or ($DevpostProjectUrl -match "^https://devpost\.com/software/")) -Details $(if ($DevpostProjectUrl) { $DevpostProjectUrl } else { "not provided" }) -Required $false

$requiredFailures = @($checks | Where-Object { $_.required -and -not $_.ok })
$ready = $requiredFailures.Count -eq 0
$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = if ($ready) { "READY" } else { "DRAFT" }
    readyForLiveInputs = $ready
    demoVideoUrl = $DemoVideoUrl
    backendUrl = $BackendUrl
    blogPostUrl = $BlogPostUrl
    devpostProjectUrl = $DevpostProjectUrl
    envFile = $EnvFile
    importedEnvNames = $importedEnvNames
    skipExternalUrlChecks = [bool]$SkipExternalUrlChecks
    skipBackendChecks = [bool]$SkipBackendChecks
    alibabaScreenshotPath = $AlibabaScreenshotPath
    alibabaProofVideoPath = $AlibabaProofVideoPath
    reportJson = $reportJson
    reportMarkdown = $reportMd
    checks = $checks
    missingRequiredChecks = @($requiredFailures | ForEach-Object { $_.name })
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Live Inputs Intake ($timestamp)",
    "",
    "- Ready for live inputs: $ready",
    "- Env file: $EnvFile",
    "- Demo video URL: $(if ($DemoVideoUrl) { $DemoVideoUrl } else { '<missing>' })",
    "- Backend URL: $(if ($BackendUrl) { $BackendUrl } else { '<missing>' })",
    "- Alibaba screenshot: $AlibabaScreenshotPath",
    "- Alibaba proof video: $AlibabaProofVideoPath",
    "- Blog/social URL: $(if ($BlogPostUrl) { $BlogPostUrl } else { '<optional>' })",
    "- Devpost project URL: $(if ($DevpostProjectUrl) { $DevpostProjectUrl } else { '<post-submit optional>' })",
    "",
    "## Checks",
    "",
    "| Check | Required | Result | Details |",
    "|---|---:|---:|---|"
)
foreach ($check in $checks) {
    $required = if ($check.required) { "yes" } else { "no" }
    $resultText = if ($check.ok) { "PASS" } else { "FAIL" }
    $lines += "| $($check.name) | $required | $resultText | $($check.details -replace '\|', '/') |"
}

if (-not $ready) {
    $lines += @(
        "",
        "## Missing Required Items",
        ""
    )
    foreach ($failure in $requiredFailures) {
        $lines += "- $($failure.name): $($failure.details)"
    }
}

$lines += @(
    "",
    "## Finalize Command",
    "",
    '```powershell',
    'scripts/qwencloud-finalize-after-urls.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>" -RefreshAlibabaProof',
    '```'
)
Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($ready) {
    Write-Host "Live inputs intake READY: $reportMd"
}
else {
    Write-Host "Live inputs intake DRAFT: $reportMd" -ForegroundColor Yellow
    Write-Host "Missing required checks: $($requiredFailures.name -join ', ')"
    if (-not $AllowDraft) {
        exit 1
    }
}
Write-Host "JSON: $reportJson"
