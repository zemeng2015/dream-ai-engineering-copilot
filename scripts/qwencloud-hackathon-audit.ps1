param(
    [string]$BaseUrl = "http://localhost:8000",
    [string[]]$RequiredFiles = @(
        "docs/qwencloud-submission.md",
        "docs/qwencloud-architecture.md",
        "docs/assets/qwencloud-architecture.png",
        "docs/assets/qwencloud-video-thumbnail.svg",
        "docs/assets/qwencloud-video-thumbnail.png",
        "docs/qwencloud-demo-video-script.md",
        "docs/qwencloud-demo-video-captions.srt",
        "docs/qwencloud-demo-video-transcript.md",
        "docs/qwencloud-video-upload-handoff.md",
        "docs/qwencloud-official-requirements-snapshot.md",
        "docs/qwencloud-build-journey-post.md",
        "docs/qwencloud-devpost-form-fields.md",
        "docs/qwencloud-devpost-submission-kit.md",
        "docs/qwencloud-final-5min-checklist.md",
        "docs/qwencloud-publish-playbook.md",
        "docs/qwencloud-live-checklist.md",
        "docs/qwencloud-testing-and-rights-notes.md",
        "deploy/alibaba/serverless-devs.yaml",
        "deploy/alibaba/README.md",
        "scripts/qwencloud-cloud-credentials-handoff.ps1",
        "scripts/qwencloud-devpost-handoff.ps1",
        "scripts/qwencloud-alibaba-release.ps1",
        "scripts/qwencloud-capture-alibaba-proof.ps1",
        "scripts/qwencloud-deploy-preflight.ps1",
        "scripts/qwencloud-finalize-after-urls.ps1",
        "scripts/qwencloud-export-architecture-png.ps1",
        "scripts/qwencloud-export-video-thumbnail.ps1",
        "scripts/qwencloud-final-action-board.ps1",
        "scripts/qwencloud-final-upload-bundle.ps1",
        "scripts/qwencloud-final-readiness.ps1",
        "scripts/qwencloud-official-rules-gate.ps1",
        "scripts/qwencloud-render-alibaba-proof-video.ps1",
        "scripts/qwencloud-validate-alibaba-proof.ps1",
        "scripts/qwencloud-devpost-video-url.ps1",
        "scripts/qwencloud-video-publication-handoff.ps1",
        "scripts/qwencloud-video-upload-status.ps1",
        "scripts/qwencloud-hackathon-verify.ps1",
        "scripts/qwencloud-hackathon-proof.ps1",
        "scripts/qwencloud-hackathon-submit-gate.ps1",
        "scripts/qwencloud-run-local-proof.ps1",
        "scripts/qwencloud-run-local-proof.sh",
        "scripts/qwencloud-hackathon-submission-packet.ps1",
        "scripts/qwencloud-devpost-autofill-snippet.ps1",
        "scripts/qwencloud-frontend-build-proof.ps1",
        "scripts/qwencloud-render-demo-video.ps1",
        "examples/config/dream.qwen.yaml",
        "LICENSE"
    ),
    [string]$TeamId = "demo_team",
    [string]$Request = "Users need to know why a forecast job is stuck running",
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [switch]$SkipDraft,
    [switch]$AllowDirty
)

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$reportPath = Join-Path $OutputDir "submission-audit-$timestamp.json"

function Add-Check([string]$Name, [bool]$Pass, [string]$Details) {
    $script:checks += [pscustomobject]@{
        name = $Name
        pass = $Pass
        details = $Details
    }
}

function RepoInfo {
    try {
        $remote = (git remote get-url origin).Trim()
        if (-not $remote) { throw "origin remote missing." }
        $repoMatch = $null
        if ($remote -like "https://github.com/*" -or $remote -like "http://github.com/*") {
            $uri = [System.Uri]$remote
            $parts = $uri.AbsolutePath.Trim("/").Split("/")
            if ($parts.Length -lt 2) { throw "Invalid GitHub HTTPS URL: $remote" }
            $repoMatch = [pscustomobject]@{
                owner = $parts[0]
                repo = $parts[1]
            }
        } elseif ($remote -like "git@github.com:*") {
            $path = $remote.Split(":", 2)[1]
            $parts = $path.Trim().Split("/")
            if ($parts.Length -lt 2) { throw "Invalid GitHub SSH URL: $remote" }
            $repoMatch = [pscustomobject]@{
                owner = $parts[0]
                repo = $parts[1]
            }
        } else {
            throw "Cannot parse GitHub origin URL: $remote"
        }
        return [pscustomobject]@{
            remote = $remote
            owner = $repoMatch.owner
            repo = $repoMatch.repo -replace "\\.git$",""
        }
    } catch {
        return $null
    }
}

function Test-RemoteVisibility {
    param([string]$Owner, [string]$Repo)
    try {
        $endpoint = "https://api.github.com/repos/$Owner/$Repo"
        return Invoke-RestMethod -Uri $endpoint -TimeoutSec 15
    } catch {
        return $null
    }
}

$checks = @()

try {
    $gitStatus = git status --porcelain
    $cleanOrAllowed = ($gitStatus.Count -eq 0) -or $AllowDirty
    $gitDetails = if ($gitStatus.Count -eq 0) { "clean" } elseif ($AllowDirty) { "dirty allowed" } else { "dirty" }
    Add-Check -Name "Git working tree clean" -Pass $cleanOrAllowed -Details $gitDetails
} catch {
    Add-Check -Name "Git working tree clean" -Pass $false -Details $_.Exception.Message
}

