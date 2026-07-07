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
    [Parameter(Mandatory = $false)]
    [string]$ArchitectureUploadPath = "docs/assets/qwencloud-architecture.png",
    [Parameter(Mandatory = $false)]
    [string]$LocalDemoVideoPath = "artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4",
    [Parameter(Mandatory = $false)]
    [string]$AlibabaScreenshotPath = "artifacts/qwencloud-proof/alibaba-deployment-screenshot.png",
    [Parameter(Mandatory = $false)]
    [string]$AlibabaProofVideoPath = "artifacts/qwencloud-proof/alibaba-deployment-proof.mp4",
    [Parameter(Mandatory = $false)]
    [string]$EnvFile = "",
    [switch]$SkipBackendDraft,
    [switch]$SkipExternalUrlChecks,
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
. (Join-Path $PSScriptRoot "qwencloud-env.ps1")
$importedEnvNames = @()
if (-not [string]::IsNullOrWhiteSpace($EnvFile)) {
    $importedEnvNames = @(Import-QwenCloudEnvFile -Path $EnvFile)
}

$bundleRoot = Join-Path $OutputDir "final-upload-bundle-$timestamp"
$uploadsDir = Join-Path $bundleRoot "uploads"
New-Item -ItemType Directory -Path $uploadsDir -Force | Out-Null

$manifestJson = Join-Path $bundleRoot "manifest.json"
$manifestMd = Join-Path $bundleRoot "manifest.md"
$zipPath = Join-Path $OutputDir "final-upload-bundle-$timestamp.zip"
$items = @()
$missing = @()

function Add-Item([string]$Name, [string]$Path, [bool]$Required = $true) {
    $exists = Test-Path $Path
    $dest = $null
    $details = ""

    if ($exists) {
        $source = Get-Item -LiteralPath $Path
        $dest = Join-Path $script:uploadsDir $source.Name
        Copy-Item -LiteralPath $source.FullName -Destination $dest -Force
        $details = "copied=$dest; size=$($source.Length)"
    }
    else {
        $details = "missing=$Path"
        if ($Required) {
            $script:missing += $Name
        }
    }

    $script:items += [ordered]@{
        name = $Name
        source = $Path
        required = $Required
        exists = $exists
        bundledPath = $dest
        details = $details
    }
}

function Add-LatestItem([string]$Name, [string]$Filter, [bool]$Required = $false) {
    $latest = Get-ChildItem -LiteralPath $OutputDir -Filter $Filter -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($latest) {
        Add-Item -Name $Name -Path $latest.FullName -Required $Required
    }
    else {
        Add-Item -Name $Name -Path (Join-Path $OutputDir $Filter) -Required $Required
    }
}

function Add-ExternalRequirement([string]$Name, [bool]$Ok, [string]$Details, [bool]$Required = $true) {
    if ($Required -and -not $Ok) {
        $script:missing += $Name
    }

    $script:items += [ordered]@{
        name = $Name
        source = $Details
        required = $Required
        exists = $Ok
        bundledPath = $null
        details = $Details
    }
}

function Get-PowerShellExe {
    $pwsh = Get-Command "pwsh" -ErrorAction SilentlyContinue
    if ($pwsh) { return $pwsh.Source }

    $powershell = Get-Command "powershell" -ErrorAction SilentlyContinue
    if ($powershell) { return $powershell.Source }

    throw "PowerShell executable not found."
}

