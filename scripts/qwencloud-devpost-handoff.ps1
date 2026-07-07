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
    [string]$ArchitectureUploadPath = "docs/assets/qwencloud-architecture.png",
    [Parameter(Mandatory = $false)]
    [string]$LocalDemoVideoPath = "artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4",
    [Parameter(Mandatory = $false)]
    [string]$AlibabaScreenshotPath = "artifacts/qwencloud-proof/alibaba-deployment-screenshot.png",
    [Parameter(Mandatory = $false)]
    [string]$AlibabaProofVideoPath = "artifacts/qwencloud-proof/alibaba-deployment-proof.mp4",
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$handoffJson = Join-Path $OutputDir "devpost-handoff-$timestamp.json"
$handoffMd = Join-Path $OutputDir "devpost-handoff-$timestamp.md"
$handoffHtml = Join-Path $OutputDir "devpost-handoff-$timestamp.html"

$projectTitle = "DREAM: Qwen Cloud MemoryAgent for Source-Backed Engineering Intelligence"
$track = "Track 1: MemoryAgent"
$deadline = "July 9, 2026 at 2:00pm PDT / 5:00pm EDT"
$devpostUrl = "https://qwencloud-hackathon.devpost.com/"
$devpostPreviewUrl = "https://devpost.com/software/dream-qwen-cloud-memoryagent"
$devpostProjectDetailsUrl = "https://devpost.com/submit-to/29966-global-ai-hackathon-series-with-qwen-cloud/manage/submissions/1073064-dream-qwen-cloud-memoryagent/project_details/edit"
$devpostAdditionalInfoUrl = "https://devpost.com/submit-to/29966-global-ai-hackathon-series-with-qwen-cloud/manage/submissions/1073064-dream-qwen-cloud-memoryagent/additional-info/edit"
$devpostFinalizationUrl = "https://devpost.com/submit-to/29966-global-ai-hackathon-series-with-qwen-cloud/manage/submissions/1073064-dream-qwen-cloud-memoryagent/finalization"
$deploymentProofUrl = "$RepoUrl/blob/main/deploy/alibaba/serverless-devs.yaml"
$licenseUrl = "$RepoUrl/blob/main/LICENSE"

function Has-Env([string]$Name) {
    return -not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($Name))
}

function Test-ServerlessDevsDefaultAccess {
    if (-not (Get-Command "s" -ErrorAction SilentlyContinue)) {
        return [pscustomobject]@{ ok = $false; details = "s command missing" }
    }

    try {
        $output = (& s config get -a default 2>&1) -join "`n"
        $ok = $output -notmatch "not yet|not found|not.*configured|configured key information"
        return [pscustomobject]@{
            ok = $ok
            details = if ($ok) { "default access configured" } else { "default access not configured" }
        }
    }
    catch {
        return [pscustomobject]@{ ok = $false; details = $_.Exception.Message }
    }
}

function Get-AbsolutePath([string]$Path) {
    if (Test-Path $Path) {
        return (Resolve-Path $Path).Path
    }
    return [System.IO.Path]::GetFullPath($Path)
}

function Get-FileUri([string]$Path) {
    if (-not (Test-Path $Path)) {
        return ""
    }
    return ([System.Uri](Resolve-Path $Path).Path).AbsoluteUri
}

function Get-UploadItem([string]$Name, [string]$Path, [bool]$Required = $true) {
    $exists = Test-Path $Path
    $item = if ($exists) { Get-Item -LiteralPath $Path } else { $null }
    return [ordered]@{
        name = $Name
        required = $Required
        path = $Path
        absolutePath = Get-AbsolutePath -Path $Path
        fileUri = Get-FileUri -Path $Path
        exists = $exists
        size = if ($item) { $item.Length } else { 0 }
    }
}

function Html($Value) {
    return [System.Net.WebUtility]::HtmlEncode([string]$Value)
}

