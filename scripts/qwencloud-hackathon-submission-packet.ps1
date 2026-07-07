param(
    [Parameter(Mandatory = $false)]
    [string]$RepoUrl = "",
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
    [switch]$SkipExternalUrlChecks,
    [switch]$SkipBackendDraft,
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
. (Join-Path $PSScriptRoot "qwencloud-devpost-video-url.ps1")
$packetJson = Join-Path $OutputDir "devpost-submission-packet-$timestamp.json"
$packetMd = Join-Path $OutputDir "devpost-submission-packet-$timestamp.md"
$checks = @()
$ready = $true

$projectTitle = "DREAM: Qwen Cloud MemoryAgent for Source-Backed Engineering Intelligence"
$track = "Track 1: MemoryAgent"
$defaultRepoUrl = "https://github.com/zemeng2015/dream-ai-engineering-copilot"

function Add-Check([string]$Name, [bool]$Ok, [string]$Details, [bool]$Required = $true) {
    $script:checks += [ordered]@{
        name = $Name
        ok = $Ok
        required = $Required
        details = $Details
    }

    if ($Required -and -not $Ok) {
        $script:ready = $false
    }
}

function Normalize-RepoUrl([string]$Url) {
    if (-not [string]::IsNullOrWhiteSpace($Url)) {
        return ($Url -replace "\.git$", "")
    }

    try {
        $origin = (& git remote get-url origin 2>$null).Trim()
        if ($origin -match "^https://github.com/(?<owner>[^/]+)/(?<repo>[^/]+?)(\.git)?$") {
            return "https://github.com/$($matches.owner)/$($matches.repo)"
        }
        if ($origin -match "^git@github.com:(?<owner>[^/]+)/(?<repo>[^/]+?)(\.git)?$") {
            return "https://github.com/$($matches.owner)/$($matches.repo)"
        }
    }
    catch {
        # Fall through to the known public repo for this submission.
    }

    return $defaultRepoUrl
}

function Test-PublicGitHubRepo([string]$Url) {
    if ($Url -notmatch "^https://github.com/(?<owner>[^/]+)/(?<repo>[^/]+)$") {
        return [pscustomobject]@{
            ok = $false
            details = "Not a normalized GitHub HTTPS repo URL."
            license = $null
        }
    }

    try {
        $apiUrl = "https://api.github.com/repos/$($matches.owner)/$($matches.repo)"
        $repoData = Invoke-RestMethod -Uri $apiUrl -UserAgent "dream-qwencloud-submission-packet/1.0" -TimeoutSec 15
        return [pscustomobject]@{
            ok = ($repoData.visibility -eq "public" -and -not [bool]$repoData.private)
            details = "visibility=$($repoData.visibility)"
            license = $repoData.license.spdx_id
        }
    }
    catch {
        return [pscustomobject]@{
            ok = $false
            details = $_.Exception.Message
            license = $null
        }
    }
}

function Is-PublicVideoUrl([string]$Url) {
    return Test-QwenCloudDevpostVideoUrl -Url $Url
}

function Is-HttpUrl([string]$Url) {
    if ([string]::IsNullOrWhiteSpace($Url)) {
        return $false
    }
    if ($Url -match "[<>]|\.\.\.") {
        return $false
    }
    return [bool]($Url -match "^https?://")
}

function Test-HttpReachable([string]$Url) {
    if (-not (Is-HttpUrl $Url)) {
        return [pscustomobject]@{
            ok = $false
            details = "not an http(s) URL"
        }
    }

    try {
        $response = Invoke-WebRequest -Method Head -Uri $Url -UserAgent "dream-qwencloud-submission-packet/1.0" -TimeoutSec 20 -MaximumRedirection 5 -ErrorAction Stop
        return [pscustomobject]@{
            ok = ([int]$response.StatusCode -ge 200 -and [int]$response.StatusCode -lt 400)
            details = "HEAD status=$([int]$response.StatusCode)"
        }
    }
    catch {
        try {
            $response = Invoke-WebRequest -Method Get -Uri $Url -UserAgent "dream-qwencloud-submission-packet/1.0" -TimeoutSec 20 -MaximumRedirection 5 -ErrorAction Stop
            return [pscustomobject]@{
                ok = ([int]$response.StatusCode -ge 200 -and [int]$response.StatusCode -lt 400)
                details = "GET status=$([int]$response.StatusCode)"
            }
        }
        catch {
            return [pscustomobject]@{
                ok = $false
                details = $_.Exception.Message
            }
        }
    }
}

function Get-PowerShellExe {
    $pwsh = Get-Command "pwsh" -ErrorAction SilentlyContinue
    if ($pwsh) { return $pwsh.Source }

    $powershell = Get-Command "powershell" -ErrorAction SilentlyContinue
    if ($powershell) { return $powershell.Source }

    throw "PowerShell executable not found."
}

function Invoke-AlibabaProofIntegrity {
    if (-not (Test-Path "scripts/qwencloud-validate-alibaba-proof.ps1")) {
        return [pscustomobject]@{
            ok = $false
            details = "missing scripts/qwencloud-validate-alibaba-proof.ps1"
        }
    }

    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "alibaba-proof-integrity-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-validate-alibaba-proof.ps1",
        "-OutputDir", $OutputDir,
        "-ScreenshotPath", $AlibabaScreenshotPath,
        "-ProofVideoPath", $AlibabaProofVideoPath,
        "-AllowDraft"
    )
    if ($BackendUrl) { $args += @("-BackendUrl", $BackendUrl) }

    $stdout = Join-Path $OutputDir "submission-packet-alibaba-proof-integrity-$timestamp.out"
    $stderr = Join-Path $OutputDir "submission-packet-alibaba-proof-integrity-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        return [pscustomobject]@{ ok = $false; details = "exit=$($proc.ExitCode); stdout=$stdout; stderr=$stderr" }
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "alibaba-proof-integrity-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $newest = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $newest) {
        $newest = @($after | Select-Object -First 1)
    }
    if (-not $newest) {
        return [pscustomobject]@{ ok = $false; details = "integrity JSON not found; stdout=$stdout; stderr=$stderr" }
    }

    $proof = Get-Content -LiteralPath $newest.FullName -Raw | ConvertFrom-Json
    $failedRequired = @($proof.checks | Where-Object { $_.required -and -not $_.ok } | ForEach-Object { $_.name })
    return [pscustomobject]@{
        ok = [bool]$proof.readyForDevpostAlibabaProof
        details = if ($proof.readyForDevpostAlibabaProof) { "proof integrity READY: $($newest.FullName)" } else { "proof integrity DRAFT: $($newest.FullName); missing=$($failedRequired -join ', ')" }
    }
}

