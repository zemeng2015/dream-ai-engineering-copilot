# SPDX-License-Identifier: Apache-2.0

param(
    [Parameter(Mandatory = $false)]
    [string]$OverviewUrl = "https://qwencloud-hackathon.devpost.com/",
    [Parameter(Mandatory = $false)]
    [string]$RulesUrl = "https://qwencloud-hackathon.devpost.com/rules",
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [string]$OverviewHtmlPath = "",
    [Parameter(Mandatory = $false)]
    [string]$RulesHtmlPath = "",
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$reportJson = Join-Path $OutputDir "official-source-refresh-$timestamp.json"
$reportMd = Join-Path $OutputDir "official-source-refresh-$timestamp.md"
$checks = @()

function Normalize-SourceText([string]$Text) {
    if ([string]::IsNullOrWhiteSpace($Text)) {
        return ""
    }

    $withoutTags = $Text -replace "<script[\s\S]*?</script>", " " `
        -replace "<style[\s\S]*?</style>", " " `
        -replace "<[^>]+>", " "
    $decoded = [System.Net.WebUtility]::HtmlDecode($withoutTags)
    return (($decoded -replace "\u00a0", " ") -replace "\s+", " ").Trim()
}

function Get-SourceText([string]$Url, [string]$Path, [string]$Label) {
    if (-not [string]::IsNullOrWhiteSpace($Path)) {
        if (-not (Test-Path -LiteralPath $Path)) {
            throw "$Label HTML fixture not found: $Path"
        }
        return [pscustomobject]@{
            ok = $true
            source = $Path
            text = Normalize-SourceText -Text (Get-Content -LiteralPath $Path -Raw)
            details = "read fixture: $Path"
        }
    }

    try {
        $response = Invoke-WebRequest `
            -Uri $Url `
            -UserAgent "dream-qwencloud-official-source-refresh/1.0" `
            -TimeoutSec 30 `
            -MaximumRedirection 5 `
            -UseBasicParsing
        return [pscustomobject]@{
            ok = ([int]$response.StatusCode -ge 200 -and [int]$response.StatusCode -lt 400)
            source = $Url
            text = Normalize-SourceText -Text ([string]$response.Content)
            details = "GET status=$([int]$response.StatusCode)"
        }
    }
    catch {
        return [pscustomobject]@{
            ok = $false
            source = $Url
            text = ""
            details = $_.Exception.Message
        }
    }
}

function Add-Check {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][bool]$Ok,
        [Parameter(Mandatory = $true)][string]$Details,
        [Parameter(Mandatory = $false)][bool]$Required = $true
    )

    $script:checks += [ordered]@{
        name = $Name
        ok = $Ok
        required = $Required
        details = $Details
    }
}

function Test-Text([string]$Text, [string]$Pattern) {
    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $false
    }
    return [bool]($Text -match $Pattern)
}

function Get-MatchSnippet([string]$Text, [string]$Pattern) {
    if ([string]::IsNullOrWhiteSpace($Text)) {
        return ""
    }
    $match = [regex]::Match($Text, $Pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if (-not $match.Success) {
        return ""
    }
    $start = [Math]::Max(0, $match.Index - 80)
    $length = [Math]::Min(220, $Text.Length - $start)
    return ($Text.Substring($start, $length) -replace "\|", "/").Trim()
}

$overview = Get-SourceText -Url $OverviewUrl -Path $OverviewHtmlPath -Label "Overview"
$rules = Get-SourceText -Url $RulesUrl -Path $RulesHtmlPath -Label "Rules"
$combined = "$($overview.text) $($rules.text)"

Add-Check -Name "overview_source_available" -Ok $overview.ok -Details $overview.details
Add-Check -Name "rules_source_available" -Ok $rules.ok -Details $rules.details
Add-Check `
    -Name "deadline_overview_present" `
    -Ok (Test-Text -Text $overview.text -Pattern "Deadline:\s*Jul\s+9,\s+2026\s+@\s+2:00pm\s+PDT") `
    -Details (Get-MatchSnippet -Text $overview.text -Pattern "Deadline:\s*Jul\s+9,\s+2026\s+@\s+2:00pm\s+PDT")
Add-Check `
    -Name "deadline_rules_present" `
    -Ok (Test-Text -Text $rules.text -Pattern "Jul\s+9,\s+2026\s*\(?2:00\s*pm\s+Pacific\s+Time") `
    -Details (Get-MatchSnippet -Text $rules.text -Pattern "Submission Period:.{0,180}Jul\s+9,\s+2026")
Add-Check `
    -Name "track1_memoryagent_present" `
    -Ok ((Test-Text -Text $combined -Pattern "Track\s+1:\s*MemoryAgent") -and (Test-Text -Text $combined -Pattern "persistent memory")) `
    -Details (Get-MatchSnippet -Text $combined -Pattern "Track\s+1:\s*MemoryAgent.{0,220}persistent memory")
Add-Check `
    -Name "qwen_cloud_model_requirement_present" `
    -Ok (Test-Text -Text $combined -Pattern "using Qwen models available on Qwen Cloud") `
    -Details (Get-MatchSnippet -Text $combined -Pattern "using Qwen models available on Qwen Cloud")
Add-Check `
    -Name "public_repo_requirement_present" `
    -Ok ((Test-Text -Text $combined -Pattern "code repository") -and (Test-Text -Text $combined -Pattern "public and open source")) `
    -Details (Get-MatchSnippet -Text $combined -Pattern "code repository.{0,260}public and open source")
Add-Check `
    -Name "alibaba_deployment_proof_requirement_present" `
    -Ok (Test-Text -Text $combined -Pattern "Proof of Alibaba Cloud Deployment") `
    -Details (Get-MatchSnippet -Text $combined -Pattern "Proof of Alibaba Cloud Deployment.{0,260}Alibaba Cloud")
Add-Check `
    -Name "architecture_diagram_requirement_present" `
    -Ok (Test-Text -Text $combined -Pattern "Architecture Diagram") `
    -Details (Get-MatchSnippet -Text $combined -Pattern "Architecture Diagram.{0,220}Qwen Cloud")
Add-Check `
    -Name "video_under_three_minutes_present" `
    -Ok (Test-Text -Text $combined -Pattern "less than three\s*\(3\)\s*minutes|about 3 minutes") `
    -Details (Get-MatchSnippet -Text $combined -Pattern "less than three\s*\(3\)\s*minutes|about 3 minutes")
Add-Check `
    -Name "video_platform_overview_facebook_present" `
    -Ok ((Test-Text -Text $overview.text -Pattern "YouTube") -and (Test-Text -Text $overview.text -Pattern "Vimeo") -and (Test-Text -Text $overview.text -Pattern "Facebook Video")) `
    -Details (Get-MatchSnippet -Text $overview.text -Pattern "YouTube.{0,120}Vimeo.{0,120}Facebook Video")
Add-Check `
    -Name "video_platform_rules_youku_present" `
    -Ok ((Test-Text -Text $rules.text -Pattern "YouTube") -and (Test-Text -Text $rules.text -Pattern "Vimeo") -and (Test-Text -Text $rules.text -Pattern "Youku")) `
    -Details (Get-MatchSnippet -Text $rules.text -Pattern "YouTube.{0,120}Vimeo.{0,120}Youku")
Add-Check `
    -Name "testing_access_requirement_present" `
    -Ok (Test-Text -Text $rules.text -Pattern "Access must be provided.{0,240}working Project") `
    -Details (Get-MatchSnippet -Text $rules.text -Pattern "Access must be provided.{0,260}working Project")
Add-Check `
    -Name "judging_weights_present" `
    -Ok ((Test-Text -Text $combined -Pattern "Innovation\s*&\s*AI Creativity\s*\(30%\)") -and (Test-Text -Text $combined -Pattern "Technical Depth\s*&\s*Engineering\s*\(30%\)") -and (Test-Text -Text $combined -Pattern "Problem Value\s*&\s*Impact\s*\(25%\)") -and (Test-Text -Text $combined -Pattern "Presentation\s*&\s*Documentation\s*\(15%\)")) `
    -Details "30/30/25/15 criteria detected"
Add-Check `
    -Name "optional_blog_post_present" `
    -Ok (Test-Text -Text $combined -Pattern "Blog.*Social Post|Blog Post Prize") `
    -Details (Get-MatchSnippet -Text $combined -Pattern "Blog.*Social Post|Blog Post Prize") `
    -Required $false

$requiredFailures = @($checks | Where-Object { $_.required -and -not $_.ok })
$ready = $requiredFailures.Count -eq 0
$videoPlatformUnion = @("YouTube", "Vimeo", "Facebook Video", "Youku")

$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = if ($ready) { "READY" } else { "DRAFT" }
    readyForOfficialSourceSnapshot = $ready
    overviewUrl = $OverviewUrl
    rulesUrl = $RulesUrl
    overviewHtmlPath = $OverviewHtmlPath
    rulesHtmlPath = $RulesHtmlPath
    overviewSource = $overview.source
    rulesSource = $rules.source
    acceptedVideoPlatformUnion = $videoPlatformUnion
    recommendedVideoPlatforms = @("YouTube", "Vimeo")
    checks = $checks
    missingRequiredChecks = @($requiredFailures | ForEach-Object { $_.name })
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Official Source Refresh ($timestamp)",
    "",
    "- Status: $($result.status)",
    "- Ready for official source snapshot: $ready",
    "- Overview source: $($overview.source)",
    "- Rules source: $($rules.source)",
    "- Accepted video platform union: $($videoPlatformUnion -join ', ')",
    "- Recommended final video platforms: YouTube, Vimeo",
    "",
    "## Checks",
    "",
    "| Check | Required | Result | Evidence |",
    "|---|---:|---:|---|"
)
foreach ($check in $checks) {
    $required = if ($check.required) { "yes" } else { "no" }
    $resultText = if ($check.ok) { "PASS" } else { "FAIL" }
    $details = ([string]$check.details) -replace "\|", "/"
    $lines += "| $($check.name) | $required | $resultText | $details |"
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
    "## Video Platform Note",
    "",
    "The public overview names YouTube, Vimeo, and Facebook Video. The Official Rules page names YouTube, Vimeo, and Youku. The local validator accepts the union so a rules-compliant URL is not rejected, while the final handoff recommends YouTube or Vimeo to minimize ambiguity.",
    "",
    "## Next Commands",
    "",
    '```powershell',
    'scripts/qwencloud-video-upload-status.ps1 -DemoVideoUrl "<public-video-url>"',
    'scripts/qwencloud-official-rules-gate.ps1 -DemoVideoUrl "<public-video-url>" -BackendUrl "<deployed-backend-url>"',
    '```'
)
Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($ready) {
    Write-Host "Official source refresh READY: $reportMd"
}
else {
    Write-Host "Official source refresh DRAFT: $reportMd" -ForegroundColor Yellow
    Write-Host "Missing required checks: $($requiredFailures.name -join ', ')"
}
Write-Host "JSON: $reportJson"

if (-not $ready -and -not $AllowDraft) {
    exit 1
}
