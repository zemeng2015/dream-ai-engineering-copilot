# SPDX-License-Identifier: Apache-2.0

param(
    [Parameter(Mandatory = $false)]
    [string]$RepoUrl = "https://github.com/zemeng2015/dream-ai-engineering-copilot",
    [Parameter(Mandatory = $false)]
    [string]$Repo = "zemeng2015/dream-ai-engineering-copilot",
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
    [Parameter(Mandatory = $false)]
    [ValidateRange(1, 86400)]
    [int]$StepTimeoutSeconds = 900,
    [switch]$UseGitHubReleaseWorkflow,
    [switch]$SetGitHubSecrets,
    [switch]$RunLocalRelease,
    [switch]$RefreshAlibabaProof,
    [switch]$SkipExternalUrlChecks,
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

$reportJson = Join-Path $OutputDir "final-sprint-$timestamp.json"
$reportMd = Join-Path $OutputDir "final-sprint-$timestamp.md"
$steps = @()
$nextActions = @()

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
        [Parameter(Mandatory = $true)][bool]$Ok,
        [Parameter(Mandatory = $true)][string]$Details,
        [Parameter(Mandatory = $false)][string]$Stdout = "",
        [Parameter(Mandatory = $false)][string]$Stderr = ""
    )

    $script:steps += [ordered]@{
        name = $Name
        ok = $Ok
        details = $Details
        stdout = $Stdout
        stderr = $Stderr
    }
}

function Add-NextAction {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Reason,
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $false)][bool]$RequiresZackConfirmation = $false
    )

    $script:nextActions += [ordered]@{
        name = $Name
        reason = $Reason
        command = $Command
        requiresZackConfirmation = $RequiresZackConfirmation
    }
}

function Stop-ProcessTree {
    param(
        [Parameter(Mandatory = $true)][int]$ProcessId
    )

    $children = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.ParentProcessId -eq $ProcessId })
    foreach ($child in $children) {
        Stop-ProcessTree -ProcessId ([int]$child.ProcessId)
    }

    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

function Invoke-SprintStep {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $false)][int[]]$AllowedExitCodes = @(0)
    )

    $stdout = Join-Path $OutputDir "$Name-$timestamp.out"
    $stderr = Join-Path $OutputDir "$Name-$timestamp.err"
    try {
        $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $Arguments -NoNewWindow -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
        $completed = $proc.WaitForExit($StepTimeoutSeconds * 1000)
        if (-not $completed) {
            Stop-ProcessTree -ProcessId $proc.Id
            Add-Step -Name $Name -Ok $false -Details "timeout after ${StepTimeoutSeconds}s; process tree stopped" -Stdout $stdout -Stderr $stderr
            return [pscustomobject]@{
                ok = $false
                exitCode = -2
                timedOut = $true
                stdout = $stdout
                stderr = $stderr
            }
        }

        $proc.Refresh()
        $ok = $AllowedExitCodes -contains $proc.ExitCode
        Add-Step -Name $Name -Ok $ok -Details "exit=$($proc.ExitCode)" -Stdout $stdout -Stderr $stderr
        return [pscustomobject]@{
            ok = $ok
            exitCode = $proc.ExitCode
            timedOut = $false
            stdout = $stdout
            stderr = $stderr
        }
    }
    catch {
        Add-Step -Name $Name -Ok $false -Details $_.Exception.Message -Stdout $stdout -Stderr $stderr
        return [pscustomobject]@{
            ok = $false
            exitCode = -1
            timedOut = $false
            stdout = $stdout
            stderr = $stderr
        }
    }
}