function Test-UploadAsset([string]$Path, [string[]]$Extensions, [int]$MaxMb) {
    if (-not (Test-Path $Path)) {
        return [pscustomobject]@{
            ok = $false
            details = "missing: $Path"
        }
    }

    $item = Get-Item $Path
    $extensionOk = $Extensions -contains $item.Extension.ToLowerInvariant()
    $sizeOk = $item.Length -le ($MaxMb * 1024 * 1024)
    return [pscustomobject]@{
        ok = ($extensionOk -and $sizeOk)
        details = "path=$Path; extension=$($item.Extension); size=$($item.Length); maxMb=$MaxMb"
    }
}

function Get-PngDimensions([string]$Path) {
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

    $width = ([int]$bytes[16] -shl 24) -bor ([int]$bytes[17] -shl 16) -bor ([int]$bytes[18] -shl 8) -bor [int]$bytes[19]
    $height = ([int]$bytes[20] -shl 24) -bor ([int]$bytes[21] -shl 16) -bor ([int]$bytes[22] -shl 8) -bor [int]$bytes[23]
    return [pscustomobject]@{
        width = $width
        height = $height
    }
}

function Get-VideoMetadata([string]$Path) {
    if (-not (Test-Path $Path)) {
        return $null
    }
    if (-not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
        return $null
    }

    $probeJson = & ffprobe -v error -show_entries format=duration,size,format_name -show_streams -of json $Path
    $probe = $probeJson | ConvertFrom-Json
    $videoStream = @($probe.streams | Where-Object { $_.codec_type -eq "video" } | Select-Object -First 1)
    return [pscustomobject]@{
        duration = [double]$probe.format.duration
        size = [int64]$probe.format.size
        format = $probe.format.format_name
        width = if ($videoStream) { [int]$videoStream.width } else { 0 }
        height = if ($videoStream) { [int]$videoStream.height } else { 0 }
        codec = if ($videoStream) { [string]$videoStream.codec_name } else { "" }
    }
}

