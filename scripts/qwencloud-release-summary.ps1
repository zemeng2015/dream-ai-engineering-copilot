param(
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [string]$MarkdownPath = "",
    [Parameter(Mandatory = $false)]
    [string]$DemoVideoUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$BackendUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$BlogPostUrl = "",
    [switch]$NoGitHubStepSummary
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$summaryJson = Join-Path $OutputDir "release-summary-$timestamp.json"
$artifactMarkdown = Join-Path $OutputDir "release-summary-$timestamp.md"

function Get-LatestFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Filter,
        [switch]$Directory
    )

    $items = if ($Directory) {
        Get-ChildItem -LiteralPath $OutputDir -Filter $Filter -Directory -ErrorAction SilentlyContinue
    }
    else {
        Get-ChildItem -LiteralPath $OutputDir -Filter $Filter -File -ErrorAction SilentlyContinue
    }

    return $items | Sort-Object LastWriteTime -Descending | Select-Object -First 1
}

function Read-LatestJson {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Filter
    )

    $file = Get-LatestFile -Filter $Filter
    if (-not $file) {
        return [pscustomobject]@{
            path = ""
            data = $null
            ok = $false
            error = "missing"
        }
    }

    try {
        $data = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
        return [pscustomobject]@{
            path = $file.FullName
            data = $data
            ok = $true
            error = ""
        }
    }
    catch {
        return [pscustomobject]@{
            path = $file.FullName
            data = $null
            ok = $false
            error = $_.Exception.Message
        }
    }
}

function Read-JsonFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path)) {
        return [pscustomobject]@{
            path = $Path
            data = $null
            ok = $false
            error = "missing"
        }
    }

    try {
        $data = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
        return [pscustomobject]@{
            path = $Path
            data = $data
            ok = $true
            error = ""
        }
    }
    catch {
        return [pscustomobject]@{
            path = $Path
            data = $null
            ok = $false
            error = $_.Exception.Message
        }
    }
}

function First-Text {
    param(
        [Parameter(Mandatory = $false)]
        [AllowNull()]
        [object[]]$Values
    )

    foreach ($value in $Values) {
        $text = [string]$value
        if (-not [string]::IsNullOrWhiteSpace($text)) {
            return $text
        }
    }

    return ""
}

