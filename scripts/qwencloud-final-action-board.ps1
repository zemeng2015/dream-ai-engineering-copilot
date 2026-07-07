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
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [string]$EnvFile = "",
    [switch]$SkipExternalUrlChecks,
    [switch]$SkipGitHubSecrets,
    [switch]$SkipLocalVideoChecks,
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
. (Join-Path $PSScriptRoot "qwencloud-env.ps1")
$importedEnvNames = @()
if (-not [string]::IsNullOrWhiteSpace($EnvFile)) {
    $importedEnvNames = @(Import-QwenCloudEnvFile -Path $EnvFile)
}

$reportJson = Join-Path $OutputDir "final-action-board-$timestamp.json"
$reportMd = Join-Path $OutputDir "final-action-board-$timestamp.md"
$steps = @()
$actions = @()

function Get-PowerShellExe {
    $pwsh = Get-Command "pwsh" -ErrorAction SilentlyContinue
    if ($pwsh) { return $pwsh.Source }

    $powershell = Get-Command "powershell" -ErrorAction SilentlyContinue
    if ($powershell) { return $powershell.Source }

    throw "PowerShell executable not found."
}

function Add-Step([string]$Name, [int]$ExitCode, [string]$Details) {
    $script:steps += [ordered]@{
        name = $Name
        exitCode = $ExitCode
        ok = ($ExitCode -eq 0)
        details = $Details
    }
}

function Add-Action([string]$Name, [string]$Reason, [string[]]$Commands, [bool]$RequiresUser = $false) {
    $script:actions += [ordered]@{
        name = $Name
        reason = $Reason
        commands = $Commands
        requiresUser = $RequiresUser
    }
}

function Invoke-BoardStep {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $false)][int[]]$AllowedExitCodes = @(0)
    )

    $stdout = Join-Path $OutputDir "$Name-$timestamp.out"
    $stderr = Join-Path $OutputDir "$Name-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $Arguments -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    Add-Step -Name $Name -ExitCode $proc.ExitCode -Details "stdout=$stdout; stderr=$stderr"
    if ($AllowedExitCodes -notcontains $proc.ExitCode) {
        throw "$Name failed with exit code $($proc.ExitCode). See $stderr"
    }
}

function Get-NewestFile([string]$Filter) {
    Get-ChildItem -LiteralPath $OutputDir -Filter $Filter -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Read-LatestJson([string]$Filter) {
    $file = Get-NewestFile -Filter $Filter
    if (-not $file) {
        return [pscustomobject]@{
            file = $null
            data = $null
        }
    }

    return [pscustomobject]@{
        file = $file.FullName
        data = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
    }
}

function Get-Check($Readiness, [string]$Name) {
    if (-not $Readiness) { return $null }
    return @($Readiness.checks | Where-Object { $_.name -eq $Name } | Select-Object -First 1)
}

$videoArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts/qwencloud-video-upload-status.ps1",
    "-OutputDir", $OutputDir,
    "-AllowDraft"
)
if ($DemoVideoUrl) { $videoArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
if ($SkipExternalUrlChecks) { $videoArgs += "-SkipExternalUrlChecks" }
if ($SkipLocalVideoChecks) { $videoArgs += "-SkipLocalVideoChecks" }
Invoke-BoardStep -Name "video-upload-status" -Arguments $videoArgs

$cloudArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts/qwencloud-cloud-credentials-handoff.ps1",
    "-OutputDir", $OutputDir,
    "-AllowDraft"
)
if ($DemoVideoUrl) { $cloudArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
if ($BackendUrl) { $cloudArgs += @("-BackendUrl", $BackendUrl) }
if ($EnvFile) { $cloudArgs += @("-EnvFile", $EnvFile) }
Invoke-BoardStep -Name "cloud-credentials-handoff" -Arguments $cloudArgs

if ($SkipGitHubSecrets) {
    Add-Step -Name "github-secrets-handoff" -ExitCode 0 -Details "skipped by -SkipGitHubSecrets"
}
else {
    $secretsArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-github-secrets-handoff.ps1",
        "-Repo", $RepoName,
        "-OutputDir", $OutputDir,
        "-AllowDraft"
    )
    if ($EnvFile) { $secretsArgs += @("-EnvFile", $EnvFile) }
    Invoke-BoardStep -Name "github-secrets-handoff" -Arguments $secretsArgs
}

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
if ($BlogPostUrl) { $readinessArgs += @("-BlogPostUrl", $BlogPostUrl) }
if ($EnvFile) { $readinessArgs += @("-EnvFile", $EnvFile) }
if ($SkipExternalUrlChecks) { $readinessArgs += "-SkipExternalUrlChecks" }
Invoke-BoardStep -Name "final-readiness" -Arguments $readinessArgs -AllowedExitCodes @(0, 1)

