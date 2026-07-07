param(
    [Parameter(Mandatory = $true)]
    [string]$BaseUrl,
    [Parameter(Mandatory = $false)]
    [string]$OutputPng = "artifacts/qwencloud-proof/alibaba-deployment-screenshot.png",
    [Parameter(Mandatory = $false)]
    [int]$Width = 1280,
    [Parameter(Mandatory = $false)]
    [int]$Height = 720,
    [switch]$IncludeDraft,
    [switch]$AllowLocal
)

$ErrorActionPreference = "Stop"

function Assert-Equals($Actual, [string]$Expected, [string]$Field) {
    if ($Actual -ne $Expected) {
        throw "$Field mismatch: expected '$Expected', got '$Actual'."
    }
}

function Assert-Matches([string]$Actual, [string]$Pattern, [string]$Field) {
    if ($Actual -notmatch $Pattern) {
        throw "$Field mismatch: expected match '$Pattern', got '$Actual'."
    }
}

function Html-Escape([string]$Text) {
    if ($null -eq $Text) {
        return ""
    }
    return [System.Net.WebUtility]::HtmlEncode($Text)
}

function Get-Browser {
    $browserCandidates = @(
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "$env:ProgramFiles(x86)\Google\Chrome\Application\chrome.exe",
        "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
        "$env:ProgramFiles(x86)\Microsoft\Edge\Application\msedge.exe"
    )

    $browser = $browserCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $browser) {
        foreach ($commandName in @("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "msedge")) {
            $command = Get-Command $commandName -ErrorAction SilentlyContinue
            if ($command) {
                $browser = $command.Source
                break
            }
        }
    }
    if (-not $browser) {
        throw "Chrome or Edge is required to capture the Alibaba deployment proof screenshot."
    }
    return $browser
}

function Add-Row([string]$Name, [bool]$Pass, [string]$Details) {
    $script:checks += [ordered]@{
        name = $Name
        pass = $Pass
        details = $Details
    }
}

if ($BaseUrl -notmatch "^https?://") {
    throw "BaseUrl must be an http(s) URL."
}

$base = $BaseUrl.TrimEnd("/")
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$artifactDir = "artifacts/qwencloud-proof"
New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null

$jsonPath = Join-Path $artifactDir "alibaba-deployment-proof-$timestamp.json"
$htmlPath = Join-Path $artifactDir "alibaba-deployment-proof-$timestamp.html"
$resolvedOutput = Join-Path (Get-Location) $OutputPng
$outputDir = Split-Path -Parent $resolvedOutput
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

$checks = @()
$health = $null
$draft = $null

try {
    $health = Invoke-RestMethod -Method Get -Uri "$base/health" -TimeoutSec 20 -ErrorAction Stop
    Add-Row -Name "health_reachable" -Pass $true -Details "$base/health"
}
catch {
    Add-Row -Name "health_reachable" -Pass $false -Details $_.Exception.Message
    throw "Unable to read deployment health from $base/health"
}

Assert-Equals -Actual $health.status -Expected "ok" -Field "status"
Add-Row -Name "status_ok" -Pass $true -Details $health.status

Assert-Equals -Actual $health.track -Expected "Track 1: MemoryAgent" -Field "track"
Add-Row -Name "track_memoryagent" -Pass $true -Details $health.track

Assert-Equals -Actual $health.llm_provider -Expected "qwen-cloud" -Field "llm_provider"
Add-Row -Name "provider_qwen_cloud" -Pass $true -Details $health.llm_provider

Assert-Equals -Actual $health.proof_file -Expected "deploy/alibaba/serverless-devs.yaml" -Field "proof_file"
Add-Row -Name "proof_file" -Pass $true -Details $health.proof_file

if ($AllowLocal) {
    Add-Row -Name "deployment_target_alibaba" -Pass ($health.deployment_target -match "Alibaba Cloud|local") -Details "$($health.deployment_target) (AllowLocal)"
}
else {
    Assert-Matches -Actual $health.deployment_target -Pattern "Alibaba Cloud Function Compute" -Field "deployment_target"
    Add-Row -Name "deployment_target_alibaba" -Pass $true -Details $health.deployment_target
}

if ($AllowLocal) {
    Add-Row -Name "alibaba_region_present" -Pass $true -Details $(if ($health.alibaba_cloud_region) { $health.alibaba_cloud_region } else { "AllowLocal" })
}
else {
    if ([string]::IsNullOrWhiteSpace($health.alibaba_cloud_region)) {
        throw "alibaba_cloud_region is missing from /health."
    }
    Add-Row -Name "alibaba_region_present" -Pass $true -Details $health.alibaba_cloud_region
}

