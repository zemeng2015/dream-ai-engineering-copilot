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

$videoPublicationArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts/qwencloud-video-publication-handoff.ps1",
    "-OutputDir", $OutputDir,
    "-AllowDraft"
)
if ($DemoVideoUrl) { $videoPublicationArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
Invoke-BoardStep -Name "video-publication-handoff" -Arguments $videoPublicationArgs

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

$releaseConfigArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts/qwencloud-release-config-audit.ps1",
    "-OutputDir", $OutputDir,
    "-AllowDraft"
)
if ($EnvFile) { $releaseConfigArgs += @("-EnvFile", $EnvFile) }
Invoke-BoardStep -Name "release-config-audit" -Arguments $releaseConfigArgs

$liveInputsArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts/qwencloud-live-inputs-intake.ps1",
    "-OutputDir", $OutputDir,
    "-AllowDraft"
)
if ($DemoVideoUrl) { $liveInputsArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
if ($BackendUrl) { $liveInputsArgs += @("-BackendUrl", $BackendUrl) }
if ($BlogPostUrl) { $liveInputsArgs += @("-BlogPostUrl", $BlogPostUrl) }
if ($EnvFile) { $liveInputsArgs += @("-EnvFile", $EnvFile) }
if ($SkipExternalUrlChecks) { $liveInputsArgs += "-SkipExternalUrlChecks" }
Invoke-BoardStep -Name "live-inputs-intake" -Arguments $liveInputsArgs

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
Invoke-BoardStep -Name "judging-scorecard" -Arguments $scorecardArgs

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
if ($SkipLocalVideoChecks) { $readinessArgs += "-SkipLocalVideoChecks" }
Invoke-BoardStep -Name "final-readiness" -Arguments $readinessArgs -AllowedExitCodes @(0, 1)

$videoReport = Read-LatestJson -Filter "video-upload-status-*.json"
$videoPublicationReport = Read-LatestJson -Filter "video-publication-handoff-*.json"
$cloudReport = Read-LatestJson -Filter "cloud-credentials-handoff-*.json"
$liveInputsReport = Read-LatestJson -Filter "live-inputs-intake-*.json"
$releaseConfigReport = Read-LatestJson -Filter "release-config-audit-*.json"
$scorecardReport = Read-LatestJson -Filter "judging-scorecard-*.json"
$secretsReport = Read-LatestJson -Filter "github-secrets-handoff-*.json"
$officialRulesReport = Read-LatestJson -Filter "official-rules-gate-*.json"
$readinessReport = Read-LatestJson -Filter "final-readiness-*.json"

$videoReady = [bool]($videoReport.data -and $videoReport.data.readyForDevpostVideoField)
$videoPublicationReady = [bool]($videoPublicationReport.data -and $videoPublicationReport.data.readyForManualUpload)
$cloudReady = [bool]($cloudReport.data -and $cloudReport.data.readyForCloudRelease)
$liveInputsReady = [bool]($liveInputsReport.data -and $liveInputsReport.data.readyForLiveInputs)
$releaseConfigReady = [bool]($releaseConfigReport.data -and $releaseConfigReport.data.readyForReleaseConfig)
$scorecardReady = [bool]($scorecardReport.data -and $scorecardReport.data.readyForJudgingNarrative)
$scorecardStaticReady = [bool]($scorecardReport.data -and $scorecardReport.data.weightedStaticEvidenceReady -eq $scorecardReport.data.weightedTotal)
$scorecardMissingExternalInputs = @()
$scorecardMissingEvidencePaths = @()
if ($scorecardReport.data) {
    $scorecardMissingExternalInputs = @($scorecardReport.data.criteria | ForEach-Object { @($_.missingExternalInputs) } | Where-Object { $_ } | Sort-Object -Unique)
    $scorecardMissingEvidencePaths = @($scorecardReport.data.criteria | ForEach-Object { @($_.missingEvidencePaths) } | Where-Object { $_ } | Sort-Object -Unique)
}
$secretsReady = [bool]($SkipGitHubSecrets -or ($secretsReport.data -and $secretsReport.data.readyForGitHubReleaseWorkflow))
$officialRulesReady = [bool]($officialRulesReport.data -and $officialRulesReport.data.readyForOfficialRules)
$finalReady = [bool]($readinessReport.data -and $readinessReport.data.readyForFinalSubmit)

$readiness = $readinessReport.data
$proofCheck = Get-Check -Readiness $readiness -Name "alibaba_proof_integrity_ready"
$packetCheck = Get-Check -Readiness $readiness -Name "devpost_submission_packet_ready"
$ciCheck = Get-Check -Readiness $readiness -Name "latest_head_ci_success"
$deployPreflightCheck = Get-Check -Readiness $readiness -Name "latest_deploy_preflight_build_smoke"

if (-not $videoReady) {
    Add-Action -Name "Publish public demo video" -Reason "Devpost requires a public demo video URL." -RequiresUser $true -Commands @(
        'scripts/qwencloud-video-publication-handoff.ps1',
        "# Enable Chrome file access only after explicit confirmation, or upload manually.",
        "# Upload artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4 to YouTube, Vimeo, Facebook Video, or Youku.",
        'scripts/qwencloud-video-upload-status.ps1 -DemoVideoUrl "<public-video-url>"'
    )
}

if (-not $secretsReady) {
    Add-Action -Name "Set GitHub release secrets" -Reason "The GitHub release workflow cannot deploy without required Alibaba/Qwen secrets." -RequiresUser $true -Commands @(
        "# Set same-named local env vars for Alibaba/Qwen/registry credentials.",
        "scripts/qwencloud-github-secrets-handoff.ps1 -EnvFile .env.qwencloud.local -SetFromEnv",
        'gh workflow run "Qwen Cloud Release" --repo zemeng2015/dream-ai-engineering-copilot -f demoVideoUrl="<public-video-url>"',
        "# After the workflow completes:",
        "# Ingest auto-selects the latest completed successful run and skips active runs.",
        'scripts/qwencloud-github-release-artifact-ingest.ps1 -Repo zemeng2015/dream-ai-engineering-copilot',
        "# If the run fails after uploading qwencloud-release-proof, recover the latest completed run with -AllowDraft or force a specific run with:",
        'scripts/qwencloud-github-release-artifact-ingest.ps1 -Repo zemeng2015/dream-ai-engineering-copilot -RunId "<workflow-run-id>" -AllowDraft'
    )
}

if (-not $cloudReady) {
    Add-Action -Name "Configure local Alibaba release environment" -Reason "Local release needs Serverless Devs default access and required env vars." -RequiresUser $true -Commands @(
        'scripts/qwencloud-cloud-credentials-handoff.ps1 -EnvFile .env.qwencloud.local -AllowDraft',
        's config add -a default --AccessKeyID "<alibaba-access-key-id>" --AccessKeySecret "<alibaba-access-key-secret>" --force',
        'scripts/qwencloud-alibaba-release.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>"'
    )
}

if (-not $releaseConfigReady) {
    $configMissing = if ($releaseConfigReport.data) { @($releaseConfigReport.data.missingRequiredChecks) -join ', ' } else { "release config audit report missing" }
    Add-Action -Name "Fix release config audit" -Reason "Release config audit is not READY: $configMissing." -RequiresUser $true -Commands @(
        'Copy-Item .env.qwencloud.local.example .env.qwencloud.local',
        "# Fill .env.qwencloud.local locally; do not commit it.",
        'scripts/qwencloud-release-config-audit.ps1 -EnvFile .env.qwencloud.local -AllowDraft',
        'scripts/qwencloud-github-secrets-handoff.ps1 -EnvFile .env.qwencloud.local -SetFromEnv'
    )
}

if (-not $liveInputsReady) {
    $liveMissing = if ($liveInputsReport.data) { @($liveInputsReport.data.missingRequiredChecks) -join ', ' } else { "live inputs intake report missing" }
    Add-Action -Name "Collect live submission inputs" -Reason "Live inputs intake is not READY: $liveMissing." -RequiresUser $true -Commands @(
        'Copy-Item .env.qwencloud.local.example .env.qwencloud.local',
        "# Fill .env.qwencloud.local locally; do not commit it.",
        'scripts/qwencloud-live-inputs-intake.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>"',
        'scripts/qwencloud-finalize-after-urls.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>" -RefreshAlibabaProof'
    )
}

if (-not $scorecardReady) {
    $scorecardMissing = if ($scorecardReport.data) { @($scorecardReport.data.missingRequiredCriteria) -join ', ' } else { "judging scorecard report missing" }
    if ($scorecardStaticReady -and $scorecardMissingEvidencePaths.Count -eq 0) {
        $externalMissing = if ($scorecardMissingExternalInputs.Count -gt 0) { $scorecardMissingExternalInputs -join ', ' } else { $scorecardMissing }
        Add-Action -Name "Supply public video/backend URLs for final scorecard" -Reason "Static judging evidence is complete ($($scorecardReport.data.weightedStaticEvidenceReady)/$($scorecardReport.data.weightedTotal)); the scorecard is DRAFT only because external inputs are missing: $externalMissing." -RequiresUser $true -Commands @(
            'scripts/qwencloud-judging-scorecard.ps1 -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>"',
            'scripts/qwencloud-judge-rehearsal.ps1 -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>" -AllowDraft',
            "# This should flip the scorecard to READY once the public video and deployed backend URL are real."
        )
    }
    else {
        Add-Action -Name "Close judging scorecard gaps" -Reason "Judging scorecard is not READY: $scorecardMissing." -RequiresUser $true -Commands @(
            'scripts/qwencloud-judging-scorecard.ps1 -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>"',
            'scripts/qwencloud-judge-rehearsal.ps1 -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>" -AllowDraft',
            "# Use the latest judging-scorecard-*.md to tighten Devpost text and demo narration before final submit."
        )
    }
}

if (-not ($deployPreflightCheck -and $deployPreflightCheck.ok)) {
    Add-Action -Name "Refresh Docker deploy preflight" -Reason "The latest Docker build plus container smoke check is not ready." -Commands @(
        'scripts/qwencloud-deploy-preflight.ps1 -BuildImage -SmokeContainer -AllowDraft',
        'scripts/qwencloud-final-readiness.ps1 -AllowDraftPacket'
    )
}

if ([string]::IsNullOrWhiteSpace($BackendUrl)) {
    Add-Action -Name "Produce deployed Alibaba backend URL" -Reason "Final packet and proof capture need the live Function Compute endpoint." -RequiresUser $true -Commands @(
        'scripts/qwencloud-alibaba-release.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>"',
        'gh workflow run "Qwen Cloud Release" --repo zemeng2015/dream-ai-engineering-copilot -f demoVideoUrl="<public-video-url>"',
        "# If using GitHub Actions, after the workflow completes:",
        "# Ingest auto-selects the latest completed successful run and skips active runs.",
        'scripts/qwencloud-github-release-artifact-ingest.ps1 -Repo zemeng2015/dream-ai-engineering-copilot',
        "# If the run fails after uploading qwencloud-release-proof, recover the latest completed run with -AllowDraft or force a specific run with:",
        'scripts/qwencloud-github-release-artifact-ingest.ps1 -Repo zemeng2015/dream-ai-engineering-copilot -RunId "<workflow-run-id>" -AllowDraft'
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
        'scripts/qwencloud-finalize-after-urls.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>" -RefreshAlibabaProof',
        'scripts/qwencloud-final-upload-bundle.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>"'
    )
}

if (-not $officialRulesReady) {
    $officialMissing = if ($officialRulesReport.data) { @($officialRulesReport.data.missingRequired) -join ', ' } else { "official rules gate report missing" }
    Add-Action -Name "Clear official rules gate" -Reason "Official rules gate is not READY: $officialMissing." -Commands @(
        'scripts/qwencloud-official-rules-gate.ps1 -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>"',
        'scripts/qwencloud-final-readiness.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>"'
    )
}

Add-Action -Name "Prepare and save Devpost draft fields" -Reason "The live Devpost draft still needs public text fields saved before final review." -RequiresUser $true -Commands @(
    'scripts/qwencloud-devpost-draft-payload.ps1 -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>" -AllowDraft',
    'scripts/qwencloud-devpost-autofill-snippet.ps1 -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>" -AllowDraft',
    "# After Zack confirms, save only non-legal public text fields to Devpost.",
    "# Do not upload files, check legal attestations, or click final Submit from this step."
)

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
        videoPublicationHandoff = $videoPublicationReport.file
        cloudCredentialsHandoff = $cloudReport.file
        liveInputsIntake = $liveInputsReport.file
        releaseConfigAudit = $releaseConfigReport.file
        judgingScorecard = $scorecardReport.file
        githubSecretsHandoff = if ($SkipGitHubSecrets) { "<skipped>" } else { $secretsReport.file }
        finalReadiness = $readinessReport.file
        officialRulesGate = $officialRulesReport.file
    }
    statusSummary = [ordered]@{
        videoReady = $videoReady
        videoPublicationHandoffReady = $videoPublicationReady
        cloudReady = $cloudReady
        liveInputsReady = $liveInputsReady
        releaseConfigReady = $releaseConfigReady
        judgingScorecardReady = $scorecardReady
        judgingScorecardWeightedEvidenceReady = if ($scorecardReport.data) { $scorecardReport.data.weightedEvidenceReady } else { $null }
        judgingScorecardWeightedStaticEvidenceReady = if ($scorecardReport.data) { $scorecardReport.data.weightedStaticEvidenceReady } else { $null }
        judgingScorecardWeightedTotal = if ($scorecardReport.data) { $scorecardReport.data.weightedTotal } else { $null }
        judgingScorecardStaticEvidenceReady = $scorecardStaticReady
        judgingScorecardMissingExternalInputs = $scorecardMissingExternalInputs
        judgingScorecardMissingEvidencePaths = $scorecardMissingEvidencePaths
        githubSecretsReady = $secretsReady
        githubSecretsSkipped = [bool]$SkipGitHubSecrets
        localVideoChecksSkipped = [bool]$SkipLocalVideoChecks
        latestCiReady = [bool]($ciCheck -and $ciCheck.ok)
        dockerDeployPreflightReady = [bool]($deployPreflightCheck -and $deployPreflightCheck.ok)
        officialRulesGateReady = $officialRulesReady
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
    "| Video publication handoff | $(if ($videoPublicationReady) { 'yes' } else { 'no' }) |",
    "| Local cloud release env | $(if ($cloudReady) { 'yes' } else { 'no' }) |",
    "| Release config audit | $(if ($releaseConfigReady) { 'yes' } else { 'no' }) |",
    "| Live inputs intake | $(if ($liveInputsReady) { 'yes' } else { 'no' }) |",
    "| Judging scorecard | $(if ($scorecardReady) { 'yes' } else { 'no' }) |",
    "| GitHub release secrets | $(if ($SkipGitHubSecrets) { 'skipped' } elseif ($secretsReady) { 'yes' } else { 'no' }) |",
    "| Latest CI | $(if ($ciCheck -and $ciCheck.ok) { 'yes' } else { 'no' }) |",
    "| Docker deploy preflight | $(if ($deployPreflightCheck -and $deployPreflightCheck.ok) { 'yes' } else { 'no' }) |",
    "| Official rules gate | $(if ($officialRulesReady) { 'yes' } else { 'no' }) |",
    "| Alibaba proof integrity | $(if ($proofCheck -and $proofCheck.ok) { 'yes' } else { 'no' }) |",
    "| Devpost packet | $(if ($packetCheck -and $packetCheck.ok) { 'yes' } else { 'no' }) |",
    "",
    "## Reports",
    "",
    "- Video status: $(if ($videoReport.file) { $videoReport.file } else { '<missing>' })",
    "- Video publication handoff: $(if ($videoPublicationReport.file) { $videoPublicationReport.file } else { '<missing>' })",
    "- Cloud credentials: $(if ($cloudReport.file) { $cloudReport.file } else { '<missing>' })",
    "- Release config audit: $(if ($releaseConfigReport.file) { $releaseConfigReport.file } else { '<missing>' })",
    "- Live inputs intake: $(if ($liveInputsReport.file) { $liveInputsReport.file } else { '<missing>' })",
    "- Judging scorecard: $(if ($scorecardReport.file) { $scorecardReport.file } else { '<missing>' })",
    "- GitHub secrets: $(if ($SkipGitHubSecrets) { '<skipped>' } elseif ($secretsReport.file) { $secretsReport.file } else { '<missing>' })",
    "- Official rules gate: $(if ($officialRulesReport.file) { $officialRulesReport.file } else { '<missing>' })",
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
