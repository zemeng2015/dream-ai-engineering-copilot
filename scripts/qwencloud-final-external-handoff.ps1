# SPDX-License-Identifier: Apache-2.0

param(
    [Parameter(Mandatory = $false)]
    [string]$RepoUrl = "https://github.com/zemeng2015/dream-ai-engineering-copilot",
    [Parameter(Mandatory = $false)]
    [string]$RepoName = "zemeng2015/dream-ai-engineering-copilot",
    [Parameter(Mandatory = $false)]
    [string]$DemoVideoUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$BackendUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$BlogPostUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$EnvFile = "",
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [string]$LocalVideoPath = "artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4",
    [switch]$SkipVideoPublication,
    [switch]$SkipOfficialSourceRefresh,
    [switch]$SkipCloudCredentials,
    [switch]$SkipGitHubSecrets,
    [switch]$SkipDevpostDraftPayload,
    [switch]$SkipActionBoard,
    [switch]$SkipExternalUrlChecks,
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$handoffRoot = Join-Path $OutputDir "external-handoff-$timestamp"
$handoffUploads = Join-Path $handoffRoot "reports"
New-Item -ItemType Directory -Path $handoffUploads -Force | Out-Null

$reportJson = Join-Path $OutputDir "external-handoff-$timestamp.json"
$reportMd = Join-Path $OutputDir "external-handoff-$timestamp.md"
$commandsPath = Join-Path $handoffRoot "commands.ps1"
$zipPath = Join-Path $OutputDir "external-handoff-$timestamp.zip"
$steps = @()
$reports = @()

function Get-PowerShellExe {
    $pwsh = Get-Command "pwsh" -ErrorAction SilentlyContinue
    if ($pwsh) { return $pwsh.Source }

    $powershell = Get-Command "powershell" -ErrorAction SilentlyContinue
    if ($powershell) { return $powershell.Source }

    throw "PowerShell executable not found."
}

function Add-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Status,
        [Parameter(Mandatory = $true)][string]$Details,
        [Parameter(Mandatory = $false)][string]$JsonPath = "",
        [Parameter(Mandatory = $false)][string]$MarkdownPath = "",
        [Parameter(Mandatory = $false)][bool]$Required = $true
    )

    $script:steps += [ordered]@{
        name = $Name
        status = $Status
        ok = ($Status -eq "pass" -or $Status -eq "draft" -or $Status -eq "skipped")
        required = $Required
        details = $Details
        jsonPath = $JsonPath
        markdownPath = $MarkdownPath
    }
}

function Get-NewestFile([string]$Filter) {
    return Get-ChildItem -LiteralPath $OutputDir -Filter $Filter -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Read-Json($File) {
    if (-not $File) { return $null }
    return Get-Content -LiteralPath $File.FullName -Raw | ConvertFrom-Json
}

function Copy-ReportFile([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path)) {
        return ""
    }
    $item = Get-Item -LiteralPath $Path
    $dest = Join-Path $handoffUploads $item.Name
    Copy-Item -LiteralPath $item.FullName -Destination $dest -Force
    return $dest
}

function Invoke-HandoffStep {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$JsonFilter,
        [Parameter(Mandatory = $false)][int[]]$AllowedExitCodes = @(0)
    )

    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter $JsonFilter -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty FullName)
    $safeName = $Name -replace "[^A-Za-z0-9_.-]", "-"
    $stdout = Join-Path $OutputDir "external-handoff-$safeName-$timestamp.out"
    $stderr = Join-Path $OutputDir "external-handoff-$safeName-$timestamp.err"
    $proc = Start-Process `
        -FilePath (Get-PowerShellExe) `
        -ArgumentList $Arguments `
        -NoNewWindow `
        -Wait `
        -PassThru `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr

    if ($AllowedExitCodes -notcontains $proc.ExitCode) {
        Add-Step -Name $Name -Status "fail" -Details "exit=$($proc.ExitCode); stdout=$stdout; stderr=$stderr"
        throw "$Name failed with exit code $($proc.ExitCode). See $stderr"
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter $JsonFilter -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending)
    $json = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $json) {
        $json = @($after | Select-Object -First 1)
    }

    $jsonPath = if ($json) { $json.FullName } else { "" }
    $markdownPath = if ($jsonPath) { [System.IO.Path]::ChangeExtension($jsonPath, ".md") } else { "" }
    $status = "pass"
    $data = Read-Json -File $json
    if ($data -and $data.status -eq "DRAFT") {
        $status = "draft"
    }

    Add-Step `
        -Name $Name `
        -Status $status `
        -Details "exit=$($proc.ExitCode); stdout=$stdout; stderr=$stderr" `
        -JsonPath $jsonPath `
        -MarkdownPath $markdownPath

    Copy-ReportFile -Path $jsonPath | Out-Null
    Copy-ReportFile -Path $markdownPath | Out-Null
    return [pscustomobject]@{
        json = $jsonPath
        markdown = $markdownPath
        data = $data
    }
}

$officialSourceReport = $null
if ($SkipOfficialSourceRefresh) {
    Add-Step -Name "official-source-refresh" -Status "skipped" -Details "skipped by -SkipOfficialSourceRefresh" -Required $false
}
else {
    $sourceArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-official-source-refresh.ps1",
        "-OutputDir", $OutputDir,
        "-AllowDraft"
    )
    $officialSourceReport = Invoke-HandoffStep `
        -Name "official-source-refresh" `
        -Arguments $sourceArgs `
        -JsonFilter "official-source-refresh-*.json"
}

