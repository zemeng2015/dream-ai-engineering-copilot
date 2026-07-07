# SPDX-License-Identifier: Apache-2.0

param(
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [string]$PostSubmitVerificationJson = "",
    [Parameter(Mandatory = $false)]
    [string]$FinalBundleManifest = "",
    [Parameter(Mandatory = $false)]
    [string]$ReleaseSummaryJson = "",
    [Parameter(Mandatory = $false)]
    [string]$DevpostProjectUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$DemoVideoUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$BackendUrl = "",
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$archiveRoot = Join-Path $OutputDir "final-completion-evidence-$timestamp"
$archiveUploads = Join-Path $archiveRoot "evidence"
$archiveJson = Join-Path $archiveRoot "manifest.json"
$archiveMd = Join-Path $archiveRoot "manifest.md"
$zipPath = Join-Path $OutputDir "final-completion-evidence-$timestamp.zip"
$reportJson = Join-Path $OutputDir "final-completion-evidence-$timestamp.json"
$reportMd = Join-Path $OutputDir "final-completion-evidence-$timestamp.md"
New-Item -ItemType Directory -Path $archiveUploads -Force | Out-Null

$checks = @()
$items = @()

function Add-Check([string]$Name, [bool]$Ok, [string]$Details, [bool]$Required = $true) {
    $script:checks += [ordered]@{
        name = $Name
        ok = $Ok
        required = $Required
        details = $Details
    }
}

function Get-LatestFile([string]$Filter) {
    return Get-ChildItem -LiteralPath $OutputDir -Filter $Filter -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Get-LatestBundleManifest {
    if (-not [string]::IsNullOrWhiteSpace($FinalBundleManifest)) {
        return $FinalBundleManifest
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

function Read-JsonOrNull([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path)) {
        return $null
    }

    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Resolve-PathText([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return ""
    }
    if (Test-Path -LiteralPath $Path) {
        return (Resolve-Path -LiteralPath $Path).Path
    }
    return $Path
}

function Get-Sha256([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path)) {
        return ""
    }

    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Add-EvidenceItem([string]$Name, [string]$Path, [bool]$Required = $true) {
    $exists = (-not [string]::IsNullOrWhiteSpace($Path)) -and (Test-Path -LiteralPath $Path)
    $destination = ""
    $sha256 = ""
    $size = 0
    if ($exists) {
        $source = Get-Item -LiteralPath $Path
        $destination = Join-Path $script:archiveUploads $source.Name
        Copy-Item -LiteralPath $source.FullName -Destination $destination -Force
        $sha256 = Get-Sha256 -Path $destination
        $size = $source.Length
    }

    $script:items += [ordered]@{
        name = $Name
        source = $Path
        required = $Required
        exists = $exists
        archivedPath = $destination
        sizeBytes = $size
        sha256 = $sha256
    }
    Add-Check -Name "evidence_item.$Name" -Ok $exists -Details $(if ($exists) { "$Path sha256=$sha256" } else { "missing: $Path" }) -Required $Required
}

function First-Text([object[]]$Values) {
    foreach ($value in $Values) {
        $text = [string]$value
        if (-not [string]::IsNullOrWhiteSpace($text)) {
            return $text
        }
    }
    return ""
}

$postPath = if ($PostSubmitVerificationJson) { $PostSubmitVerificationJson } else { $latest = Get-LatestFile -Filter "devpost-post-submit-verification-*.json"; if ($latest) { $latest.FullName } else { "" } }
$summaryPath = if ($ReleaseSummaryJson) { $ReleaseSummaryJson } else { $latest = Get-LatestFile -Filter "release-summary-*.json"; if ($latest) { $latest.FullName } else { "" } }
$bundleManifestPath = Get-LatestBundleManifest

$postSubmit = Read-JsonOrNull -Path $postPath
$releaseSummary = Read-JsonOrNull -Path $summaryPath
$bundleManifest = Read-JsonOrNull -Path $bundleManifestPath

$bundleZipPath = ""
if ($bundleManifest -and -not [string]::IsNullOrWhiteSpace([string]$bundleManifest.zipPath)) {
    $bundleZipPath = [string]$bundleManifest.zipPath
}
elseif ($releaseSummary -and $releaseSummary.finalBundle -and -not [string]::IsNullOrWhiteSpace([string]$releaseSummary.finalBundle.zip)) {
    $bundleZipPath = [string]$releaseSummary.finalBundle.zip
}
$bundleZipPath = Resolve-PathText -Path $bundleZipPath

$effectiveDevpostUrl = First-Text -Values @($DevpostProjectUrl, $(if ($postSubmit) { $postSubmit.devpostProjectUrl } else { "" }))
$effectiveVideoUrl = First-Text -Values @($DemoVideoUrl, $(if ($postSubmit) { $postSubmit.demoVideoUrl } else { "" }), $(if ($releaseSummary) { $releaseSummary.demoVideoUrl } else { "" }))
$effectiveBackendUrl = First-Text -Values @($BackendUrl, $(if ($postSubmit) { $postSubmit.backendUrl } else { "" }), $(if ($releaseSummary) { $releaseSummary.backendUrl } else { "" }))

Add-Check -Name "post_submit_verification_present" -Ok ($null -ne $postSubmit) -Details $(if ($postSubmit) { $postPath } else { "missing devpost-post-submit-verification-*.json" })
Add-Check -Name "post_submit_verification_ready" -Ok ($postSubmit -and [bool]$postSubmit.readyForGoalCompletionEvidence) -Details $(if ($postSubmit) { "status=$($postSubmit.status); readyForGoalCompletionEvidence=$($postSubmit.readyForGoalCompletionEvidence)" } else { "missing" })
Add-Check -Name "release_summary_present" -Ok ($null -ne $releaseSummary) -Details $(if ($releaseSummary) { $summaryPath } else { "missing release-summary-*.json" })
Add-Check -Name "release_summary_ready" -Ok ($releaseSummary -and [bool]$releaseSummary.readyForFinalSubmit) -Details $(if ($releaseSummary) { "status=$($releaseSummary.status); readyForFinalSubmit=$($releaseSummary.readyForFinalSubmit)" } else { "missing" })
Add-Check -Name "final_bundle_manifest_present" -Ok ($null -ne $bundleManifest) -Details $(if ($bundleManifest) { $bundleManifestPath } else { "missing final-upload-bundle-*/manifest.json" })
Add-Check -Name "final_bundle_ready_for_upload" -Ok ($bundleManifest -and [bool]$bundleManifest.readyForUpload) -Details $(if ($bundleManifest) { "readyForUpload=$($bundleManifest.readyForUpload)" } else { "missing" })
Add-Check -Name "final_bundle_zip_present" -Ok (-not [string]::IsNullOrWhiteSpace($bundleZipPath) -and (Test-Path -LiteralPath $bundleZipPath)) -Details $(if ($bundleZipPath) { $bundleZipPath } else { "missing zip path" })
Add-Check -Name "devpost_project_url_present" -Ok ($effectiveDevpostUrl -match "^https://devpost\.com/software/[^/?#]+") -Details $(if ($effectiveDevpostUrl) { $effectiveDevpostUrl } else { "missing" })
Add-Check -Name "demo_video_url_present" -Ok ($effectiveVideoUrl -match "^https?://") -Details $(if ($effectiveVideoUrl) { $effectiveVideoUrl } else { "missing" })
Add-Check -Name "backend_url_present" -Ok ($effectiveBackendUrl -match "^https?://") -Details $(if ($effectiveBackendUrl) { $effectiveBackendUrl } else { "missing" })

$postMd = if ($postPath) { [System.IO.Path]::ChangeExtension($postPath, ".md") } else { "" }
$summaryMd = if ($summaryPath) { [System.IO.Path]::ChangeExtension($summaryPath, ".md") } else { "" }
$bundleMd = if ($bundleManifestPath) { [System.IO.Path]::ChangeExtension($bundleManifestPath, ".md") } else { "" }

Add-EvidenceItem -Name "post_submit_verification_json" -Path $postPath
Add-EvidenceItem -Name "post_submit_verification_markdown" -Path $postMd
Add-EvidenceItem -Name "release_summary_json" -Path $summaryPath
Add-EvidenceItem -Name "release_summary_markdown" -Path $summaryMd
Add-EvidenceItem -Name "final_bundle_manifest_json" -Path $bundleManifestPath
Add-EvidenceItem -Name "final_bundle_manifest_markdown" -Path $bundleMd
Add-EvidenceItem -Name "final_upload_bundle_zip" -Path $bundleZipPath

$requiredFailures = @($checks | Where-Object { $_.required -and -not $_.ok })
$ready = $requiredFailures.Count -eq 0
$status = if ($ready) { "READY" } else { "DRAFT" }

$archiveManifest = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = $status
    readyForGoalCompletionArchive = $ready
    devpostProjectUrl = $effectiveDevpostUrl
    demoVideoUrl = $effectiveVideoUrl
    backendUrl = $effectiveBackendUrl
    postSubmitVerificationJson = $postPath
    releaseSummaryJson = $summaryPath
    finalBundleManifest = $bundleManifestPath
    finalBundleZip = $bundleZipPath
    finalBundleZipSha256 = Get-Sha256 -Path $bundleZipPath
    requiredFailures = @($requiredFailures | ForEach-Object { $_.name })
    checks = $checks
    evidenceItems = $items
    archiveRoot = $archiveRoot
    archiveZip = $zipPath
    reportJson = $reportJson
    reportMarkdown = $reportMd
}
Set-Content -Path $archiveJson -Value ($archiveManifest | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Final Completion Evidence ($timestamp)",
    "",
    "- Status: $status",
    "- Ready for goal completion archive: $ready",
    "- Devpost project URL: $(if ($effectiveDevpostUrl) { $effectiveDevpostUrl } else { '<missing>' })",
    "- Demo video URL: $(if ($effectiveVideoUrl) { $effectiveVideoUrl } else { '<missing>' })",
    "- Backend URL: $(if ($effectiveBackendUrl) { $effectiveBackendUrl } else { '<missing>' })",
    "- Final upload bundle: $(if ($bundleZipPath) { $bundleZipPath } else { '<missing>' })",
    "- Final upload bundle SHA256: $(if ($archiveManifest.finalBundleZipSha256) { $archiveManifest.finalBundleZipSha256 } else { '<missing>' })",
    "",
    "## Checks",
    "",
    "| Check | Required | Result | Details |",
    "|---|---:|---:|---|"
)
foreach ($check in $checks) {
    $lines += "| $($check.name) | $(if ($check.required) { 'yes' } else { 'no' }) | $(if ($check.ok) { 'PASS' } else { 'FAIL' }) | $($check.details -replace '\|', '/') |"
}
if ($requiredFailures.Count -gt 0) {
    $lines += @(
        "",
        "## Missing Required Checks",
        ""
    )
    foreach ($failure in $requiredFailures) {
        $lines += "- $($failure.name): $($failure.details)"
    }
}
$lines += @(
    "",
    "## Evidence Items",
    "",
    "| Item | Exists | SHA256 |",
    "|---|---:|---|"
)
foreach ($item in $items) {
    $lines += "| $($item.name) | $(if ($item.exists) { 'yes' } else { 'no' }) | $($item.sha256) |"
}
Set-Content -Path $archiveMd -Value ($lines -join "`r`n") -Encoding UTF8
Set-Content -Path $reportJson -Value ($archiveManifest | ConvertTo-Json -Depth 12) -Encoding UTF8
Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -Path (Join-Path $archiveRoot "*") -DestinationPath $zipPath -Force

if ($ready) {
    Write-Host "Final completion evidence READY: $zipPath"
}
else {
    Write-Host "Final completion evidence DRAFT: $zipPath" -ForegroundColor Yellow
    Write-Host "Missing required checks: $($requiredFailures.name -join ', ')"
}
Write-Host "Report: $reportMd"
Write-Host "JSON: $reportJson"

if (-not $ready -and -not $AllowDraft) {
    exit 1
}