$videoReport = Read-LatestJson -Filter "video-upload-status-*.json"
$cloudReport = Read-LatestJson -Filter "cloud-credentials-handoff-*.json"
$secretsReport = Read-LatestJson -Filter "github-secrets-handoff-*.json"
$readinessReport = Read-LatestJson -Filter "final-readiness-*.json"

$videoReady = [bool]($videoReport.data -and $videoReport.data.readyForDevpostVideoField)
$cloudReady = [bool]($cloudReport.data -and $cloudReport.data.readyForCloudRelease)
$secretsReady = [bool]($SkipGitHubSecrets -or ($secretsReport.data -and $secretsReport.data.readyForGitHubReleaseWorkflow))
$finalReady = [bool]($readinessReport.data -and $readinessReport.data.readyForFinalSubmit)

$readiness = $readinessReport.data
$proofCheck = Get-Check -Readiness $readiness -Name "alibaba_proof_integrity_ready"
$packetCheck = Get-Check -Readiness $readiness -Name "devpost_submission_packet_ready"
$ciCheck = Get-Check -Readiness $readiness -Name "latest_head_ci_success"

if (-not $videoReady) {
    Add-Action -Name "Publish public demo video" -Reason "Devpost requires a public demo video URL." -RequiresUser $true -Commands @(
        "# Enable Chrome file access only after explicit confirmation, or upload manually.",
        "# Upload artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4 to YouTube, Vimeo, or Youku.",
        'scripts/qwencloud-video-upload-status.ps1 -DemoVideoUrl "<public-video-url>"'
    )
}

if (-not $secretsReady) {
    Add-Action -Name "Set GitHub release secrets" -Reason "The GitHub release workflow cannot deploy without required Alibaba/Qwen secrets." -RequiresUser $true -Commands @(
        "# Set same-named local env vars for Alibaba/Qwen/registry credentials.",
        "scripts/qwencloud-github-secrets-handoff.ps1 -EnvFile .env.qwencloud.local -SetFromEnv",
        'gh workflow run "Qwen Cloud Release" --repo zemeng2015/dream-ai-engineering-copilot -f demoVideoUrl="<public-video-url>"'
    )
}

if (-not $cloudReady) {
    Add-Action -Name "Configure local Alibaba release environment" -Reason "Local release needs Serverless Devs default access and required env vars." -RequiresUser $true -Commands @(
        'scripts/qwencloud-cloud-credentials-handoff.ps1 -EnvFile .env.qwencloud.local -AllowDraft',
        's config add -a default --AccessKeyID "<alibaba-access-key-id>" --AccessKeySecret "<alibaba-access-key-secret>" --force',
        'scripts/qwencloud-alibaba-release.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>"'
    )
}

if ([string]::IsNullOrWhiteSpace($BackendUrl)) {
    Add-Action -Name "Produce deployed Alibaba backend URL" -Reason "Final packet and proof capture need the live Function Compute endpoint." -RequiresUser $true -Commands @(
        'scripts/qwencloud-alibaba-release.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>"',
        'gh workflow run "Qwen Cloud Release" --repo zemeng2015/dream-ai-engineering-copilot -f demoVideoUrl="<public-video-url>"'
    )
}

if (-not ($proofCheck -and $proofCheck.ok)) {
    Add-Action -Name "Generate Alibaba proof evidence" -Reason "Devpost requires Alibaba deployment proof and the integrity gate is not ready." -Commands @(
        'scripts/qwencloud-render-alibaba-proof-video.ps1 -BaseUrl "<deployed-backend-url>" -IncludeDraft',
        'scripts/qwencloud-validate-alibaba-proof.ps1 -BackendUrl "<deployed-backend-url>"'
    )
}

if (-not ($packetCheck -and $packetCheck.ok)) {
    Add-Action -Name "Generate final Devpost packet" -Reason "The copy/paste packet is still DRAFT." -Commands @(
        'scripts/qwencloud-finalize-after-urls.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>"',
        'scripts/qwencloud-final-upload-bundle.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>"'
    )
}

Add-Action -Name "Final Devpost legal submit" -Reason "Eligibility and Official Rules / Terms checkboxes are legal attestations." -RequiresUser $true -Commands @(
    "# Zack confirms age, jurisdiction, sponsor/government employment, Official Rules, and Devpost Terms.",
    "# Submit Devpost only after final-readiness reports READY."
)