$uploadItems = @(
    Get-UploadItem -Name "architecture_diagram" -Path $ArchitectureUploadPath
    Get-UploadItem -Name "local_demo_video_for_public_upload" -Path $LocalDemoVideoPath -Required ([string]::IsNullOrWhiteSpace($DemoVideoUrl))
    Get-UploadItem -Name "video_upload_handoff" -Path "docs/qwencloud-video-upload-handoff.md"
    Get-UploadItem -Name "video_publication_handoff_script" -Path "scripts/qwencloud-video-publication-handoff.ps1" -Required $false
    Get-UploadItem -Name "alibaba_deployment_screenshot" -Path $AlibabaScreenshotPath
    Get-UploadItem -Name "alibaba_backend_proof_recording" -Path $AlibabaProofVideoPath
    Get-UploadItem -Name "devpost_form_fields_reference" -Path "docs/qwencloud-devpost-form-fields.md"
)

$blockers = @()
if ([string]::IsNullOrWhiteSpace($DemoVideoUrl)) {
    $blockers += "public_demo_video_url"
}
if ([string]::IsNullOrWhiteSpace($BackendUrl)) {
    $blockers += "deployed_backend_url"
}
foreach ($item in $uploadItems) {
    if ($item.required -and -not $item.exists) {
        $blockers += $item.name
    }
}

$deployInputChecks = @()
if ([string]::IsNullOrWhiteSpace($BackendUrl)) {
    $sAccess = Test-ServerlessDevsDefaultAccess
    $deployInputChecks += [ordered]@{ name = "serverless_devs_default_access"; ok = $sAccess.ok; details = $sAccess.details }
    foreach ($envName in @("DASHSCOPE_API_KEY", "ALIBABA_CLOUD_REGION", "ALIBABA_CLOUD_CONTAINER_IMAGE")) {
        $deployInputChecks += [ordered]@{
            name = "env.$envName"
            ok = Has-Env $envName
            details = if (Has-Env $envName) { "set" } else { "missing" }
        }
    }

    foreach ($check in $deployInputChecks) {
        if (-not $check.ok) {
            $blockers += $check.name
        }
    }
}

$ready = $blockers.Count -eq 0
$status = if ($ready) { "READY" } else { "DRAFT" }
$videoValue = if ($DemoVideoUrl) { $DemoVideoUrl } else { "<paste public YouTube/Vimeo/Youku URL>" }
$backendValue = if ($BackendUrl) { $BackendUrl } else { "<paste Alibaba Function Compute backend URL>" }
$blogValue = if ($BlogPostUrl) { $BlogPostUrl } else { "<optional public blog/social post URL>" }

$description = @"
Engineering teams lose critical context across tickets, code, incidents, runbooks, and review decisions. DREAM makes that context persistent and governed. It loads knowledge packs, indexes local codebases, distills reviewable memory claims, retrieves source-backed context, and uses Qwen Cloud through an OpenAI-compatible provider to produce traceable requirement and review outputs.

The system is built as a production-minded Track 1 MemoryAgent: memory can be promoted, rejected, audited, evaluated, and reused across workflows. The public health endpoint exposes runtime proof such as Track 1, qwen-cloud provider, model, deployment target, region, and the Alibaba Cloud proof file path without exposing secrets.
"@

$shortPitch = "DREAM is a Qwen Cloud MemoryAgent for source-backed engineering intelligence. It turns docs, codebase structure, incidents, Jira and PR history, and reviewed memory claims into durable, auditable context for requirement drafting and review workflows."

$nextCommands = @(
    'scripts/qwencloud-render-demo-video.ps1',
    'scripts/qwencloud-video-publication-handoff.ps1',
    'scripts/qwencloud-alibaba-release.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>"',
    'scripts/qwencloud-hackathon-submission-packet.ps1 -RepoUrl "https://github.com/zemeng2015/dream-ai-engineering-copilot" -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-url>"',
    'scripts/qwencloud-final-readiness.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-url>"',
    'scripts/qwencloud-final-upload-bundle.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-url>"'
)

