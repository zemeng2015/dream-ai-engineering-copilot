param(
    [Parameter(Mandatory = $false)]
    [string]$DemoVideoUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$LocalVideoPath = "artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4",
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [switch]$SkipExternalUrlChecks,
    [switch]$SkipLocalVideoChecks,
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
. (Join-Path $PSScriptRoot "qwencloud-devpost-video-url.ps1")

$reportJson = Join-Path $OutputDir "video-upload-status-$timestamp.json"
$reportMd = Join-Path $OutputDir "video-upload-status-$timestamp.md"
$checks = @()

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

function Get-VideoMetadata([string]$Path) {
    if (-not (Test-Path $Path)) { return $null }
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

function Test-AcceptedVideoUrl([string]$Url) {
    if ([string]::IsNullOrWhiteSpace($Url)) {
        return [pscustomobject]@{ ok = $false; details = "missing" }
    }

    return [pscustomobject]@{
        ok = (Test-QwenCloudDevpostVideoUrl -Url $Url)
        details = if (Test-QwenCloudDevpostVideoUrl -Url $Url) { "accepted Devpost Rules video URL" } else { Get-QwenCloudDevpostVideoPlatformMessage }
    }
}

function Test-ExternalReachable([string]$Url) {
    if ([string]::IsNullOrWhiteSpace($Url)) {
        return [pscustomobject]@{ ok = $false; details = "missing" }
    }
    if ($SkipExternalUrlChecks) {
        return [pscustomobject]@{ ok = $true; details = "skipped by -SkipExternalUrlChecks" }
    }

    try {
        $response = Invoke-WebRequest -Method Head -Uri $Url -MaximumRedirection 5 -TimeoutSec 20 -ErrorAction Stop
        return [pscustomobject]@{ ok = ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400); details = "HEAD status=$($response.StatusCode)" }
    }
    catch {
        try {
            $response = Invoke-WebRequest -Method Get -Uri $Url -MaximumRedirection 5 -TimeoutSec 20 -ErrorAction Stop
            return [pscustomobject]@{ ok = ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400); details = "GET status=$($response.StatusCode)" }
        }
        catch {
            return [pscustomobject]@{ ok = $false; details = $_.Exception.Message }
        }
    }
}

if ($SkipLocalVideoChecks) {
    Add-Check -Name "local_demo_video_exists" -Ok $true -Details "skipped by -SkipLocalVideoChecks" -Required $false
    Add-Check -Name "local_demo_video_metadata" -Ok $true -Details "skipped by -SkipLocalVideoChecks" -Required $false
}
else {
    $fileExists = Test-Path $LocalVideoPath
    Add-Check -Name "local_demo_video_exists" -Ok $fileExists -Details $(if ($fileExists) { $LocalVideoPath } else { "missing: $LocalVideoPath" })

    $metadata = Get-VideoMetadata -Path $LocalVideoPath
    if ($metadata) {
        Add-Check -Name "local_demo_video_under_3_minutes" -Ok ($metadata.duration -gt 0 -and $metadata.duration -lt 180) -Details "duration=$($metadata.duration); size=$($metadata.size); resolution=$($metadata.width)x$($metadata.height); codec=$($metadata.codec)"
        Add-Check -Name "local_demo_video_720p" -Ok ($metadata.width -ge 1280 -and $metadata.height -ge 720) -Details "resolution=$($metadata.width)x$($metadata.height)"
        Add-Check -Name "local_demo_video_h264" -Ok ($metadata.codec -eq "h264") -Details "codec=$($metadata.codec)"
    }
    else {
        Add-Check -Name "local_demo_video_metadata" -Ok $false -Details "ffprobe unavailable or video missing"
    }
}

$platform = Test-AcceptedVideoUrl -Url $DemoVideoUrl
Add-Check -Name "public_demo_video_url_platform" -Ok $platform.ok -Details $platform.details

$reachable = Test-ExternalReachable -Url $DemoVideoUrl
Add-Check -Name "public_demo_video_url_reachable" -Ok $reachable.ok -Details $reachable.details

$requiredFailures = @($checks | Where-Object { $_.required -and -not $_.ok })
$ready = $requiredFailures.Count -eq 0
$status = if ($ready) { "READY" } else { "DRAFT" }

$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = $status
    readyForDevpostVideoField = $ready
    localVideoPath = $LocalVideoPath
    skipLocalVideoChecks = [bool]$SkipLocalVideoChecks
    demoVideoUrl = $DemoVideoUrl
    reportJson = $reportJson
    reportMarkdown = $reportMd
    checks = $checks
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Video Upload Status ($timestamp)",
    "",
    "- Status: $status",
    "- Ready for Devpost video field: $ready",
    "- Local video: $LocalVideoPath",
    "- Public video URL: $(if ($DemoVideoUrl) { $DemoVideoUrl } else { '<missing>' })",
    "",
    "## Checks",
    "",
    "| Check | Required | Result | Details |",
    "|---|---:|---:|---|"
)
foreach ($check in $checks) {
    $lines += "| $($check.name) | $(if ($check.required) { 'yes' } else { 'no' }) | $(if ($check.ok) { 'PASS' } else { 'FAIL' }) | $($check.details -replace '\|', '/') |"
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
    "## Upload Handoff",
    "",
    "- Upload file: ``$LocalVideoPath``",
    "- Preferred platform: YouTube",
    '- Title: `DREAM: Qwen Cloud MemoryAgent for Source-Backed Engineering Intelligence`',
    '- If Codex-controlled Chrome file upload returns `Not allowed`, enable Chrome extension file access:',
    "",
    '```text',
    'To enable file upload, go to chrome://extensions in Chrome, click Details under the Codex extension, and enable "Allow access to file URLs." See https://developers.openai.com/codex/app/chrome-extension#upload-files for details.',
    '```',
    "",
    "## Next Commands",
    "",
    '```powershell',
    'scripts/qwencloud-video-upload-status.ps1 -DemoVideoUrl "<public-video-url>"',
    'scripts/qwencloud-finalize-after-urls.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-url>"',
    '```'
)
Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($ready) {
    Write-Host "Video upload status READY: $reportMd"
}
else {
    Write-Host "Video upload status DRAFT: $reportMd" -ForegroundColor Yellow
    Write-Host "Missing required items: $($requiredFailures.name -join ', ')"
}
Write-Host "JSON: $reportJson"

if (-not $ready -and -not $AllowDraft) {
    exit 1
}