function Get-LatestFile([string]$Filter) {
    return Get-ChildItem -LiteralPath $OutputDir -Filter $Filter -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Read-LatestJson([string]$Filter) {
    $file = Get-LatestFile -Filter $Filter
    if (-not $file) {
        return [pscustomobject]@{
            file = $null
            data = $null
        }
    }

    try {
        return [pscustomobject]@{
            file = $file.FullName
            data = (Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json)
        }
    }
    catch {
        return [pscustomobject]@{
            file = $file.FullName
            data = $null
            error = $_.Exception.Message
        }
    }
}

function Get-RepoNameFromUrl([string]$Url, [string]$Fallback) {
    if ($Url -match "^https://github.com/(?<owner>[^/]+)/(?<repo>[^/]+?)(\.git)?$") {
        return "$($matches.owner)/$($matches.repo)"
    }
    return $Fallback
}

if ([string]::IsNullOrWhiteSpace($Repo)) {
    $Repo = Get-RepoNameFromUrl -Url $RepoUrl -Fallback "zemeng2015/dream-ai-engineering-copilot"
}

$videoArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts/qwencloud-video-upload-status.ps1",
    "-OutputDir", $OutputDir,
    "-LocalVideoPath", $LocalVideoPath,
    "-AllowDraft"
)
if ($DemoVideoUrl) { $videoArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
if ($SkipExternalUrlChecks) { $videoArgs += "-SkipExternalUrlChecks" }
Invoke-SprintStep -Name "final-sprint-video-status" -Arguments $videoArgs | Out-Null

$videoPublicationArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts/qwencloud-video-publication-handoff.ps1",
    "-OutputDir", $OutputDir,
    "-LocalVideoPath", $LocalVideoPath,
    "-AllowDraft"
)
if ($DemoVideoUrl) { $videoPublicationArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
Invoke-SprintStep -Name "final-sprint-video-publication-handoff" -Arguments $videoPublicationArgs | Out-Null

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
Invoke-SprintStep -Name "final-sprint-cloud-handoff" -Arguments $cloudArgs | Out-Null

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
Invoke-SprintStep -Name "final-sprint-live-inputs-intake" -Arguments $liveInputsArgs | Out-Null

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
Invoke-SprintStep -Name "final-sprint-judging-scorecard" -Arguments $scorecardArgs | Out-Null

$githubArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts/qwencloud-github-secrets-handoff.ps1",
    "-Repo", $Repo,
    "-OutputDir", $OutputDir,
    "-AllowDraft"
)
if ($EnvFile) { $githubArgs += @("-EnvFile", $EnvFile) }
if ($SetGitHubSecrets) { $githubArgs += "-SetFromEnv" }
Invoke-SprintStep -Name "final-sprint-github-secrets" -Arguments $githubArgs | Out-Null

if ($RunLocalRelease) {
    $releaseArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-alibaba-release.ps1",
        "-RepoUrl", $RepoUrl,
        "-OutputDir", $OutputDir
    )
    if ($DemoVideoUrl) { $releaseArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
    if ($BackendUrl) { $releaseArgs += @("-BackendUrl", $BackendUrl) }
    if ($BlogPostUrl) { $releaseArgs += @("-BlogPostUrl", $BlogPostUrl) }
    if ($EnvFile) { $releaseArgs += @("-EnvFile", $EnvFile) }
    Invoke-SprintStep -Name "final-sprint-local-release" -Arguments $releaseArgs | Out-Null
}
else {
    $releaseArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-alibaba-release.ps1",
        "-RepoUrl", $RepoUrl,
        "-OutputDir", $OutputDir,
        "-PlanOnly"
    )
    if ($DemoVideoUrl) { $releaseArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
    if ($BackendUrl) { $releaseArgs += @("-BackendUrl", $BackendUrl) }
    if ($BlogPostUrl) { $releaseArgs += @("-BlogPostUrl", $BlogPostUrl) }
    if ($EnvFile) { $releaseArgs += @("-EnvFile", $EnvFile) }
    Invoke-SprintStep -Name "final-sprint-release-plan" -Arguments $releaseArgs | Out-Null
}

$releaseAfterDeploy = Read-LatestJson -Filter "alibaba-release-*.json"
$backendForFinalize = if ($BackendUrl) {
    $BackendUrl
}
elseif ($releaseAfterDeploy.data) {
    [string]$releaseAfterDeploy.data.backendUrl
}
else {
    ""
}
$finalizeSkippedForDraft = $false

$finalizeArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts/qwencloud-finalize-after-urls.ps1",
    "-RepoUrl", $RepoUrl,
    "-OutputDir", $OutputDir,
    "-AllowDraft"
)
if ($DemoVideoUrl) { $finalizeArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
if ($backendForFinalize) { $finalizeArgs += @("-BackendUrl", $backendForFinalize) }
if ($BlogPostUrl) { $finalizeArgs += @("-BlogPostUrl", $BlogPostUrl) }
if ($EnvFile) { $finalizeArgs += @("-EnvFile", $EnvFile) }
if ($RefreshAlibabaProof) { $finalizeArgs += "-RefreshAlibabaProof" }
if ($SkipExternalUrlChecks) { $finalizeArgs += "-SkipExternalUrlChecks" }
if ($AllowDraft -and ([string]::IsNullOrWhiteSpace($DemoVideoUrl) -or [string]::IsNullOrWhiteSpace($backendForFinalize))) {
    $finalizeSkippedForDraft = $true
    Add-Step `
        -Name "final-sprint-finalize-after-urls" `
        -Ok $true `
        -Details "skipped in draft mode until both DemoVideoUrl and BackendUrl are available"
}
else {
    Invoke-SprintStep -Name "final-sprint-finalize-after-urls" -Arguments $finalizeArgs | Out-Null
}

$actionBoardArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts/qwencloud-final-action-board.ps1",
    "-RepoUrl", $RepoUrl,
    "-OutputDir", $OutputDir,
    "-AllowDraft"
)
if ($DemoVideoUrl) { $actionBoardArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
if ($backendForFinalize) { $actionBoardArgs += @("-BackendUrl", $backendForFinalize) }
if ($BlogPostUrl) { $actionBoardArgs += @("-BlogPostUrl", $BlogPostUrl) }
if ($EnvFile) { $actionBoardArgs += @("-EnvFile", $EnvFile) }
if ($SkipExternalUrlChecks) { $actionBoardArgs += "-SkipExternalUrlChecks" }
Invoke-SprintStep -Name "final-sprint-action-board" -Arguments $actionBoardArgs | Out-Null

$video = Read-LatestJson -Filter "video-upload-status-*.json"
$videoPublication = Read-LatestJson -Filter "video-publication-handoff-*.json"
$cloud = Read-LatestJson -Filter "cloud-credentials-handoff-*.json"
$liveInputs = Read-LatestJson -Filter "live-inputs-intake-*.json"
$scorecard = Read-LatestJson -Filter "judging-scorecard-*.json"
$github = Read-LatestJson -Filter "github-secrets-handoff-*.json"
$release = Read-LatestJson -Filter "alibaba-release-*.json"
$finalize = if ($finalizeSkippedForDraft) {
    [pscustomobject]@{
        file = $null
        data = $null
    }
}
else {
    Read-LatestJson -Filter "finalize-after-urls-*.json"
}
$readiness = Read-LatestJson -Filter "final-readiness-*.json"
$officialRules = Read-LatestJson -Filter "official-rules-gate-*.json"
$actionBoard = Read-LatestJson -Filter "final-action-board-*.json"
$uploadBundleManifest = if ($finalizeSkippedForDraft) {
    $null
}
else {
    Get-ChildItem -LiteralPath $OutputDir -Filter "final-upload-bundle-*" -Directory -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        ForEach-Object {
            $candidate = Join-Path $_.FullName "manifest.json"
            if (Test-Path $candidate) { Get-Item -LiteralPath $candidate }
        } |
        Select-Object -First 1
}
$uploadBundle = [pscustomobject]@{ file = $null; data = $null }
if ($uploadBundleManifest) {
    $uploadBundle = [pscustomobject]@{
        file = $uploadBundleManifest.FullName
        data = (Get-Content -LiteralPath $uploadBundleManifest.FullName -Raw | ConvertFrom-Json)
    }
}

$effectiveDemoVideoUrl = if ($DemoVideoUrl) { $DemoVideoUrl } elseif ($video.data) { [string]$video.data.demoVideoUrl } else { "" }
$effectiveBackendUrl = if ($BackendUrl) { $BackendUrl } elseif ($release.data) { [string]$release.data.backendUrl } elseif ($readiness.data) { [string]$readiness.data.backendUrl } else { "" }
$deployPreflightCheck = $null
if ($readiness.data) {
    $deployPreflightCheck = @($readiness.data.checks | Where-Object { $_.name -eq "latest_deploy_preflight_build_smoke" } | Select-Object -First 1)
}

$signals = [ordered]@{
    publicDemoVideoReady = [bool]($video.data -and $video.data.readyForDevpostVideoField)
    videoPublicationHandoffReady = [bool]($videoPublication.data -and $videoPublication.data.readyForManualUpload)
    cloudReleaseReady = [bool]($cloud.data -and $cloud.data.readyForCloudRelease)
    liveInputsReady = [bool]($liveInputs.data -and $liveInputs.data.readyForLiveInputs)
    judgingScorecardReady = [bool]($scorecard.data -and $scorecard.data.readyForJudgingNarrative)
    githubReleaseWorkflowRequired = [bool]$UseGitHubReleaseWorkflow
    githubReleaseWorkflowReady = [bool]((-not $UseGitHubReleaseWorkflow) -or ($github.data -and $github.data.readyForGitHubReleaseWorkflow))
    githubSecretsPresent = [bool]($github.data -and $github.data.readyForGitHubReleaseWorkflow)
    dockerDeployPreflightReady = [bool]($deployPreflightCheck -and $deployPreflightCheck.ok)
    deployedBackendUrlPresent = -not [string]::IsNullOrWhiteSpace($effectiveBackendUrl)
    officialRulesGateReady = [bool]($officialRules.data -and $officialRules.data.readyForOfficialRules)
    finalizeAfterUrlsReady = [bool]($finalize.data -and $finalize.data.readyForDevpostSubmit)
    finalUploadBundleReady = [bool]($uploadBundle.data -and $uploadBundle.data.readyForUpload)
    finalReadinessReady = [bool]($readiness.data -and $readiness.data.readyForFinalSubmit)
    actionBoardReady = [bool]($actionBoard.data -and $actionBoard.data.readyForFinalSubmit)
}

if (-not $signals.publicDemoVideoReady) {
    Add-NextAction `
        -Name "Publish public demo video" `
        -Reason "Devpost video field needs a public YouTube, Vimeo, Facebook Video, or Youku URL." `
        -Command 'scripts/qwencloud-video-publication-handoff.ps1; scripts/qwencloud-video-upload-status.ps1 -DemoVideoUrl "<public-video-url>"' `
        -RequiresZackConfirmation $true
}

if (-not $signals.cloudReleaseReady) {
    Add-NextAction `
        -Name "Configure Alibaba/Qwen local release env" `
        -Reason "Deployment cannot run until the local env file and Serverless Devs default access are configured." `
        -Command 'scripts/qwencloud-cloud-credentials-handoff.ps1 -EnvFile .env.qwencloud.local -AllowDraft' `
        -RequiresZackConfirmation $true
}

if (-not $signals.liveInputsReady) {
    $liveMissing = if ($liveInputs.data) { @($liveInputs.data.missingRequiredChecks) -join ', ' } else { "live inputs intake report missing" }
    Add-NextAction `
        -Name "Collect live submission inputs" `
        -Reason "The live inputs gate is still DRAFT: $liveMissing." `
        -Command 'scripts/qwencloud-live-inputs-intake.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>"' `
        -RequiresZackConfirmation $true
}

if (-not $signals.judgingScorecardReady) {
    $scorecardMissing = if ($scorecard.data) { @($scorecard.data.missingRequiredCriteria) -join ', ' } else { "judging scorecard report missing" }
    Add-NextAction `
        -Name "Close judging scorecard gaps" `
        -Reason "The judging scorecard is still DRAFT: $scorecardMissing." `
        -Command 'scripts/qwencloud-judging-scorecard.ps1 -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>"; scripts/qwencloud-judge-rehearsal.ps1 -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>" -AllowDraft' `
        -RequiresZackConfirmation $true
}

if (-not $signals.dockerDeployPreflightReady) {
    Add-NextAction `
        -Name "Refresh Docker deploy preflight" `
        -Reason "The final readiness report does not have a passing Docker build plus container smoke artifact." `
        -Command 'scripts/qwencloud-deploy-preflight.ps1 -BuildImage -SmokeContainer -AllowDraft' `
        -RequiresZackConfirmation $false
}

if ($UseGitHubReleaseWorkflow -and -not $signals.githubReleaseWorkflowReady) {
    Add-NextAction `
        -Name "Set GitHub release secrets if using Actions" `
        -Reason "The optional Qwen Cloud Release workflow cannot deploy without Alibaba/Qwen secrets." `
        -Command 'scripts/qwencloud-github-secrets-handoff.ps1 -EnvFile .env.qwencloud.local -SetFromEnv' `
        -RequiresZackConfirmation $true
}

if ($signals.cloudReleaseReady -and -not $signals.deployedBackendUrlPresent) {
    Add-NextAction `
        -Name "Deploy Alibaba backend" `
        -Reason "A deployed Function Compute backend URL is required for Stage One, Technical Depth, and Alibaba proof." `
        -Command 'scripts/qwencloud-alibaba-release.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>"' `
        -RequiresZackConfirmation $true
}

if ($signals.deployedBackendUrlPresent -and -not $signals.finalReadinessReady) {
    Add-NextAction `
        -Name "Generate final proof and packet" `
        -Reason "The backend URL exists, but the final proof chain or Devpost packet is not READY yet." `
        -Command 'scripts/qwencloud-finalize-after-urls.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>" -RefreshAlibabaProof' `
        -RequiresZackConfirmation $false
}

if (-not $signals.officialRulesGateReady) {
    Add-NextAction `
        -Name "Clear official rules gate" `
        -Reason "The official Devpost requirement matrix is still DRAFT." `
        -Command 'scripts/qwencloud-official-rules-gate.ps1 -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>"' `
        -RequiresZackConfirmation $false
}

if ($signals.finalReadinessReady) {
    Add-NextAction `
        -Name "Save Devpost draft and final submit" `
        -Reason "All machine checks are ready; remaining actions are Devpost form save, legal attestations, final submit, and public-page verification." `
        -Command 'Use the latest devpost-handoff HTML, confirm legal checkboxes before Submit, then run scripts/qwencloud-post-submit-verification.ps1 -DevpostProjectUrl "<public-devpost-project-url>" -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>".' `
        -RequiresZackConfirmation $true
}

$ready = [bool]$signals.finalReadinessReady
$status = if ($ready) { "READY" } else { "DRAFT" }

$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = $status
    readyForFinalDevpostSubmit = $ready
    repoUrl = $RepoUrl
    repo = $Repo
    demoVideoUrl = $effectiveDemoVideoUrl
    backendUrl = $effectiveBackendUrl
    blogPostUrl = $BlogPostUrl
    envFile = $EnvFile
    importedEnvNames = $importedEnvNames
    stepTimeoutSeconds = $StepTimeoutSeconds
    sideEffectSwitches = [ordered]@{
        useGitHubReleaseWorkflow = [bool]$UseGitHubReleaseWorkflow
        setGitHubSecrets = [bool]$SetGitHubSecrets
        runLocalRelease = [bool]$RunLocalRelease
        refreshAlibabaProof = [bool]$RefreshAlibabaProof
        finalizeAfterUrlsSkippedForDraft = [bool]$finalizeSkippedForDraft
    }
    signals = $signals
    reports = [ordered]@{
        videoUploadStatusJson = $video.file
        videoPublicationHandoffJson = $videoPublication.file
        cloudCredentialsHandoffJson = $cloud.file
        liveInputsIntakeJson = $liveInputs.file
        judgingScorecardJson = $scorecard.file
        githubSecretsHandoffJson = $github.file
        alibabaReleaseJson = $release.file
        finalizeAfterUrlsJson = $finalize.file
        officialRulesGateJson = $officialRules.file
        finalReadinessJson = $readiness.file
        finalActionBoardJson = $actionBoard.file
        finalUploadBundleManifestJson = $uploadBundle.file
        finalUploadBundleZip = if ($uploadBundle.data) { $uploadBundle.data.zipPath } else { $null }
    }
    steps = $steps
    nextActions = $nextActions
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Final Sprint ($timestamp)",
    "",
    "- Status: $status",
    "- Ready for final Devpost submit: $ready",
    "- Repo: $RepoUrl",
    "- Demo video URL: $(if ($effectiveDemoVideoUrl) { $effectiveDemoVideoUrl } else { '<missing>' })",
    "- Backend URL: $(if ($effectiveBackendUrl) { $effectiveBackendUrl } else { '<missing>' })",
    "- Env file imported: $(if ($EnvFile) { $EnvFile } else { '<none>' })",
    "- Step timeout seconds: $StepTimeoutSeconds",
    "- Use GitHub release workflow: $([bool]$UseGitHubReleaseWorkflow)",
    "- Set GitHub secrets requested: $([bool]$SetGitHubSecrets)",
    "- Run local release requested: $([bool]$RunLocalRelease)",
    "- Refresh Alibaba proof requested: $([bool]$RefreshAlibabaProof)",
    "- Finalize after URLs skipped for draft: $([bool]$finalizeSkippedForDraft)",
    "",
    "## Signals",
    "",
    "| Signal | Ready |",
    "|---|---:|"
)
foreach ($signal in $signals.GetEnumerator()) {
    $lines += "| $($signal.Key) | $(if ($signal.Value) { 'yes' } else { 'no' }) |"
}

$lines += @(
    "",
    "## Step Runs",
    "",
    "| Step | Result | Details |",
    "|---|---:|---|"
)
foreach ($step in $steps) {
    $lines += "| $($step.name) | $(if ($step.ok) { 'PASS' } else { 'FAIL' }) | $($step.details); stdout=$($step.stdout); stderr=$($step.stderr) |"
}

$lines += @(
    "",
    "## Reports",
    "",
    "- Video upload status: $(if ($video.file) { $video.file } else { '<missing>' })",
    "- Video publication handoff: $(if ($videoPublication.file) { $videoPublication.file } else { '<missing>' })",
    "- Cloud credentials handoff: $(if ($cloud.file) { $cloud.file } else { '<missing>' })",
    "- Live inputs intake: $(if ($liveInputs.file) { $liveInputs.file } else { '<missing>' })",
    "- Judging scorecard: $(if ($scorecard.file) { $scorecard.file } else { '<missing>' })",
    "- GitHub secrets handoff: $(if ($github.file) { $github.file } else { '<missing>' })",
    "- Alibaba release report: $(if ($release.file) { $release.file } else { '<missing>' })",
    "- Finalize after URLs: $(if ($finalize.file) { $finalize.file } else { '<missing>' })",
    "- Official rules gate: $(if ($officialRules.file) { $officialRules.file } else { '<missing>' })",
    "- Final readiness: $(if ($readiness.file) { $readiness.file } else { '<missing>' })",
    "- Final action board: $(if ($actionBoard.file) { $actionBoard.file } else { '<missing>' })",
    "- Final upload bundle manifest: $(if ($uploadBundle.file) { $uploadBundle.file } else { '<missing>' })",
    "- Final upload bundle zip: $(if ($uploadBundle.data) { $uploadBundle.data.zipPath } else { '<missing>' })",
    "",
    "## Next Actions",
    ""
)
if ($nextActions.Count -eq 0) {
    $lines += "- None"
}
else {
    foreach ($action in $nextActions) {
        $lines += "- $($action.name): $($action.reason)"
        $lines += "  Requires Zack/action-time confirmation: $(if ($action.requiresZackConfirmation) { 'yes' } else { 'no' })"
        $lines += "  Command: ``$($action.command)``"
    }
}

$lines += @(
    "",
    "## Confirmation Boundaries",
    "",
    "- Saving Devpost draft fields, uploading files, setting GitHub secrets, deploying to Alibaba, and final Devpost submit require action-time confirmation.",
    "- This report does not store secret values; it only records whether required values are configured.",
    "- Do not mark the hackathon goal complete until the public Devpost page, public video URL, deployed Alibaba backend URL, proof screenshot/recording, and submission proof are verified."
)
Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($ready) {
    Write-Host "Final sprint READY: $reportMd"
}
else {
    Write-Host "Final sprint DRAFT: $reportMd" -ForegroundColor Yellow
    Write-Host "Next actions: $($nextActions.name -join ', ')"
    if (-not $AllowDraft) {
        exit 1
    }
}
Write-Host "JSON: $reportJson"