$handoff = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = $status
    readyForDevpostFinalSubmit = $ready
    deadline = $deadline
    officialDevpostUrl = $devpostUrl
    liveDevpostDraft = [ordered]@{
        projectName = "DREAM Qwen Cloud MemoryAgent"
        observedStatus = "DRAFT"
        observedStepsDone = "2/5"
        previewUrl = $devpostPreviewUrl
        projectDetailsUrl = $devpostProjectDetailsUrl
        additionalInfoUrl = $devpostAdditionalInfoUrl
        finalizationUrl = $devpostFinalizationUrl
    }
    repoUrl = $RepoUrl
    demoVideoUrl = $DemoVideoUrl
    backendUrl = $BackendUrl
    blogPostUrl = $BlogPostUrl
    blockers = $blockers
    deployInputChecks = $deployInputChecks
    uploadItems = $uploadItems
    copyFields = [ordered]@{
        projectTitle = $projectTitle
        track = $track
        shortPitch = $shortPitch
        description = $description
        builtWith = "Qwen Cloud, Alibaba Cloud Function Compute, FastAPI, Typer, Angular, Docker, SQLite, Python, TypeScript."
        submitterType = "Individual"
        country = "United States"
        projectStartDate = "06-21-26"
        repoUrl = $RepoUrl
        licenseUrl = $licenseUrl
        deploymentProofCodeFile = $deploymentProofUrl
        demoVideoUrl = $videoValue
        backendUrl = $backendValue
        blogPostUrl = $blogValue
    }
    actionTimeConfirmations = @(
        "Confirm age of majority eligibility checkbox.",
        "Confirm eligible jurisdiction checkbox.",
        "Confirm not sponsor/affiliate/government-entity employee checkbox.",
        "Confirm final Official Rules and Devpost Terms of Service checkbox.",
        "Confirm final Devpost Submit only after final readiness is READY."
    )
    nextCommands = $nextCommands
    markdown = $handoffMd
    html = $handoffHtml
}

Set-Content -Path $handoffJson -Value ($handoff | ConvertTo-Json -Depth 12) -Encoding UTF8

$md = @(
    "# Qwen Cloud Devpost Handoff ($timestamp)",
    "",
    "- Status: $status",
    "- Ready for final Devpost submit: $ready",
    "- Deadline: $deadline",
    "- Official page: $devpostUrl",
    "- Live draft project details: $devpostProjectDetailsUrl",
    "- Live draft additional info: $devpostAdditionalInfoUrl",
    "- Live draft finalization: $devpostFinalizationUrl",
    "- Repo: $RepoUrl",
    "- Demo video URL: $videoValue",
    "- Backend URL: $backendValue",
    "- Blog/social URL: $blogValue",
    "",
    "## Official Requirement Checklist",
    "",
    "- Public open-source code repository with visible license: $RepoUrl",
    "- Alibaba Cloud backend deployment proof code file: $deploymentProofUrl",
    "- Architecture diagram upload: $ArchitectureUploadPath",
    "- Public demo video on YouTube, Vimeo, or Youku: $videoValue",
    "- Text description and feature/functionality explanation: included below",
    "- Track: $track",
    "- Optional blog/social journey URL: $blogValue",
    "- Legal eligibility checkboxes: Zack confirmation required at final submit",
    "",
    "## Blockers",
    ""
)
if ($blockers.Count -eq 0) {
    $md += "- None"
}
else {
    foreach ($blocker in $blockers) {
        $md += "- $blocker"
    }
}

$md += @(
    "",
    "## Upload Files",
    "",
    "| Item | Exists | Absolute Path |",
    "|---|---:|---|"
)
foreach ($item in $uploadItems) {
    $exists = if ($item.exists) { "yes" } else { "no" }
    $md += "| $($item.name) | $exists | $($item.absolutePath -replace '\|', '/') |"
}

