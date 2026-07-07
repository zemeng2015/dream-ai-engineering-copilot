# SPDX-License-Identifier: Apache-2.0

param(
    [Parameter(Mandatory = $false)]
    [string]$RepoUrl = "https://github.com/zemeng2015/dream-ai-engineering-copilot",
    [Parameter(Mandatory = $false)]
    [string]$DemoVideoUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$BackendUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [int]$SeedPromoteCount = 6,
    [switch]$SkipRuntimeProof,
    [switch]$SkipFrontendBuild,
    [switch]$SkipScorecard,
    [switch]$SkipReadiness,
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$reportJson = Join-Path $OutputDir "judge-rehearsal-$timestamp.json"
$reportMd = Join-Path $OutputDir "judge-rehearsal-$timestamp.md"
$steps = @()
$checks = @()

function Get-PowerShellExe {
    $pwsh = Get-Command "pwsh" -ErrorAction SilentlyContinue
    if ($pwsh) { return $pwsh.Source }

    $powershell = Get-Command "powershell" -ErrorAction SilentlyContinue
    if ($powershell) { return $powershell.Source }

    throw "PowerShell executable not found."
}

function Resolve-OutputPath([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return ""
    }
    if ([System.IO.Path]::IsPathRooted($Path)) {
        return $Path
    }
    return (Join-Path (Get-Location) $Path)
}

function Add-Check([string]$Name, [bool]$Ok, [string]$Details, [bool]$Required = $true) {
    $script:checks += [ordered]@{
        name = $Name
        ok = $Ok
        required = $Required
        details = $Details
    }
}

function Add-SkippedStep([string]$Name, [string]$Details, [bool]$Required = $false) {
    $step = [ordered]@{
        name = $Name
        skipped = $true
        ok = (-not $Required)
        required = $Required
        exitCode = $null
        command = ""
        stdout = ""
        stderr = ""
        details = $Details
    }
    $script:steps += $step
    return [pscustomobject]$step
}

function Invoke-LoggedStep {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $false)][bool]$Required = $true,
        [Parameter(Mandatory = $false)][bool]$AcceptNonZero = $false
    )

    $safeName = $Name -replace "[^A-Za-z0-9_.-]", "-"
    $stdout = Join-Path $OutputDir "judge-rehearsal-$safeName-$timestamp.out"
    $stderr = Join-Path $OutputDir "judge-rehearsal-$safeName-$timestamp.err"
    $started = Get-Date
    $proc = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $Arguments `
        -NoNewWindow `
        -Wait `
        -PassThru `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr
    $duration = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
    $ok = ($proc.ExitCode -eq 0) -or $AcceptNonZero
    $step = [ordered]@{
        name = $Name
        skipped = $false
        ok = $ok
        required = $Required
        exitCode = $proc.ExitCode
        command = "$FilePath $($Arguments -join ' ')"
        stdout = $stdout
        stderr = $stderr
        durationSeconds = $duration
        details = "exit=$($proc.ExitCode); stdout=$stdout; stderr=$stderr"
    }
    $script:steps += $step
    return [pscustomobject]$step
}

function Read-JsonFile([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path $Path)) {
        return $null
    }
    return (Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json)
}

function Extract-PathFromStdout([string]$StdoutPath, [string]$Label) {
    if (-not (Test-Path $StdoutPath)) {
        return ""
    }
    $text = Get-Content -LiteralPath $StdoutPath -Raw
    $pattern = "(?m)^$([regex]::Escape($Label)):\s*(?<path>.+?)\s*$"
    $match = [regex]::Match($text, $pattern)
    if (-not $match.Success) {
        return ""
    }
    return (Resolve-OutputPath $match.Groups["path"].Value.Trim())
}

function Get-LatestArtifact([string]$Filter) {
    $item = Get-ChildItem -LiteralPath $OutputDir -Filter $Filter -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($item) { return $item.FullName }
    return ""
}