function Get-FileUrl([string]$Repo, [string]$Path) {
    return "$Repo/blob/main/$Path"
}

$repoUsed = Normalize-RepoUrl -Url $RepoUrl
$licenseUrl = Get-FileUrl -Repo $repoUsed -Path "LICENSE"
$architectureSvgUrl = Get-FileUrl -Repo $repoUsed -Path "docs/assets/qwencloud-architecture.svg"
$architecturePngUrl = Get-FileUrl -Repo $repoUsed -Path "docs/assets/qwencloud-architecture.png"
$deploymentProofUrl = Get-FileUrl -Repo $repoUsed -Path "deploy/alibaba/serverless-devs.yaml"
$deployPreflightUrl = Get-FileUrl -Repo $repoUsed -Path "scripts/qwencloud-deploy-preflight.ps1"
$qwenConfigUrl = Get-FileUrl -Repo $repoUsed -Path "examples/config/dream.qwen.yaml"
$buildJourneyDraftUrl = Get-FileUrl -Repo $repoUsed -Path "docs/qwencloud-build-journey-post.md"
$testingAndRightsNotesUrl = Get-FileUrl -Repo $repoUsed -Path "docs/qwencloud-testing-and-rights-notes.md"
$devpostAutofillSnippetScriptUrl = Get-FileUrl -Repo $repoUsed -Path "scripts/qwencloud-devpost-autofill-snippet.ps1"
$judgingScorecardScriptUrl = Get-FileUrl -Repo $repoUsed -Path "scripts/qwencloud-judging-scorecard.ps1"
$officialRulesGateScriptUrl = Get-FileUrl -Repo $repoUsed -Path "scripts/qwencloud-official-rules-gate.ps1"
$ciUrl = "$repoUsed/actions/workflows/ci.yml"

$requiredPaths = @(
    "README.md",
    "LICENSE",
    "Dockerfile",
    "docs/qwencloud-submission.md",
    "docs/qwencloud-devpost-form-fields.md",
    "docs/qwencloud-devpost-submission-kit.md",
    "docs/qwencloud-final-5min-checklist.md",
    "docs/qwencloud-video-upload-handoff.md",
    "docs/qwencloud-testing-and-rights-notes.md",
    "docs/qwencloud-architecture.md",
    "docs/assets/qwencloud-architecture.svg",
    "docs/assets/qwencloud-architecture.png",
    "docs/assets/qwencloud-video-thumbnail.svg",
    "docs/assets/qwencloud-video-thumbnail.png",
    "docs/qwencloud-demo-video-captions.srt",
    "docs/qwencloud-demo-video-transcript.md",
    "docs/qwencloud-official-requirements-snapshot.md",
    "docs/qwencloud-build-journey-post.md",
    "deploy/alibaba/serverless-devs.yaml",
    "deploy/alibaba/README.md",
    "examples/config/dream.qwen.yaml",
    "scripts/qwencloud-cloud-credentials-handoff.ps1",
    "scripts/qwencloud-devpost-handoff.ps1",
    "scripts/qwencloud-alibaba-release.ps1",
    "scripts/qwencloud-capture-alibaba-proof.ps1",
    "scripts/qwencloud-render-alibaba-proof-video.ps1",
    "scripts/qwencloud-validate-alibaba-proof.ps1",
    "scripts/qwencloud-export-architecture-png.ps1",
    "scripts/qwencloud-export-video-thumbnail.ps1",
    "scripts/qwencloud-finalize-after-urls.ps1",
    "scripts/qwencloud-deploy-preflight.ps1",
    "scripts/qwencloud-final-readiness.ps1",
    "scripts/qwencloud-final-upload-bundle.ps1",
    "scripts/qwencloud-judge-rehearsal.ps1",
    "scripts/qwencloud-final-external-handoff.ps1",
    "scripts/qwencloud-devpost-draft-payload.ps1",
    "scripts/qwencloud-devpost-autofill-snippet.ps1",
    "scripts/qwencloud-judging-scorecard.ps1",
    "scripts/qwencloud-official-rules-gate.ps1",
    "scripts/qwencloud-official-source-refresh.ps1",
    "scripts/qwencloud-video-publication-handoff.ps1",
    "scripts/qwencloud-hackathon-audit.ps1",
    "scripts/qwencloud-hackathon-proof.ps1",
    "scripts/qwencloud-run-local-proof.ps1",
    "scripts/qwencloud-run-local-proof.sh",
    "scripts/qwencloud-hackathon-submit-gate.ps1",
    "scripts/qwencloud-hackathon-verify.ps1",
    "scripts/qwencloud-frontend-build-proof.ps1",
    "scripts/qwencloud-render-demo-video.ps1"
)

