# SPDX-License-Identifier: Apache-2.0
param(
    [Parameter(Mandatory = $false)]
    [string]$RepoUrl = "https://github.com/zemeng2015/dream-ai-engineering-copilot",
    [Parameter(Mandatory = $false)]
    [string]$Branch = "main",
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [string]$RepoJsonPath = "",
    [Parameter(Mandatory = $false)]
    [string]$RunsJsonPath = "",
    [Parameter(Mandatory = $false)]
    [string]$GitHead = "",
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$reportJson = Join-Path $OutputDir "github-ci-proof-$timestamp.json"
$reportMd = Join-Path $OutputDir "github-ci-proof-$timestamp.md"
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

    try {
        return (git rev-parse HEAD).Trim()
    }
    catch {
        return ""
    }
}

function Get-RemoteSyncDetails {
    try {
        $sync = (git rev-list --left-right --count "HEAD...@{u}") -split "\s+"
        $ahead = [int]$sync[0]
        $behind = [int]$sync[1]
        return [pscustomobject]@{
            ok = ($ahead -eq 0 -and $behind -eq 0)
            details = "ahead=$ahead; behind=$behind"
        }
    }
    catch {
        return [pscustomobject]@{
            ok = $false
            details = $_.Exception.Message
        }
    }
}

function Get-RepoData([string]$RepoName) {
    if (-not [string]::IsNullOrWhiteSpace($RepoJsonPath)) {
        return Read-JsonPath -Path $RepoJsonPath
    }

    $json = gh repo view $RepoName --json nameWithOwner,visibility,isPrivate,url,licenseInfo,defaultBranchRef,pushedAt
    return $json | ConvertFrom-Json
}

function Get-RunData([string]$RepoName) {
    if (-not [string]::IsNullOrWhiteSpace($RunsJsonPath)) {
        return ConvertTo-FlatArray -Value (Read-JsonPath -Path $RunsJsonPath)
    }

    $json = gh run list --repo $RepoName --branch $Branch --limit 20 --json databaseId,headSha,status,conclusion,displayTitle,url,createdAt,updatedAt,event,workflowName
    return ConvertTo-FlatArray -Value ($json | ConvertFrom-Json)
}

$usingFixtures = (-not [string]::IsNullOrWhiteSpace($RepoJsonPath)) -and (-not [string]::IsNullOrWhiteSpace($RunsJsonPath))
$repoName = Get-RepoName -Url $RepoUrl
$head = Get-LocalHead

Add-Check -Name "repo_url_github" -Ok (-not [string]::IsNullOrWhiteSpace($repoName)) -Details $(if ($repoName) { $repoName } else { "not a normalized GitHub HTTPS repo URL: $RepoUrl" })
Add-Check -Name "git_head_present" -Ok (-not [string]::IsNullOrWhiteSpace($head)) -Details $(if ($head) { $head } else { "missing git HEAD" })
Add-Check -Name "gh_command_available" -Ok (Has-Command "gh") -Details $(if (Has-Command "gh") { (Get-Command "gh").Source } else { "missing" }) -Required (-not $usingFixtures)

$remoteSync = if ($usingFixtures) {
    [pscustomobject]@{ ok = $true; details = "skipped for fixture run" }
}
else {
    Get-RemoteSyncDetails
}
Add-Check -Name "git_remote_synced" -Ok $remoteSync.ok -Details $remoteSync.details -Required (-not $usingFixtures)

