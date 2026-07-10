# SPDX-License-Identifier: Apache-2.0
param(
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [string]$DeadlineUtc = "2026-07-20T21:00:00Z",
    [Parameter(Mandatory = $false)]
    [string]$NowUtc = "",
    [Parameter(Mandatory = $false)]
    [int]$WarningHours = 24,
    [Parameter(Mandatory = $false)]
    [string]$OfficialRequirementsSnapshotPath = "docs/qwencloud-official-requirements-snapshot.md",
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$reportJson = Join-Path $OutputDir "deadline-guard-$timestamp.json"
$reportMd = Join-Path $OutputDir "deadline-guard-$timestamp.md"
$checks = @()

function Add-Check([string]$Name, [bool]$Ok, [string]$Details, [bool]$Required = $true) {
    $script:checks += [ordered]@{
        name = $Name
        ok = $Ok
        required = $Required
        details = $Details
    }
}

function Parse-UtcDateTimeOffset([string]$Value, [string]$Label) {
    try {
        return [DateTimeOffset]::Parse($Value).ToUniversalTime()
    }
    catch {
        throw "$Label must be an ISO date/time value. Received: $Value"
    }
}

$deadline = Parse-UtcDateTimeOffset -Value $DeadlineUtc -Label "DeadlineUtc"
$now = if ([string]::IsNullOrWhiteSpace($NowUtc)) {
    [DateTimeOffset]::UtcNow
}
else {
    Parse-UtcDateTimeOffset -Value $NowUtc -Label "NowUtc"
}

$timeRemaining = $deadline - $now
$hoursRemaining = [Math]::Round($timeRemaining.TotalHours, 2)
$submissionWindowOpen = $timeRemaining.TotalSeconds -gt 0
$warningWindow = $submissionWindowOpen -and $timeRemaining.TotalHours -le $WarningHours
$urgency = if (-not $submissionWindowOpen) {
    "expired"
}
elseif ($warningWindow) {
    "final-day"
}
else {
    "open"
}

Add-Check -Name "deadline_utc_configured" -Ok ($deadline.ToString("o") -eq "2026-07-20T21:00:00.0000000+00:00") -Details "deadlineUtc=$($deadline.ToString('o')); expected=2026-07-20T21:00:00Z"
Add-Check -Name "submission_window_open" -Ok $submissionWindowOpen -Details "nowUtc=$($now.ToString('o')); deadlineUtc=$($deadline.ToString('o')); hoursRemaining=$hoursRemaining"
Add-Check -Name "deadline_warning_window" -Ok (-not $warningWindow) -Details "urgency=$urgency; warningHours=$WarningHours; hoursRemaining=$hoursRemaining" -Required $false

if (Test-Path -LiteralPath $OfficialRequirementsSnapshotPath) {
    $snapshot = Get-Content -LiteralPath $OfficialRequirementsSnapshotPath -Raw
    Add-Check `
        -Name "official_snapshot_deadline_present" `
        -Ok (($snapshot -match "July 20, 2026 at 2:00pm PDT") -and ($snapshot -match "2026-07-20T21:00:00Z")) `
        -Details $OfficialRequirementsSnapshotPath
}
else {
    Add-Check -Name "official_snapshot_deadline_present" -Ok $false -Details "missing: $OfficialRequirementsSnapshotPath"
}

$requiredFailures = @($checks | Where-Object { $_.required -and -not $_.ok })
$ready = $requiredFailures.Count -eq 0

$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = if ($ready) { "READY" } else { "DRAFT" }
    readyForSubmissionWindow = $ready
    urgency = $urgency
    nowUtc = $now.ToString("o")
    deadlineUtc = $deadline.ToString("o")
    hoursRemaining = $hoursRemaining
    warningHours = $WarningHours
    officialRequirementsSnapshotPath = $OfficialRequirementsSnapshotPath
    reportJson = $reportJson
    reportMarkdown = $reportMd
    checks = $checks
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Deadline Guard ($timestamp)",
    "",
    "- Ready for submission window: $ready",
    "- Urgency: $urgency",
    "- Now UTC: $($now.ToString('o'))",
    "- Deadline UTC: $($deadline.ToString('o'))",
    "- Hours remaining: $hoursRemaining",
    "- Official snapshot: $OfficialRequirementsSnapshotPath",
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
    "## Next Command",
    "",
    '```powershell',
    'scripts/qwencloud-finalize-after-urls.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>" -RefreshAlibabaProof',
    '```'
)

Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($ready) {
    Write-Host "Deadline guard READY: $reportMd"
}
else {
    Write-Host "Deadline guard DRAFT: $reportMd" -ForegroundColor Yellow
    Write-Host "Missing required checks: $($requiredFailures.name -join ', ')"
    if (-not $AllowDraft) {
        exit 1
    }
}
Write-Host "JSON: $reportJson"