foreach ($path in $requiredPaths) {
    Add-Check -Name "required_path.$path" -Ok (Test-Path $path) -Details $path
}

try {
    $gitStatus = git status --porcelain
    Add-Check -Name "git_worktree_clean" -Ok ($gitStatus.Count -eq 0) -Details $(if ($gitStatus.Count -eq 0) { "clean" } else { "dirty" })
}
catch {
    Add-Check -Name "git_worktree_clean" -Ok $false -Details $_.Exception.Message
}

Add-Check -Name "repo_url_present" -Ok (Is-HttpUrl $repoUsed) -Details $repoUsed
$repoCheck = Test-PublicGitHubRepo -Url $repoUsed
Add-Check -Name "repo_public_github" -Ok $repoCheck.ok -Details $repoCheck.details
Add-Check -Name "license_apache_2_detected" -Ok ($repoCheck.license -eq "Apache-2.0" -or ((Test-Path "LICENSE") -and ((Get-Content "LICENSE" -Raw) -match "Apache License"))) -Details $(if ($repoCheck.license) { $repoCheck.license } else { "local LICENSE fallback" })

$architectureAsset = Test-UploadAsset -Path $ArchitectureUploadPath -Extensions @(".png", ".jpg", ".jpeg", ".pdf") -MaxMb 35
Add-Check -Name "devpost_architecture_upload_asset" -Ok $architectureAsset.ok -Details $architectureAsset.details
$architectureDims = Get-PngDimensions -Path $ArchitectureUploadPath
Add-Check -Name "architecture_png_dimensions" -Ok ($architectureDims -and $architectureDims.width -ge 1000 -and $architectureDims.height -ge 600) -Details $(if ($architectureDims) { "$($architectureDims.width)x$($architectureDims.height)" } else { "not a readable PNG" })

$alibabaScreenshotAsset = Test-UploadAsset -Path $AlibabaScreenshotPath -Extensions @(".png", ".jpg", ".jpeg") -MaxMb 35
Add-Check -Name "devpost_alibaba_deployment_screenshot" -Ok $alibabaScreenshotAsset.ok -Details $alibabaScreenshotAsset.details
if (Test-Path $AlibabaScreenshotPath) {
    $alibabaScreenshotDims = Get-PngDimensions -Path $AlibabaScreenshotPath
    Add-Check -Name "alibaba_screenshot_png_dimensions" -Ok ($null -ne $alibabaScreenshotDims) -Details $(if ($alibabaScreenshotDims) { "$($alibabaScreenshotDims.width)x$($alibabaScreenshotDims.height)" } else { "not a readable PNG" }) -Required $false
}

$alibabaProofVideoAsset = Test-UploadAsset -Path $AlibabaProofVideoPath -Extensions @(".mp4", ".mov") -MaxMb 100
Add-Check -Name "devpost_alibaba_deployment_proof_video" -Ok $alibabaProofVideoAsset.ok -Details $alibabaProofVideoAsset.details
$alibabaProofVideoMetadata = Get-VideoMetadata -Path $AlibabaProofVideoPath
if ($alibabaProofVideoMetadata) {
    Add-Check -Name "alibaba_proof_video_duration" -Ok ($alibabaProofVideoMetadata.duration -gt 0 -and $alibabaProofVideoMetadata.duration -le 60) -Details "duration=$($alibabaProofVideoMetadata.duration); size=$($alibabaProofVideoMetadata.size); format=$($alibabaProofVideoMetadata.format)"
    Add-Check -Name "alibaba_proof_video_resolution" -Ok ($alibabaProofVideoMetadata.width -ge 1280 -and $alibabaProofVideoMetadata.height -ge 720) -Details "$($alibabaProofVideoMetadata.width)x$($alibabaProofVideoMetadata.height); codec=$($alibabaProofVideoMetadata.codec)"
}
else {
    Add-Check -Name "alibaba_proof_video_duration" -Ok $false -Details "ffprobe unavailable or proof video missing"
    Add-Check -Name "alibaba_proof_video_resolution" -Ok $false -Details "ffprobe unavailable or proof video missing"
}

