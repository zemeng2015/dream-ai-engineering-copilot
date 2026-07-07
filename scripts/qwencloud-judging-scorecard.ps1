param(
    [Parameter(Mandatory = $false)]
    [string]$RepoUrl = "https://github.com/zemeng2015/dream-ai-engineering-copilot",
    [Parameter(Mandatory = $false)]
    [string]$DemoVideoUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$BackendUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$reportJson = Join-Path $OutputDir "judging-scorecard-$timestamp.json"
$reportMd = Join-Path $OutputDir "judging-scorecard-$timestamp.md"
$criteria = @()

function Test-EvidencePath([string]$Path) {
    $exists = Test-Path $Path
    return [ordered]@{
        path = $Path
        exists = $exists
        repoUrl = "$RepoUrl/blob/main/$Path"
    }
}

function Add-Criterion {
    param(
        [string]$Name,
        [int]$Weight,
        [string]$OfficialFocus,
        [string]$DREAMClaim,
        [string[]]$EvidencePaths,
        [bool]$RequiresDemoVideo = $false,
        [bool]$RequiresBackend = $false
    )

    $evidence = @($EvidencePaths | ForEach-Object { Test-EvidencePath -Path $_ })
    $missing = @($evidence | Where-Object { -not $_.exists } | ForEach-Object { $_.path })

    if ($RequiresDemoVideo -and [string]::IsNullOrWhiteSpace($DemoVideoUrl)) {
        $missing += "public_demo_video_url"
    }
    if ($RequiresBackend -and [string]::IsNullOrWhiteSpace($BackendUrl)) {
        $missing += "deployed_backend_url"
    }

    $script:criteria += [ordered]@{
        name = $Name
        weight = $Weight
        officialFocus = $OfficialFocus
        dreamClaim = $DREAMClaim
        evidence = $evidence
        requiresDemoVideo = $RequiresDemoVideo
        requiresBackend = $RequiresBackend
        complete = ($missing.Count -eq 0)
        missing = $missing
    }
}

Add-Criterion `
    -Name "Stage One: baseline viability and required Qwen Cloud use" `
    -Weight 0 `
    -OfficialFocus "Project reasonably fits the hackathon theme and applies the required APIs/SDKs." `
    -DREAMClaim "DREAM is submitted as Track 1 MemoryAgent and uses Qwen Cloud through the qwen-cloud provider, Qwen config, and Alibaba Function Compute deployment proof." `
    -EvidencePaths @(
        "examples/config/dream.qwen.yaml",
        "dream/llm/qwen_cloud.py",
        "tests/test_qwen_cloud_provider.py",
        "deploy/alibaba/serverless-devs.yaml",
        "docs/qwencloud-submission.md"
    ) `
    -RequiresBackend $true

Add-Criterion `
    -Name "Innovation and AI Creativity" `
    -Weight 30 `
    -OfficialFocus "Sophisticated use of Qwen Cloud APIs, custom skills or integrations, and algorithmic/engineering innovation." `
    -DREAMClaim "DREAM combines source-backed persistent memory, claim review, retrieval traces, requirement drafting, audit/eval feedback, and Qwen Cloud generation instead of a one-shot chatbot prompt." `
    -EvidencePaths @(
        "dream/llm/qwen_cloud.py",
        "dream/memory/distiller.py",
        "dream/knowledge/pack_loader.py",
        "dream/context/service.py",
        "dream/codebase/retriever.py",
        "dream/requirements/generator.py",
        "docs/memory-distillation.md",
        "docs/context-intelligence-layer.md",
        "docs/evaluation-agent.md"
    )

Add-Criterion `
    -Name "Technical Depth and Engineering" `
    -Weight 30 `
    -OfficialFocus "Architecture quality, modularity, scalability, error handling, clean code, non-trivial logic, and thoughtful stack adoption." `
    -DREAMClaim "The project includes provider abstraction, API/CLI surfaces, Docker packaging, Alibaba custom container deployment, CI, proof automation, final readiness gates, and deterministic local verification." `
    -EvidencePaths @(
        "dream/api/app.py",
        "dream/core/config.py",
        "dream/config/loader.py",
        "Dockerfile",
        ".github/workflows/ci.yml",
        ".github/workflows/qwencloud-release.yml",
        "scripts/qwencloud-final-readiness.ps1",
        "scripts/qwencloud-final-upload-bundle.ps1",
        "docs/qwencloud-architecture.md",
        "docs/assets/qwencloud-architecture.png"
    ) `
    -RequiresBackend $true

Add-Criterion `
    -Name "Problem Value and Impact" `
    -Weight 25 `
    -OfficialFocus "Real-world relevance, authentic business or technical pain point, scalability potential, and productization/open-source potential." `
    -DREAMClaim "DREAM targets engineering teams that lose context across tickets, source, incidents, and review history; it turns that context into auditable requirement and review outputs with reusable governed memory." `
    -EvidencePaths @(
        "docs/qwencloud-devpost-form-fields.md",
        "docs/requirement-intelligence.md",
        "docs/pr-review.md",
        "docs/open-core-strategy.md",
        "tests/test_requirement_cases.py",
        "tests/test_pr_review.py",
        "tests/test_codebase_memory.py"
    )

Add-Criterion `
    -Name "Presentation and Documentation" `
    -Weight 15 `
    -OfficialFocus "Technical demo clarity, key logic visualized effectively, and clear documentation including architecture docs." `
    -DREAMClaim "The repo includes architecture SVG/PNG, a rendered demo-video pipeline, video upload handoff, Devpost field payloads, final action board, and upload bundle manifests." `
    -EvidencePaths @(
        "docs/assets/qwencloud-architecture.svg",
        "docs/assets/qwencloud-architecture.png",
        "docs/assets/qwencloud-video-thumbnail.svg",
        "docs/assets/qwencloud-video-thumbnail.png",
        "docs/qwencloud-demo-video-script.md",
        "docs/qwencloud-demo-video-captions.srt",
        "docs/qwencloud-demo-video-transcript.md",
        "scripts/qwencloud-frontend-build-proof.ps1",
        "scripts/qwencloud-render-demo-video.ps1",
        "scripts/qwencloud-export-video-thumbnail.ps1",
        "scripts/qwencloud-devpost-video-url.ps1",
        "scripts/qwencloud-video-publication-handoff.ps1",
        "scripts/qwencloud-video-upload-status.ps1",
        "scripts/qwencloud-devpost-draft-payload.ps1",
        "docs/qwencloud-video-upload-handoff.md",
        "docs/qwencloud-official-requirements-snapshot.md",
        "docs/qwencloud-devpost-submission-kit.md"
    ) `
    -RequiresDemoVideo $true

$missingRequired = @($criteria | Where-Object { -not $_.complete } | ForEach-Object { $_.name })
$weightedEvidenceReady = 0
$weightedTotal = 0
foreach ($criterion in $criteria) {
    if ($criterion.weight -gt 0) {
        $weightedTotal += $criterion.weight
        if ($criterion.complete) {
            $weightedEvidenceReady += $criterion.weight
        }
    }
}

$ready = $missingRequired.Count -eq 0
$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = if ($ready) { "READY" } else { "DRAFT" }
    readyForJudgingNarrative = $ready
    repoUrl = $RepoUrl
    demoVideoUrl = $DemoVideoUrl
    backendUrl = $BackendUrl
    weightedEvidenceReady = $weightedEvidenceReady
    weightedTotal = $weightedTotal
    criteria = $criteria
    missingRequiredCriteria = $missingRequired
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Judging Scorecard ($timestamp)",
    "",
    "- Status: $($result.status)",
    "- Ready for judging narrative: $ready",
    "- Weighted evidence ready: $weightedEvidenceReady / $weightedTotal",
    "- Repo: $RepoUrl",
    "- Demo video URL: $(if ($DemoVideoUrl) { $DemoVideoUrl } else { '<missing>' })",
    "- Backend URL: $(if ($BackendUrl) { $BackendUrl } else { '<missing>' })",
    "",
    "## Criteria",
    "",
    "| Criterion | Weight | Complete | Official focus | DREAM claim | Missing |",
    "|---|---:|---:|---|---|---|"
)

