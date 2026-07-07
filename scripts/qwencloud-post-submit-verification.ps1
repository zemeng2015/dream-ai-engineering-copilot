# SPDX-License-Identifier: Apache-2.0

param(
    [Parameter(Mandatory = $false)]
    [string]$DevpostProjectUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$RepoUrl = "https://github.com/zemeng2015/dream-ai-engineering-copilot",
    [Parameter(Mandatory = $false)]
    [string]$DemoVideoUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$BackendUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [string]$ExpectedTitle = "DREAM",
    [Parameter(Mandatory = $false)]
    [string]$ExpectedTrack = "Track 1: MemoryAgent",
    [Parameter(Mandatory = $false)]
    [string]$AlibabaScreenshotPath = "artifacts/qwencloud-proof/alibaba-deployment-screenshot.png",
    [Parameter(Mandatory = $false)]
    [string]$AlibabaProofVideoPath = "artifacts/qwencloud-proof/alibaba-deployment-proof.mp4",
    [switch]$SkipExternalUrlChecks,
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$reportJson = Join-Path $OutputDir "devpost-post-submit-verification-$timestamp.json"
$reportMd = Join-Path $OutputDir "devpost-post-submit-verification-$timestamp.md"
$checks = @()

function Add-Check([string]$Name, [bool]$Ok, [string]$Details, [bool]$Required = $true) {
    $script:checks += [ordered]@{
        name = $Name
        ok = $Ok
        required = $Required
        details = $Details
    }
}

function Is-HttpUrl([string]$Url) {
    return -not [string]::IsNullOrWhiteSpace($Url) -and $Url -match "^https?://" -and $Url -notmatch "[<>]|\.\.\."
}

function Is-DevpostProjectUrl([string]$Url) {
    return (Is-HttpUrl $Url) -and $Url -match "^https://devpost\.com/software/[^/?#]+"
}

function Is-DevpostVideoUrl([string]$Url) {
    return (Is-HttpUrl $Url) -and $Url -match "^https?://((www|m|v)\.)?(youtube\.com/watch\?v=|youtu\.be/|vimeo\.com/|youku\.com/)"
}

function Test-Url {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $false)][string]$Method = "Get"
    )

    if (-not (Is-HttpUrl $Url)) {
        return [pscustomobject]@{ ok = $false; status = 0; content = ""; details = "not an http(s) URL" }
    }
    if ($SkipExternalUrlChecks) {
        return [pscustomobject]@{ ok = $true; status = 0; content = ""; details = "skipped by -SkipExternalUrlChecks" }
    }

    try {
        $response = Invoke-WebRequest -Method $Method -Uri $Url -MaximumRedirection 5 -TimeoutSec 25 -ErrorAction Stop
        return [pscustomobject]@{
            ok = ([int]$response.StatusCode -ge 200 -and [int]$response.StatusCode -lt 400)
            status = [int]$response.StatusCode
            content = [string]$response.Content
            details = "$Method status=$([int]$response.StatusCode)"
        }
    }
    catch {
        return [pscustomobject]@{ ok = $false; status = 0; content = ""; details = $_.Exception.Message }
    }
}

function Test-File([string]$Path, [int]$MinBytes = 1) {
    if (-not (Test-Path $Path)) {
        return [pscustomobject]@{ ok = $false; details = "missing: $Path" }
    }
    $item = Get-Item -LiteralPath $Path
    return [pscustomobject]@{
        ok = $item.Length -ge $MinBytes
        details = "path=$Path; size=$($item.Length)"
    }
}

function Get-PngDimensions([string]$Path) {
    if (-not (Test-Path $Path)) { return $null }
    $bytes = [System.IO.File]::ReadAllBytes((Resolve-Path $Path))
    if ($bytes.Length -lt 24) { return $null }

    $signature = @(137, 80, 78, 71, 13, 10, 26, 10)
    for ($i = 0; $i -lt $signature.Count; $i++) {
        if ([int]$bytes[$i] -ne $signature[$i]) { return $null }
    }

    return [pscustomobject]@{
        width = ([int]$bytes[16] -shl 24) -bor ([int]$bytes[17] -shl 16) -bor ([int]$bytes[18] -shl 8) -bor [int]$bytes[19]
        height = ([int]$bytes[20] -shl 24) -bor ([int]$bytes[21] -shl 16) -bor ([int]$bytes[22] -shl 8) -bor [int]$bytes[23]
    }
}

