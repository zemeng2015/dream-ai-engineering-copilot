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
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [string]$LocalVideoPath = "artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4",
    [Parameter(Mandatory = $false)]
    [string]$ArchitectureUploadPath = "docs/assets/qwencloud-architecture.png",
    [Parameter(Mandatory = $false)]
    [string]$AlibabaScreenshotPath = "artifacts/qwencloud-proof/alibaba-deployment-screenshot.png",
    [Parameter(Mandatory = $false)]
    [string]$AlibabaProofVideoPath = "artifacts/qwencloud-proof/alibaba-deployment-proof.mp4",
    [Parameter(Mandatory = $false)]
    [string]$OfficialRequirementsSnapshotPath = "docs/qwencloud-official-requirements-snapshot.md",
    [switch]$SkipExternalUrlChecks,
    [switch]$SkipLocalVideoChecks,
    [switch]$SkipBackendDraft,
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
. (Join-Path $PSScriptRoot "qwencloud-devpost-video-url.ps1")

$reportJson = Join-Path $OutputDir "official-rules-gate-$timestamp.json"
$reportMd = Join-Path $OutputDir "official-rules-gate-$timestamp.md"
$officialRulesUrl = "https://qwencloud-hackathon.devpost.com/rules"
$submissionDeadlineUtc = [DateTimeOffset]::Parse("2026-07-09T14:00:00-07:00").UtcDateTime
$requirements = @()

function Add-Requirement {
    param(
        [string]$Id,
        [string]$OfficialRequirement,
        [bool]$Ok,
        [string]$Evidence,
        [bool]$Required = $true
    )

    $script:requirements += [ordered]@{
        id = $Id
        officialRequirement = $OfficialRequirement
        required = $Required
        ok = $Ok
        evidence = $Evidence
    }
}

function Is-HttpUrl([string]$Url) {
    if ([string]::IsNullOrWhiteSpace($Url)) { return $false }
    if ($Url -match "[<>]|\.\.\.") { return $false }
    return [bool]($Url -match "^https?://")
}

function Is-DevpostRulesVideoUrl([string]$Url) {
    return Test-QwenCloudDevpostVideoUrl -Url $Url
}

function Normalize-RepoUrl([string]$Url) {
    if ([string]::IsNullOrWhiteSpace($Url)) {
        return ""
    }

    return ($Url.Trim() -replace "\.git$", "")
}

function Test-File([string]$Path, [int]$MinBytes = 1) {
    if (-not (Test-Path $Path)) {
        return [pscustomobject]@{
            ok = $false
            details = "missing: $Path"
        }
    }

    $item = Get-Item -LiteralPath $Path
    return [pscustomobject]@{
        ok = ($item.Length -ge $MinBytes)
        details = "path=$Path; size=$($item.Length)"
    }
}

function Test-RepoPublication([string]$Url) {
    $normalized = Normalize-RepoUrl -Url $Url
    if ($normalized -notmatch "^https://github.com/(?<owner>[^/]+)/(?<repo>[^/]+)$") {
        return [pscustomobject]@{
            normalized = $normalized
            publicOk = $false
            licenseOk = $false
            details = "not a normalized GitHub HTTPS repo URL: $Url"
            license = ""
        }
    }

    try {
        $apiUrl = "https://api.github.com/repos/$($matches.owner)/$($matches.repo)"
        $repoData = Invoke-RestMethod -Uri $apiUrl -UserAgent "dream-qwencloud-official-rules-gate/1.0" -TimeoutSec 20
        $license = if ($repoData.license) { [string]$repoData.license.spdx_id } else { "" }
        return [pscustomobject]@{
            normalized = $normalized
            publicOk = ($repoData.visibility -eq "public" -and -not [bool]$repoData.private)
            licenseOk = ($license -eq "Apache-2.0")
            details = "visibility=$($repoData.visibility); private=$($repoData.private); license=$license"
            license = $license
        }
    }
    catch {
        $localLicenseOk = (Test-Path "LICENSE") -and ((Get-Content "LICENSE" -Raw) -match "Apache License")
        return [pscustomobject]@{
            normalized = $normalized
            publicOk = $false
            licenseOk = $localLicenseOk
            details = "GitHub metadata unavailable: $($_.Exception.Message); localLicenseOk=$localLicenseOk"
            license = if ($localLicenseOk) { "Apache-2.0 local fallback" } else { "" }
        }
    }
}

