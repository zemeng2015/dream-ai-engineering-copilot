# SPDX-License-Identifier: Apache-2.0
param(
    [Parameter(Mandatory = $false)]
    [string]$Repo = "zemeng2015/dream-ai-engineering-copilot",
    [Parameter(Mandatory = $false)]
    [string]$Branch = "main",
    [Parameter(Mandatory = $false)]
    [string]$WorkflowName = "Qwen Cloud Release",
    [Parameter(Mandatory = $false)]
    [string]$ArtifactName = "qwencloud-release-proof",
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [string]$RunId = "",
    [Parameter(Mandatory = $false)]
    [string]$ArtifactSourceDir = "",
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$reportJson = Join-Path $OutputDir "github-release-artifact-ingest-$timestamp.json"
$reportMd = Join-Path $OutputDir "github-release-artifact-ingest-$timestamp.md"
$downloadRoot = Join-Path $OutputDir "github-release-artifact-$timestamp"
$steps = @()
$copiedFiles = @()
$releaseRunSelection = ""

function Add-Step([string]$Name, [bool]$Ok, [string]$Details, [bool]$Required = $true) {
    $script:steps += [ordered]@{
        name = $Name
        ok = $Ok
        required = $Required
        details = $Details
    }
}

function Has-Command([string]$Name) {
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-PowerShellExe {
    $pwsh = Get-Command "pwsh" -ErrorAction SilentlyContinue
    if ($pwsh) { return $pwsh.Source }

    $powershell = Get-Command "powershell" -ErrorAction SilentlyContinue
    if ($powershell) { return $powershell.Source }

    throw "PowerShell executable not found."
}

function Read-JsonFile([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path)) {
        return $null
    }

    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Get-LatestFile([string]$Filter, [switch]$Directory) {
    $items = if ($Directory) {
        Get-ChildItem -LiteralPath $OutputDir -Filter $Filter -Directory -ErrorAction SilentlyContinue
    }
    else {
        Get-ChildItem -LiteralPath $OutputDir -Filter $Filter -File -ErrorAction SilentlyContinue
    }

    return $items | Sort-Object LastWriteTime -Descending | Select-Object -First 1
}

function Read-LatestJson([string]$Filter) {
    $file = Get-LatestFile -Filter $Filter
    if (-not $file) {
        return [pscustomobject]@{ file = ""; data = $null }
    }

    try {
        return [pscustomobject]@{
            file = $file.FullName
            data = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
        }
    }
    catch {
        return [pscustomobject]@{ file = $file.FullName; data = $null; error = $_.Exception.Message }
    }
}

function Copy-ArtifactTree([string]$SourceDir, [string]$DestinationDir) {
    if ([string]::IsNullOrWhiteSpace($SourceDir) -or -not (Test-Path -LiteralPath $SourceDir)) {
        throw "Artifact source directory is missing: $SourceDir"
    }

    $sourceRoot = (Resolve-Path -LiteralPath $SourceDir).Path.TrimEnd("\", "/")
    $destinationRoot = (Resolve-Path -LiteralPath $DestinationDir).Path.TrimEnd("\", "/")
    $files = @(Get-ChildItem -LiteralPath $sourceRoot -Recurse -File -ErrorAction SilentlyContinue)
    foreach ($file in $files) {
        $fullName = $file.FullName
        if (-not $fullName.StartsWith($sourceRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Artifact file resolved outside source root: $fullName"
        }

        $relative = $fullName.Substring($sourceRoot.Length).TrimStart("\", "/")
        if ([string]::IsNullOrWhiteSpace($relative) -or $relative -match "(^|[\\/])\.\.([\\/]|$)" -or [System.IO.Path]::IsPathRooted($relative)) {
            throw "Unsafe artifact relative path: $relative"
        }

        $dest = Join-Path $destinationRoot $relative
        $destFull = [System.IO.Path]::GetFullPath($dest)
        if (-not $destFull.StartsWith($destinationRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Artifact destination escaped output directory: $destFull"
        }

        $parent = Split-Path -Parent $destFull
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $destFull -Force
        $script:copiedFiles += $destFull
    }
}

function Select-ReleaseRun([object[]]$Runs) {
    $flatRuns = @()
    foreach ($item in $Runs) {
        if ($item -is [System.Array]) {
            foreach ($nestedItem in $item) {
                $flatRuns += $nestedItem
            }
        }
        else {
            $flatRuns += $item
        }
    }

    $workflowRuns = @(
        $flatRuns |
            Where-Object { $_.workflowName -eq $WorkflowName } |
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
    if ($workflowRuns.Count -eq 0) {
        $script:releaseRunSelection = "no runs found for workflow '$WorkflowName'"
        return $null
    }

    $completedRuns = @($workflowRuns | Where-Object { $_.status -eq "completed" })
    $activeRunCount = @($workflowRuns | Where-Object { $_.status -ne "completed" }).Count

    if ([bool]$AllowDraft) {
        if ($completedRuns.Count -gt 0) {
            $script:releaseRunSelection = "selected latest completed run because -AllowDraft is set; matching=$($workflowRuns.Count); activeSkipped=$activeRunCount"
            return $completedRuns[0]
        }

        $script:releaseRunSelection = "no completed runs available with -AllowDraft; reporting latest workflow run; matching=$($workflowRuns.Count); activeSkipped=0"
        return $workflowRuns[0]
    }

    $successfulRuns = @($completedRuns | Where-Object { $_.conclusion -eq "success" })
    if ($successfulRuns.Count -gt 0) {
        $script:releaseRunSelection = "selected latest completed successful run; matching=$($workflowRuns.Count); activeSkipped=$activeRunCount"
        return $successfulRuns[0]
    }

    if ($completedRuns.Count -gt 0) {
        $script:releaseRunSelection = "no completed successful runs available; reporting latest completed non-success run; matching=$($workflowRuns.Count); activeSkipped=$activeRunCount"
        return $completedRuns[0]
    }

    $script:releaseRunSelection = "no completed runs available; reporting latest workflow run; matching=$($workflowRuns.Count); activeSkipped=$activeRunCount"
    return $workflowRuns[0]
}

function Get-ReleaseRun {
    if (-not [string]::IsNullOrWhiteSpace($ArtifactSourceDir)) {
        $script:releaseRunSelection = "using fixture artifact source"
        return [pscustomobject]@{
            databaseId = if ($RunId) { $RunId } else { "fixture" }
            headSha = ""
            status = "completed"
            conclusion = "success"
            displayTitle = "Fixture artifact source"
            workflowName = $WorkflowName
            url = ""
        }
    }

    if (-not (Has-Command "gh")) {
        throw "GitHub CLI `gh` is required unless -ArtifactSourceDir is set."
    }

    if (-not [string]::IsNullOrWhiteSpace($RunId)) {
        $script:releaseRunSelection = "using explicit run id: $RunId"
        $json = gh run view $RunId --repo $Repo --json databaseId,headSha,status,conclusion,displayTitle,workflowName,url,createdAt,updatedAt
        return $json | ConvertFrom-Json
    }

    $runsJson = gh run list --repo $Repo --branch $Branch --limit 50 --json databaseId,headSha,status,conclusion,displayTitle,workflowName,url,createdAt,updatedAt
    $runs = @($runsJson | ConvertFrom-Json)
    return Select-ReleaseRun -Runs $runs
}

function Invoke-ReleaseSummary {
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-release-summary.ps1",
        "-OutputDir", $OutputDir,
        "-NoGitHubStepSummary"
    )
    $output = (& (Get-PowerShellExe) @args 2>&1) -join "`n"
    if ($LASTEXITCODE -ne 0) {
        throw $output
    }
    return $output
}

$usingFixture = -not [string]::IsNullOrWhiteSpace($ArtifactSourceDir)
$run = $null
$artifactSource = ""

try {
    $run = Get-ReleaseRun
    Add-Step -Name "release_run_selection" -Ok ($null -ne $run) -Details $(if ($releaseRunSelection) { $releaseRunSelection } else { "no selection details" }) -Required $false
    Add-Step -Name "release_run_found" -Ok ($null -ne $run) -Details $(if ($run) { "$($run.workflowName); $($run.status); $($run.conclusion); $($run.url)" } else { "missing $WorkflowName run" })
    if ($run) {
        $releaseRunSuccess = $run.status -eq "completed" -and $run.conclusion -eq "success"
        $downloadAllowed = $run.status -eq "completed" -and ($releaseRunSuccess -or [bool]$AllowDraft)
        Add-Step -Name "release_run_success" -Ok $releaseRunSuccess -Details "status=$($run.status); conclusion=$($run.conclusion); run=$($run.databaseId)" -Required (-not [bool]$AllowDraft)
        Add-Step -Name "release_run_artifact_downloadable" -Ok $downloadAllowed -Details "status=$($run.status); conclusion=$($run.conclusion); run=$($run.databaseId); allowDraft=$([bool]$AllowDraft)"
        if ($downloadAllowed -and -not $releaseRunSuccess) {
            Add-Step -Name "release_run_draft_artifacts_allowed" -Ok $true -Details "downloading artifacts from non-success run because -AllowDraft is set" -Required $false
        }
    }
    else {
        Add-Step -Name "release_run_success" -Ok $false -Details "no run"
        Add-Step -Name "release_run_artifact_downloadable" -Ok $false -Details "no run"
    }
}
catch {
    Add-Step -Name "release_run_found" -Ok $false -Details $_.Exception.Message
    Add-Step -Name "release_run_success" -Ok $false -Details $_.Exception.Message
    Add-Step -Name "release_run_artifact_downloadable" -Ok $false -Details $_.Exception.Message
}

try {
    if ($usingFixture) {
        $artifactSource = (Resolve-Path -LiteralPath $ArtifactSourceDir).Path
        Add-Step -Name "artifact_source" -Ok $true -Details "fixture=$artifactSource"
    }
    elseif ($run -and $run.status -eq "completed" -and ($run.conclusion -eq "success" -or [bool]$AllowDraft)) {
        New-Item -ItemType Directory -Path $downloadRoot -Force | Out-Null
        $downloadOutput = (& gh run download $run.databaseId --repo $Repo --name $ArtifactName --dir $downloadRoot 2>&1) -join "`n"
        if ($LASTEXITCODE -ne 0) {
            throw $downloadOutput
        }
        $artifactSource = (Resolve-Path -LiteralPath $downloadRoot).Path
        Add-Step -Name "artifact_download" -Ok $true -Details "run=$($run.databaseId); artifact=$ArtifactName; dir=$artifactSource"
    }
    else {
        Add-Step -Name "artifact_download" -Ok $false -Details "release run is not downloadable; status=$(if ($run) { $run.status } else { '<missing>' }); conclusion=$(if ($run) { $run.conclusion } else { '<missing>' }); allowDraft=$([bool]$AllowDraft)"
    }

    if (-not [string]::IsNullOrWhiteSpace($artifactSource)) {
        Copy-ArtifactTree -SourceDir $artifactSource -DestinationDir $OutputDir
        Add-Step -Name "artifact_copy" -Ok ($copiedFiles.Count -gt 0) -Details "copied=$($copiedFiles.Count) files into $OutputDir"
    }
    else {
        Add-Step -Name "artifact_copy" -Ok $false -Details "artifact source missing"
    }
}
catch {
    Add-Step -Name "artifact_copy" -Ok $false -Details $_.Exception.Message
}

try {
    $summaryOutput = Invoke-ReleaseSummary
    Add-Step -Name "release_summary_refresh" -Ok $true -Details ($summaryOutput -replace "\|", "/")
}
catch {
    Add-Step -Name "release_summary_refresh" -Ok $false -Details $_.Exception.Message
}

$releaseSummary = Read-LatestJson -Filter "release-summary-*.json"
$alibabaRelease = Read-LatestJson -Filter "alibaba-release-*.json"
$finalBundleZip = Get-LatestFile -Filter "final-upload-bundle-*.zip"
$backendUrl = ""
if ($releaseSummary.data -and -not [string]::IsNullOrWhiteSpace([string]$releaseSummary.data.backendUrl)) {
    $backendUrl = [string]$releaseSummary.data.backendUrl
}
elseif ($alibabaRelease.data) {
    $backendUrl = [string]$alibabaRelease.data.backendUrl
}

$requiredFailures = @($steps | Where-Object { $_.required -and -not $_.ok })
$ready = $requiredFailures.Count -eq 0 -and $copiedFiles.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace($releaseSummary.file)
$status = if ($ready) { "READY" } else { "DRAFT" }

$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = $status
    readyForGitHubReleaseArtifactIngest = $ready
    allowDraft = [bool]$AllowDraft
    repo = $Repo
    branch = $Branch
    workflowName = $WorkflowName
    artifactName = $ArtifactName
    runId = if ($run) { [string]$run.databaseId } else { $RunId }
    releaseRunSelection = $releaseRunSelection
    run = $run
    usingFixture = $usingFixture
    artifactSourceDir = $artifactSource
    outputDir = $OutputDir
    copiedFileCount = $copiedFiles.Count
    copiedFiles = $copiedFiles
    backendUrl = $backendUrl
    releaseSummaryJson = $releaseSummary.file
    releaseSummaryStatus = if ($releaseSummary.data) { $releaseSummary.data.status } else { "" }
    alibabaReleaseJson = $alibabaRelease.file
    finalBundleZip = if ($finalBundleZip) { $finalBundleZip.FullName } else { "" }
    steps = $steps
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud GitHub Release Artifact Ingest ($timestamp)",
    "",
    "- Status: $status",
    "- Ready for artifact ingest: $ready",
    "- Repo: $Repo",
    "- Workflow: $WorkflowName",
    "- Run: $(if ($run) { $run.databaseId } else { '<missing>' })",
    "- Run selection: $(if ($releaseRunSelection) { $releaseRunSelection } else { '<missing>' })",
    "- Allow draft/non-success run artifacts: $([bool]$AllowDraft)",
    "- Artifact: $ArtifactName",
    "- Source: $(if ($artifactSource) { $artifactSource } else { '<missing>' })",
    "- Copied files: $($copiedFiles.Count)",
    "- Backend URL: $(if ($backendUrl) { $backendUrl } else { '<missing>' })",
    "- Release summary: $(if ($releaseSummary.file) { $releaseSummary.file } else { '<missing>' })",
    "- Release summary status: $(if ($releaseSummary.data) { $releaseSummary.data.status } else { '<missing>' })",
    "- Final bundle zip: $(if ($finalBundleZip) { $finalBundleZip.FullName } else { '<missing>' })",
    "",
    "## Steps",
    "",
    "| Step | Required | Result | Details |",
    "|---|---:|---:|---|"
)
foreach ($step in $steps) {
    $lines += "| $($step.name) | $(if ($step.required) { 'yes' } else { 'no' }) | $(if ($step.ok) { 'PASS' } else { 'FAIL' }) | $($step.details -replace '\|', '/') |"
}

if ($backendUrl) {
    $lines += @(
        "",
        "## Next Command",
        "",
        '```powershell',
        "scripts/qwencloud-finalize-after-urls.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl `"<public-video-url>`" -BackendUrl `"$backendUrl`" -RefreshAlibabaProof",
        '```'
    )
}

Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($ready) {
    Write-Host "GitHub release artifact ingest READY: $reportMd"
}
else {
    Write-Host "GitHub release artifact ingest DRAFT: $reportMd" -ForegroundColor Yellow
    Write-Host "Missing required steps: $($requiredFailures.name -join ', ')"
    if (-not $AllowDraft) {
        exit 1
    }
}
Write-Host "JSON: $reportJson"