function Get-Sha256 {
    param(
        [Parameter(Mandatory = $false)]
        [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path)) {
        return ""
    }

    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Get-RequiredFailures {
    param(
        [Parameter(Mandatory = $false)]
        [AllowNull()]
        [object]$Checks
    )

    if (-not $Checks) {
        return @()
    }

    return @(
        $Checks |
            Where-Object { $_.required -and -not $_.ok } |
            ForEach-Object { $_.name }
    )
}

function Get-EmbeddedReleaseSummaryItems {
    param(
        [Parameter(Mandatory = $false)]
        [AllowNull()]
        [object]$BundleManifestData
    )

    if (-not $BundleManifestData -or -not $BundleManifestData.items) {
        return @()
    }

    return @(
        $BundleManifestData.items |
            Where-Object {
                $name = [string]$_.name
                $name -match "release_summary" -and $name -ne "github_release_summary_script"
            } |
            ForEach-Object { [string]$_.name }
    )
}

function Format-PathOrMissing {
    param(
        [Parameter(Mandatory = $false)]
        [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return "<missing>"
    }

    return $Path
}

$release = Read-LatestJson -Filter "alibaba-runtime-release-*.json"
if (-not $release.data) {
    $release = Read-LatestJson -Filter "alibaba-release-*.json"
}
$showcase = Read-LatestJson -Filter "showcase-*.json"
$deployPreflight = Read-LatestJson -Filter "deploy-preflight-*.json"
$readiness = Read-LatestJson -Filter "final-readiness-*.json"
$actionBoard = Read-LatestJson -Filter "final-action-board-*.json"
$bundleZip = Get-LatestFile -Filter "final-upload-bundle-*.zip"
$bundleDir = Get-LatestFile -Filter "final-upload-bundle-*" -Directory
$bundleManifestPath = if ($bundleDir) { Join-Path $bundleDir.FullName "manifest.json" } else { "" }
$bundleManifest = Read-JsonFile -Path $bundleManifestPath

$effectiveBackendUrl = First-Text -Values @(
    $BackendUrl,
    $(if ($release.data) { $release.data.backendUrl } else { "" }),
    $(if ($bundleManifest.data) { $bundleManifest.data.backendUrl } else { "" }),
    $(if ($readiness.data) { $readiness.data.backendUrl } else { "" }),
    $(if ($actionBoard.data) { $actionBoard.data.backendUrl } else { "" })
)
$effectiveDemoVideoUrl = First-Text -Values @(
    $DemoVideoUrl,
    $(if ($bundleManifest.data) { $bundleManifest.data.demoVideoUrl } else { "" }),
    $(if ($readiness.data) { $readiness.data.demoVideoUrl } else { "" }),
    $(if ($actionBoard.data) { $actionBoard.data.demoVideoUrl } else { "" })
)
$effectiveBlogPostUrl = First-Text -Values @(
    $BlogPostUrl,
    $(if ($bundleManifest.data) { $bundleManifest.data.blogPostUrl } else { "" }),
    $(if ($readiness.data) { $readiness.data.blogPostUrl } else { "" }),
    $(if ($actionBoard.data) { $actionBoard.data.blogPostUrl } else { "" })
)

$showcaseReady = $false
$showcaseSignal = "missing"
if ($showcase.data) {
    $showcaseReady = (
        $showcase.data.track -eq "Track 1: MemoryAgent" -and
        $showcase.data.runtime.status -eq "ok" -and
        $showcase.data.runtime.llm_provider -eq "qwen-cloud" -and
        [int]$showcase.data.scorecard.weighted_static_evidence_ready -eq 100
    )
    $showcaseSignal = "track=$($showcase.data.track); provider=$($showcase.data.runtime.llm_provider); static=$($showcase.data.scorecard.weighted_static_evidence_ready)/$($showcase.data.scorecard.weighted_total); live=$($showcase.data.runtime.live_backend_ready)"
}
elseif (-not $showcase.ok -and -not [string]::IsNullOrWhiteSpace($showcase.path)) {
    $showcaseSignal = "unreadable: $($showcase.error)"
}

$preflightFailures = Get-RequiredFailures -Checks $(if ($deployPreflight.data) { $deployPreflight.data.checks } else { $null })
$readinessFailures = Get-RequiredFailures -Checks $(if ($readiness.data) { $readiness.data.checks } else { $null })
$bundleMissing = @(
    if ($bundleManifest.data -and $bundleManifest.data.missingRequiredItems) {
        $bundleManifest.data.missingRequiredItems
    }
)
$embeddedReleaseSummaryItems = @(Get-EmbeddedReleaseSummaryItems -BundleManifestData $bundleManifest.data)
$bundleSummaryPackagingOk = $embeddedReleaseSummaryItems.Count -eq 0
$nextActionNames = @(
    if ($actionBoard.data -and $actionBoard.data.nextActions) {
        $actionBoard.data.nextActions | ForEach-Object { $_.name }
    }
)

$bundleZipPath = if ($bundleZip) { $bundleZip.FullName } else { "" }
$bundleZipSha = Get-Sha256 -Path $bundleZipPath
$bundleReady = [bool]($bundleManifest.data -and $bundleManifest.data.readyForUpload)
$readinessReady = [bool]($readiness.data -and $readiness.data.readyForFinalSubmit)
$status = if ($bundleReady -and $readinessReady -and $showcaseReady -and $bundleSummaryPackagingOk -and -not [string]::IsNullOrWhiteSpace($effectiveBackendUrl)) { "READY" } else { "DRAFT" }

$checks = @(
    [ordered]@{
        name = "backend_url_known"
        ok = -not [string]::IsNullOrWhiteSpace($effectiveBackendUrl)
        details = $(if ($effectiveBackendUrl) { $effectiveBackendUrl } else { "missing" })
    },
    [ordered]@{
        name = "showcase_proof_ready"
        ok = $showcaseReady
        details = $showcaseSignal
    },
    [ordered]@{
        name = "deploy_preflight_present"
        ok = [bool]$deployPreflight.data
        details = $(if ($deployPreflight.data) { $deployPreflight.path } else { $deployPreflight.error })
    },
    [ordered]@{
        name = "final_readiness_ready"
        ok = $readinessReady
        details = $(if ($readiness.data) { "readyForFinalSubmit=$($readiness.data.readyForFinalSubmit); missing=$($readinessFailures -join ', ')" } else { $readiness.error })
    },
    [ordered]@{
        name = "final_bundle_ready"
        ok = $bundleReady
        details = $(if ($bundleManifest.data) { "readyForUpload=$($bundleManifest.data.readyForUpload); missing=$($bundleMissing -join ', ')" } else { $bundleManifest.error })
    },
    [ordered]@{
        name = "final_bundle_zip_hash_present"
        ok = -not [string]::IsNullOrWhiteSpace($bundleZipSha)
        details = $(if ($bundleZipSha) { "$bundleZipPath sha256=$bundleZipSha" } else { "missing" })
    },
    [ordered]@{
        name = "final_bundle_no_embedded_release_summary"
        ok = $bundleSummaryPackagingOk
        details = $(if ($bundleSummaryPackagingOk) { "release summary generated after bundle, not embedded" } else { "embedded release summary items: $($embeddedReleaseSummaryItems -join ', ')" })
    }
)

$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = $status
    readyForFinalSubmit = ($status -eq "READY")
    demoVideoUrl = $effectiveDemoVideoUrl
    backendUrl = $effectiveBackendUrl
    blogPostUrl = $effectiveBlogPostUrl
    artifacts = [ordered]@{
        releaseJson = $release.path
        showcaseJson = $showcase.path
        deployPreflightJson = $deployPreflight.path
        finalReadinessJson = $readiness.path
        finalActionBoardJson = $actionBoard.path
        finalBundleManifest = $bundleManifest.path
        finalBundleZip = $bundleZipPath
        finalBundleZipSha256 = $bundleZipSha
        markdown = $artifactMarkdown
        json = $summaryJson
    }
    showcase = [ordered]@{
        ready = $showcaseReady
        signal = $showcaseSignal
        path = $showcase.path
        endpoint = "/qwencloud/showcase"
    }
    finalReadiness = [ordered]@{
        ready = $readinessReady
        path = $readiness.path
        missingRequiredChecks = $readinessFailures
    }
    finalBundle = [ordered]@{
        ready = $bundleReady
        manifest = $bundleManifest.path
        zip = $bundleZipPath
        zipSha256 = $bundleZipSha
        missingRequiredItems = $bundleMissing
        releaseSummaryPackagingOk = $bundleSummaryPackagingOk
        embeddedReleaseSummaryItems = @($embeddedReleaseSummaryItems)
    }
    deployPreflight = [ordered]@{
        path = $deployPreflight.path
        missingRequiredChecks = $preflightFailures
    }
    actionBoard = [ordered]@{
        path = $actionBoard.path
        nextActionNames = $nextActionNames
    }
    checks = $checks
}

Set-Content -Path $summaryJson -Value ($result | ConvertTo-Json -Depth 20) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Release Summary ($timestamp)",
    "",
    "- Status: $status",
    "- Ready for final Devpost submit: $($status -eq 'READY')",
    "- Backend URL: $(if ($effectiveBackendUrl) { $effectiveBackendUrl } else { '<missing>' })",
    "- Demo video URL: $(if ($effectiveDemoVideoUrl) { $effectiveDemoVideoUrl } else { '<missing>' })",
    "- Blog/social URL: $(if ($effectiveBlogPostUrl) { $effectiveBlogPostUrl } else { '<optional>' })",
    "- Showcase endpoint: /qwencloud/showcase",
    "- Showcase proof: $(Format-PathOrMissing -Path $showcase.path)",
    "- Final bundle zip: $(Format-PathOrMissing -Path $bundleZipPath)",
    "- Final bundle SHA256: $(if ($bundleZipSha) { $bundleZipSha } else { '<missing>' })",
    "- Release summary packaging: $(if ($bundleSummaryPackagingOk) { 'generated after bundle; not embedded in zip' } else { 'stale embedded summary found: ' + ($embeddedReleaseSummaryItems -join ', ') })",
    "",
    "## Artifact Map",
    "",
    "| Artifact | Latest file | Signal |",
    "|---|---|---|",
    "| Alibaba release | $(Format-PathOrMissing -Path $release.path) | backend=$(if ($release.data) { $release.data.backendUrl } else { '<missing>' }) |",
    "| Showcase JSON | $(Format-PathOrMissing -Path $showcase.path) | $($showcaseSignal -replace '\|', '/') |",
    "| Deploy preflight | $(Format-PathOrMissing -Path $deployPreflight.path) | missing=$($preflightFailures -join ', ') |",
    "| Final readiness | $(Format-PathOrMissing -Path $readiness.path) | ready=$readinessReady; missing=$($readinessFailures -join ', ') |",
    "| Final action board | $(Format-PathOrMissing -Path $actionBoard.path) | nextActions=$($nextActionNames.Count) |",
    "| Final bundle manifest | $(Format-PathOrMissing -Path $bundleManifest.path) | ready=$bundleReady; missing=$($bundleMissing -join ', ') |",
    "| Final bundle zip | $(Format-PathOrMissing -Path $bundleZipPath) | sha256=$(if ($bundleZipSha) { $bundleZipSha } else { '<missing>' }) |",
    "| Release summary packaging | $(Format-PathOrMissing -Path $summaryJson) | embedded=$($embeddedReleaseSummaryItems.Count); generated after bundle |",
    "",
    "## External Blockers",
    ""
)