$videoReport = $null
if ($SkipVideoPublication) {
    Add-Step -Name "video-publication-handoff" -Status "skipped" -Details "skipped by -SkipVideoPublication" -Required $false
}
else {
    $videoArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-video-publication-handoff.ps1",
        "-OutputDir", $OutputDir,
        "-LocalVideoPath", $LocalVideoPath,
        "-AllowDraft"
    )
    if ($DemoVideoUrl) { $videoArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
    $videoReport = Invoke-HandoffStep `
        -Name "video-publication-handoff" `
        -Arguments $videoArgs `
        -JsonFilter "video-publication-handoff-*.json"
}

$cloudReport = $null
if ($SkipCloudCredentials) {
    Add-Step -Name "cloud-credentials-handoff" -Status "skipped" -Details "skipped by -SkipCloudCredentials" -Required $false
}
else {
    $cloudArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-cloud-credentials-handoff.ps1",
        "-OutputDir", $OutputDir,
        "-AllowDraft"
    )
    if ($EnvFile) { $cloudArgs += @("-EnvFile", $EnvFile) }
    if ($DemoVideoUrl) { $cloudArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
    if ($BackendUrl) { $cloudArgs += @("-BackendUrl", $BackendUrl) }
    $cloudReport = Invoke-HandoffStep `
        -Name "cloud-credentials-handoff" `
        -Arguments $cloudArgs `
        -JsonFilter "cloud-credentials-handoff-*.json"
}

$githubReport = $null
if ($SkipGitHubSecrets) {
    Add-Step -Name "github-secrets-handoff" -Status "skipped" -Details "skipped by -SkipGitHubSecrets" -Required $false
}
else {
    $githubArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-github-secrets-handoff.ps1",
        "-Repo", $RepoName,
        "-OutputDir", $OutputDir,
        "-AllowDraft"
    )
    if ($EnvFile) { $githubArgs += @("-EnvFile", $EnvFile) }
    $githubReport = Invoke-HandoffStep `
        -Name "github-secrets-handoff" `
        -Arguments $githubArgs `
        -JsonFilter "github-secrets-handoff-*.json"
}

$draftPayloadReport = $null
if ($SkipDevpostDraftPayload) {
    Add-Step -Name "devpost-draft-payload" -Status "skipped" -Details "skipped by -SkipDevpostDraftPayload" -Required $false
}
else {
    $payloadArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-devpost-draft-payload.ps1",
        "-RepoUrl", $RepoUrl,
        "-OutputDir", $OutputDir,
        "-AllowDraft"
    )
    if ($DemoVideoUrl) { $payloadArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
    if ($BackendUrl) { $payloadArgs += @("-BackendUrl", $BackendUrl) }
    if ($BlogPostUrl) { $payloadArgs += @("-BlogPostUrl", $BlogPostUrl) }
    $draftPayloadReport = Invoke-HandoffStep `
        -Name "devpost-draft-payload" `
        -Arguments $payloadArgs `
        -JsonFilter "devpost-draft-payload-*.json"
}

$actionBoardReport = $null
if ($SkipActionBoard) {
    Add-Step -Name "final-action-board" -Status "skipped" -Details "skipped by -SkipActionBoard" -Required $false
}
else {
    $boardArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-final-action-board.ps1",
        "-RepoUrl", $RepoUrl,
        "-RepoName", $RepoName,
        "-OutputDir", $OutputDir,
        "-AllowDraft"
    )
    if ($DemoVideoUrl) { $boardArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
    if ($BackendUrl) { $boardArgs += @("-BackendUrl", $BackendUrl) }
    if ($BlogPostUrl) { $boardArgs += @("-BlogPostUrl", $BlogPostUrl) }
    if ($EnvFile) { $boardArgs += @("-EnvFile", $EnvFile) }
    if ($SkipExternalUrlChecks) { $boardArgs += "-SkipExternalUrlChecks" }
    if ($SkipGitHubSecrets) { $boardArgs += "-SkipGitHubSecrets" }
    $actionBoardReport = Invoke-HandoffStep `
        -Name "final-action-board" `
        -Arguments $boardArgs `
        -JsonFilter "final-action-board-*.json" `
        -AllowedExitCodes @(0, 1)
}