function Get-VideoMetadata([string]$Path) {
    if (-not (Test-Path $Path)) { return $null }
    if (-not (Get-Command "ffprobe" -ErrorAction SilentlyContinue)) { return $null }

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

Add-Check -Name "devpost_public_project_url_present" -Ok (Is-DevpostProjectUrl $DevpostProjectUrl) -Details $(if ($DevpostProjectUrl) { $DevpostProjectUrl } else { "missing" })
if (Is-DevpostProjectUrl $DevpostProjectUrl) {
    $devpost = Test-Url -Url $DevpostProjectUrl -Method "Get"
    Add-Check -Name "devpost_public_project_reachable" -Ok $devpost.ok -Details $devpost.details
    if ($SkipExternalUrlChecks) {
        Add-Check -Name "devpost_public_project_mentions_dream" -Ok $true -Details "skipped by -SkipExternalUrlChecks" -Required $false
        Add-Check -Name "devpost_public_project_mentions_qwen" -Ok $true -Details "skipped by -SkipExternalUrlChecks" -Required $false
    }
    else {
        Add-Check -Name "devpost_public_project_mentions_dream" -Ok ($devpost.content -match [regex]::Escape($ExpectedTitle)) -Details "expected text: $ExpectedTitle"
        Add-Check -Name "devpost_public_project_mentions_qwen" -Ok ($devpost.content -match "Qwen") -Details "expected text: Qwen"
    }
}
else {
    Add-Check -Name "devpost_public_project_reachable" -Ok $false -Details "DevpostProjectUrl missing or not public project URL"
    Add-Check -Name "devpost_public_project_mentions_dream" -Ok $false -Details "DevpostProjectUrl missing or not public project URL"
    Add-Check -Name "devpost_public_project_mentions_qwen" -Ok $false -Details "DevpostProjectUrl missing or not public project URL"
}

Add-Check -Name "repo_url_present" -Ok (Is-HttpUrl $RepoUrl) -Details $RepoUrl
$repo = Test-Url -Url $RepoUrl -Method "Get"
Add-Check -Name "repo_public_page_reachable" -Ok $repo.ok -Details $repo.details

Add-Check -Name "demo_video_url_platform" -Ok (Is-DevpostVideoUrl $DemoVideoUrl) -Details $(if ($DemoVideoUrl) { $DemoVideoUrl } else { "missing" })
if (Is-DevpostVideoUrl $DemoVideoUrl) {
    $video = Test-Url -Url $DemoVideoUrl -Method "Get"
    Add-Check -Name "demo_video_url_reachable" -Ok $video.ok -Details $video.details
}
else {
    Add-Check -Name "demo_video_url_reachable" -Ok $false -Details "DemoVideoUrl missing or not YouTube/Vimeo/Youku"
}

Add-Check -Name "backend_url_present" -Ok (Is-HttpUrl $BackendUrl) -Details $(if ($BackendUrl) { $BackendUrl } else { "missing" })
if (Is-HttpUrl $BackendUrl) {
    try {
        $base = $BackendUrl.TrimEnd("/")
        $health = Invoke-RestMethod -Method Get -Uri "$base/health" -TimeoutSec 25
        Add-Check -Name "backend_health_status_ok" -Ok ($health.status -eq "ok") -Details "status=$($health.status)"
        Add-Check -Name "backend_track_memoryagent" -Ok ($health.track -eq $ExpectedTrack) -Details "track=$($health.track)"
        Add-Check -Name "backend_provider_qwen_cloud" -Ok ($health.llm_provider -eq "qwen-cloud") -Details "llm_provider=$($health.llm_provider)"
        Add-Check -Name "backend_deployment_target_alibaba" -Ok ([string]$health.deployment_target -match "Alibaba Cloud Function Compute") -Details "deployment_target=$($health.deployment_target)"
        Add-Check -Name "backend_alibaba_region_present" -Ok (-not [string]::IsNullOrWhiteSpace([string]$health.alibaba_cloud_region)) -Details "region=$($health.alibaba_cloud_region)"
        Add-Check -Name "backend_api_key_configured" -Ok ([bool]$health.llm_api_key_configured) -Details "llm_api_key_configured=$($health.llm_api_key_configured)"
        Add-Check -Name "backend_proof_file" -Ok ($health.proof_file -eq "deploy/alibaba/serverless-devs.yaml") -Details "proof_file=$($health.proof_file)"
    }
    catch {
        foreach ($name in @(
            "backend_health_status_ok",
            "backend_track_memoryagent",
            "backend_provider_qwen_cloud",
            "backend_deployment_target_alibaba",
            "backend_alibaba_region_present",
            "backend_api_key_configured",
            "backend_proof_file"
        )) {
            Add-Check -Name $name -Ok $false -Details $_.Exception.Message
        }
    }
}
else {
    foreach ($name in @(
        "backend_health_status_ok",
        "backend_track_memoryagent",
        "backend_provider_qwen_cloud",
        "backend_deployment_target_alibaba",
        "backend_alibaba_region_present",
        "backend_api_key_configured",
        "backend_proof_file"
    )) {
        Add-Check -Name $name -Ok $false -Details "BackendUrl missing"
    }
}

$screenshot = Test-File -Path $AlibabaScreenshotPath -MinBytes 1024
Add-Check -Name "alibaba_screenshot_exists" -Ok $screenshot.ok -Details $screenshot.details
$screenshotDims = Get-PngDimensions -Path $AlibabaScreenshotPath
Add-Check -Name "alibaba_screenshot_1280x720" -Ok ($screenshotDims -and $screenshotDims.width -ge 1280 -and $screenshotDims.height -ge 720) -Details $(if ($screenshotDims) { "$($screenshotDims.width)x$($screenshotDims.height)" } else { "not a readable PNG" })

$proofVideo = Test-File -Path $AlibabaProofVideoPath -MinBytes 1024
Add-Check -Name "alibaba_proof_video_exists" -Ok $proofVideo.ok -Details $proofVideo.details
$proofMetadata = Get-VideoMetadata -Path $AlibabaProofVideoPath
if ($proofMetadata) {
    Add-Check -Name "alibaba_proof_video_720p_h264" -Ok ($proofMetadata.width -ge 1280 -and $proofMetadata.height -ge 720 -and $proofMetadata.codec -eq "h264") -Details "resolution=$($proofMetadata.width)x$($proofMetadata.height); codec=$($proofMetadata.codec)"
    Add-Check -Name "alibaba_proof_video_short" -Ok ($proofMetadata.duration -gt 0 -and $proofMetadata.duration -le 60) -Details "duration=$($proofMetadata.duration); size=$($proofMetadata.size)"
}
else {
    Add-Check -Name "alibaba_proof_video_720p_h264" -Ok $false -Details "ffprobe unavailable or proof video missing"
    Add-Check -Name "alibaba_proof_video_short" -Ok $false -Details "ffprobe unavailable or proof video missing"
}

$requiredFailures = @($checks | Where-Object { $_.required -and -not $_.ok })
$ready = $requiredFailures.Count -eq 0
$status = if ($ready) { "READY" } else { "DRAFT" }

$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = $status
    readyForGoalCompletionEvidence = $ready
    devpostProjectUrl = $DevpostProjectUrl
    repoUrl = $RepoUrl
    demoVideoUrl = $DemoVideoUrl
    backendUrl = $BackendUrl
    alibabaScreenshotPath = $AlibabaScreenshotPath
    alibabaProofVideoPath = $AlibabaProofVideoPath
    reportJson = $reportJson
    reportMarkdown = $reportMd
    checks = $checks
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Post-Submit Verification ($timestamp)",
    "",
    "- Status: $status",
    "- Ready for goal completion evidence: $ready",
    "- Devpost public project URL: $(if ($DevpostProjectUrl) { $DevpostProjectUrl } else { '<missing>' })",
    "- Demo video URL: $(if ($DemoVideoUrl) { $DemoVideoUrl } else { '<missing>' })",
    "- Backend URL: $(if ($BackendUrl) { $BackendUrl } else { '<missing>' })",
    "- Repo URL: $RepoUrl",
    "- Alibaba screenshot: $AlibabaScreenshotPath",
    "- Alibaba proof video: $AlibabaProofVideoPath",
    "",
    "## Checks",
    "",
    "| Check | Required | Result | Details |",
    "|---|---:|---:|---|"
)
foreach ($check in $checks) {
    $resultText = if ($check.ok) { "PASS" } else { "FAIL" }
    $requiredText = if ($check.required) { "yes" } else { "no" }
    $lines += "| $($check.name) | $requiredText | $resultText | $($check.details -replace '\|', '/') |"
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
    "## Final Evidence Command",
    "",
    '```powershell',
    'scripts/qwencloud-post-submit-verification.ps1 -DevpostProjectUrl "https://devpost.com/software/<project-slug>" -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>"',
    '```'
)
Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($ready) {
    Write-Host "Post-submit verification READY: $reportMd"
}
else {
    Write-Host "Post-submit verification DRAFT: $reportMd" -ForegroundColor Yellow
    Write-Host "Missing required items: $($requiredFailures.name -join ', ')"
    if (-not $AllowDraft) {
        exit 1
    }
}
Write-Host "JSON: $reportJson"