$status = if ($finalReady) { "READY" } else { "DRAFT" }
$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = $status
    readyForFinalSubmit = $finalReady
    repoUrl = $RepoUrl
    repoName = $RepoName
    demoVideoUrl = $DemoVideoUrl
    backendUrl = $BackendUrl
    blogPostUrl = $BlogPostUrl
    envFile = $EnvFile
    importedEnvNames = $importedEnvNames
    deadline = "2026-07-09 14:00 PDT / 17:00 EDT"
    reports = [ordered]@{
        videoUploadStatus = $videoReport.file
        cloudCredentialsHandoff = $cloudReport.file
        githubSecretsHandoff = if ($SkipGitHubSecrets) { "<skipped>" } else { $secretsReport.file }
        finalReadiness = $readinessReport.file
    }
    statusSummary = [ordered]@{
        videoReady = $videoReady
        cloudReady = $cloudReady
        githubSecretsReady = $secretsReady
        githubSecretsSkipped = [bool]$SkipGitHubSecrets
        localVideoChecksSkipped = [bool]$SkipLocalVideoChecks
        latestCiReady = [bool]($ciCheck -and $ciCheck.ok)
        alibabaProofIntegrityReady = [bool]($proofCheck -and $proofCheck.ok)
        devpostPacketReady = [bool]($packetCheck -and $packetCheck.ok)
    }
    steps = $steps
    nextActions = $actions
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Final Action Board ($timestamp)",
    "",
    "- Status: $status",
    "- Ready for final Devpost submit: $finalReady",
    "- Deadline: 2026-07-09 14:00 PDT / 17:00 EDT",
    "- Repo: $RepoUrl",
    "- Demo video URL: $(if ($DemoVideoUrl) { $DemoVideoUrl } else { '<missing>' })",
    "- Backend URL: $(if ($BackendUrl) { $BackendUrl } else { '<missing>' })",
    "- Env file imported: $(if ($EnvFile) { $EnvFile } else { '<none>' })",
    "",
    "## Status Summary",
    "",
    "| Signal | Ready |",
    "|---|---:|",
    "| Video URL | $(if ($videoReady) { 'yes' } else { 'no' }) |",
    "| Local cloud release env | $(if ($cloudReady) { 'yes' } else { 'no' }) |",
    "| GitHub release secrets | $(if ($SkipGitHubSecrets) { 'skipped' } elseif ($secretsReady) { 'yes' } else { 'no' }) |",
    "| Latest CI | $(if ($ciCheck -and $ciCheck.ok) { 'yes' } else { 'no' }) |",
    "| Alibaba proof integrity | $(if ($proofCheck -and $proofCheck.ok) { 'yes' } else { 'no' }) |",
    "| Devpost packet | $(if ($packetCheck -and $packetCheck.ok) { 'yes' } else { 'no' }) |",
    "",
    "## Reports",
    "",
    "- Video status: $(if ($videoReport.file) { $videoReport.file } else { '<missing>' })",
    "- Cloud credentials: $(if ($cloudReport.file) { $cloudReport.file } else { '<missing>' })",
    "- GitHub secrets: $(if ($SkipGitHubSecrets) { '<skipped>' } elseif ($secretsReport.file) { $secretsReport.file } else { '<missing>' })",
    "- Final readiness: $(if ($readinessReport.file) { $readinessReport.file } else { '<missing>' })",
    "",
    "## Next Actions",
    ""
)

foreach ($action in $actions) {
    $lines += "### $($action.name)"
    $lines += "- Reason: $($action.reason)"
    $lines += "- Requires Zack/action-time confirmation: $(if ($action.requiresUser) { 'yes' } else { 'no' })"
    $lines += ""
    $lines += '```powershell'
    foreach ($command in $action.commands) {
        $lines += $command
    }
    $lines += '```'
    $lines += ""
}

$lines += @(
    "## Board Steps",
    "",
    "| Step | Exit | Details |",
    "|---|---:|---|"
)
foreach ($step in $steps) {
    $lines += "| $($step.name) | $($step.exitCode) | $($step.details -replace '\|', '/') |"
}

Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($finalReady) {
    Write-Host "Final action board READY: $reportMd"
}
else {
    Write-Host "Final action board DRAFT: $reportMd" -ForegroundColor Yellow
}
Write-Host "JSON: $reportJson"

if (-not $finalReady -and -not $AllowDraft) {
    exit 1
}
