param(
    [Parameter(Mandatory = $false)]
    [string]$BackendUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [string]$ScreenshotPath = "artifacts/qwencloud-proof/alibaba-deployment-screenshot.png",
    [Parameter(Mandatory = $false)]
    [string]$ProofVideoPath = "artifacts/qwencloud-proof/alibaba-deployment-proof.mp4",
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$reportJson = Join-Path $OutputDir "alibaba-proof-integrity-$timestamp.json"
$reportMd = Join-Path $OutputDir "alibaba-proof-integrity-$timestamp.md"
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

function Normalize-Url([string]$Url) {
    if ([string]::IsNullOrWhiteSpace($Url)) {
        return ""
    }
    return $Url.Trim().TrimEnd("/")
}

function Is-HttpUrl([string]$Url) {
    return -not [string]::IsNullOrWhiteSpace($Url) -and $Url -match "^https?://"
}

function Test-TrueBoolean($Value) {
    if ($Value -is [bool]) {
        return $Value
    }
    return @("true", "1", "yes") -contains ([string]$Value).ToLowerInvariant()
}

function Get-LatestCaptureJson {
    Get-ChildItem -LiteralPath $OutputDir -Filter "alibaba-deployment-proof-*.json" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Test-PngDimensions([string]$Path) {
    if (-not (Test-Path $Path)) {
        return $null
    }

    $bytes = [System.IO.File]::ReadAllBytes((Resolve-Path $Path))
    if ($bytes.Length -lt 24) {
        return $null
    }

    $signature = @(137, 80, 78, 71, 13, 10, 26, 10)
    for ($i = 0; $i -lt $signature.Count; $i++) {
        if ([int]$bytes[$i] -ne $signature[$i]) {
            return $null
        }
    }

    return [pscustomobject]@{
        width = ([int]$bytes[16] -shl 24) -bor ([int]$bytes[17] -shl 16) -bor ([int]$bytes[18] -shl 8) -bor [int]$bytes[19]
        height = ([int]$bytes[20] -shl 24) -bor ([int]$bytes[21] -shl 16) -bor ([int]$bytes[22] -shl 8) -bor [int]$bytes[23]
    }
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

$normalizedBackendUrl = Normalize-Url -Url $BackendUrl
Add-Check -Name "backend_url_present" -Ok (Is-HttpUrl $normalizedBackendUrl) -Details $(if ($normalizedBackendUrl) { $normalizedBackendUrl } else { "missing" })

$captureJsonFile = Get-LatestCaptureJson
Add-Check -Name "capture_json_exists" -Ok ($null -ne $captureJsonFile) -Details $(if ($captureJsonFile) { $captureJsonFile.FullName } else { "missing alibaba-deployment-proof-*.json" })

$capture = $null
if ($captureJsonFile) {
    try {
        $capture = Get-Content -LiteralPath $captureJsonFile.FullName -Raw | ConvertFrom-Json
        Add-Check -Name "capture_json_parseable" -Ok $true -Details $captureJsonFile.FullName
    }
    catch {
        Add-Check -Name "capture_json_parseable" -Ok $false -Details $_.Exception.Message
    }
}
else {
    Add-Check -Name "capture_json_parseable" -Ok $false -Details "capture JSON missing"
}

if ($capture) {
    $health = $capture.health
    Add-Check -Name "capture_base_url_matches_backend_url" -Ok ((Normalize-Url -Url $capture.baseUrl) -eq $normalizedBackendUrl) -Details "capture=$($capture.baseUrl); backend=$normalizedBackendUrl"
    Add-Check -Name "capture_output_png_matches" -Ok ($capture.outputPng -eq $ScreenshotPath) -Details "capture=$($capture.outputPng); expected=$ScreenshotPath" -Required $false
    Add-Check -Name "health_status_ok" -Ok ($health.status -eq "ok") -Details "status=$($health.status)"
    Add-Check -Name "health_track_memoryagent" -Ok ($health.track -eq "Track 1: MemoryAgent") -Details "track=$($health.track)"
    Add-Check -Name "health_provider_qwen_cloud" -Ok ($health.llm_provider -eq "qwen-cloud") -Details "llm_provider=$($health.llm_provider)"
    Add-Check -Name "health_proof_file" -Ok ($health.proof_file -eq "deploy/alibaba/serverless-devs.yaml") -Details "proof_file=$($health.proof_file)"
    Add-Check -Name "health_deployment_target_alibaba" -Ok ([string]$health.deployment_target -match "Alibaba Cloud Function Compute") -Details "deployment_target=$($health.deployment_target)"
    Add-Check -Name "health_alibaba_region_present" -Ok (-not [string]::IsNullOrWhiteSpace([string]$health.alibaba_cloud_region)) -Details "region=$($health.alibaba_cloud_region)"
    Add-Check -Name "health_alibaba_service_present" -Ok (-not [string]::IsNullOrWhiteSpace([string]$health.alibaba_cloud_service)) -Details "service=$($health.alibaba_cloud_service)" -Required $false
    Add-Check -Name "health_api_key_configured" -Ok (Test-TrueBoolean $health.llm_api_key_configured) -Details "llm_api_key_configured=$($health.llm_api_key_configured)"

    $failedCaptureChecks = @($capture.checks | Where-Object { -not $_.pass } | ForEach-Object { $_.name })
    Add-Check -Name "capture_checks_all_passed" -Ok ($failedCaptureChecks.Count -eq 0) -Details $(if ($failedCaptureChecks.Count -eq 0) { "all pass" } else { $failedCaptureChecks -join ", " })
}
else {
    foreach ($name in @(
        "capture_base_url_matches_backend_url",
        "health_status_ok",
        "health_track_memoryagent",
        "health_provider_qwen_cloud",
        "health_proof_file",
        "health_deployment_target_alibaba",
        "health_alibaba_region_present",
        "health_api_key_configured",
        "capture_checks_all_passed"
    )) {
        Add-Check -Name $name -Ok $false -Details "capture JSON unavailable"
    }
}

$screenshotExists = Test-Path $ScreenshotPath
Add-Check -Name "screenshot_exists" -Ok $screenshotExists -Details $(if ($screenshotExists) { $ScreenshotPath } else { "missing: $ScreenshotPath" })
$screenshotDims = Test-PngDimensions -Path $ScreenshotPath
Add-Check -Name "screenshot_png_1280x720" -Ok ($screenshotDims -and $screenshotDims.width -ge 1280 -and $screenshotDims.height -ge 720) -Details $(if ($screenshotDims) { "$($screenshotDims.width)x$($screenshotDims.height)" } else { "not a readable PNG" })

$videoExists = Test-Path $ProofVideoPath
Add-Check -Name "proof_video_exists" -Ok $videoExists -Details $(if ($videoExists) { $ProofVideoPath } else { "missing: $ProofVideoPath" })
$videoMetadata = Get-VideoMetadata -Path $ProofVideoPath
if ($videoMetadata) {
    Add-Check -Name "proof_video_duration_short" -Ok ($videoMetadata.duration -ge 5 -and $videoMetadata.duration -le 60) -Details "duration=$($videoMetadata.duration); size=$($videoMetadata.size); format=$($videoMetadata.format)"
    Add-Check -Name "proof_video_720p_h264" -Ok ($videoMetadata.width -ge 1280 -and $videoMetadata.height -ge 720 -and $videoMetadata.codec -eq "h264") -Details "resolution=$($videoMetadata.width)x$($videoMetadata.height); codec=$($videoMetadata.codec)"
}
else {
    Add-Check -Name "proof_video_duration_short" -Ok $false -Details "ffprobe unavailable or proof video missing"
    Add-Check -Name "proof_video_720p_h264" -Ok $false -Details "ffprobe unavailable or proof video missing"
}

$requiredFailures = @($checks | Where-Object { $_.required -and -not $_.ok })
$ready = $requiredFailures.Count -eq 0
$status = if ($ready) { "READY" } else { "DRAFT" }

$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = $status
    readyForDevpostAlibabaProof = $ready
    backendUrl = $normalizedBackendUrl
    screenshotPath = $ScreenshotPath
    proofVideoPath = $ProofVideoPath
    captureJson = if ($captureJsonFile) { $captureJsonFile.FullName } else { $null }
    reportJson = $reportJson
    reportMarkdown = $reportMd
    checks = $checks
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Alibaba Proof Integrity ($timestamp)",
    "",
    "- Status: $status",
    "- Ready for Devpost Alibaba proof: $ready",
    "- Backend URL: $(if ($normalizedBackendUrl) { $normalizedBackendUrl } else { '<missing>' })",
    "- Screenshot: $ScreenshotPath",
    "- Proof video: $ProofVideoPath",
    "- Capture JSON: $(if ($captureJsonFile) { $captureJsonFile.FullName } else { '<missing>' })",
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
    "## Regenerate Proof",
    "",
    '```powershell',
    'scripts/qwencloud-render-alibaba-proof-video.ps1 -BaseUrl "<deployed-backend-url>" -IncludeDraft',
    'scripts/qwencloud-validate-alibaba-proof.ps1 -BackendUrl "<deployed-backend-url>"',
    '```'
)
Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($ready) {
    Write-Host "Alibaba proof integrity READY: $reportMd"
}
else {
    Write-Host "Alibaba proof integrity DRAFT: $reportMd" -ForegroundColor Yellow
    Write-Host "Missing required items: $($requiredFailures.name -join ', ')"
}
Write-Host "JSON: $reportJson"

if (-not $ready -and -not $AllowDraft) {
    exit 1
}
