param(
    [Parameter(Mandatory = $true)]
    [string]$BaseUrl,
    [Parameter(Mandatory = $false)]
    [string]$ScreenshotPath = "artifacts/qwencloud-proof/alibaba-deployment-screenshot.png",
    [Parameter(Mandatory = $false)]
    [string]$OutputMp4 = "artifacts/qwencloud-proof/alibaba-deployment-proof.mp4",
    [Parameter(Mandatory = $false)]
    [int]$DurationSeconds = 12,
    [switch]$IncludeDraft,
    [switch]$AllowLocal,
    [switch]$SkipCapture
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$artifactDir = "artifacts/qwencloud-proof"
New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null

function Resolve-WorkspacePath([string]$Path) {
    if ([System.IO.Path]::IsPathRooted($Path)) {
        return $Path
    }
    return Join-Path (Get-Location) $Path
}

function Get-PowerShellExe {
    $pwsh = Get-Command "pwsh" -ErrorAction SilentlyContinue
    if ($pwsh) { return $pwsh.Source }

    $powershell = Get-Command "powershell" -ErrorAction SilentlyContinue
    if ($powershell) { return $powershell.Source }

    throw "PowerShell executable not found."
}

function Quote-ProcessArgument([string]$Argument) {
    return '"' + ($Argument -replace '"', '\"') + '"'
}

if ($BaseUrl -notmatch "^https?://") {
    throw "BaseUrl must be an http(s) URL."
}
if ($DurationSeconds -lt 5 -or $DurationSeconds -gt 60) {
    throw "DurationSeconds must be between 5 and 60."
}
if (-not (Get-Command "ffmpeg" -ErrorAction SilentlyContinue)) {
    throw "ffmpeg is required to render the Alibaba deployment proof video."
}

$resolvedScreenshot = Resolve-WorkspacePath -Path $ScreenshotPath
$resolvedOutput = Resolve-WorkspacePath -Path $OutputMp4
New-Item -ItemType Directory -Path (Split-Path -Parent $resolvedScreenshot) -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path -Parent $resolvedOutput) -Force | Out-Null

if (-not $SkipCapture) {
    $captureArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-capture-alibaba-proof.ps1",
        "-BaseUrl", $BaseUrl,
        "-OutputPng", $ScreenshotPath
    )
    if ($IncludeDraft) { $captureArgs += "-IncludeDraft" }
    if ($AllowLocal) { $captureArgs += "-AllowLocal" }

    $captureOut = Join-Path $artifactDir "alibaba-proof-video-capture-$timestamp.out"
    $captureErr = Join-Path $artifactDir "alibaba-proof-video-capture-$timestamp.err"
    $capture = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $captureArgs -NoNewWindow -Wait -PassThru -RedirectStandardOutput $captureOut -RedirectStandardError $captureErr
    if ($capture.ExitCode -ne 0) {
        throw "Alibaba proof screenshot capture failed. See $captureErr"
    }
}

if (-not (Test-Path $resolvedScreenshot)) {
    throw "Alibaba proof screenshot is missing: $ScreenshotPath"
}

$ffmpegOut = Join-Path $artifactDir "alibaba-proof-video-$timestamp.out"
$ffmpegErr = Join-Path $artifactDir "alibaba-proof-video-$timestamp.err"
$filter = "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p"
$ffmpegArgs = @(
    "-y",
    "-loop", "1",
    "-framerate", "24",
    "-i", $resolvedScreenshot,
    "-t", "$DurationSeconds",
    "-vf", $filter,
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
    $resolvedOutput
)

$ffmpegArgumentString = ($ffmpegArgs | ForEach-Object { Quote-ProcessArgument $_ }) -join " "
$render = Start-Process -FilePath "ffmpeg" -ArgumentList $ffmpegArgumentString -NoNewWindow -Wait -PassThru -RedirectStandardOutput $ffmpegOut -RedirectStandardError $ffmpegErr
if ($render.ExitCode -ne 0) {
    throw "Alibaba proof video render failed. See $ffmpegErr"
}

if (-not (Test-Path $resolvedOutput)) {
    throw "Alibaba proof video was not created: $OutputMp4"
}

$video = Get-Item -LiteralPath $resolvedOutput
if ($video.Length -le 0) {
    throw "Alibaba proof video is empty: $OutputMp4"
}

$probeDetails = "ffprobe unavailable"
if (Get-Command "ffprobe" -ErrorAction SilentlyContinue) {
    $probeJson = & ffprobe -v error -show_entries format=duration,size -of json $resolvedOutput
    $probe = $probeJson | ConvertFrom-Json
    $probeDetails = "duration=$($probe.format.duration); size=$($probe.format.size)"
}

Write-Host "Alibaba deployment proof video exported: $OutputMp4 ($($video.Length) bytes)"
Write-Host "Source screenshot: $ScreenshotPath"
Write-Host "Video metadata: $probeDetails"