$alibabaProofIntegrity = Invoke-AlibabaProofIntegrity
Add-Check -Name "alibaba_proof_integrity_ready" -Ok $alibabaProofIntegrity.ok -Details $alibabaProofIntegrity.details

$videoExists = Test-Path $LocalVideoPath
Add-Check -Name "local_video_exists" -Ok $videoExists -Details $LocalVideoPath -Required $false
$videoMetadata = Get-VideoMetadata -Path $LocalVideoPath
if ($videoMetadata) {
    Add-Check -Name "local_video_under_3_minutes" -Ok ($videoMetadata.duration -gt 0 -and $videoMetadata.duration -lt 180) -Details "duration=$($videoMetadata.duration); size=$($videoMetadata.size); format=$($videoMetadata.format)" -Required $false
    Add-Check -Name "local_video_minimum_resolution" -Ok ($videoMetadata.width -ge 1280 -and $videoMetadata.height -ge 720) -Details "$($videoMetadata.width)x$($videoMetadata.height); codec=$($videoMetadata.codec)" -Required $false
}
else {
    Add-Check -Name "local_video_under_3_minutes" -Ok $false -Details "ffprobe unavailable or video missing" -Required $false
    Add-Check -Name "local_video_minimum_resolution" -Ok $false -Details "ffprobe unavailable or video missing" -Required $false
}

$demoVideoUrlOk = Is-PublicVideoUrl $DemoVideoUrl
Add-Check -Name "demo_video_public_url" -Ok $demoVideoUrlOk -Details $(if ($DemoVideoUrl) { $DemoVideoUrl } else { "missing" })
if ($demoVideoUrlOk) {
    if ($SkipExternalUrlChecks) {
        Add-Check -Name "demo_video_public_url_reachable" -Ok $true -Details "skipped by -SkipExternalUrlChecks" -Required $false
    }
    else {
        $videoReachable = Test-HttpReachable -Url $DemoVideoUrl
        Add-Check -Name "demo_video_public_url_reachable" -Ok $videoReachable.ok -Details $videoReachable.details
    }
}

Add-Check -Name "backend_url_present" -Ok (Is-HttpUrl $BackendUrl) -Details $(if ($BackendUrl) { $BackendUrl } else { "missing deployed or test backend URL" })

if (Is-HttpUrl $BackendUrl) {
    try {
        $base = $BackendUrl.TrimEnd("/")
        $health = Invoke-RestMethod -Uri "$base/health" -TimeoutSec 20
        Add-Check -Name "backend_health_reachable" -Ok ($health.status -eq "ok") -Details "status=$($health.status)"
        Add-Check -Name "backend_track" -Ok ($health.track -eq $track) -Details "track=$($health.track)"
        Add-Check -Name "backend_provider" -Ok ($health.llm_provider -eq "qwen-cloud") -Details "llm_provider=$($health.llm_provider)"
        Add-Check -Name "backend_proof_file" -Ok ($health.proof_file -eq "deploy/alibaba/serverless-devs.yaml") -Details "proof_file=$($health.proof_file)"

        if ($SkipBackendDraft) {
            Add-Check -Name "backend_draft_response" -Ok $true -Details "skipped" -Required $false
        }
        else {
            $draftBody = @{
                team_id = "demo_team"
                rough_business_request = "Users need to know why a forecast job is stuck running"
                llm_provider = "qwen-cloud"
            } | ConvertTo-Json
            $draft = Invoke-RestMethod -Method Post -Uri "$base/requirements/draft" -Body $draftBody -ContentType "application/json" -TimeoutSec 45
            Add-Check -Name "backend_draft_response" -Ok ($null -ne $draft.markdown -and $draft.markdown.Length -gt 0) -Details $(if ($draft.run_id) { "run_id=$($draft.run_id)" } else { "markdown returned" })
        }
    }
    catch {
        Add-Check -Name "backend_health_reachable" -Ok $false -Details $_.Exception.Message
        Add-Check -Name "backend_track" -Ok $false -Details "backend check failed"
        Add-Check -Name "backend_provider" -Ok $false -Details "backend check failed"
        Add-Check -Name "backend_proof_file" -Ok $false -Details "backend check failed"
        Add-Check -Name "backend_draft_response" -Ok $false -Details "backend check failed"
    }
}
else {
    Add-Check -Name "backend_health_reachable" -Ok $false -Details "BackendUrl missing"
    Add-Check -Name "backend_track" -Ok $false -Details "BackendUrl missing"
    Add-Check -Name "backend_provider" -Ok $false -Details "BackendUrl missing"
    Add-Check -Name "backend_proof_file" -Ok $false -Details "BackendUrl missing"
    Add-Check -Name "backend_draft_response" -Ok $false -Details "BackendUrl missing"
}