function Test-HttpReachable([string]$Url) {
    if (-not (Is-HttpUrl $Url)) {
        return [pscustomobject]@{ ok = $false; details = "not an http(s) URL" }
    }

    try {
        $response = Invoke-WebRequest -Method Head -Uri $Url -UserAgent "dream-qwencloud-official-rules-gate/1.0" -TimeoutSec 20 -MaximumRedirection 5 -ErrorAction Stop
        return [pscustomobject]@{ ok = ([int]$response.StatusCode -ge 200 -and [int]$response.StatusCode -lt 400); details = "HEAD status=$([int]$response.StatusCode)" }
    }
    catch {
        try {
            $response = Invoke-WebRequest -Method Get -Uri $Url -UserAgent "dream-qwencloud-official-rules-gate/1.0" -TimeoutSec 20 -MaximumRedirection 5 -ErrorAction Stop
            return [pscustomobject]@{ ok = ([int]$response.StatusCode -ge 200 -and [int]$response.StatusCode -lt 400); details = "GET status=$([int]$response.StatusCode)" }
        }
        catch {
            return [pscustomobject]@{ ok = $false; details = $_.Exception.Message }
        }
    }
}

function Get-VideoMetadata([string]$Path) {
    if (-not (Test-Path $Path)) { return $null }
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
        return [pscustomobject]@{ ok = ($health.status -eq "ok"); details = "status=$($health.status); deployment_target=$($health.deployment_target); provider=$($health.llm_provider)"; health = $health }
    }
    catch {
        return [pscustomobject]@{ ok = $false; details = $_.Exception.Message; health = $null }
    }
}

function Test-BackendShowcase([string]$Url) {
    if ($SkipBackendDraft) {
        return [pscustomobject]@{ ok = $true; details = "skipped by -SkipBackendDraft" }
    }
    if (-not (Is-HttpUrl $Url)) {
        return [pscustomobject]@{ ok = $false; details = "BackendUrl missing" }
    }

    try {
        $base = $Url.TrimEnd("/")
        $showcase = Invoke-RestMethod -Uri "$base/qwencloud/showcase" -TimeoutSec 20
        return [pscustomobject]@{
            ok = (
                $showcase.track -eq "Track 1: MemoryAgent" -and
                $showcase.runtime.status -eq "ok" -and
                [int]$showcase.scorecard.weighted_static_evidence_ready -eq 100
            )
            details = "track=$($showcase.track); live_backend_ready=$($showcase.runtime.live_backend_ready); weighted_static_evidence_ready=$($showcase.scorecard.weighted_static_evidence_ready)"
        }
    }
    catch {
        return [pscustomobject]@{ ok = $false; details = $_.Exception.Message }
    }
}

$repo = Test-RepoPublication -Url $RepoUrl
$backend = Get-BackendHealth -Url $BackendUrl
$health = $backend.health
$localVideo = Get-VideoMetadata -Path $LocalVideoPath
$proofVideo = Get-VideoMetadata -Path $AlibabaProofVideoPath
$requirementsSnapshot = Test-File -Path $OfficialRequirementsSnapshotPath
$nowUtc = (Get-Date).ToUniversalTime()
$runtimeQwenOk = if ($null -ne $health) { $health.llm_provider -eq "qwen-cloud" } else { $true }
$runtimeTrackOk = if ($null -ne $health) { $health.track -eq "Track 1: MemoryAgent" } else { $true }

Add-Requirement `
    -Id "official_requirements_snapshot" `
    -OfficialRequirement "Keep a local snapshot of the current public Devpost requirements used by readiness gates." `
    -Ok ($requirementsSnapshot.ok -and ((Get-Content -LiteralPath $OfficialRequirementsSnapshotPath -Raw) -match "July 9, 2026") -and ((Get-Content -LiteralPath $OfficialRequirementsSnapshotPath -Raw) -match "YouTube, Vimeo, or Facebook Video") -and ((Get-Content -LiteralPath $OfficialRequirementsSnapshotPath -Raw) -match "YouTube, Vimeo, or Youku")) `
    -Evidence $requirementsSnapshot.details

Add-Requirement `
    -Id "submission_period_open" `
    -OfficialRequirement "Submission must be completed during the Submission Period ending Jul 9, 2026 at 2:00pm Pacific Time." `
    -Ok ($nowUtc -lt $submissionDeadlineUtc) `
    -Evidence "nowUtc=$($nowUtc.ToString('o')); deadlineUtc=$($submissionDeadlineUtc.ToString('o'))"

Add-Requirement `
    -Id "public_repo_with_open_source_license" `
    -OfficialRequirement "Provide a public open source code repository with all necessary source, assets, instructions, and a detectable license." `
    -Ok ($repo.publicOk -and $repo.licenseOk -and (Test-Path "README.md") -and (Test-Path "LICENSE")) `
    -Evidence "repo=$($repo.normalized); $($repo.details); README=$(Test-Path 'README.md'); LICENSE=$(Test-Path 'LICENSE')"