foreach ($path in @(
    "scripts/qwencloud_seed_demo_artifact.py",
    "scripts/qwencloud-run-local-proof.ps1",
    "scripts/qwencloud-frontend-build-proof.ps1",
    "scripts/qwencloud-judging-scorecard.ps1",
    "scripts/qwencloud-final-readiness.ps1",
    "frontend/src/app/features/hackathon-demo/hackathon-demo.component.ts",
    "docs/qwencloud-devpost-submission-kit.md"
)) {
    Add-Check -Name "file.$path" -Ok (Test-Path $path) -Details $path
}

$python = Get-Command "python" -ErrorAction SilentlyContinue
Add-Check -Name "tool.python" -Ok ($null -ne $python) -Details $(if ($python) { $python.Source } else { "missing" })
$powerShellExe = Get-PowerShellExe

$seedStep = Invoke-LoggedStep `
    -Name "seeded-demo-artifact" `
    -FilePath $(if ($python) { $python.Source } else { "python" }) `
    -Arguments @(
        "scripts/qwencloud_seed_demo_artifact.py",
        "--output-dir", $OutputDir,
        "--promote-count", "$SeedPromoteCount"
    )
$seedSummaryPath = Extract-PathFromStdout -StdoutPath $seedStep.stdout -Label "JSON"
$seedZipPath = Extract-PathFromStdout -StdoutPath $seedStep.stdout -Label "ZIP"
$seedSummary = Read-JsonFile -Path $seedSummaryPath
$seedReady = $seedStep.ok -and $seedSummary -and [bool]$seedSummary.readyForJudgeDemo

if ($SkipRuntimeProof) {
    $localProofStep = Add-SkippedStep -Name "local-runtime-proof" -Details "skipped by -SkipRuntimeProof" -Required $true
    $localProofPath = ""
}
else {
    $localProofStep = Invoke-LoggedStep `
        -Name "local-runtime-proof" `
        -FilePath $powerShellExe `
        -Arguments @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", "scripts/qwencloud-run-local-proof.ps1",
            "-OutputDir", $OutputDir,
            "-SkipDraft",
            "-AllowDirty"
        )
    $localProofPath = Get-LatestArtifact -Filter "local-proof-*.json"
}

if ($SkipFrontendBuild) {
    $frontendStep = Add-SkippedStep -Name "frontend-build-proof" -Details "skipped by -SkipFrontendBuild" -Required $true
    $frontendProofPath = ""
}
else {
    $frontendStep = Invoke-LoggedStep `
        -Name "frontend-build-proof" `
        -FilePath $powerShellExe `
        -Arguments @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", "scripts/qwencloud-frontend-build-proof.ps1",
            "-OutputDir", $OutputDir,
            "-AllowDraft"
        )
    $frontendProofPath = Get-LatestArtifact -Filter "frontend-build-proof-*.json"
}

if ($SkipScorecard) {
    $scorecardStep = Add-SkippedStep -Name "judging-scorecard" -Details "skipped by -SkipScorecard"
    $scorecardPath = ""
}
else {
    $scorecardArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-judging-scorecard.ps1",
        "-RepoUrl", $RepoUrl,
        "-OutputDir", $OutputDir,
        "-AllowDraft"
    )
    if ($DemoVideoUrl) { $scorecardArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
    if ($BackendUrl) { $scorecardArgs += @("-BackendUrl", $BackendUrl) }
    $scorecardStep = Invoke-LoggedStep `
        -Name "judging-scorecard" `
        -FilePath $powerShellExe `
        -Arguments $scorecardArgs
    $scorecardPath = Get-LatestArtifact -Filter "judging-scorecard-*.json"
}

