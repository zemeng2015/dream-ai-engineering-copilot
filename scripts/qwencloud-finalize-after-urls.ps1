param(
    [Parameter(Mandatory = $false)]
    [string]$RepoUrl = "https://github.com/zemeng2015/dream-ai-engineering-copilot",
    [Parameter(Mandatory = $false)]
    [string]$DemoVideoUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$BackendUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$BlogPostUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [switch]$SkipBackendDraft,
    [switch]$SkipExternalUrlChecks,
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$reportJson = Join-Path $OutputDir "finalize-after-urls-$timestamp.json"
$reportMd = Join-Path $OutputDir "finalize-after-urls-$timestamp.md"
$steps = @()

function Add-Step([string]$Name, [bool]$Ok, [string]$Details, [string]$Markdown = "") {
    $script:steps += [ordered]@{
        name = $Name
        ok = $Ok
        details = $Details
        markdown = $Markdown
    }
}

function Get-PowerShellExe {
    $pwsh = Get-Command "pwsh" -ErrorAction SilentlyContinue
    if ($pwsh) { return $pwsh.Source }

    $powershell = Get-Command "powershell" -ErrorAction SilentlyContinue
    if ($powershell) { return $powershell.Source }

    throw "PowerShell executable not found."
}

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList,
        [Parameter(Mandatory = $false)][int[]]$AllowedExitCodes = @(0)
    )

    $stdout = Join-Path $OutputDir "$Name-$timestamp.out"
    $stderr = Join-Path $OutputDir "$Name-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $ArgumentList -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    $ok = $AllowedExitCodes -contains $proc.ExitCode
    Add-Step -Name $Name -Ok $ok -Details "exit=$($proc.ExitCode); stdout=$stdout; stderr=$stderr"
    if (-not $ok) {
        throw "$Name failed with exit code $($proc.ExitCode). See $stderr"
    }
}