function Invoke-Packet {
    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "devpost-submission-packet-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-hackathon-submission-packet.ps1",
        "-RepoUrl", $RepoUrl,
        "-OutputDir", $OutputDir,
        "-ArchitectureUploadPath", $ArchitectureUploadPath,
        "-LocalVideoPath", $LocalDemoVideoPath,
        "-AlibabaScreenshotPath", $AlibabaScreenshotPath,
        "-AlibabaProofVideoPath", $AlibabaProofVideoPath
    )
    if ($DemoVideoUrl) { $args += @("-DemoVideoUrl", $DemoVideoUrl) }
    if ($BackendUrl) { $args += @("-BackendUrl", $BackendUrl) }
    if ($BlogPostUrl) { $args += @("-BlogPostUrl", $BlogPostUrl) }
    if ($SkipBackendDraft) { $args += "-SkipBackendDraft" }
    if ($SkipExternalUrlChecks) { $args += "-SkipExternalUrlChecks" }
    if ($AllowDraft -or [string]::IsNullOrWhiteSpace($DemoVideoUrl) -or [string]::IsNullOrWhiteSpace($BackendUrl)) {
        $args += "-AllowDraft"
    }

    $stdout = Join-Path $OutputDir "final-upload-bundle-packet-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-upload-bundle-packet-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        throw "Submission packet generation failed. See $stderr"
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "devpost-submission-packet-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $json = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $json) {
        $json = @($after | Select-Object -First 1)
    }
    if (-not $json) {
        throw "Submission packet JSON was not found."
    }

    $mdPath = [System.IO.Path]::ChangeExtension($json.FullName, ".md")
    $packetData = Get-Content -LiteralPath $json.FullName -Raw | ConvertFrom-Json
    $failedRequired = @($packetData.checks | Where-Object { $_.required -and -not $_.ok } | ForEach-Object { $_.name })
    return [pscustomobject]@{
        json = $json.FullName
        markdown = $mdPath
        ready = [bool]$packetData.readyForDevpost
        failedRequired = $failedRequired
    }
}

function Invoke-Handoff {
    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "devpost-handoff-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-devpost-handoff.ps1",
        "-RepoUrl", $RepoUrl,
        "-OutputDir", $OutputDir,
        "-ArchitectureUploadPath", $ArchitectureUploadPath,
        "-LocalDemoVideoPath", $LocalDemoVideoPath,
        "-AlibabaScreenshotPath", $AlibabaScreenshotPath,
        "-AlibabaProofVideoPath", $AlibabaProofVideoPath
    )
    if ($DemoVideoUrl) { $args += @("-DemoVideoUrl", $DemoVideoUrl) }
    if ($BackendUrl) { $args += @("-BackendUrl", $BackendUrl) }
    if ($BlogPostUrl) { $args += @("-BlogPostUrl", $BlogPostUrl) }
    if ($AllowDraft -or [string]::IsNullOrWhiteSpace($DemoVideoUrl) -or [string]::IsNullOrWhiteSpace($BackendUrl)) {
        $args += "-AllowDraft"
    }

    $stdout = Join-Path $OutputDir "final-upload-bundle-handoff-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-upload-bundle-handoff-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        throw "Devpost handoff generation failed. See $stderr"
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "devpost-handoff-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $json = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $json) {
        $json = @($after | Select-Object -First 1)
    }
    if (-not $json) {
        throw "Devpost handoff JSON was not found."
    }

    $data = Get-Content -LiteralPath $json.FullName -Raw | ConvertFrom-Json
    return [pscustomobject]@{
        json = $json.FullName
        markdown = [string]$data.markdown
        html = [string]$data.html
        ready = [bool]$data.readyForDevpostFinalSubmit
        blockers = @($data.blockers)
    }
}

function Invoke-DraftPayload {
    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "devpost-draft-payload-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-devpost-draft-payload.ps1",
        "-RepoUrl", $RepoUrl,
        "-OutputDir", $OutputDir,
        "-ArchitectureUploadPath", $ArchitectureUploadPath,
        "-AlibabaScreenshotPath", $AlibabaScreenshotPath
    )
    if ($DemoVideoUrl) { $args += @("-DemoVideoUrl", $DemoVideoUrl) }
    if ($BackendUrl) { $args += @("-BackendUrl", $BackendUrl) }
    if ($BlogPostUrl) { $args += @("-BlogPostUrl", $BlogPostUrl) }
    if ($AllowDraft -or [string]::IsNullOrWhiteSpace($DemoVideoUrl)) {
        $args += "-AllowDraft"
    }

    $stdout = Join-Path $OutputDir "final-upload-bundle-draft-payload-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-upload-bundle-draft-payload-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        throw "Devpost draft payload generation failed. See $stderr"
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "devpost-draft-payload-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $json = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $json) {
        $json = @($after | Select-Object -First 1)
    }
    if (-not $json) {
        throw "Devpost draft payload JSON was not found."
    }

    $data = Get-Content -LiteralPath $json.FullName -Raw | ConvertFrom-Json
    return [pscustomobject]@{
        json = $json.FullName
        markdown = [System.IO.Path]::ChangeExtension($json.FullName, ".md")
        ready = [bool]$data.readyForFinalDevpostFields
        publicTextReady = [bool]$data.readyForPublicTextAutofill
        failures = @($data.requiredFailures)
    }
}