$repo = $null
$repoDetails = ""
try {
    if ([string]::IsNullOrWhiteSpace($repoName)) {
        throw "RepoUrl is not a normalized GitHub HTTPS URL."
    }
    if (-not $usingFixtures -and -not (Has-Command "gh")) {
        throw "gh command missing."
    }
    $repo = Get-RepoData -RepoName $repoName
    $licenseKey = ""
    if ($repo.licenseInfo) {
        $licenseKey = [string]$repo.licenseInfo.key
    }
    elseif ($repo.license) {
        $licenseKey = [string]$repo.license.spdx_id
    }
    $repoDetails = "repo=$($repo.nameWithOwner); visibility=$($repo.visibility); isPrivate=$($repo.isPrivate); license=$licenseKey; url=$($repo.url)"
    Add-Check -Name "repo_public" -Ok (($repo.visibility -eq "PUBLIC") -and -not [bool]$repo.isPrivate) -Details $repoDetails
    Add-Check -Name "repo_license_apache_2_0" -Ok ($licenseKey -eq "apache-2.0" -or $licenseKey -eq "Apache-2.0") -Details $repoDetails
}
catch {
    Add-Check -Name "repo_public" -Ok $false -Details $_.Exception.Message
    Add-Check -Name "repo_license_apache_2_0" -Ok $false -Details $_.Exception.Message
}

$matchingRun = $null
try {
    if ([string]::IsNullOrWhiteSpace($repoName) -or [string]::IsNullOrWhiteSpace($head)) {
        throw "Repo name or git HEAD missing."
    }
    if (-not $usingFixtures -and -not (Has-Command "gh")) {
        throw "gh command missing."
    }
    $runs = @(Get-RunData -RepoName $repoName)
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
    $matchingRun = if ($matchingRuns.Count -gt 0) { $matchingRuns[0] } else { $null }
    Add-Check -Name "ci_run_for_head_present" -Ok ($null -ne $matchingRun) -Details $(if ($matchingRun) { "$($matchingRun.displayTitle); $($matchingRun.url)" } else { "no run found for HEAD $head on branch $Branch" })
    if ($matchingRun) {
        Add-Check -Name "ci_run_completed_success" -Ok ($matchingRun.status -eq "completed" -and $matchingRun.conclusion -eq "success") -Details "status=$($matchingRun.status); conclusion=$($matchingRun.conclusion); url=$($matchingRun.url)"
    }
    else {
        Add-Check -Name "ci_run_completed_success" -Ok $false -Details "no matching run"
    }
}
catch {
    Add-Check -Name "ci_run_for_head_present" -Ok $false -Details $_.Exception.Message
    Add-Check -Name "ci_run_completed_success" -Ok $false -Details $_.Exception.Message
}

$requiredFailures = @($checks | Where-Object { $_.required -and -not $_.ok })
$ready = $requiredFailures.Count -eq 0

$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = if ($ready) { "READY" } else { "DRAFT" }
    readyForGitHubCiProof = $ready
    repoUrl = $RepoUrl
    repoName = $repoName
    branch = $Branch
    gitHead = $head
    usingFixtures = $usingFixtures
    repo = $repo
    matchingRun = $matchingRun
    reportJson = $reportJson
    reportMarkdown = $reportMd
    checks = $checks
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud GitHub CI Proof ($timestamp)",
    "",
    "- Ready for CI proof: $ready",
    "- Repo: $RepoUrl",
    "- Branch: $Branch",
    "- Git HEAD: $(if ($head) { $head } else { '<missing>' })",
    "- CI run: $(if ($matchingRun) { $matchingRun.url } else { '<missing>' })",
    "",
    "## Checks",
    "",
    "| Check | Required | Result | Details |",
    "|---|---:|---:|---|"
)
foreach ($check in $checks) {
    $required = if ($check.required) { "yes" } else { "no" }
    $resultText = if ($check.ok) { "PASS" } else { "FAIL" }
    $lines += "| $($check.name) | $required | $resultText | $($check.details -replace '\|', '/') |"
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

Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($ready) {
    Write-Host "GitHub CI proof READY: $reportMd"
}
else {
    Write-Host "GitHub CI proof DRAFT: $reportMd" -ForegroundColor Yellow
    Write-Host "Missing required checks: $($requiredFailures.name -join ', ')"
    if (-not $AllowDraft) {
        exit 1
    }
}
Write-Host "JSON: $reportJson"