$blogUrlOk = [string]::IsNullOrWhiteSpace($BlogPostUrl) -or (Is-HttpUrl $BlogPostUrl)
Add-Check -Name "blog_post_url_optional" -Ok $blogUrlOk -Details $(if ($BlogPostUrl) { $BlogPostUrl } else { "not provided" }) -Required $false
if (-not [string]::IsNullOrWhiteSpace($BlogPostUrl) -and $blogUrlOk -and -not $SkipExternalUrlChecks) {
    $blogReachable = Test-HttpReachable -Url $BlogPostUrl
    Add-Check -Name "blog_post_url_reachable_optional" -Ok $blogReachable.ok -Details $blogReachable.details -Required $false
}

$packet = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    readyForDevpost = $ready
    allowDraft = [bool]$AllowDraft
    project = [ordered]@{
        title = $projectTitle
        track = $track
        repoUrl = $repoUsed
        demoVideoUrl = $DemoVideoUrl
        backendUrl = $BackendUrl
        blogPostUrl = $BlogPostUrl
    }
    uploadAssets = [ordered]@{
        architectureDiagram = $ArchitectureUploadPath
        alibabaDeploymentScreenshot = $AlibabaScreenshotPath
        alibabaDeploymentProofVideo = $AlibabaProofVideoPath
        localDemoVideo = $LocalVideoPath
    }
    devpostAdditionalInfo = [ordered]@{
        submitterType = "Individual"
        countryOfResidence = "United States"
        projectStatus = "New"
        projectStartDate = "06-21-26"
        beforeMay26UpdateExplanation = "Not applicable. The public DREAM memory platform release started on 06-21-26; Qwen Cloud Track 1 integration, Alibaba packaging, CI audit, architecture assets, and demo/submission materials were added during the hackathon submission period."
        selectedTrack = $track
        repositoryUrl = $repoUsed
        alibabaProofCodeFile = $deploymentProofUrl
        aiToolsUsed = "Qwen Cloud for the runtime LLM provider, OpenAI Codex for implementation assistance, GitHub Actions for CI verification, and local automation scripts for audit, render, deploy preflight, and submission packet generation."
        learningLevel = "Significant"
    }
    links = [ordered]@{
        license = $licenseUrl
        architectureSvg = $architectureSvgUrl
        architecturePng = $architecturePngUrl
        deploymentProof = $deploymentProofUrl
        deployPreflight = $deployPreflightUrl
        qwenConfig = $qwenConfigUrl
        buildJourneyDraft = $buildJourneyDraftUrl
        testingAndRightsNotes = $testingAndRightsNotesUrl
        devpostAutofillSnippetScript = $devpostAutofillSnippetScriptUrl
        judgingScorecardScript = $judgingScorecardScriptUrl
        officialRulesGateScript = $officialRulesGateScriptUrl
        ci = $ciUrl
    }
    checks = $checks
}

Set-Content -Path $packetJson -Value ($packet | ConvertTo-Json -Depth 12) -Encoding UTF8

$statusWord = if ($ready) { "READY" } else { "DRAFT - missing required external URLs or backend proof" }
$videoLine = if ($DemoVideoUrl) { $DemoVideoUrl } else { "<paste public YouTube/Vimeo/Facebook Video/Youku URL>" }
$backendLine = if ($BackendUrl) { $BackendUrl } else { "<paste Alibaba Function Compute backend URL>" }
$blogLine = if ($BlogPostUrl) { $BlogPostUrl } else { "<optional public blog/social post URL>" }