function Invoke-JudgingScorecard {
    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "judging-scorecard-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-judging-scorecard.ps1",
        "-RepoUrl", $RepoUrl,
        "-OutputDir", $OutputDir
    )
    if ($DemoVideoUrl) { $args += @("-DemoVideoUrl", $DemoVideoUrl) }
    if ($BackendUrl) { $args += @("-BackendUrl", $BackendUrl) }
    if ($AllowDraft -or [string]::IsNullOrWhiteSpace($DemoVideoUrl) -or [string]::IsNullOrWhiteSpace($BackendUrl)) {
        $args += "-AllowDraft"
    }

    $stdout = Join-Path $OutputDir "final-upload-bundle-judging-scorecard-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-upload-bundle-judging-scorecard-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        throw "Judging scorecard generation failed. See $stderr"
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "judging-scorecard-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $json = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $json) {
        $json = @($after | Select-Object -First 1)
    }
    if (-not $json) {
        throw "Judging scorecard JSON was not found."
    }

    $data = Get-Content -LiteralPath $json.FullName -Raw | ConvertFrom-Json
    return [pscustomobject]@{
        json = $json.FullName
        markdown = [System.IO.Path]::ChangeExtension($json.FullName, ".md")
        ready = [bool]$data.readyForJudgingNarrative
        missing = @($data.missingRequiredCriteria)
    }
}

function Invoke-CloudCredentialsHandoff {
    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "cloud-credentials-handoff-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-cloud-credentials-handoff.ps1",
        "-OutputDir", $OutputDir,
        "-AllowDraft"
    )
    if ($DemoVideoUrl) { $args += @("-DemoVideoUrl", $DemoVideoUrl) }
    if ($BackendUrl) { $args += @("-BackendUrl", $BackendUrl) }
    if ($EnvFile) { $args += @("-EnvFile", $EnvFile) }

    $stdout = Join-Path $OutputDir "final-upload-bundle-cloud-handoff-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-upload-bundle-cloud-handoff-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        throw "Cloud credentials handoff generation failed. See $stderr"
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "cloud-credentials-handoff-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $json = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $json) {
        $json = @($after | Select-Object -First 1)
    }
    if (-not $json) {
        throw "Cloud credentials handoff JSON was not found."
    }

    $data = Get-Content -LiteralPath $json.FullName -Raw | ConvertFrom-Json
    return [pscustomobject]@{
        json = $json.FullName
        markdown = [string]$data.markdown
        template = [string]$data.template
        ready = [bool]$data.readyForCloudRelease
        blockers = @($data.blockers)
    }
}

$packet = Invoke-Packet
$handoff = Invoke-Handoff
$draftPayload = Invoke-DraftPayload
$judgingScorecard = Invoke-JudgingScorecard
$cloudHandoff = Invoke-CloudCredentialsHandoff

