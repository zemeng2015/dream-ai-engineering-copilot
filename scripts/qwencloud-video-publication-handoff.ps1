# SPDX-License-Identifier: Apache-2.0

param(
    [Parameter(Mandatory = $false)]
    [string]$LocalVideoPath = "artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4",
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [string]$Platform = "YouTube",
    [Parameter(Mandatory = $false)]
    [string]$ChannelName = "Zemeng Wang",
    [Parameter(Mandatory = $false)]
    [string]$Visibility = "Public or Devpost-accessible unlisted",
    [Parameter(Mandatory = $false)]
    [string]$DemoVideoUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$ThumbnailPath = "artifacts/qwencloud-proof/video-v3/dream-v3-thumbnail.png",
    [Parameter(Mandatory = $false)]
    [string]$CaptionPath = "docs/qwencloud-demo-video-captions.srt",
    [Parameter(Mandatory = $false)]
    [string]$Title = "DREAM MemoryAgent: One Current Truth Across Qwen Sessions | Qwen Cloud",
    [Parameter(Mandatory = $false)]
    [string]$Description = "",
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
. (Join-Path $PSScriptRoot "qwencloud-devpost-video-url.ps1")

$reportJson = Join-Path $OutputDir "video-publication-handoff-$timestamp.json"
$reportMd = Join-Path $OutputDir "video-publication-handoff-$timestamp.md"
$checks = @()

if ([string]::IsNullOrWhiteSpace($Description)) {
    $Description = @"
DREAM gives Qwen governed cross-session experience. In three live sessions, Qwen remembers a durable preference, supersedes stale guidance, and recalls only the current truth in 19 of 64 tokens without leaking the old value.

The persistence proof rebuilds the same source onto a different Function Compute instance while preserving the same memory, decision, and Qwen provider receipt in Alibaba Tablestore. A public 20-request contention run completed 20/20 writes with one active truth, 19 historical versions, and no errors.

In a clearly labeled seven-case synthetic comparison, the same qwen3.7-plus model improved from 25.3 to 48.7 with DREAM (+23.4, 7/7 paired wins). A separate lifecycle suite passed 24/24 cases across recall, stale-leak, and token-budget checks. These are reproducible synthetic results, not production-effectiveness claims.

Runtime: Alibaba Cloud Function Compute + Qwen Cloud + Alibaba Tablestore, ap-southeast-1.
Live judge flow: https://dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run/hackathon-demo

Repo: https://github.com/zemeng2015/dream-ai-engineering-copilot/tree/codex/champion-memory-loop
Track: Track 1: MemoryAgent
"@
}

function Add-Check([string]$Name, [bool]$Ok, [string]$Details, [bool]$Required = $true) {
    $script:checks += [ordered]@{
        name = $Name
        ok = $Ok
        required = $Required
        details = $Details
    }
}

function Has-Command([string]$Name) {
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-FileSha256([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return "" }
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Get-VideoMetadata([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    if (-not (Has-Command "ffprobe")) { return $null }

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

function Get-LatestJson([string]$Filter) {
    $file = Get-ChildItem -LiteralPath $OutputDir -Filter $Filter -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $file) { return $null }

    return [pscustomobject]@{
        path = $file.FullName
        data = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
    }
}

function Test-AcceptedVideoUrl([string]$Url) {
    if ([string]::IsNullOrWhiteSpace($Url)) {
        return [pscustomobject]@{ ok = $false; details = "missing" }
    }

    return [pscustomobject]@{
        ok = (Test-QwenCloudDevpostVideoUrl -Url $Url)
        details = if (Test-QwenCloudDevpostVideoUrl -Url $Url) { "accepted Devpost Rules video URL" } else { Get-QwenCloudDevpostVideoPlatformMessage }
    }
}

$fileExists = Test-Path -LiteralPath $LocalVideoPath
$resolvedVideoPath = if ($fileExists) { (Resolve-Path -LiteralPath $LocalVideoPath).Path } else { $LocalVideoPath }
$videoSha256 = Get-FileSha256 -Path $LocalVideoPath
$thumbnailExists = Test-Path -LiteralPath $ThumbnailPath
$resolvedThumbnailPath = if ($thumbnailExists) { (Resolve-Path -LiteralPath $ThumbnailPath).Path } else { $ThumbnailPath }
$thumbnailSha256 = Get-FileSha256 -Path $ThumbnailPath
$captionExists = Test-Path -LiteralPath $CaptionPath
$resolvedCaptionPath = if ($captionExists) { (Resolve-Path -LiteralPath $CaptionPath).Path } else { $CaptionPath }
$captionSha256 = Get-FileSha256 -Path $CaptionPath
$metadata = Get-VideoMetadata -Path $LocalVideoPath
$render = Get-LatestJson -Filter "dream-qwencloud-devpost-final-validation.json"
if (-not $render) {
    $render = Get-LatestJson -Filter "demo-video-render-*.json"
}
$urlCheck = Test-AcceptedVideoUrl -Url $DemoVideoUrl

Add-Check -Name "local_video_exists" -Ok $fileExists -Details $(if ($fileExists) { $resolvedVideoPath } else { "missing: $LocalVideoPath" })
Add-Check -Name "thumbnail_exists" -Ok $thumbnailExists -Details $(if ($thumbnailExists) { $resolvedThumbnailPath } else { "missing: $ThumbnailPath" }) -Required $false
Add-Check -Name "caption_file_exists" -Ok $captionExists -Details $(if ($captionExists) { $resolvedCaptionPath } else { "missing: $CaptionPath" }) -Required $false
if ($metadata) {
    Add-Check -Name "local_video_under_3_minutes" -Ok ($metadata.duration -gt 0 -and $metadata.duration -lt 180) -Details "duration=$($metadata.duration)"
    Add-Check -Name "local_video_720p" -Ok ($metadata.width -ge 1280 -and $metadata.height -ge 720) -Details "resolution=$($metadata.width)x$($metadata.height)"
    Add-Check -Name "local_video_h264" -Ok ($metadata.codec -eq "h264") -Details "codec=$($metadata.codec)"
}
else {
    Add-Check -Name "local_video_metadata" -Ok $false -Details "ffprobe unavailable or local video missing"
}

if ($render) {
    $renderHash = if ($render.data.sha256) {
        [string]$render.data.sha256
    }
    else {
        [string]$render.data.outputSha256
    }
    Add-Check -Name "render_manifest_matches_video" -Ok ($renderHash -eq $videoSha256) -Details "render=$renderHash; video=$videoSha256"
}
else {
    Add-Check -Name "render_manifest_available" -Ok $false -Details "missing demo-video-render-*.json" -Required $false
}

Add-Check -Name "upload_title_ready" -Ok (-not [string]::IsNullOrWhiteSpace($Title)) -Details $Title
Add-Check -Name "upload_description_ready" -Ok (-not [string]::IsNullOrWhiteSpace($Description)) -Details "length=$($Description.Length)"
Add-Check -Name "public_video_url_ready" -Ok $urlCheck.ok -Details $urlCheck.details -Required $false

$requiredFailures = @($checks | Where-Object { $_.required -and -not $_.ok })
$readyForManualUpload = $requiredFailures.Count -eq 0
$status = if ($readyForManualUpload) { "READY" } else { "DRAFT" }
$tags = @(
    "Qwen Cloud",
    "Alibaba Cloud",
    "MemoryAgent",
    "experience memory",
    "cross-session memory",
    "context engineering",
    "hackathon"
)

$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = $status
    readyForManualUpload = $readyForManualUpload
    readyForDevpostVideoField = $urlCheck.ok
    requiresActionTimeConfirmation = $true
    platform = $Platform
    channelName = $ChannelName
    visibility = $Visibility
    localVideoPath = $LocalVideoPath
    resolvedVideoPath = $resolvedVideoPath
    localVideoSha256 = $videoSha256
    thumbnailPath = $ThumbnailPath
    resolvedThumbnailPath = $resolvedThumbnailPath
    thumbnailSha256 = $thumbnailSha256
    captionPath = $CaptionPath
    resolvedCaptionPath = $resolvedCaptionPath
    captionSha256 = $captionSha256
    renderManifestJson = if ($render) { $render.path } else { "" }
    demoVideoUrl = $DemoVideoUrl
    title = $Title
    description = $Description
    tags = $tags
    checks = $checks
    reportJson = $reportJson
    reportMarkdown = $reportMd
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Video Publication Handoff ($timestamp)",
    "",
    "- Status: $status",
    "- Ready for manual upload: $readyForManualUpload",
    "- Ready for Devpost video field: $($urlCheck.ok)",
    "- Requires action-time confirmation before upload: yes",
    "- Platform: $Platform",
    "- Channel/account: $ChannelName",
    "- Visibility: $Visibility",
    "- Local video: ``$resolvedVideoPath``",
    "- Local video SHA256: ``$videoSha256``",
    "- Thumbnail: ``$resolvedThumbnailPath``",
    "- Thumbnail SHA256: ``$thumbnailSha256``",
    "- Captions: ``$resolvedCaptionPath``",
    "- Captions SHA256: ``$captionSha256``",
    "- Public video URL: $(if ($DemoVideoUrl) { $DemoVideoUrl } else { '<missing>' })",
    "",
    "## Upload Copy",
    "",
    "Title:",
    "",
    '```text',
    $Title,
    '```',
    "",
    "Description:",
    "",
    '```text',
    $Description.Trim(),
    '```',
    "",
    "Tags:",
    "",
    '```text',
    ($tags -join ", "),
    '```',
    "",
    "Custom thumbnail:",
    "",
    '```text',
    $resolvedThumbnailPath,
    '```',
    "",
    "Captions/subtitles:",
    "",
    '```text',
    $resolvedCaptionPath,
    '```',
    "",
    "## Confirmation Boundary",
    "",
    "- Selecting the MP4 in YouTube/Vimeo/Facebook Video/Youku transmits the local file to that service.",
    "- Selecting the custom thumbnail transmits the thumbnail image to that service.",
    "- Selecting the caption/subtitle file transmits the caption text to that service.",
    "- Confirm the destination account/channel and visibility at action time before selecting the file.",
    "- Do not paste the resulting URL into Devpost until the public page is reachable without private login.",
    "",
    "## Checks",
    "",
    "| Check | Required | Result | Details |",
    "|---|---:|---:|---|"
)
foreach ($check in $checks) {
    $lines += "| $($check.name) | $(if ($check.required) { 'yes' } else { 'no' }) | $(if ($check.ok) { 'PASS' } else { 'FAIL' }) | $($check.details -replace '\|', '/') |"
}

if ($requiredFailures.Count -gt 0) {
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
    "## After Upload",
    "",
    '```powershell',
    'scripts/qwencloud-video-upload-status.ps1 -DemoVideoUrl "<public-video-url>"',
    'scripts/qwencloud-final-sprint.ps1 -DemoVideoUrl "<public-video-url>" -AllowDraft',
    '```'
)
Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($readyForManualUpload) {
    Write-Host "Video publication handoff READY: $reportMd"
}
else {
    Write-Host "Video publication handoff DRAFT: $reportMd" -ForegroundColor Yellow
    Write-Host "Missing required items: $($requiredFailures.name -join ', ')"
}
Write-Host "JSON: $reportJson"

if (-not $readyForManualUpload -and -not $AllowDraft) {
    exit 1
}