if ($SkipReadiness) {
    $readinessStep = Add-SkippedStep -Name "final-readiness" -Details "skipped by -SkipReadiness"
    $readinessPath = ""
}
else {
    $readinessArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-final-readiness.ps1",
        "-RepoUrl", $RepoUrl,
        "-OutputDir", $OutputDir,
        "-AllowDraftPacket"
    )
    if ($DemoVideoUrl) { $readinessArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
    if ($BackendUrl) { $readinessArgs += @("-BackendUrl", $BackendUrl) }
    $readinessStep = Invoke-LoggedStep `
        -Name "final-readiness" `
        -FilePath $powerShellExe `
        -Arguments $readinessArgs `
        -AcceptNonZero $true `
        -Required $false
    $readinessPath = Get-LatestArtifact -Filter "final-readiness-*.json"
}

$scorecard = Read-JsonFile -Path $scorecardPath
$readiness = Read-JsonFile -Path $readinessPath
$readinessFailures = @()
if ($readiness) {
    $readinessFailures = @($readiness.checks |
        Where-Object { $_.required -and -not $_.ok } |
        ForEach-Object { $_.name })
}

$demoShots = @(
    [ordered]@{
        name = "Guided route and live Qwen health proof"
        ready = ($localProofStep.ok -and $frontendStep.ok)
        evidence = @($localProofPath, $frontendProofPath) | Where-Object { $_ }
        fallback = "Open /hackathon-demo; if backend is offline the route still shows an explicit waiting state."
    },
    [ordered]@{
        name = "Seeded Memory Hub claim review"
        ready = $seedReady
        evidence = @($seedSummaryPath, $seedZipPath) | Where-Object { $_ }
        fallback = "Run python scripts/qwencloud_seed_demo_artifact.py --promote-count $SeedPromoteCount."
    },
    [ordered]@{
        name = "Requirement draft flow"
        ready = $localProofStep.ok
        evidence = @($localProofPath) | Where-Object { $_ }
        fallback = "Use scripts/qwencloud-run-local-proof.ps1 to show /health and optional draft checks."
    },
    [ordered]@{
        name = "Audit, eval, and judging alignment"
        ready = ($scorecardStep.ok -and -not [string]::IsNullOrWhiteSpace($scorecardPath))
        evidence = @($scorecardPath) | Where-Object { $_ }
        fallback = "Open the latest judging-scorecard-*.md for criterion-by-criterion evidence."
    }
)

$requiredFailures = @()
foreach ($check in $checks) {
    if ($check.required -and -not $check.ok) {
        $requiredFailures += $check.name
    }
}
foreach ($step in $steps) {
    if ($step.required -and -not $step.ok) {
        $requiredFailures += $step.name
    }
}
foreach ($shot in $demoShots) {
    if (-not $shot.ready) {
        $requiredFailures += "demo_shot.$($shot.name)"
    }
}

$finalSubmissionBlockers = @()
if ([string]::IsNullOrWhiteSpace($DemoVideoUrl)) { $finalSubmissionBlockers += "public_demo_video_url" }
if ([string]::IsNullOrWhiteSpace($BackendUrl)) { $finalSubmissionBlockers += "deployed_backend_url" }
if ($readinessFailures.Count -gt 0) { $finalSubmissionBlockers += $readinessFailures }

$ready = $requiredFailures.Count -eq 0
$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = if ($ready) { "READY" } else { "DRAFT" }
    readyForJudgeRehearsal = $ready
    repoUrl = $RepoUrl
    demoVideoUrl = $DemoVideoUrl
    backendUrl = $BackendUrl
    seedPromoteCount = $SeedPromoteCount
    seedSummaryJson = $seedSummaryPath
    seedZip = $seedZipPath
    localProofJson = $localProofPath
    frontendProofJson = $frontendProofPath
    judgingScorecardJson = $scorecardPath
    finalReadinessJson = $readinessPath
    scorecardStatus = if ($scorecard) { [string]$scorecard.status } else { "" }
    finalReadinessReady = if ($readiness) { [bool]$readiness.readyForFinalSubmit } else { $false }
    demoShots = $demoShots
    checks = $checks
    steps = $steps
    requiredFailures = $requiredFailures
    finalSubmissionBlockers = @($finalSubmissionBlockers | Select-Object -Unique)
    externalBlockers = @($finalSubmissionBlockers | Select-Object -Unique)
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Judge Rehearsal ($timestamp)",
    "",
    "- Status: $($result.status)",
    "- Ready for judge rehearsal: $ready",
    "- Repo: $RepoUrl",
    "- Demo video URL: $(if ($DemoVideoUrl) { $DemoVideoUrl } else { '<missing>' })",
    "- Backend URL: $(if ($BackendUrl) { $BackendUrl } else { '<missing>' })",
    "",
    "## Demo Shot Readiness",
    "",
    "| Shot | Ready | Evidence | Fallback |",
    "|---|---:|---|---|"
)

foreach ($shot in $demoShots) {
    $evidence = (@($shot.evidence) -join "<br>") -replace "\|", "/"
    $fallback = ([string]$shot.fallback) -replace "\|", "/"
    $lines += "| $($shot.name) | $(if ($shot.ready) { 'yes' } else { 'no' }) | $evidence | $fallback |"
}

$lines += @(
    "",
    "## Step Results",
    "",
    "| Step | Required | Result | Details |",
    "|---|---:|---:|---|"
)
foreach ($step in $steps) {
    $resultText = if ($step.skipped) { "SKIP" } elseif ($step.ok) { "PASS" } else { "FAIL" }
    $requiredText = if ($step.required) { "yes" } else { "no" }
    $details = ([string]$step.details) -replace "\|", "/"
    $lines += "| $($step.name) | $requiredText | $resultText | $details |"
}

$lines += @(
    "",
    "## Reports",
    "",
    "- Seed summary JSON: $(if ($seedSummaryPath) { $seedSummaryPath } else { '<missing>' })",
    "- Seed ZIP: $(if ($seedZipPath) { $seedZipPath } else { '<missing>' })",
    "- Local proof JSON: $(if ($localProofPath) { $localProofPath } else { '<missing>' })",
    "- Frontend proof JSON: $(if ($frontendProofPath) { $frontendProofPath } else { '<missing>' })",
    "- Judging scorecard JSON: $(if ($scorecardPath) { $scorecardPath } else { '<missing>' })",
    "- Final readiness JSON: $(if ($readinessPath) { $readinessPath } else { '<missing>' })",
    "",
    "## Fast Rehearsal Commands",
    "",
    '```powershell',
    'python scripts/qwencloud_seed_demo_artifact.py --promote-count 6',
    'scripts/qwencloud-run-local-proof.ps1 -SkipDraft',
    'scripts/qwencloud-frontend-build-proof.ps1 -AllowDraft',
    'scripts/qwencloud-judging-scorecard.ps1 -AllowDraft',
    'scripts/qwencloud-final-readiness.ps1 -AllowDraftPacket',
    '```'
)

if ($finalSubmissionBlockers.Count -gt 0) {
    $lines += @(
        "",
        "## Final Submission Blockers",
        ""
    )
    foreach ($blocker in @($finalSubmissionBlockers | Select-Object -Unique)) {
        $lines += "- $blocker"
    }
}

if ($requiredFailures.Count -gt 0) {
    $lines += @(
        "",
        "## Rehearsal Failures",
        ""
    )
    foreach ($failure in $requiredFailures) {
        $lines += "- $failure"
    }
}

Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($ready) {
    Write-Host "Judge rehearsal READY: $reportMd"
}
else {
    Write-Host "Judge rehearsal DRAFT: $reportMd" -ForegroundColor Yellow
    Write-Host "Missing rehearsal items: $($requiredFailures -join ', ')"
}
Write-Host "JSON: $reportJson"

if (-not $ready -and -not $AllowDraft) {
    exit 1
}
