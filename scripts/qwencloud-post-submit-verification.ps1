# SPDX-License-Identifier: Apache-2.0

param(
    [Parameter(Mandatory = $false)]
    [string]$DevpostProjectUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$DevpostHtmlPath = "",
    [Parameter(Mandatory = $false)]
    [string]$RepoUrl = "https://github.com/zemeng2015/dream-ai-engineering-copilot",
    [Parameter(Mandatory = $false)]
    [string]$DemoVideoUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$BackendUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [string]$FinalBundleManifest = "",
    [Parameter(Mandatory = $false)]
    [string]$RunsJsonPath = "",
    [Parameter(Mandatory = $false)]
    [string]$RepoJsonPath = "",
    [Parameter(Mandatory = $false)]
    [string]$GitHead = "",
    [Parameter(Mandatory = $false)]
    [string]$ExpectedTitle = "DREAM",
    [Parameter(Mandatory = $false)]
    [string]$ExpectedTrack = "Track 1: MemoryAgent",
    [Parameter(Mandatory = $false)]
    [string]$AlibabaScreenshotPath = "artifacts/qwencloud-proof/alibaba-deployment-screenshot.png",
    [Parameter(Mandatory = $false)]
    [string]$AlibabaProofVideoPath = "artifacts/qwencloud-proof/alibaba-deployment-proof.mp4",
    [switch]$SkipExternalUrlChecks,
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
. (Join-Path $PSScriptRoot "qwencloud-devpost-video-url.ps1")

$reportJson = Join-Path $OutputDir "devpost-post-submit-verification-$timestamp.json"
$reportMd = Join-Path $OutputDir "devpost-post-submit-verification-$timestamp.md"
$checks = @()

function Add-Check([string]$Name, [bool]$Ok, [string]$Details, [bool]$Required = $true) {
    $script:checks += [ordered]@{
        name = $Name
        ok = $Ok
        required = $Required
        details = $Details
    }
}

function Has-Command([string]$Name) {
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Invoke-GitText([string[]]$Arguments) {
    try {
        $output = & git @Arguments 2>$null
        if ($LASTEXITCODE -ne 0) {
            return ""
        }

        return (($output | Out-String).Trim())
    }
    catch {
        return ""
    }
}

function Read-JsonPath([string]$Path) {
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function ConvertTo-FlatArray([AllowNull()][object]$Value) {
    $items = @()
    foreach ($item in @($Value)) {
        if ($item -is [System.Array]) {
            foreach ($nestedItem in $item) {
                $items += $nestedItem
            }
        }
        else {
            $items += $item
        }
    }

    return $items
}

function Get-RepoName([string]$Url) {
    if ($Url -match "^https://github.com/(?<owner>[^/]+)/(?<repo>[^/]+?)(\.git)?$") {
        return "$($matches.owner)/$($matches.repo)"
    }
    return ""
}

function Get-LocalHead {
    if (-not [string]::IsNullOrWhiteSpace($GitHead)) {
        return $GitHead
    }

    $gitHead = Invoke-GitText -Arguments @("rev-parse", "HEAD")
    if (-not [string]::IsNullOrWhiteSpace($gitHead)) {
        return $gitHead
    }

    try {
        $manifestPath = Get-LatestFinalBundleManifest -ExplicitPath $FinalBundleManifest
        if (-not [string]::IsNullOrWhiteSpace($manifestPath) -and (Test-Path -LiteralPath $manifestPath)) {
            $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
            if (-not [string]::IsNullOrWhiteSpace([string]$manifest.gitCommit)) {
                return [string]$manifest.gitCommit
            }
        }
    }
    catch {
        return ""
    }

    return ""
}

function Is-HttpUrl([string]$Url) {
    return -not [string]::IsNullOrWhiteSpace($Url) -and $Url -match "^https?://" -and $Url -notmatch "[<>]|\.\.\."
}

function Is-DevpostProjectUrl([string]$Url) {
    return (Is-HttpUrl $Url) -and $Url -match "^https://devpost\.com/software/[^/?#]+"
}

function Is-DevpostVideoUrl([string]$Url) {
    return Test-QwenCloudDevpostVideoUrl -Url $Url
}

function Is-TrueBoolean($Value) {
    return ([string]$Value).ToLowerInvariant() -eq "true"
}

function Test-TextContains([string]$Text, [string]$Needle) {
    if ([string]::IsNullOrWhiteSpace($Text) -or [string]::IsNullOrWhiteSpace($Needle)) {
        return $false
    }

    return $Text.IndexOf($Needle, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
}

function Get-UrlHostToken([string]$Url) {
    try {
        return ([System.Uri]$Url).Host.ToLowerInvariant() -replace "^www\.", ""
    }
    catch {
        return ""
    }
}

function Get-VideoUrlToken([string]$Url) {
    if ($Url -match "youtu\.be/(?<id>[A-Za-z0-9_-]{6,})") {
        return $matches.id
    }
    if ($Url -match "youtube\.com/(?:watch\?[^#]*v=|embed/|shorts/)(?<id>[A-Za-z0-9_-]{6,})") {
        return $matches.id
    }
    if ($Url -match "vimeo\.com/(?:video/)?(?<id>[0-9]+)") {
        return $matches.id
    }
    if ($Url -match "facebook\.com/.*/videos/(?<id>[0-9]+)") {
        return $matches.id
    }
    if ($Url -match "facebook\.com/watch/\?v=(?<id>[0-9]+)") {
        return $matches.id
    }
    if ($Url -match "youku\.com/(?:v_show/)?id_(?<id>[A-Za-z0-9=_-]+)") {
        return $matches.id
    }

    return ""
}

function Test-DevpostRepoMention([string]$Content, [string]$RepoUrlValue, [string]$RepoNameValue) {
    $exactUrl = Test-TextContains -Text $Content -Needle $RepoUrlValue
    $repoNameMention = Test-TextContains -Text $Content -Needle $RepoNameValue
    return [pscustomobject]@{
        ok = ($exactUrl -or $repoNameMention)
        details = "repoUrl=$exactUrl; repoName=$repoNameMention"
    }
}

function Test-DevpostVideoMention([string]$Content, [string]$VideoUrlValue) {
    if (-not (Is-DevpostVideoUrl $VideoUrlValue)) {
        return [pscustomobject]@{ ok = $false; details = "DemoVideoUrl missing or not $script:QwenCloudDevpostVideoPlatformLabel" }
    }

    $exactUrl = Test-TextContains -Text $Content -Needle $VideoUrlValue
    $videoHost = Get-UrlHostToken -Url $VideoUrlValue
    $videoToken = Get-VideoUrlToken -Url $VideoUrlValue
    $hostCandidates = @($videoHost)
    if ($videoHost -match "youtube" -or $videoHost -eq "youtu.be") {
        $hostCandidates += @("youtube.com", "youtu.be", "youtube-nocookie.com")
    }
    elseif ($videoHost -match "facebook") {
        $hostCandidates += @("facebook.com", "fb.watch")
    }

    $hostMention = $false
    foreach ($candidate in @($hostCandidates | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)) {
        if (Test-TextContains -Text $Content -Needle $candidate) {
            $hostMention = $true
            break
        }
    }

    $tokenMention = if ([string]::IsNullOrWhiteSpace($videoToken)) { $true } else { Test-TextContains -Text $Content -Needle $videoToken }
    return [pscustomobject]@{
        ok = ($exactUrl -or ($hostMention -and $tokenMention))
        details = "exactUrl=$exactUrl; host=$videoHost; hostMention=$hostMention; videoToken=$(if ($videoToken) { $videoToken } else { '<none>' }); tokenMention=$tokenMention"
    }
}

function Test-Url {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $false)][string]$Method = "Get"
    )

    if (-not (Is-HttpUrl $Url)) {
        return [pscustomobject]@{ ok = $false; status = 0; content = ""; details = "not an http(s) URL" }
    }
    if ($SkipExternalUrlChecks) {
        return [pscustomobject]@{ ok = $true; status = 0; content = ""; details = "skipped by -SkipExternalUrlChecks" }
    }

    try {
        $response = Invoke-WebRequest -Method $Method -Uri $Url -MaximumRedirection 5 -TimeoutSec 25 -ErrorAction Stop
        return [pscustomobject]@{
            ok = ([int]$response.StatusCode -ge 200 -and [int]$response.StatusCode -lt 400)
            status = [int]$response.StatusCode
            content = [string]$response.Content
            details = "$Method status=$([int]$response.StatusCode)"
        }
    }
    catch {
        return [pscustomobject]@{ ok = $false; status = 0; content = ""; details = $_.Exception.Message }
    }
}

function Get-DevpostProjectResponse([string]$Url) {
    if (-not [string]::IsNullOrWhiteSpace($DevpostHtmlPath)) {
        if (-not (Test-Path -LiteralPath $DevpostHtmlPath)) {
            return [pscustomobject]@{ ok = $false; status = 0; content = ""; details = "DevpostHtmlPath missing: $DevpostHtmlPath" }
        }

        $content = Get-Content -LiteralPath $DevpostHtmlPath -Raw
        return [pscustomobject]@{
            ok = $true
            status = 0
            content = [string]$content
            details = "fixture=$DevpostHtmlPath"
        }
    }

    return Test-Url -Url $Url -Method "Get"
}

function Get-GitHubRepoMetadata([string]$RepoName) {
    if (-not [string]::IsNullOrWhiteSpace($RepoJsonPath)) {
        return Read-JsonPath -Path $RepoJsonPath
    }

    if ([string]::IsNullOrWhiteSpace($RepoName)) {
        return $null
    }

    try {
        return Invoke-RestMethod `
            -Uri "https://api.github.com/repos/$RepoName" `
            -UserAgent "dream-qwencloud-post-submit-verification/1.0" `
            -TimeoutSec 25
    }
    catch {
        return $null
    }
}

function Test-File([string]$Path, [int]$MinBytes = 1) {
    if (-not (Test-Path $Path)) {
        return [pscustomobject]@{ ok = $false; details = "missing: $Path" }
    }
    $item = Get-Item -LiteralPath $Path
    return [pscustomobject]@{
        ok = $item.Length -ge $MinBytes
        details = "path=$Path; size=$($item.Length)"
    }
}

function Get-PngDimensions([string]$Path) {
    if (-not (Test-Path $Path)) { return $null }
    $bytes = [System.IO.File]::ReadAllBytes((Resolve-Path $Path))
    if ($bytes.Length -lt 24) { return $null }

    $signature = @(137, 80, 78, 71, 13, 10, 26, 10)
    for ($i = 0; $i -lt $signature.Count; $i++) {
        if ([int]$bytes[$i] -ne $signature[$i]) { return $null }
    }

    return [pscustomobject]@{
        width = ([int]$bytes[16] -shl 24) -bor ([int]$bytes[17] -shl 16) -bor ([int]$bytes[18] -shl 8) -bor [int]$bytes[19]
        height = ([int]$bytes[20] -shl 24) -bor ([int]$bytes[21] -shl 16) -bor ([int]$bytes[22] -shl 8) -bor [int]$bytes[23]
    }
}

function Test-HeadCiSuccess {
    if ([string]::IsNullOrWhiteSpace($RunsJsonPath) -and -not (Has-Command "gh")) {
        return [pscustomobject]@{ ok = $false; details = "gh command missing" }
    }

    try {
        $repoName = Get-RepoName -Url $RepoUrl
        if ([string]::IsNullOrWhiteSpace($repoName) -and [string]::IsNullOrWhiteSpace($RunsJsonPath)) {
            return [pscustomobject]@{ ok = $false; details = "RepoUrl is not a normalized GitHub HTTPS URL: $RepoUrl" }
        }

        $head = Get-LocalHead
        if ([string]::IsNullOrWhiteSpace($head)) {
            return [pscustomobject]@{ ok = $false; details = "git HEAD unavailable" }
        }

        $runs = if (-not [string]::IsNullOrWhiteSpace($RunsJsonPath)) {
            ConvertTo-FlatArray -Value (Read-JsonPath -Path $RunsJsonPath)
        }
        else {
            $runsJson = gh run list --repo $repoName --branch main --limit 10 --json databaseId,headSha,status,conclusion,url,displayTitle,createdAt,updatedAt
            ConvertTo-FlatArray -Value ($runsJson | ConvertFrom-Json)
        }
        $matchingRuns = @(
            $runs |
                Where-Object { $_.headSha -eq $head } |
                Sort-Object -Property @(
                    @{ Expression = {
                            $runDate = if ($_.createdAt) { $_.createdAt } elseif ($_.updatedAt) { $_.updatedAt } else { "" }
                            try { [DateTimeOffset]::Parse([string]$runDate).UtcDateTime } catch { [datetime]::MinValue }
                        }; Descending = $true
                    },
                    @{ Expression = {
                            try { [int64]$_.databaseId } catch { 0 }
                        }; Descending = $true
                    }
                )
        )
        $run = if ($matchingRuns.Count -gt 0) { $matchingRuns[0] } else { $null }
        if (-not $run) {
            return [pscustomobject]@{ ok = $false; details = "no CI run found for HEAD $head" }
        }

        return [pscustomobject]@{
            ok = ($run.status -eq "completed" -and $run.conclusion -eq "success")
            details = "run=$($run.databaseId); $($run.displayTitle); status=$($run.status); conclusion=$($run.conclusion); $($run.url)"
        }
    }
    catch {
        return [pscustomobject]@{ ok = $false; details = $_.Exception.Message }
    }
}

function Get-LatestFinalBundleManifest([string]$ExplicitPath) {
    if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
        return $ExplicitPath
    }

    $candidate = Get-ChildItem -LiteralPath $OutputDir -Filter "final-upload-bundle-*" -Directory -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        ForEach-Object {
            $manifest = Join-Path $_.FullName "manifest.json"
            if (Test-Path -LiteralPath $manifest) { Get-Item -LiteralPath $manifest }
        } |
        Select-Object -First 1

    if ($candidate) { return $candidate.FullName }
    return ""
}

function Get-VideoMetadata([string]$Path) {
    if (-not (Test-Path $Path)) { return $null }
    if (-not (Get-Command "ffprobe" -ErrorAction SilentlyContinue)) { return $null }

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

$headCommit = Get-LocalHead
$repoName = Get-RepoName -Url $RepoUrl
$headCi = Test-HeadCiSuccess
Add-Check -Name "latest_head_ci_success" -Ok $headCi.ok -Details $headCi.details

$bundleManifestPath = Get-LatestFinalBundleManifest -ExplicitPath $FinalBundleManifest
Add-Check -Name "final_bundle_manifest_present" -Ok (-not [string]::IsNullOrWhiteSpace($bundleManifestPath) -and (Test-Path -LiteralPath $bundleManifestPath)) -Details $(if ($bundleManifestPath) { $bundleManifestPath } else { "missing final-upload-bundle-*/manifest.json" })
if (-not [string]::IsNullOrWhiteSpace($bundleManifestPath) -and (Test-Path -LiteralPath $bundleManifestPath)) {
    try {
        $bundle = Get-Content -LiteralPath $bundleManifestPath -Raw | ConvertFrom-Json
        $bundleZipPath = [string]$bundle.zipPath
        Add-Check -Name "final_bundle_ready_for_upload" -Ok ([bool]$bundle.readyForUpload) -Details "readyForUpload=$($bundle.readyForUpload)"
        Add-Check -Name "final_bundle_git_commit_matches_head" -Ok (-not [string]::IsNullOrWhiteSpace($headCommit) -and [string]$bundle.gitCommit -eq $headCommit) -Details "bundle=$($bundle.gitCommit); head=$headCommit"
        Add-Check -Name "final_bundle_worktree_clean" -Ok ([bool]$bundle.gitWorktreeClean) -Details "gitWorktreeClean=$($bundle.gitWorktreeClean)"
        Add-Check -Name "final_bundle_remote_synced" -Ok ([bool]$bundle.gitRemoteSynced) -Details "gitRemoteSynced=$($bundle.gitRemoteSynced)"
        Add-Check -Name "final_bundle_zip_exists" -Ok (-not [string]::IsNullOrWhiteSpace($bundleZipPath) -and (Test-Path -LiteralPath $bundleZipPath)) -Details $(if ($bundleZipPath) { $bundleZipPath } else { "missing zipPath" })

        $itemNames = @($bundle.items | ForEach-Object { [string]$_.name })
        foreach ($name in @(
            "devpost_packet_markdown",
            "devpost_handoff_html",
            "official_rules_gate_json",
            "local_demo_video_for_public_upload",
            "alibaba_deployment_screenshot",
            "alibaba_backend_proof_recording"
        )) {
            Add-Check -Name "final_bundle_item.$name" -Ok ($itemNames -contains $name) -Details $(if ($itemNames -contains $name) { "present" } else { "missing" })
        }
    }
    catch {
        Add-Check -Name "final_bundle_manifest_parseable" -Ok $false -Details $_.Exception.Message
    }
}
else {
    foreach ($name in @(
        "final_bundle_ready_for_upload",
        "final_bundle_git_commit_matches_head",
        "final_bundle_worktree_clean",
        "final_bundle_remote_synced",
        "final_bundle_zip_exists",
        "final_bundle_item.devpost_packet_markdown",
        "final_bundle_item.devpost_handoff_html",
        "final_bundle_item.official_rules_gate_json",
        "final_bundle_item.local_demo_video_for_public_upload",
        "final_bundle_item.alibaba_deployment_screenshot",
        "final_bundle_item.alibaba_backend_proof_recording"
    )) {
        Add-Check -Name $name -Ok $false -Details "final bundle manifest missing"
    }
}

Add-Check -Name "devpost_public_project_url_present" -Ok (Is-DevpostProjectUrl $DevpostProjectUrl) -Details $(if ($DevpostProjectUrl) { $DevpostProjectUrl } else { "missing" })
if (Is-DevpostProjectUrl $DevpostProjectUrl) {
    $devpost = Get-DevpostProjectResponse -Url $DevpostProjectUrl
    Add-Check -Name "devpost_public_project_reachable" -Ok $devpost.ok -Details $devpost.details
    if ($SkipExternalUrlChecks -and [string]::IsNullOrWhiteSpace($DevpostHtmlPath)) {
        Add-Check -Name "devpost_public_project_mentions_dream" -Ok $true -Details "skipped by -SkipExternalUrlChecks" -Required $false
        Add-Check -Name "devpost_public_project_mentions_qwen" -Ok $true -Details "skipped by -SkipExternalUrlChecks" -Required $false
        Add-Check -Name "devpost_public_project_mentions_repo" -Ok $true -Details "skipped by -SkipExternalUrlChecks" -Required $false
        Add-Check -Name "devpost_public_project_mentions_demo_video" -Ok $true -Details "skipped by -SkipExternalUrlChecks" -Required $false
        Add-Check -Name "devpost_public_project_mentions_track_memoryagent" -Ok $true -Details "skipped by -SkipExternalUrlChecks" -Required $false
    }
    else {
        $repoMention = Test-DevpostRepoMention -Content $devpost.content -RepoUrlValue $RepoUrl -RepoNameValue $repoName
        $videoMention = Test-DevpostVideoMention -Content $devpost.content -VideoUrlValue $DemoVideoUrl
        Add-Check -Name "devpost_public_project_mentions_dream" -Ok ($devpost.ok -and (Test-TextContains -Text $devpost.content -Needle $ExpectedTitle)) -Details "expected text: $ExpectedTitle"
        Add-Check -Name "devpost_public_project_mentions_qwen" -Ok ($devpost.ok -and (Test-TextContains -Text $devpost.content -Needle "Qwen")) -Details "expected text: Qwen"
        Add-Check -Name "devpost_public_project_mentions_repo" -Ok ($devpost.ok -and $repoMention.ok) -Details $repoMention.details
        Add-Check -Name "devpost_public_project_mentions_demo_video" -Ok ($devpost.ok -and $videoMention.ok) -Details $videoMention.details
        Add-Check -Name "devpost_public_project_mentions_track_memoryagent" -Ok ($devpost.ok -and (Test-TextContains -Text $devpost.content -Needle "MemoryAgent")) -Details "optional expected text: MemoryAgent" -Required $false
    }
}
else {
    Add-Check -Name "devpost_public_project_reachable" -Ok $false -Details "DevpostProjectUrl missing or not public project URL"
    Add-Check -Name "devpost_public_project_mentions_dream" -Ok $false -Details "DevpostProjectUrl missing or not public project URL"
    Add-Check -Name "devpost_public_project_mentions_qwen" -Ok $false -Details "DevpostProjectUrl missing or not public project URL"
    Add-Check -Name "devpost_public_project_mentions_repo" -Ok $false -Details "DevpostProjectUrl missing or not public project URL"
    Add-Check -Name "devpost_public_project_mentions_demo_video" -Ok $false -Details "DevpostProjectUrl missing or not public project URL"
    Add-Check -Name "devpost_public_project_mentions_track_memoryagent" -Ok $false -Details "DevpostProjectUrl missing or not public project URL" -Required $false
}

Add-Check -Name "repo_url_present" -Ok (Is-HttpUrl $RepoUrl) -Details $RepoUrl
Add-Check -Name "repo_url_github" -Ok (-not [string]::IsNullOrWhiteSpace($repoName)) -Details $(if ($repoName) { $repoName } else { "not a normalized GitHub HTTPS repo URL: $RepoUrl" })
$repoMetadata = Get-GitHubRepoMetadata -RepoName $repoName
if ($repoMetadata) {
    $licenseKey = if ($repoMetadata.licenseInfo) { [string]$repoMetadata.licenseInfo.key } elseif ($repoMetadata.license) { [string]$repoMetadata.license.spdx_id } else { "" }
    $visibility = if ($repoMetadata.visibility) { [string]$repoMetadata.visibility } elseif ([bool]$repoMetadata.private) { "private" } else { "public" }
    Add-Check -Name "repo_github_public" -Ok (($visibility.ToLowerInvariant() -eq "public") -and -not [bool]$repoMetadata.private) -Details "repo=$repoName; visibility=$visibility; private=$($repoMetadata.private)"
    Add-Check -Name "repo_license_apache_2_0" -Ok ($licenseKey -eq "Apache-2.0" -or $licenseKey -eq "apache-2.0") -Details "repo=$repoName; license=$licenseKey"
}
else {
    Add-Check -Name "repo_github_public" -Ok $false -Details "GitHub metadata unavailable for $repoName"
    Add-Check -Name "repo_license_apache_2_0" -Ok $false -Details "GitHub metadata unavailable for $repoName"
}
$repo = Test-Url -Url $RepoUrl -Method "Get"
Add-Check -Name "repo_public_page_reachable" -Ok $repo.ok -Details $repo.details

Add-Check -Name "demo_video_url_platform" -Ok (Is-DevpostVideoUrl $DemoVideoUrl) -Details $(if ($DemoVideoUrl) { $DemoVideoUrl } else { "missing" })
if (Is-DevpostVideoUrl $DemoVideoUrl) {
    $video = Test-Url -Url $DemoVideoUrl -Method "Get"
    Add-Check -Name "demo_video_url_reachable" -Ok $video.ok -Details $video.details
}
else {
    Add-Check -Name "demo_video_url_reachable" -Ok $false -Details "DemoVideoUrl missing or not $script:QwenCloudDevpostVideoPlatformLabel"
}

Add-Check -Name "backend_url_present" -Ok (Is-HttpUrl $BackendUrl) -Details $(if ($BackendUrl) { $BackendUrl } else { "missing" })
if (Is-HttpUrl $BackendUrl) {
    $base = $BackendUrl.TrimEnd("/")
    try {
        $health = Invoke-RestMethod -Method Get -Uri "$base/health" -TimeoutSec 25
        Add-Check -Name "backend_health_status_ok" -Ok ($health.status -eq "ok") -Details "status=$($health.status)"
        Add-Check -Name "backend_track_memoryagent" -Ok ($health.track -eq $ExpectedTrack) -Details "track=$($health.track)"
        Add-Check -Name "backend_provider_qwen_cloud" -Ok ($health.llm_provider -eq "qwen-cloud") -Details "llm_provider=$($health.llm_provider)"
        Add-Check -Name "backend_deployment_target_alibaba" -Ok ([string]$health.deployment_target -match "Alibaba Cloud Function Compute") -Details "deployment_target=$($health.deployment_target)"
        Add-Check -Name "backend_alibaba_region_present" -Ok (-not [string]::IsNullOrWhiteSpace([string]$health.alibaba_cloud_region)) -Details "region=$($health.alibaba_cloud_region)"
        Add-Check -Name "backend_api_key_configured" -Ok ([bool]$health.llm_api_key_configured) -Details "llm_api_key_configured=$($health.llm_api_key_configured)"
        Add-Check -Name "backend_proof_file" -Ok ($health.proof_file -eq "deploy/alibaba/serverless-devs.yaml") -Details "proof_file=$($health.proof_file)"
    }
    catch {
        foreach ($name in @(
            "backend_health_status_ok",
            "backend_track_memoryagent",
            "backend_provider_qwen_cloud",
            "backend_deployment_target_alibaba",
            "backend_alibaba_region_present",
            "backend_api_key_configured",
            "backend_proof_file"
        )) {
            Add-Check -Name $name -Ok $false -Details $_.Exception.Message
        }
    }

    try {
        $showcase = Invoke-RestMethod -Method Get -Uri "$base/qwencloud/showcase" -TimeoutSec 25
        Add-Check -Name "backend_showcase_reachable" -Ok ($null -ne $showcase) -Details "$base/qwencloud/showcase"
        Add-Check -Name "backend_showcase_status_ok" -Ok ($showcase.runtime.status -eq "ok") -Details "status=$($showcase.runtime.status)"
        Add-Check -Name "backend_showcase_track_memoryagent" -Ok ($showcase.track -eq $ExpectedTrack) -Details "track=$($showcase.track)"
        Add-Check -Name "backend_showcase_provider_qwen_cloud" -Ok ($showcase.runtime.llm_provider -eq "qwen-cloud") -Details "llm_provider=$($showcase.runtime.llm_provider)"
        Add-Check -Name "backend_showcase_static_evidence_ready" -Ok ([int]$showcase.scorecard.weighted_static_evidence_ready -eq 100) -Details "$($showcase.scorecard.weighted_static_evidence_ready)/$($showcase.scorecard.weighted_total)"
        Add-Check -Name "backend_showcase_live_backend_ready" -Ok (Is-TrueBoolean $showcase.runtime.live_backend_ready) -Details "live_backend_ready=$($showcase.runtime.live_backend_ready)"
    }
    catch {
        foreach ($name in @(
            "backend_showcase_reachable",
            "backend_showcase_status_ok",
            "backend_showcase_track_memoryagent",
            "backend_showcase_provider_qwen_cloud",
            "backend_showcase_static_evidence_ready",
            "backend_showcase_live_backend_ready"
        )) {
            Add-Check -Name $name -Ok $false -Details $_.Exception.Message
        }
    }
}
else {
    foreach ($name in @(
        "backend_health_status_ok",
        "backend_track_memoryagent",
        "backend_provider_qwen_cloud",
        "backend_deployment_target_alibaba",
        "backend_alibaba_region_present",
        "backend_api_key_configured",
        "backend_proof_file",
        "backend_showcase_reachable",
        "backend_showcase_status_ok",
        "backend_showcase_track_memoryagent",
        "backend_showcase_provider_qwen_cloud",
        "backend_showcase_static_evidence_ready",
        "backend_showcase_live_backend_ready"
    )) {
        Add-Check -Name $name -Ok $false -Details "BackendUrl missing"
    }
}

$screenshot = Test-File -Path $AlibabaScreenshotPath -MinBytes 1024
Add-Check -Name "alibaba_screenshot_exists" -Ok $screenshot.ok -Details $screenshot.details
$screenshotDims = Get-PngDimensions -Path $AlibabaScreenshotPath
Add-Check -Name "alibaba_screenshot_1280x720" -Ok ($screenshotDims -and $screenshotDims.width -ge 1280 -and $screenshotDims.height -ge 720) -Details $(if ($screenshotDims) { "$($screenshotDims.width)x$($screenshotDims.height)" } else { "not a readable PNG" })

$proofVideo = Test-File -Path $AlibabaProofVideoPath -MinBytes 1024
Add-Check -Name "alibaba_proof_video_exists" -Ok $proofVideo.ok -Details $proofVideo.details
$proofMetadata = Get-VideoMetadata -Path $AlibabaProofVideoPath
if ($proofMetadata) {
    Add-Check -Name "alibaba_proof_video_720p_h264" -Ok ($proofMetadata.width -ge 1280 -and $proofMetadata.height -ge 720 -and $proofMetadata.codec -eq "h264") -Details "resolution=$($proofMetadata.width)x$($proofMetadata.height); codec=$($proofMetadata.codec)"
    Add-Check -Name "alibaba_proof_video_short" -Ok ($proofMetadata.duration -gt 0 -and $proofMetadata.duration -le 60) -Details "duration=$($proofMetadata.duration); size=$($proofMetadata.size)"
}
else {
    Add-Check -Name "alibaba_proof_video_720p_h264" -Ok $false -Details "ffprobe unavailable or proof video missing"
    Add-Check -Name "alibaba_proof_video_short" -Ok $false -Details "ffprobe unavailable or proof video missing"
}

$requiredFailures = @($checks | Where-Object { $_.required -and -not $_.ok })
$ready = $requiredFailures.Count -eq 0
$status = if ($ready) { "READY" } else { "DRAFT" }

$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = $status
    readyForGoalCompletionEvidence = $ready
    devpostProjectUrl = $DevpostProjectUrl
    devpostHtmlPath = $DevpostHtmlPath
    repoUrl = $RepoUrl
    repoName = $repoName
    demoVideoUrl = $DemoVideoUrl
    backendUrl = $BackendUrl
    finalBundleManifest = $bundleManifestPath
    alibabaScreenshotPath = $AlibabaScreenshotPath
    alibabaProofVideoPath = $AlibabaProofVideoPath
    reportJson = $reportJson
    reportMarkdown = $reportMd
    checks = $checks
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Post-Submit Verification ($timestamp)",
    "",
    "- Status: $status",
    "- Ready for goal completion evidence: $ready",
    "- Devpost public project URL: $(if ($DevpostProjectUrl) { $DevpostProjectUrl } else { '<missing>' })",
    "- Demo video URL: $(if ($DemoVideoUrl) { $DemoVideoUrl } else { '<missing>' })",
    "- Backend URL: $(if ($BackendUrl) { $BackendUrl } else { '<missing>' })",
    "- Final bundle manifest: $(if ($bundleManifestPath) { $bundleManifestPath } else { '<missing>' })",
    "- Repo URL: $RepoUrl",
    "- Alibaba screenshot: $AlibabaScreenshotPath",
    "- Alibaba proof video: $AlibabaProofVideoPath",
    "",
    "## Checks",
    "",
    "| Check | Required | Result | Details |",
    "|---|---:|---:|---|"
)
foreach ($check in $checks) {
    $resultText = if ($check.ok) { "PASS" } else { "FAIL" }
    $requiredText = if ($check.required) { "yes" } else { "no" }
    $lines += "| $($check.name) | $requiredText | $resultText | $($check.details -replace '\|', '/') |"
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
    "## Final Evidence Command",
    "",
    '```powershell',
    'scripts/qwencloud-post-submit-verification.ps1 -DevpostProjectUrl "https://devpost.com/software/<project-slug>" -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>" -FinalBundleManifest "artifacts/qwencloud-proof/final-upload-bundle-<timestamp>/manifest.json"',
    '```'
)
Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($ready) {
    Write-Host "Post-submit verification READY: $reportMd"
}
else {
    Write-Host "Post-submit verification DRAFT: $reportMd" -ForegroundColor Yellow
    Write-Host "Missing required items: $($requiredFailures.name -join ', ')"
    if (-not $AllowDraft) {
        exit 1
    }
}
Write-Host "JSON: $reportJson"