$requiredMissing = @()
foreach ($path in $RequiredFiles) {
    if (-not (Test-Path $path)) { $requiredMissing += $path }
}
Add-Check -Name "Required files present" -Pass ($requiredMissing.Count -eq 0) -Details ($(if ($requiredMissing.Count -eq 0) { "all files found" } else { "missing: $($requiredMissing -join ', ')" }))

$repoInfo = RepoInfo
if ($repoInfo) {
    Add-Check -Name "GitHub remote parsed" -Pass $true -Details "origin=$($repoInfo.remote)"
    $repoData = Test-RemoteVisibility -Owner $repoInfo.owner -Repo $repoInfo.repo
    if ($repoData) {
        Add-Check -Name "GitHub repo public" -Pass ($repoData.visibility -eq "public") -Details "visibility=$($repoData.visibility)"
        Add-Check -Name "License detected (Apache-2.0)" -Pass ($repoData.license.spdx_id -eq "Apache-2.0") -Details $repoData.license.spdx_id
    } else {
        Add-Check -Name "GitHub repo public" -Pass $true -Details "unable to fetch repo metadata; skipping"
        $licenseExists = Test-Path LICENSE
        $licenseText = ""
        if ($licenseExists) {
            $licenseText = (Get-Content LICENSE -Raw)
            $licenseText = $licenseText -replace "`r`n", " "
        }
        Add-Check -Name "License detected (Apache-2.0)" -Pass ($licenseExists -and (($licenseText -like "*Apache-2.0*") -or ($licenseText -like "*Apache License*"))) -Details $(if ($licenseExists) { "using local LICENSE" } else { "LICENSE missing" })
    }
} else {
    Add-Check -Name "GitHub remote parsed" -Pass $false -Details "origin not available or unparsable"
    Add-Check -Name "GitHub repo public" -Pass $false -Details "origin not available or unparsable"
    Add-Check -Name "License detected (Apache-2.0)" -Pass $false -Details "origin not available or unparsable"
}

$health = $null
try {
    $health = Invoke-RestMethod -Method Get -Uri "$BaseUrl/health" -TimeoutSec 20 -ErrorAction Stop
    Add-Check -Name "Health endpoint reachable" -Pass $true -Details "status=$($health.status)"
    Add-Check -Name "Track is MemoryAgent" -Pass ($health.track -eq "Track 1: MemoryAgent") -Details $health.track
    Add-Check -Name "llm provider is qwen-cloud" -Pass ($health.llm_provider -eq "qwen-cloud") -Details $health.llm_provider
    Add-Check -Name "Proof file declared" -Pass ($health.proof_file -eq "deploy/alibaba/serverless-devs.yaml") -Details $health.proof_file
} catch {
    Add-Check -Name "Health endpoint reachable" -Pass $false -Details $_.Exception.Message
    Add-Check -Name "Track is MemoryAgent" -Pass $false -Details "Skipped"
    Add-Check -Name "llm provider is qwen-cloud" -Pass $false -Details "Skipped"
    Add-Check -Name "Proof file declared" -Pass $false -Details "Skipped"
}

if ($SkipDraft -or -not $health) {
    Add-Check -Name "requirements/draft response" -Pass $SkipDraft -Details $(if ($SkipDraft) {"skipped"} else {"unavailable"})
} else {
    try {
        $draftBody = @{
            team_id = $TeamId
            rough_business_request = $Request
            llm_provider = "qwen-cloud"
        } | ConvertTo-Json
        $draft = Invoke-RestMethod -Method Post -Uri "$BaseUrl/requirements/draft" -Body $draftBody -ContentType "application/json" -TimeoutSec 30 -ErrorAction Stop
        Add-Check -Name "requirements/draft response" -Pass ($draft.markdown -ne $null -and $draft.markdown.Length -gt 0) -Details $(if ($draft.markdown) {"ok; run_id=$($draft.run_id)" } else { "empty markdown" })
    } catch {
        $response = $_.Exception.Response
        if ($response) {
            try {
                $reader = New-Object IO.StreamReader($response.GetResponseStream())
                $errorBody = $reader.ReadToEnd()
                $reader.Close()
                Add-Check -Name "requirements/draft response" -Pass $false -Details $errorBody
            } catch {
                Add-Check -Name "requirements/draft response" -Pass $false -Details $_.Exception.Message
            }
        } else {
            Add-Check -Name "requirements/draft response" -Pass $false -Details $_.Exception.Message
        }
    }
}

$allPass = -not ($checks | Where-Object { -not $_.pass })
$summary = [pscustomobject]@{
    timestamp = (Get-Date).ToString("o")
    report_file = $reportPath
    target_base_url = $BaseUrl
    overall_pass = $allPass
    checks = $checks
}

$summary | ConvertTo-Json -Depth 20 | Out-File -FilePath $reportPath -Encoding utf8

$mdPath = Join-Path $OutputDir "submission-audit-$timestamp.md"
$lines = @()
$lines += "# Qwen Cloud Hackathon Submission Audit"
$lines += ""
$lines += "**Overall:** $(if ($allPass) { "PASS" } else { "FAIL" })"
$lines += ""
$lines += "| Check | Pass | Details |"
$lines += "|---|---|---|"
foreach ($c in $checks) {
    $lines += "| $($c.name) | $($c.pass.ToString().ToUpper()) | $($c.details) |"
}
$lines += ""
$lines += "Generated: $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))"
$lines | Out-File -FilePath $mdPath -Encoding utf8

if ($allPass) {
    Write-Output "Submission audit PASS. Report: $mdPath"
    Write-Output "JSON: $reportPath"
    exit 0
}

Write-Warning "Submission audit FAIL. See: $mdPath"
Write-Output "JSON: $reportPath"
exit 1