Add-Requirement `
    -Id "qwen_cloud_model_usage" `
    -OfficialRequirement "Build a project using Qwen models available on Qwen Cloud." `
    -Ok ((Test-Path "dream/llm/qwen_cloud.py") -and (Test-Path "examples/config/dream.qwen.yaml") -and (Test-Path "tests/test_qwen_cloud_provider.py") -and $runtimeQwenOk) `
    -Evidence "providerCode=dream/llm/qwen_cloud.py; config=examples/config/dream.qwen.yaml; tests=tests/test_qwen_cloud_provider.py; runtimeProvider=$(if ($health) { $health.llm_provider } else { '<not deployed>' })"

Add-Requirement `
    -Id "track_identified_memoryagent" `
    -OfficialRequirement "Identify which track the submission enters; Track 1 requires a persistent-memory agent." `
    -Ok ((Test-Path "docs/qwencloud-submission.md") -and ((Get-Content "docs/qwencloud-submission.md" -Raw) -match "Track 1: MemoryAgent") -and $runtimeTrackOk) `
    -Evidence "doc=docs/qwencloud-submission.md; runtimeTrack=$(if ($health) { $health.track } else { '<not deployed>' })"

$proofCode = Test-File -Path "deploy/alibaba/serverless-devs.yaml"
Add-Requirement `
    -Id "alibaba_deployment_proof_code" `
    -OfficialRequirement "Include proof of Alibaba Cloud deployment as a link to a code file demonstrating Alibaba Cloud services and APIs." `
    -Ok $proofCode.ok `
    -Evidence "$($proofCode.details); url=$($repo.normalized)/blob/main/deploy/alibaba/serverless-devs.yaml"

Add-Requirement `
    -Id "backend_running_on_alibaba_cloud" `
    -OfficialRequirement "Demonstrate that the backend is running on Alibaba Cloud and functions as depicted." `
    -Ok ($backend.ok -and $health -and ([string]$health.deployment_target -match "Alibaba Cloud Function Compute") -and ($health.proof_file -eq "deploy/alibaba/serverless-devs.yaml")) `
    -Evidence "backend=$BackendUrl; $($backend.details); proofFile=$(if ($health) { $health.proof_file } else { '<missing>' })"

$backendShowcase = Test-BackendShowcase -Url $BackendUrl
Add-Requirement `
    -Id "working_project_testing_access" `
    -OfficialRequirement "Provide access to a working project, website, functioning demo, or test build for judging." `
    -Ok ($backend.ok -and $backendShowcase.ok) `
    -Evidence "backend=$BackendUrl; health=$($backend.details); showcase=$($backendShowcase.details)"

$architecture = Test-File -Path $ArchitectureUploadPath -MinBytes 10000
Add-Requirement `
    -Id "architecture_diagram_upload" `
    -OfficialRequirement "Include an architecture diagram showing how Qwen Cloud connects to backend, database, and frontend." `
    -Ok ($architecture.ok -and (Test-Path "docs/qwencloud-architecture.md")) `
    -Evidence "$($architecture.details); doc=docs/qwencloud-architecture.md"

Add-Requirement `
    -Id "demo_video_public_url" `
    -OfficialRequirement "Include a public demo video URL on an accepted official platform. Overview names YouTube, Vimeo, or Facebook Video; Official Rules name YouTube, Vimeo, or Youku." `
    -Ok (Is-DevpostRulesVideoUrl $DemoVideoUrl) `
    -Evidence $(if ($DemoVideoUrl) { $DemoVideoUrl } else { "missing" })

if ((Is-DevpostRulesVideoUrl $DemoVideoUrl) -and -not $SkipExternalUrlChecks) {
    $videoReachable = Test-HttpReachable -Url $DemoVideoUrl
    Add-Requirement `
        -Id "demo_video_url_reachable" `
        -OfficialRequirement "The public demo video must be visible for judging." `
        -Ok $videoReachable.ok `
        -Evidence $videoReachable.details
}