$md = @(
    "# DREAM Qwen Cloud Devpost Submission Packet ($timestamp)",
    "",
    "- Status: $statusWord",
    "- Project: $projectTitle",
    "- Track: $track",
    "- Repo: $repoUsed",
    "- Demo video: $videoLine",
    "- Testing backend: $backendLine",
    "- Optional blog/social post: $blogLine",
    "- Architecture upload file: $ArchitectureUploadPath",
    "- Alibaba deployment screenshot file: $AlibabaScreenshotPath",
    "- Alibaba deployment proof video file: $AlibabaProofVideoPath",
    "",
    "## Required Links",
    "",
    "- Source code: $repoUsed",
    "- License: $licenseUrl",
    "- Architecture diagram (SVG): $architectureSvgUrl",
    "- Architecture diagram (PNG upload asset): $architecturePngUrl",
    "- Alibaba Cloud deployment proof: $deploymentProofUrl",
    "- Deploy preflight script: $deployPreflightUrl",
    "- Qwen mode config: $qwenConfigUrl",
    "- Testing and rights notes: $testingAndRightsNotesUrl",
    "- Devpost autofill snippet generator: $devpostAutofillSnippetScriptUrl",
    "- Judging scorecard generator: $judgingScorecardScriptUrl",
    "- Official rules gate: $officialRulesGateScriptUrl",
    "- Blog/social build journey draft: $buildJourneyDraftUrl",
    "- CI proof: $ciUrl",
    "",
    "## Copy To Devpost",
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
    "DREAM is a Qwen Cloud MemoryAgent for source-backed engineering intelligence. It turns docs, codebase structure, incidents, Jira and PR history, and reviewed memory claims into durable, auditable context for requirement drafting and review workflows.",
    "",
    "### Description",
    "",
    "Engineering teams lose critical context across tickets, code, incidents, runbooks, and review decisions. DREAM makes that context persistent and governed. It loads knowledge packs, indexes local codebases, distills reviewable memory claims, retrieves source-backed context, and uses Qwen Cloud through an OpenAI-compatible provider to produce traceable requirement and review outputs.",
    "",
    "The system is built as a production-minded Track 1 MemoryAgent: memory can be promoted, rejected, audited, evaluated, and reused across workflows. The public health endpoint exposes runtime proof such as Track 1, qwen-cloud provider, model, deployment target, region, and the Alibaba Cloud proof file path without exposing secrets.",
    "",
    "### Judging alignment",
    "",
    "- Innovation and AI Creativity: Qwen Cloud is used inside a governed memory workflow with claim distillation, source-backed retrieval, requirement drafting, audit/eval feedback, and human review loops.",
    "- Technical Depth and Engineering: DREAM includes provider abstraction, API/CLI surfaces, Docker packaging, Alibaba Function Compute deployment, architecture assets, CI, release workflow, proof automation, and final readiness gates.",
    "- Problem Value and Impact: the product solves a real engineering pain point: lost context across Jira, code, incidents, runbooks, and PR history, turning it into reusable auditable memory.",
    "- Presentation and Documentation: the repo includes architecture diagrams, generated demo/proof videos, deployment proof, field-level Devpost payloads, judging scorecard, and a final upload bundle.",
    "",
    "### Built with",
    "",
    "Qwen Cloud, Alibaba Cloud Function Compute, FastAPI, Typer, Angular, Docker, SQLite, Python, TypeScript.",
    "",
    "## Devpost Additional Info",
    "",
    "- Submitter type: Individual",
    "- Country of residence: United States",
    "- Newly built or existing project: New",
    "- Project start date: 06-21-26",
    "- If started/existed before May 26: Not applicable. The public DREAM memory platform release started on 06-21-26; Qwen Cloud Track 1 integration, Alibaba packaging, CI audit, architecture assets, and demo/submission materials were added during the hackathon submission period.",
    "- Track: $track",
    "- Code repository URL: $repoUsed",
    "- Alibaba Cloud deployment proof code file: $deploymentProofUrl",
    "- Architecture diagram file upload: $ArchitectureUploadPath",
    "- Alibaba deployment screenshot upload: $AlibabaScreenshotPath",
    "- Alibaba deployment proof video: $AlibabaProofVideoPath",
    "- Blog/social URL: $blogLine",
    "- AI tools leveraged: Qwen Cloud for the runtime LLM provider, OpenAI Codex for implementation assistance, GitHub Actions for CI verification, and local automation scripts for audit, render, deploy preflight, and submission packet generation.",
    "- Learning level: Significant",
    "",
    "### Testing instructions",
    "",
    "Use the deployed backend URL if available: $backendLine",
    "",
    '```powershell',
    'git clone https://github.com/zemeng2015/dream-ai-engineering-copilot.git',
    'cd dream-ai-engineering-copilot',
    'python -m venv .venv',
    '.\.venv\Scripts\Activate.ps1',
    'pip install -e ".[dev]"',
    '$env:DREAM_CONFIG_FILE="examples/config/dream.qwen.yaml"',
    '$env:DASHSCOPE_API_KEY="<judge-provided-or-owner-configured-key>"',
    '$env:QWEN_BASE_URL="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"',
    'uvicorn dream.api.app:app --host 127.0.0.1 --port 8000',
    'scripts/qwencloud-hackathon-verify.ps1 -BaseUrl http://127.0.0.1:8000',
    '```',
    "",
    "Linux/macOS Bash quick proof:",
    "",
    '```bash',
    'bash scripts/qwencloud-run-local-proof.sh --skip-draft',
    '```',
    "",
    "### Deployment proof",
    "",
    "The backend is packaged for Alibaba Cloud Function Compute as a custom container. The proof file is $deploymentProofUrl, and deploy readiness can be reproduced with:",
    "",
    '```powershell',
    'scripts/qwencloud-deploy-preflight.ps1 -EnvFile .env.qwencloud.local -BuildImage -SmokeContainer -AllowDraft',
    '```',
    "",
    "## Packet Checks",
    "",
    "| Check | Required | Result | Details |",
    "|---|---:|---:|---|"
)