if ($IncludeDraft) {
    $body = @{
        team_id = "demo_team"
        rough_business_request = "Users need to know why a forecast job is stuck running"
        llm_provider = "qwen-cloud"
    } | ConvertTo-Json
    $draft = Invoke-RestMethod -Method Post -Uri "$base/requirements/draft" -Body $body -ContentType "application/json" -TimeoutSec 45 -ErrorAction Stop
    if (-not $draft.markdown) {
        throw "requirements/draft response missing markdown."
    }
    Add-Row -Name "draft_generation" -Pass $true -Details $(if ($draft.run_id) { "run_id=$($draft.run_id)" } else { "markdown returned" })
}
else {
    Add-Row -Name "draft_generation" -Pass $true -Details "skipped" 
}

$proof = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    baseUrl = $base
    outputPng = $OutputPng
    allowLocal = [bool]$AllowLocal
    includeDraft = [bool]$IncludeDraft
    health = $health
    draft = $draft
    checks = $checks
}
Set-Content -Path $jsonPath -Value ($proof | ConvertTo-Json -Depth 20) -Encoding UTF8

$healthJson = Html-Escape (($health | ConvertTo-Json -Depth 20) -join "`n")
$draftStatus = if ($IncludeDraft) { "Captured" } else { "Skipped" }
$rows = foreach ($check in $checks) {
    $class = if ($check.pass) { "pass" } else { "fail" }
    $status = if ($check.pass) { "PASS" } else { "FAIL" }
    "<tr><td>$(Html-Escape $check.name)</td><td class=""$class"">$status</td><td>$(Html-Escape $check.details)</td></tr>"
}