function Get-NewestFile([string]$Filter) {
    return Get-ChildItem -LiteralPath $OutputDir -Filter $Filter -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Read-JsonFile($File) {
    if (-not $File) { return $null }
    return Get-Content -LiteralPath $File.FullName -Raw | ConvertFrom-Json
}

if (([string]::IsNullOrWhiteSpace($DemoVideoUrl) -or [string]::IsNullOrWhiteSpace($BackendUrl)) -and -not $AllowDraft) {
    throw "DemoVideoUrl and BackendUrl are required unless -AllowDraft is set."
}

$packetArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts/qwencloud-hackathon-submission-packet.ps1",
    "-RepoUrl", $RepoUrl,
    "-OutputDir", $OutputDir
)
if ($DemoVideoUrl) { $packetArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
if ($BackendUrl) { $packetArgs += @("-BackendUrl", $BackendUrl) }
if ($BlogPostUrl) { $packetArgs += @("-BlogPostUrl", $BlogPostUrl) }
if ($SkipBackendDraft) { $packetArgs += "-SkipBackendDraft" }
if ($SkipExternalUrlChecks) { $packetArgs += "-SkipExternalUrlChecks" }
if ($AllowDraft) { $packetArgs += "-AllowDraft" }
Invoke-Step -Name "submission-packet" -ArgumentList $packetArgs

$readinessArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts/qwencloud-final-readiness.ps1",
    "-RepoUrl", $RepoUrl,
    "-OutputDir", $OutputDir
)
if ($DemoVideoUrl) { $readinessArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
if ($BackendUrl) { $readinessArgs += @("-BackendUrl", $BackendUrl) }
if ($BlogPostUrl) { $readinessArgs += @("-BlogPostUrl", $BlogPostUrl) }
if ($SkipBackendDraft) { $readinessArgs += "-SkipBackendDraft" }
if ($SkipExternalUrlChecks) { $readinessArgs += "-SkipExternalUrlChecks" }
if ($AllowDraft) { $readinessArgs += "-AllowDraftPacket" }
$allowedReadinessExitCodes = if ($AllowDraft) { @(0, 1) } else { @(0) }
Invoke-Step -Name "final-readiness" -ArgumentList $readinessArgs -AllowedExitCodes $allowedReadinessExitCodes

$actionBoardArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts/qwencloud-final-action-board.ps1",
    "-RepoUrl", $RepoUrl,
    "-OutputDir", $OutputDir
)
if ($DemoVideoUrl) { $actionBoardArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
if ($BackendUrl) { $actionBoardArgs += @("-BackendUrl", $BackendUrl) }
if ($BlogPostUrl) { $actionBoardArgs += @("-BlogPostUrl", $BlogPostUrl) }
if ($SkipExternalUrlChecks) { $actionBoardArgs += "-SkipExternalUrlChecks" }
if ($AllowDraft) { $actionBoardArgs += "-AllowDraft" }
$allowedActionBoardExitCodes = if ($AllowDraft) { @(0, 1) } else { @(0) }
Invoke-Step -Name "final-action-board" -ArgumentList $actionBoardArgs -AllowedExitCodes $allowedActionBoardExitCodes

$bundleArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts/qwencloud-final-upload-bundle.ps1",
    "-RepoUrl", $RepoUrl,
    "-OutputDir", $OutputDir
)
if ($DemoVideoUrl) { $bundleArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
if ($BackendUrl) { $bundleArgs += @("-BackendUrl", $BackendUrl) }
if ($BlogPostUrl) { $bundleArgs += @("-BlogPostUrl", $BlogPostUrl) }
if ($SkipBackendDraft) { $bundleArgs += "-SkipBackendDraft" }
if ($SkipExternalUrlChecks) { $bundleArgs += "-SkipExternalUrlChecks" }
if ($AllowDraft) { $bundleArgs += "-AllowDraft" }
Invoke-Step -Name "final-upload-bundle" -ArgumentList $bundleArgs

$packetJsonFile = Get-NewestFile -Filter "devpost-submission-packet-*.json"
$readinessJsonFile = Get-NewestFile -Filter "final-readiness-*.json"
$bundleManifestJsonFile = Get-ChildItem -LiteralPath $OutputDir -Filter "final-upload-bundle-*" -Directory -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    ForEach-Object {
        $candidate = Join-Path $_.FullName "manifest.json"
        if (Test-Path $candidate) { Get-Item -LiteralPath $candidate }
    } |
    Select-Object -First 1

$packet = Read-JsonFile -File $packetJsonFile
$readiness = Read-JsonFile -File $readinessJsonFile
$bundleManifest = Read-JsonFile -File $bundleManifestJsonFile

$packetReady = [bool]($packet -and $packet.readyForDevpost)
$readinessReady = [bool]($readiness -and $readiness.readyForFinalSubmit)
$bundleReady = [bool]($bundleManifest -and $bundleManifest.readyForUpload)
$ready = $packetReady -and $readinessReady -and $bundleReady

Add-Step -Name "packet-ready" -Ok $packetReady -Details $(if ($packetJsonFile) { $packetJsonFile.FullName } else { "missing packet JSON" })
Add-Step -Name "readiness-ready" -Ok $readinessReady -Details $(if ($readinessJsonFile) { $readinessJsonFile.FullName } else { "missing readiness JSON" })
Add-Step -Name "bundle-ready" -Ok $bundleReady -Details $(if ($bundleManifestJsonFile) { $bundleManifestJsonFile.FullName } else { "missing bundle manifest JSON" })

$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    readyForDevpostSubmit = $ready
    allowDraft = [bool]$AllowDraft
    repoUrl = $RepoUrl
    demoVideoUrl = $DemoVideoUrl
    backendUrl = $BackendUrl
    blogPostUrl = $BlogPostUrl
    packetJson = if ($packetJsonFile) { $packetJsonFile.FullName } else { $null }
    readinessJson = if ($readinessJsonFile) { $readinessJsonFile.FullName } else { $null }
    bundleManifestJson = if ($bundleManifestJsonFile) { $bundleManifestJsonFile.FullName } else { $null }
    bundleZip = if ($bundleManifest) { $bundleManifest.zipPath } else { $null }
    steps = $steps
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Finalize After URLs ($timestamp)",
    "",
    "- Ready for Devpost submit: $ready",
    "- Repo: $RepoUrl",
    "- Demo video URL: $(if ($DemoVideoUrl) { $DemoVideoUrl } else { '<missing>' })",
    "- Backend URL: $(if ($BackendUrl) { $BackendUrl } else { '<missing>' })",
    "- Blog/social URL: $(if ($BlogPostUrl) { $BlogPostUrl } else { '<optional>' })",
    "- Bundle zip: $(if ($bundleManifest) { $bundleManifest.zipPath } else { '<missing>' })",
    "",
    "## Steps",
    "",
    "| Step | Result | Details |",
    "|---|---:|---|"
)
foreach ($step in $steps) {
    $status = if ($step.ok) { "PASS" } else { "FAIL" }
    $lines += "| $($step.name) | $status | $($step.details -replace '\|', '/') |"
}

if (-not $ready) {
    $lines += @(
        "",
        "## Not Ready Yet",
        "",
        "- Packet ready: $packetReady",
        "- Final readiness ready: $readinessReady",
        "- Final upload bundle ready: $bundleReady"
    )
}

Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($ready) {
    Write-Host "Finalize after URLs READY: $reportMd"
}
else {
    Write-Host "Finalize after URLs DRAFT: $reportMd" -ForegroundColor Yellow
    if (-not $AllowDraft) {
        exit 1
    }
}
Write-Host "JSON: $reportJson"