$md += @(
    "",
    "## Copy Fields",
    "",
    "### Project title",
    "",
    $projectTitle,
    "",
    "### Track",
    "",
    $track,
    "",
    "### Short pitch",
    "",
    $shortPitch,
    "",
    "### Description",
    "",
    $description.Trim(),
    "",
    "### Built with",
    "",
    "Qwen Cloud, Alibaba Cloud Function Compute, FastAPI, Typer, Angular, Docker, SQLite, Python, TypeScript.",
    "",
    "### Additional info",
    "",
    "- Submitter type: Individual",
    "- Country of residence: United States",
    "- Newly built or existing project: New",
    "- Project start date: 06-21-26",
    "- Track: $track",
    "- Code repository URL: $RepoUrl",
    "- Alibaba Cloud deployment proof code file: $deploymentProofUrl",
    "- Architecture diagram file upload: $ArchitectureUploadPath",
    "- Alibaba deployment screenshot upload: $AlibabaScreenshotPath",
    "- Alibaba backend proof recording: $AlibabaProofVideoPath",
    "- Demo video URL: $videoValue",
    "- Blog/social URL: $blogValue",
    "- AI tools leveraged: Qwen Cloud for the runtime LLM provider, OpenAI Codex for implementation assistance, GitHub Actions for CI verification, and local automation scripts for audit, render, deploy preflight, and submission packet generation.",
    "- Learning level: Significant",
    "",
    "## Live Devpost Draft",
    "",
    "- Project: DREAM Qwen Cloud MemoryAgent",
    "- Observed status: DRAFT, 2/5 steps done",
    "- Preview: $devpostPreviewUrl",
    "- Project details: $devpostProjectDetailsUrl",
    "- Additional info: $devpostAdditionalInfoUrl",
    "- Finalization: $devpostFinalizationUrl",
    "",
    "## Action-Time Confirmations",
    "",
    "- Zack must confirm the age of majority eligibility checkbox.",
    "- Zack must confirm the eligible jurisdiction checkbox.",
    "- Zack must confirm the not sponsor/affiliate/government-entity employee checkbox.",
    "- Zack must confirm the final Official Rules and Devpost Terms of Service checkbox.",
    "- Final Devpost Submit only after final readiness reports READY.",
    "",
    "## Chrome Video Upload Fix",
    "",
    'If Codex-controlled Chrome cannot upload the MP4 and reports `Not allowed`, open `chrome://extensions`, click Details under the Codex extension, and enable `Allow access to file URLs`.',
    "",
    "## Next Commands",
    ""
)
foreach ($command in $nextCommands) {
    $md += '```powershell'
    $md += $command
    $md += '```'
}

Set-Content -Path $handoffMd -Value ($md -join "`r`n") -Encoding UTF8

$uploadRows = @()
foreach ($item in $uploadItems) {
    $class = if ($item.exists) { "pass" } else { "fail" }
    $link = if ($item.fileUri) { "<a href=""$(Html $item.fileUri)"">$(Html $item.absolutePath)</a>" } else { Html $item.absolutePath }
    $uploadRows += "<tr class=""$class""><td>$(Html $item.name)</td><td>$(Html $(if ($item.exists) { 'yes' } else { 'no' }))</td><td>$link</td><td>$(Html $item.size)</td></tr>"
}

$blockerItems = if ($blockers.Count -eq 0) {
    "<li>None</li>"
}
else {
    ($blockers | ForEach-Object { "<li>$(Html $_)</li>" }) -join "`n"
}

$commandBlocks = ($nextCommands | ForEach-Object { "<pre><code>$(Html $_)</code></pre>" }) -join "`n"