$html = @"
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>DREAM Qwen Cloud Alibaba Deployment Proof</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #17202a;
      --muted: #52606d;
      --line: #d9e2ec;
      --bg: #f6f8fb;
      --panel: #ffffff;
      --accent: #0f766e;
      --accent-2: #1d4ed8;
      --warn: #b45309;
      --ok-bg: #dcfce7;
      --ok: #166534;
      --fail-bg: #fee2e2;
      --fail: #991b1b;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      width: 1280px;
      min-height: 720px;
      background: var(--bg);
      color: var(--ink);
      font-family: "Segoe UI", Arial, sans-serif;
      letter-spacing: 0;
    }
    .page {
      width: 1280px;
      min-height: 720px;
      padding: 40px 52px;
    }
    header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 28px;
      border-bottom: 2px solid var(--line);
      padding-bottom: 22px;
    }
    h1 {
      margin: 0 0 10px;
      font-size: 36px;
      line-height: 1.08;
      font-weight: 700;
    }
    .subtitle {
      margin: 0;
      color: var(--muted);
      font-size: 18px;
      line-height: 1.35;
      max-width: 820px;
    }
    .badge {
      border: 1px solid #99f6e4;
      background: #ccfbf1;
      color: #115e59;
      padding: 10px 14px;
      border-radius: 6px;
      font-size: 15px;
      font-weight: 700;
      white-space: nowrap;
    }
    .grid {
      display: grid;
      grid-template-columns: 1.05fr 0.95fr;
      gap: 24px;
      margin-top: 24px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 22px;
    }
    h2 {
      margin: 0 0 16px;
      font-size: 20px;
      line-height: 1.2;
    }
    dl {
      display: grid;
      grid-template-columns: 190px 1fr;
      gap: 10px 16px;
      margin: 0;
      font-size: 15px;
      line-height: 1.28;
    }
    dt { color: var(--muted); font-weight: 700; }
    dd {
      margin: 0;
      overflow-wrap: anywhere;
    }
    .strong { color: var(--accent-2); font-weight: 700; }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
      line-height: 1.25;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 8px 6px;
      text-align: left;
      vertical-align: top;
    }
    th { color: var(--muted); font-size: 13px; }
    td.pass {
      color: var(--ok);
      font-weight: 800;
      background: var(--ok-bg);
      border-radius: 4px;
      text-align: center;
    }
    td.fail {
      color: var(--fail);
      font-weight: 800;
      background: var(--fail-bg);
      border-radius: 4px;
      text-align: center;
    }
    pre {
      margin: 0;
      max-height: 232px;
      overflow: hidden;
      background: #0b1220;
      color: #dbeafe;
      border-radius: 6px;
      padding: 16px;
      font-size: 12px;
      line-height: 1.35;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
    footer {
      margin-top: 20px;
      color: var(--muted);
      font-size: 13px;
      display: flex;
      justify-content: space-between;
      gap: 18px;
      border-top: 1px solid var(--line);
      padding-top: 14px;
    }
  </style>
</head>
<body>
  <main class="page">
    <header>
      <div>
        <h1>DREAM Qwen Cloud Deployment Proof</h1>
        <p class="subtitle">Machine-verified Alibaba Cloud Function Compute runtime proof for the Qwen Cloud Hackathon Devpost submission.</p>
      </div>
      <div class="badge">Track 1: MemoryAgent</div>
    </header>

    <section class="grid">
      <div class="panel">
        <h2>Runtime Evidence</h2>
        <dl>
          <dt>Backend URL</dt><dd>$(Html-Escape $base)</dd>
          <dt>Status</dt><dd class="strong">$(Html-Escape $health.status)</dd>
          <dt>Deployment Target</dt><dd class="strong">$(Html-Escape $health.deployment_target)</dd>
          <dt>Alibaba Region</dt><dd>$(Html-Escape $health.alibaba_cloud_region)</dd>
          <dt>Alibaba Service</dt><dd>$(Html-Escape $health.alibaba_cloud_service)</dd>
          <dt>LLM Provider</dt><dd class="strong">$(Html-Escape $health.llm_provider)</dd>
          <dt>LLM Model</dt><dd>$(Html-Escape $health.llm_model)</dd>
          <dt>Qwen Base URL</dt><dd>$(Html-Escape $health.llm_base_url)</dd>
          <dt>API Key Configured</dt><dd>$(Html-Escape $health.llm_api_key_configured)</dd>
          <dt>Proof File</dt><dd class="strong">$(Html-Escape $health.proof_file)</dd>
          <dt>Draft Proof</dt><dd>$(Html-Escape $draftStatus)</dd>
        </dl>
      </div>

      <div class="panel">
        <h2>Automated Checks</h2>
        <table>
          <thead><tr><th>Check</th><th>Result</th><th>Details</th></tr></thead>
          <tbody>
            $($rows -join "`n")
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel" style="margin-top: 24px;">
      <h2>/health Response</h2>
      <pre>$healthJson</pre>
    </section>

    <footer>
      <span>Generated: $((Get-Date).ToUniversalTime().ToString("o"))</span>
      <span>JSON proof: $(Html-Escape $jsonPath)</span>
    </footer>
  </main>
</body>
</html>
"@
Set-Content -Path $htmlPath -Value $html -Encoding UTF8

if (Test-Path $resolvedOutput) {
    Remove-Item -LiteralPath $resolvedOutput -Force
}

$browser = Get-Browser
$tempOutput = Join-Path ([System.IO.Path]::GetTempPath()) "dream-qwencloud-alibaba-proof-$([System.Guid]::NewGuid().ToString('N')).png"
$tempProfile = Join-Path ([System.IO.Path]::GetTempPath()) "dream-qwencloud-alibaba-proof-$([System.Guid]::NewGuid().ToString('N'))"
$htmlUri = [System.Uri]::new((Resolve-Path $htmlPath).Path).AbsoluteUri
$args = @(
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--no-first-run",
    "--no-default-browser-check",
    "--user-data-dir=$tempProfile",
    "--hide-scrollbars",
    "--window-size=$Width,$Height",
    "--screenshot=$tempOutput",
    $htmlUri
)

$stdout = Join-Path $artifactDir "alibaba-proof-screenshot-$timestamp.out"
$stderr = Join-Path $artifactDir "alibaba-proof-screenshot-$timestamp.err"
$proc = Start-Process -FilePath $browser -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
if ($proc.ExitCode -ne 0) {
    throw "Alibaba proof screenshot failed. See $stderr"
}

if (Test-Path $tempProfile) {
    Remove-Item -LiteralPath $tempProfile -Recurse -Force
}

if (-not (Test-Path $tempOutput)) {
    throw "Alibaba proof screenshot was not created: $tempOutput"
}

Move-Item -LiteralPath $tempOutput -Destination $resolvedOutput -Force
$file = Get-Item -LiteralPath $resolvedOutput
if ($file.Length -le 0) {
    throw "Alibaba proof screenshot is empty: $OutputPng"
}

Write-Host "Alibaba deployment proof screenshot exported: $OutputPng ($($file.Length) bytes)"
Write-Host "Proof JSON: $jsonPath"
Write-Host "Proof HTML: $htmlPath"