if ($SkipLocalVideoChecks) {
    Add-Requirement `
        -Id "demo_video_under_three_minutes" `
        -OfficialRequirement "The video portion should be less than three minutes; judges need not watch beyond three minutes." `
        -Ok $true `
        -Evidence "skipped by -SkipLocalVideoChecks; verify duration from the final uploaded public video before submit" `
        -Required $false
}
else {
    Add-Requirement `
        -Id "demo_video_under_three_minutes" `
        -OfficialRequirement "The video portion should be less than three minutes; judges need not watch beyond three minutes." `
        -Ok ($localVideo -and $localVideo.duration -gt 0 -and $localVideo.duration -lt 180) `
        -Evidence $(if ($localVideo) { "path=$LocalVideoPath; duration=$($localVideo.duration); resolution=$($localVideo.width)x$($localVideo.height); codec=$($localVideo.codec)" } else { "missing metadata for $LocalVideoPath" })
}

$screenshot = Test-File -Path $AlibabaScreenshotPath -MinBytes 10000
Add-Requirement `
    -Id "alibaba_screenshot_asset" `
    -OfficialRequirement "Attach Alibaba deployment proof screenshot when filling required Devpost proof assets." `
    -Ok $screenshot.ok `
    -Evidence $screenshot.details

Add-Requirement `
    -Id "alibaba_backend_proof_recording" `
    -OfficialRequirement "Attach a concise Alibaba backend proof recording for the submission evidence bundle." `
    -Ok ($proofVideo -and $proofVideo.duration -ge 5 -and $proofVideo.duration -le 60) `
    -Evidence $(if ($proofVideo) { "path=$AlibabaProofVideoPath; duration=$($proofVideo.duration); resolution=$($proofVideo.width)x$($proofVideo.height)" } else { "missing metadata for $AlibabaProofVideoPath" })

$rightsDoc = Test-File -Path "docs/qwencloud-testing-and-rights-notes.md"
Add-Requirement `
    -Id "english_testing_and_rights_notes" `
    -OfficialRequirement "Submission materials and testing instructions must be in English, and the entry must avoid unauthorized third-party IP." `
    -Ok ($rightsDoc.ok -and (Test-Path "docs/qwencloud-devpost-form-fields.md") -and (Test-Path "docs/qwencloud-devpost-submission-kit.md")) `
    -Evidence "$($rightsDoc.details); devpostFields=docs/qwencloud-devpost-form-fields.md; submissionKit=docs/qwencloud-devpost-submission-kit.md"

Add-Requirement `
    -Id "optional_blog_social_url" `
    -OfficialRequirement "Optional blog/social URL is only required for the blog post bonus prize." `
    -Ok ([string]::IsNullOrWhiteSpace($BlogPostUrl) -or (Is-HttpUrl $BlogPostUrl)) `
    -Evidence $(if ($BlogPostUrl) { $BlogPostUrl } else { "not provided" }) `
    -Required $false

$requiredFailures = @($requirements | Where-Object { $_.required -and -not $_.ok })
$ready = $requiredFailures.Count -eq 0
$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = if ($ready) { "READY" } else { "DRAFT" }
    readyForOfficialRules = $ready
    officialRulesUrl = $officialRulesUrl
    officialRequirementsSnapshotPath = $OfficialRequirementsSnapshotPath
    repoUrl = $repo.normalized
    demoVideoUrl = $DemoVideoUrl
    backendUrl = $BackendUrl
    blogPostUrl = $BlogPostUrl
    submissionDeadlineUtc = $submissionDeadlineUtc.ToString("o")
    checks = $requirements
    missingRequired = @($requiredFailures | ForEach-Object { $_.id })
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Official Rules Gate ($timestamp)",
    "",
    "- Status: $($result.status)",
    "- Ready for official rules: $ready",
    "- Official rules: $officialRulesUrl",
    "- Deadline UTC: $($submissionDeadlineUtc.ToString('o'))",
    "- Repo: $($repo.normalized)",
    "- Demo video URL: $(if ($DemoVideoUrl) { $DemoVideoUrl } else { '<missing>' })",
    "- Backend URL: $(if ($BackendUrl) { $BackendUrl } else { '<missing>' })",
    "",
    "## Requirement Matrix",
    "",
    "| Requirement | Required | Result | Official requirement | Evidence |",
    "|---|---:|---:|---|---|"
)

foreach ($requirement in $requirements) {
    $lines += "| $($requirement.id) | $(if ($requirement.required) { 'yes' } else { 'no' }) | $(if ($requirement.ok) { 'PASS' } else { 'FAIL' }) | $($requirement.officialRequirement -replace '\|', '/') | $($requirement.evidence -replace '\|', '/') |"
}

if ($requiredFailures.Count -gt 0) {
    $lines += @(
        "",
        "## Missing Required Items",
        ""
    )
    foreach ($failure in $requiredFailures) {
        $lines += "- $($failure.id): $($failure.evidence)"
    }
}

$lines += @(
    "",
    "## Next Command",
    "",
    '```powershell',
    'scripts/qwencloud-official-rules-gate.ps1 -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>"',
    '```'
)

Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($ready) {
    Write-Host "Official rules gate READY: $reportMd"
}
else {
    Write-Host "Official rules gate DRAFT: $reportMd" -ForegroundColor Yellow
    Write-Host "Missing required checks: $($requiredFailures.id -join ', ')"
    if (-not $AllowDraft) {
        exit 1
    }
}