$html = @"
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Qwen Cloud Devpost Handoff</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 32px; color: #172033; background: #f7f8fb; }
    main { max-width: 1080px; margin: 0 auto; background: #fff; padding: 28px; border: 1px solid #d8deea; }
    h1, h2, h3 { color: #101827; }
    .status { display: inline-block; padding: 6px 10px; border-radius: 4px; font-weight: 700; }
    .ready { background: #d8f5df; color: #0f6b2f; }
    .draft { background: #fff1cc; color: #7a4d00; }
    table { width: 100%; border-collapse: collapse; margin: 12px 0 24px; }
    th, td { border: 1px solid #d8deea; padding: 8px; vertical-align: top; text-align: left; }
    th { background: #eef2f8; }
    tr.pass td:nth-child(2) { color: #0f6b2f; font-weight: 700; }
    tr.fail td:nth-child(2) { color: #a61b1b; font-weight: 700; }
    pre { white-space: pre-wrap; background: #101827; color: #f5f7fb; padding: 12px; overflow-x: auto; }
    code { font-family: Consolas, monospace; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    @media (max-width: 800px) { body { margin: 12px; } .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
<main>
  <h1>Qwen Cloud Devpost Handoff</h1>
  <p><span class="status $(if ($ready) { 'ready' } else { 'draft' })">$(Html $status)</span></p>
  <p><strong>Deadline:</strong> $(Html $deadline)</p>
  <p><strong>Official page:</strong> <a href="$(Html $devpostUrl)">$(Html $devpostUrl)</a></p>
  <p><strong>Live draft:</strong> <a href="$(Html $devpostProjectDetailsUrl)">Project details</a> |
    <a href="$(Html $devpostAdditionalInfoUrl)">Additional info</a> |
    <a href="$(Html $devpostFinalizationUrl)">Finalization</a></p>
  <p><strong>Repo:</strong> <a href="$(Html $RepoUrl)">$(Html $RepoUrl)</a></p>

  <h2>Blockers</h2>
  <ul>
    $blockerItems
  </ul>

  <h2>Upload Files</h2>
  <table>
    <thead><tr><th>Item</th><th>Exists</th><th>Absolute path</th><th>Size</th></tr></thead>
    <tbody>
      $($uploadRows -join "`n")
    </tbody>
  </table>

  <div class="grid">
    <section>
      <h2>Project Title</h2>
      <pre><code>$(Html $projectTitle)</code></pre>
      <h2>Track</h2>
      <pre><code>$(Html $track)</code></pre>
      <h2>Short Pitch</h2>
      <pre><code>$(Html $shortPitch)</code></pre>
    </section>
    <section>
      <h2>Required Links</h2>
      <pre><code>Repo: $(Html $RepoUrl)
License: $(Html $licenseUrl)
Deployment proof code file: $(Html $deploymentProofUrl)
Demo video: $(Html $videoValue)
Backend: $(Html $backendValue)
Blog/social: $(Html $blogValue)</code></pre>
    </section>
  </div>

  <h2>Description</h2>
  <pre><code>$(Html $description.Trim())</code></pre>

  <h2>Additional Info</h2>
  <pre><code>Submitter type: Individual
Country of residence: United States
Newly built or existing project: New
Project start date: 06-21-26
Track: $(Html $track)
AI tools leveraged: Qwen Cloud for the runtime LLM provider, OpenAI Codex for implementation assistance, GitHub Actions for CI verification, and local automation scripts for audit, render, deploy preflight, and submission packet generation.
Learning level: Significant</code></pre>

  <h2>Action-Time Confirmations</h2>
  <pre><code>Zack must confirm age of majority, eligible jurisdiction, not sponsor/affiliate/government-entity employee, and final Official Rules / Devpost Terms of Service before final Submit.
Only click final Submit after final readiness reports READY.</code></pre>

  <h2>Chrome Video Upload Fix</h2>
  <pre><code>Open chrome://extensions, click Details under the Codex extension, and enable "Allow access to file URLs".</code></pre>

  <h2>Next Commands</h2>
  $commandBlocks
</main>
</body>
</html>
"@

Set-Content -Path $handoffHtml -Value $html -Encoding UTF8

if ($ready) {
    Write-Host "Devpost handoff READY: $handoffMd"
}
else {
    Write-Host "Devpost handoff DRAFT: $handoffMd" -ForegroundColor Yellow
    Write-Host "Missing required items: $($blockers -join ', ')"
}
Write-Host "HTML: $handoffHtml"
Write-Host "JSON: $handoffJson"

if (-not $ready -and -not $AllowDraft) {
    exit 1
}