Add-ExternalRequirement -Name "public_demo_video_url" -Ok (-not [string]::IsNullOrWhiteSpace($DemoVideoUrl)) -Details $(if ($DemoVideoUrl) { $DemoVideoUrl } else { "missing" })
Add-ExternalRequirement -Name "deployed_backend_url" -Ok (-not [string]::IsNullOrWhiteSpace($BackendUrl)) -Details $(if ($BackendUrl) { $BackendUrl } else { "missing" })
Add-ExternalRequirement -Name "devpost_packet_ready" -Ok $packet.ready -Details $(if ($packet.ready) { "READY" } else { "DRAFT; missing=$($packet.failedRequired -join ', ')" })
Add-ExternalRequirement -Name "devpost_handoff_ready" -Ok $handoff.ready -Details $(if ($handoff.ready) { "READY" } else { "DRAFT; missing=$($handoff.blockers -join ', ')" }) -Required $false
Add-ExternalRequirement -Name "devpost_draft_payload_ready" -Ok $draftPayload.ready -Details $(if ($draftPayload.ready) { "READY" } else { "DRAFT; publicTextReady=$($draftPayload.publicTextReady); missing=$($draftPayload.failures -join ', ')" })
Add-ExternalRequirement -Name "judging_scorecard_ready" -Ok $judgingScorecard.ready -Details $(if ($judgingScorecard.ready) { "READY" } else { "DRAFT; missing=$($judgingScorecard.missing -join ', ')" })
Add-ExternalRequirement -Name "cloud_credentials_handoff_ready" -Ok $cloudHandoff.ready -Details $(if ($cloudHandoff.ready) { "READY" } else { "DRAFT; missing=$($cloudHandoff.blockers -join ', ')" }) -Required $false
Add-Item -Name "architecture_diagram" -Path $ArchitectureUploadPath
Add-Item -Name "video_upload_handoff" -Path "docs/qwencloud-video-upload-handoff.md"
Add-Item -Name "video_upload_status_script" -Path "scripts/qwencloud-video-upload-status.ps1" -Required $false
Add-LatestItem -Name "latest_video_upload_status_markdown" -Filter "video-upload-status-*.md"
Add-LatestItem -Name "latest_video_upload_status_json" -Filter "video-upload-status-*.json"
Add-Item -Name "final_action_board_script" -Path "scripts/qwencloud-final-action-board.ps1" -Required $false
Add-Item -Name "final_sprint_script" -Path "scripts/qwencloud-final-sprint.ps1" -Required $false
Add-LatestItem -Name "latest_final_sprint_markdown" -Filter "final-sprint-*.md"
Add-LatestItem -Name "latest_final_sprint_json" -Filter "final-sprint-*.json"
Add-LatestItem -Name "latest_final_action_board_markdown" -Filter "final-action-board-*.md"
Add-LatestItem -Name "latest_final_action_board_json" -Filter "final-action-board-*.json"
Add-Item -Name "local_demo_video_for_public_upload" -Path $LocalDemoVideoPath -Required ([string]::IsNullOrWhiteSpace($DemoVideoUrl))
Add-Item -Name "alibaba_deployment_screenshot" -Path $AlibabaScreenshotPath
Add-Item -Name "alibaba_backend_proof_recording" -Path $AlibabaProofVideoPath
Add-Item -Name "alibaba_proof_integrity_script" -Path "scripts/qwencloud-validate-alibaba-proof.ps1" -Required $false
Add-LatestItem -Name "latest_alibaba_proof_integrity_markdown" -Filter "alibaba-proof-integrity-*.md"
Add-LatestItem -Name "latest_alibaba_proof_integrity_json" -Filter "alibaba-proof-integrity-*.json"
Add-Item -Name "devpost_packet_markdown" -Path $packet.markdown
Add-Item -Name "devpost_packet_json" -Path $packet.json
Add-Item -Name "devpost_handoff_markdown" -Path $handoff.markdown
Add-Item -Name "devpost_handoff_html" -Path $handoff.html
Add-Item -Name "devpost_handoff_json" -Path $handoff.json
Add-Item -Name "devpost_draft_payload_markdown" -Path $draftPayload.markdown
Add-Item -Name "devpost_draft_payload_json" -Path $draftPayload.json
Add-Item -Name "devpost_draft_payload_script" -Path "scripts/qwencloud-devpost-draft-payload.ps1" -Required $false
Add-Item -Name "judging_scorecard_markdown" -Path $judgingScorecard.markdown
Add-Item -Name "judging_scorecard_json" -Path $judgingScorecard.json
Add-Item -Name "judging_scorecard_script" -Path "scripts/qwencloud-judging-scorecard.ps1" -Required $false
Add-Item -Name "cloud_credentials_handoff_markdown" -Path $cloudHandoff.markdown
Add-Item -Name "cloud_credentials_template" -Path $cloudHandoff.template
Add-Item -Name "cloud_credentials_handoff_json" -Path $cloudHandoff.json
Add-Item -Name "github_secrets_handoff_script" -Path "scripts/qwencloud-github-secrets-handoff.ps1" -Required $false
Add-Item -Name "github_release_workflow" -Path ".github/workflows/qwencloud-release.yml" -Required $false
Add-Item -Name "github_release_workflow_handoff" -Path "docs/qwencloud-github-release-workflow.md" -Required $false
Add-LatestItem -Name "latest_deploy_preflight_markdown" -Filter "deploy-preflight-*.md"
Add-LatestItem -Name "latest_deploy_preflight_json" -Filter "deploy-preflight-*.json"
Add-LatestItem -Name "latest_docker_build_stdout" -Filter "docker-build-*.out"
Add-LatestItem -Name "latest_docker_build_stderr" -Filter "docker-build-*.err"
Add-LatestItem -Name "latest_docker_run_stdout" -Filter "docker-run-*.out"
Add-LatestItem -Name "latest_docker_run_stderr" -Filter "docker-run-*.err"