foreach ($report in @($officialSourceReport, $videoReport, $cloudReport, $githubReport, $draftPayloadReport, $actionBoardReport)) {
    if ($report -and $report.json) {
        $reports += [ordered]@{
            json = $report.json
            markdown = $report.markdown
            status = if ($report.data -and $report.data.status) { [string]$report.data.status } else { "" }
        }
    }
}

$readyForExternalHandoff = $true
$handoffBlockers = @()
if ($videoReport -and $videoReport.data -and -not [bool]$videoReport.data.readyForManualUpload) {
    $readyForExternalHandoff = $false
    $handoffBlockers += "local_demo_video_publication_handoff"
}
foreach ($step in $steps) {
    if ($step.required -and $step.status -eq "fail") {
        $readyForExternalHandoff = $false
        $handoffBlockers += $step.name
    }
}

$actionTimeConfirmations = @(
    [ordered]@{
        name = "Upload public demo video"
        required = $true
        owner = "Zack"
        boundary = "Uploads MP4, thumbnail, and captions to YouTube/Vimeo/Facebook Video/Youku."
    },
    [ordered]@{
        name = "Configure Alibaba and Qwen secrets"
        required = $true
        owner = "Zack"
        boundary = "Uses real Alibaba AccessKey, registry credentials, and DASHSCOPE_API_KEY."
    },
    [ordered]@{
        name = "Deploy to Alibaba Function Compute"
        required = $true
        owner = "Zack or Codex after explicit confirmation"
        boundary = "Creates or updates cloud resources and may incur provider usage."
    },
    [ordered]@{
        name = "Save Devpost draft fields"
        required = $true
        owner = "Zack or Codex after explicit confirmation"
        boundary = "Saves public text/link fields only; no legal boxes and no final Submit."
    },
    [ordered]@{
        name = "Final Devpost legal submit"
        required = $true
        owner = "Zack only"
        boundary = "Eligibility, Official Rules, and Devpost Terms legal attestations."
    }
)

$commandLines = @(
    "# SPDX-License-Identifier: Apache-2.0",
    "# Generated final external handoff commands. Fill placeholders locally.",
    "# Do not commit real secrets.",
    "",
    'scripts/qwencloud-official-source-refresh.ps1',
    'scripts/qwencloud-video-publication-handoff.ps1',
    'scripts/qwencloud-video-upload-status.ps1 -DemoVideoUrl "<public-video-url>"',
    'scripts/qwencloud-cloud-credentials-handoff.ps1 -EnvFile .env.qwencloud.local -AllowDraft',
    's config add -a default --AccessKeyID "<alibaba-access-key-id>" --AccessKeySecret "<alibaba-access-key-secret>" --force',
    'scripts/qwencloud-deploy-preflight.ps1 -EnvFile .env.qwencloud.local -BuildImage -SmokeContainer -AllowDraft',
    'scripts/qwencloud-github-secrets-handoff.ps1 -EnvFile .env.qwencloud.local -SetFromEnv',
    'gh workflow run "Qwen Cloud Release" --repo zemeng2015/dream-ai-engineering-copilot -f demoVideoUrl="<public-video-url>"',
    'scripts/qwencloud-github-release-artifact-ingest.ps1 -Repo zemeng2015/dream-ai-engineering-copilot',
    'scripts/qwencloud-github-release-artifact-ingest.ps1 -Repo zemeng2015/dream-ai-engineering-copilot -RunId "<workflow-run-id>" -AllowDraft',
    'scripts/qwencloud-alibaba-release.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>"',
    'scripts/qwencloud-render-alibaba-proof-video.ps1 -BaseUrl "<deployed-backend-url>"',
    'scripts/qwencloud-validate-alibaba-proof.ps1 -BackendUrl "<deployed-backend-url>"',
    'scripts/qwencloud-finalize-after-urls.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>" -RefreshAlibabaProof',
    'scripts/qwencloud-final-upload-bundle.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>"',
    'scripts/qwencloud-post-submit-verification.ps1 -DevpostProjectUrl "https://devpost.com/software/<project-slug>" -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>"'
)
Set-Content -Path $commandsPath -Value ($commandLines -join "`r`n") -Encoding UTF8