foreach ($check in $checks) {
    $result = if ($check.ok) { "PASS" } else { "FAIL" }
    $required = if ($check.required) { "yes" } else { "no" }
    $details = ($check.details -replace "\|", "/")
    $md += "| $($check.name) | $required | $result | $details |"
}

$md += @(
    "",
    "## Final External Steps",
    "",
    "- Configure Alibaba access with `s config add`.",
    "- Generate `scripts/qwencloud-cloud-credentials-handoff.ps1 -EnvFile .env.qwencloud.local -AllowDraft` for the local credential/setup template.",
    "- Fill `.env.qwencloud.local` with `DASHSCOPE_API_KEY`, `ALIBABA_CLOUD_REGION`, and `ALIBABA_CLOUD_CONTAINER_IMAGE`.",
    "- Push the container image and run `s deploy -t deploy/alibaba/serverless-devs.yaml -y`.",
    "- Capture and save the required Alibaba deployment screenshot as `$AlibabaScreenshotPath`.",
    "- Render the separate Alibaba deployment proof recording as `$AlibabaProofVideoPath`.",
    "- Upload `artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4` using `docs/qwencloud-video-upload-handoff.md`, then paste the public YouTube, Vimeo, Facebook Video, or Youku URL.",
    "- Generate `scripts/qwencloud-devpost-handoff.ps1 -AllowDraft` for one local HTML page with final copy fields and upload paths.",
    "- Run `scripts/qwencloud-finalize-after-urls.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl <url> -BackendUrl <url> -RefreshAlibabaProof` as the final one-command gate before submitting Devpost.",
    "- Publish `docs/qwencloud-build-journey-post.md` if pursuing the optional blog/social bonus, then pass `-BlogPostUrl`.",
    "- Paste this packet into Devpost and submit before the deadline."
)

Set-Content -Path $packetMd -Value ($md -join "`r`n") -Encoding UTF8

if ($ready) {
    Write-Host "Devpost submission packet READY: $packetMd"
    Write-Host "JSON: $packetJson"
}
else {
    Write-Host "Devpost submission packet DRAFT: $packetMd" -ForegroundColor Yellow
    Write-Host "JSON: $packetJson"
    if (-not $AllowDraft) {
        exit 1
    }
}