foreach ($criterion in $criteria) {
    $lines += "| $($criterion.name) | $($criterion.weight)% | $(if ($criterion.complete) { 'yes' } else { 'no' }) | $($criterion.officialFocus -replace '\|', '/') | $($criterion.dreamClaim -replace '\|', '/') | $(@($criterion.missing) -join ', ' -replace '\|', '/') |"
}

foreach ($criterion in $criteria) {
    $lines += @(
        "",
        "## $($criterion.name)",
        "",
        "- Weight: $($criterion.weight)%",
        "- Complete: $(if ($criterion.complete) { 'yes' } else { 'no' })",
        "- Official focus: $($criterion.officialFocus)",
        "- DREAM claim: $($criterion.dreamClaim)",
        "",
        "Evidence:"
    )
    foreach ($evidence in $criterion.evidence) {
        $lines += "- $(if ($evidence.exists) { '[x]' } else { '[ ]' }) $($evidence.path) - $($evidence.repoUrl)"
    }
    if ($criterion.missing.Count -gt 0) {
        $lines += ""
        $lines += "Missing:"
        foreach ($missing in $criterion.missing) {
            $lines += "- $missing"
        }
    }
}

Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($ready) {
    Write-Host "Judging scorecard READY: $reportMd"
}
else {
    Write-Host "Judging scorecard DRAFT: $reportMd" -ForegroundColor Yellow
    Write-Host "Missing criteria: $($missingRequired -join ', ')"
}
Write-Host "JSON: $reportJson"

if (-not $ready -and -not $AllowDraft) {
    exit 1
}