$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = if ($readyForExternalHandoff) { "READY" } else { "DRAFT" }
    readyForExternalHandoff = $readyForExternalHandoff
    repoUrl = $RepoUrl
    repoName = $RepoName
    demoVideoUrl = $DemoVideoUrl
    backendUrl = $BackendUrl
    blogPostUrl = $BlogPostUrl
    envFile = $EnvFile
    handoffRoot = $handoffRoot
    commandsPath = $commandsPath
    zipPath = $zipPath
    reports = $reports
    steps = $steps
    actionTimeConfirmations = $actionTimeConfirmations
    blockers = $handoffBlockers
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Final External Handoff ($timestamp)",
    "",
    "- Status: $($result.status)",
    "- Ready for Zack external handoff: $readyForExternalHandoff",
    "- Repo: $RepoUrl",
    "- Demo video URL: $(if ($DemoVideoUrl) { $DemoVideoUrl } else { '<missing>' })",
    "- Backend URL: $(if ($BackendUrl) { $BackendUrl } else { '<missing>' })",
    "- Env file: $(if ($EnvFile) { $EnvFile } else { '<none>' })",
    "- Commands file: $commandsPath",
    "- Zip: $zipPath",
    "",
    "## Safety Boundary",
    "",
    "- This handoff does not upload files, set GitHub secrets, configure Alibaba access, deploy, save Devpost fields, or submit Devpost.",
    "- Generated reports may say DRAFT when real URLs or secrets are still missing; that is expected before the external actions.",
    "- Legal eligibility and final Devpost Submit remain Zack-only confirmations.",
    "",
    "## Action-Time Confirmations",
    "",
    "| Action | Required | Owner | Boundary |",
    "|---|---:|---|---|"
)
foreach ($confirmation in $actionTimeConfirmations) {
    $lines += "| $($confirmation.name) | $(if ($confirmation.required) { 'yes' } else { 'no' }) | $($confirmation.owner) | $($confirmation.boundary -replace '\|', '/') |"
}

$lines += @(
    "",
    "## Ordered External Runbook",
    "",
    '1. Refresh the public Devpost overview/rules source report with `qwencloud-official-source-refresh.ps1`.',
    '2. Publish the demo video with the latest `video-publication-handoff-*.md` title, description, thumbnail, captions, and MP4 hash.',
    '3. Paste the public video URL into `qwencloud-video-upload-status.ps1` and confirm the platform is accepted by Devpost rules.',
    '4. Fill `.env.qwencloud.local` locally with Alibaba, registry, and Qwen values; never commit it.',
    '5. Configure Serverless Devs default access with `s config add` and run deploy preflight build+smoke.',
    '6. Either set GitHub release secrets and run the release workflow, or run `qwencloud-alibaba-release.ps1` locally.',
    '7. Capture Alibaba `/health` screenshot and render the separate backend proof recording.',
    '8. Run `qwencloud-finalize-after-urls.ps1`, then regenerate the final upload bundle with real URLs.',
    '9. Save non-legal Devpost text/link fields, upload required assets, then let Zack personally confirm legal boxes and submit.',
    '10. Run post-submit verification and keep the resulting proof report.',
    "",
    "## Step Reports",
    "",
    "| Step | Status | Details | JSON | Markdown |",
    "|---|---:|---|---|"
)
foreach ($step in $steps) {
    $details = ([string]$step.details) -replace "\|", "/"
    $lines += "| $($step.name) | $($step.status) | $details | $($step.jsonPath) | $($step.markdownPath) |"
}

$lines += @(
    "",
    "## Copy/Paste Command File",
    "",
    '```powershell'
) + $commandLines + @(
    '```'
)

if ($handoffBlockers.Count -gt 0) {
    $lines += @(
        "",
        "## Handoff Blockers",
        ""
    )
    foreach ($blocker in $handoffBlockers) {
        $lines += "- $blocker"
    }
}

Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8
Copy-Item -LiteralPath $reportJson -Destination (Join-Path $handoffRoot "manifest.json") -Force
Copy-Item -LiteralPath $reportMd -Destination (Join-Path $handoffRoot "README.md") -Force

if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -Path (Join-Path $handoffRoot "*") -DestinationPath $zipPath -Force

if ($readyForExternalHandoff) {
    Write-Host "Final external handoff READY: $reportMd"
}
else {
    Write-Host "Final external handoff DRAFT: $reportMd" -ForegroundColor Yellow
    Write-Host "Missing handoff items: $($handoffBlockers -join ', ')"
}
Write-Host "Commands: $commandsPath"
Write-Host "ZIP: $zipPath"
Write-Host "JSON: $reportJson"

if (-not $readyForExternalHandoff -and -not $AllowDraft) {
    exit 1
}