if ($bundleMissing.Count -eq 0 -and $readinessFailures.Count -eq 0) {
    $lines += "- None from the latest final bundle/readiness reports."
}
else {
    foreach ($item in $bundleMissing) {
        $lines += "- bundle: $item"
    }
    foreach ($item in $readinessFailures) {
        $lines += "- readiness: $item"
    }
}

if ($nextActionNames.Count -gt 0) {
    $lines += @(
        "",
        "## Next Actions",
        ""
    )
    foreach ($item in $nextActionNames) {
        $lines += "- $item"
    }
}

Set-Content -Path $artifactMarkdown -Value ($lines -join "`r`n") -Encoding UTF8

if (-not [string]::IsNullOrWhiteSpace($MarkdownPath) -and $MarkdownPath -ne $artifactMarkdown) {
    Set-Content -Path $MarkdownPath -Value ($lines -join "`r`n") -Encoding UTF8
}

if (-not $NoGitHubStepSummary -and -not [string]::IsNullOrWhiteSpace($env:GITHUB_STEP_SUMMARY)) {
    Add-Content -Path $env:GITHUB_STEP_SUMMARY -Value ($lines -join "`n") -Encoding UTF8
}

Write-Host "Qwen Cloud release summary: $artifactMarkdown"
Write-Host "JSON: $summaryJson"
Write-Host "Status: $status"