$ready = $missing.Count -eq 0
$manifest = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    readyForUpload = $ready
    allowDraft = [bool]$AllowDraft
    repoUrl = $RepoUrl
    demoVideoUrl = $DemoVideoUrl
    backendUrl = $BackendUrl
    blogPostUrl = $BlogPostUrl
    envFile = $EnvFile
    importedEnvNames = $importedEnvNames
    bundleRoot = $bundleRoot
    zipPath = $zipPath
    missingRequiredItems = $missing
    items = $items
}
Set-Content -Path $manifestJson -Value ($manifest | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Final Upload Bundle ($timestamp)",
    "",
    "- Ready for upload: $ready",
    "- Repo: $RepoUrl",
    "- Demo video URL: $(if ($DemoVideoUrl) { $DemoVideoUrl } else { '<missing>' })",
    "- Backend URL: $(if ($BackendUrl) { $BackendUrl } else { '<missing>' })",
    "- Env file imported: $(if ($EnvFile) { $EnvFile } else { '<none>' })",
    "- Bundle zip: $zipPath",
    "",
    "## Items",
    "",
    "| Item | Required | Exists | Details |",
    "|---|---:|---:|---|"
)
foreach ($item in $items) {
    $required = if ($item.required) { "yes" } else { "no" }
    $exists = if ($item.exists) { "yes" } else { "no" }
    $lines += "| $($item.name) | $required | $exists | $($item.details -replace '\|', '/') |"
}

if (-not $ready) {
    $lines += @(
        "",
        "## Missing Required Items",
        ""
    )
    foreach ($name in $missing) {
        $lines += "- $name"
    }
}

Set-Content -Path $manifestMd -Value ($lines -join "`r`n") -Encoding UTF8

Copy-Item -LiteralPath $manifestJson -Destination (Join-Path $uploadsDir "manifest.json") -Force
Copy-Item -LiteralPath $manifestMd -Destination (Join-Path $uploadsDir "manifest.md") -Force

if (-not $ready -and -not $AllowDraft) {
    Write-Host "Final upload bundle blocked. Missing: $($missing -join ', ')" -ForegroundColor Yellow
    Write-Host "Manifest: $manifestMd"
    exit 1
}

if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -Path (Join-Path $bundleRoot "*") -DestinationPath $zipPath -Force

if ($ready) {
    Write-Host "Final upload bundle READY: $zipPath"
}
else {
    Write-Host "Final upload bundle DRAFT: $zipPath" -ForegroundColor Yellow
    Write-Host "Missing required items: $($missing -join ', ')"
}
Write-Host "Manifest: $manifestMd"
