param(
    [Parameter(Mandatory = $false)]
    [string]$RepoUrl = "https://github.com/zemeng2015/dream-ai-engineering-copilot",
    [Parameter(Mandatory = $false)]
    [string]$RepoName = "zemeng2015/dream-ai-engineering-copilot",
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
    [switch]$SkipGitHubSecrets,
    [switch]$SkipLocalVideoChecks,
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

function Get-FileSha256([string]$Path) {
    if (-not (Test-Path $Path)) {
        return ""
    }

    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Add-Item([string]$Name, [string]$Path, [bool]$Required = $true) {
    $exists = (-not [string]::IsNullOrWhiteSpace($Path)) -and (Test-Path $Path)
    $dest = $null
    $details = ""
    $sourceSha256 = ""
    $bundledSha256 = ""
    $size = 0

    if ($exists) {
        $source = Get-Item -LiteralPath $Path
        $size = $source.Length
        $sourceSha256 = Get-FileSha256 -Path $source.FullName
        $dest = Join-Path $script:uploadsDir $source.Name
        Copy-Item -LiteralPath $source.FullName -Destination $dest -Force
        $bundledSha256 = Get-FileSha256 -Path $dest
        $details = "copied=$dest; size=$size; sha256=$sourceSha256"
    }
    else {
        $details = "missing=$(if ([string]::IsNullOrWhiteSpace($Path)) { '<empty path>' } else { $Path })"
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
        sizeBytes = $size
        sourceSha256 = $sourceSha256
        bundledSha256 = $bundledSha256
        hashMatches = ($exists -and $sourceSha256 -eq $bundledSha256)
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

function Invoke-DeadlineGuard {
    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "deadline-guard-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-deadline-guard.ps1",
        "-OutputDir", $OutputDir
    )
    if ($AllowDraft) { $args += "-AllowDraft" }

    $stdout = Join-Path $OutputDir "final-upload-bundle-deadline-guard-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-upload-bundle-deadline-guard-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        if (-not $AllowDraft) {
            throw "Deadline guard generation failed. See $stderr"
        }
        return [pscustomobject]@{
            json = ""
            markdown = ""
            ready = $false
            details = "exit=$($proc.ExitCode); stdout=$stdout; stderr=$stderr"
        }
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "deadline-guard-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $json = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $json) {
        $json = @($after | Select-Object -First 1)
    }
    if (-not $json) {
        return [pscustomobject]@{
            json = ""
            markdown = ""
            ready = $false
            details = "deadline guard JSON missing; stdout=$stdout; stderr=$stderr"
        }
    }

    $data = Get-Content -LiteralPath $json.FullName -Raw | ConvertFrom-Json
    $failedRequired = @($data.checks | Where-Object { $_.required -and -not $_.ok } | ForEach-Object { $_.name })
    return [pscustomobject]@{
        json = $json.FullName
        markdown = [System.IO.Path]::ChangeExtension($json.FullName, ".md")
        ready = [bool]$data.readyForSubmissionWindow
        details = if ($data.readyForSubmissionWindow) { "READY: $($json.FullName); urgency=$($data.urgency); hoursRemaining=$($data.hoursRemaining)" } else { "DRAFT; missing=$($failedRequired -join ', ')" }
    }
}

function Invoke-LiveInputsIntake {
    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "live-inputs-intake-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-live-inputs-intake.ps1",
        "-OutputDir", $OutputDir,
        "-AllowDraft"
    )
    if ($DemoVideoUrl) { $args += @("-DemoVideoUrl", $DemoVideoUrl) }
    if ($BackendUrl) { $args += @("-BackendUrl", $BackendUrl) }
    if ($BlogPostUrl) { $args += @("-BlogPostUrl", $BlogPostUrl) }
    if ($EnvFile) { $args += @("-EnvFile", $EnvFile) }
    if ($SkipExternalUrlChecks) { $args += "-SkipExternalUrlChecks" }

    $stdout = Join-Path $OutputDir "final-upload-bundle-live-inputs-intake-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-upload-bundle-live-inputs-intake-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        if (-not $AllowDraft) {
            throw "Live inputs intake generation failed. See $stderr"
        }
        return [pscustomobject]@{
            json = ""
            markdown = ""
            ready = $false
            details = "exit=$($proc.ExitCode); stdout=$stdout; stderr=$stderr"
        }
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "live-inputs-intake-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $json = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $json) {
        $json = @($after | Select-Object -First 1)
    }
    if (-not $json) {
        return [pscustomobject]@{
            json = ""
            markdown = ""
            ready = $false
            details = "live inputs intake JSON missing; stdout=$stdout; stderr=$stderr"
        }
    }

    $data = Get-Content -LiteralPath $json.FullName -Raw | ConvertFrom-Json
    return [pscustomobject]@{
        json = $json.FullName
        markdown = [System.IO.Path]::ChangeExtension($json.FullName, ".md")
        ready = [bool]$data.readyForLiveInputs
        details = if ($data.readyForLiveInputs) { "READY: $($json.FullName)" } else { "DRAFT; missing=$(@($data.missingRequiredChecks) -join ', ')" }
    }
}

function Invoke-ReleaseConfigAudit {
    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "release-config-audit-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-release-config-audit.ps1",
        "-OutputDir", $OutputDir,
        "-AllowDraft"
    )
    if ($EnvFile) { $args += @("-EnvFile", $EnvFile) }

    $stdout = Join-Path $OutputDir "final-upload-bundle-release-config-audit-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-upload-bundle-release-config-audit-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        if (-not $AllowDraft) {
            throw "Release config audit generation failed. See $stderr"
        }
        return [pscustomobject]@{
            json = ""
            markdown = ""
            ready = $false
            details = "exit=$($proc.ExitCode); stdout=$stdout; stderr=$stderr"
        }
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "release-config-audit-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $json = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $json) {
        $json = @($after | Select-Object -First 1)
    }
    if (-not $json) {
        return [pscustomobject]@{
            json = ""
            markdown = ""
            ready = $false
            details = "release config audit JSON missing; stdout=$stdout; stderr=$stderr"
        }
    }

    $data = Get-Content -LiteralPath $json.FullName -Raw | ConvertFrom-Json
    return [pscustomobject]@{
        json = $json.FullName
        markdown = [System.IO.Path]::ChangeExtension($json.FullName, ".md")
        ready = [bool]$data.readyForReleaseConfig
        details = if ($data.readyForReleaseConfig) { "READY: $($json.FullName)" } else { "DRAFT; missing=$(@($data.missingRequiredChecks) -join ', ')" }
    }
}

function Invoke-ActionBoard {
    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "final-action-board-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-final-action-board.ps1",
        "-RepoUrl", $RepoUrl,
        "-RepoName", $RepoName,
        "-OutputDir", $OutputDir,
        "-AllowDraft"
    )
    if ($DemoVideoUrl) { $args += @("-DemoVideoUrl", $DemoVideoUrl) }
    if ($BackendUrl) { $args += @("-BackendUrl", $BackendUrl) }
    if ($BlogPostUrl) { $args += @("-BlogPostUrl", $BlogPostUrl) }
    if ($EnvFile) { $args += @("-EnvFile", $EnvFile) }
    if ($SkipExternalUrlChecks) { $args += "-SkipExternalUrlChecks" }
    if ($SkipGitHubSecrets) { $args += "-SkipGitHubSecrets" }
    if ($SkipLocalVideoChecks) { $args += "-SkipLocalVideoChecks" }

    $stdout = Join-Path $OutputDir "final-upload-bundle-action-board-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-upload-bundle-action-board-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        if (-not $AllowDraft) {
            throw "Final action board generation failed. See $stderr"
        }
        return [pscustomobject]@{
            json = ""
            markdown = ""
            ready = $false
            details = "exit=$($proc.ExitCode); stdout=$stdout; stderr=$stderr"
        }
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "final-action-board-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $json = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $json) {
        $json = @($after | Select-Object -First 1)
    }
    if (-not $json) {
        return [pscustomobject]@{
            json = ""
            markdown = ""
            ready = $false
            details = "final action board JSON missing; stdout=$stdout; stderr=$stderr"
        }
    }

    $data = Get-Content -LiteralPath $json.FullName -Raw | ConvertFrom-Json
    return [pscustomobject]@{
        json = $json.FullName
        markdown = [System.IO.Path]::ChangeExtension($json.FullName, ".md")
        ready = [bool]$data.readyForFinalSubmit
        details = if ($data.readyForFinalSubmit) { "READY: $($json.FullName)" } else { "DRAFT; nextActions=$(@($data.nextActions | ForEach-Object { $_.name }) -join ', ')" }
    }
}

function Invoke-GitHubCiProof {
    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "github-ci-proof-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-github-ci-proof.ps1",
        "-RepoUrl", $RepoUrl,
        "-OutputDir", $OutputDir,
        "-Branch", "main"
    )
    if ($AllowDraft) { $args += "-AllowDraft" }

    $stdout = Join-Path $OutputDir "final-upload-bundle-github-ci-proof-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-upload-bundle-github-ci-proof-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        if (-not $AllowDraft) {
            throw "GitHub CI proof generation failed. See $stderr"
        }
        return [pscustomobject]@{
            json = ""
            markdown = ""
            ready = $false
            failures = @("github_ci_proof_generation_failed")
            details = "exit=$($proc.ExitCode); stdout=$stdout; stderr=$stderr"
        }
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "github-ci-proof-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $json = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $json) {
        $json = @($after | Select-Object -First 1)
    }
    if (-not $json) {
        return [pscustomobject]@{
            json = ""
            markdown = ""
            ready = $false
            failures = @("github_ci_proof_json_missing")
            details = "stdout=$stdout; stderr=$stderr"
        }
    }

    $data = Get-Content -LiteralPath $json.FullName -Raw | ConvertFrom-Json
    $failedRequired = @($data.checks | Where-Object { $_.required -and -not $_.ok } | ForEach-Object { $_.name })
    return [pscustomobject]@{
        json = $json.FullName
        markdown = [System.IO.Path]::ChangeExtension($json.FullName, ".md")
        ready = [bool]$data.readyForGitHubCiProof
        failures = $failedRequired
        details = if ($data.readyForGitHubCiProof) { "READY: $($json.FullName)" } else { "DRAFT; missing=$($failedRequired -join ', ')" }
    }
}

function Invoke-OfficialSourceRefresh {
    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "official-source-refresh-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-official-source-refresh.ps1",
        "-OutputDir", $OutputDir
    )
    if ($AllowDraft) { $args += "-AllowDraft" }

    $stdout = Join-Path $OutputDir "final-upload-bundle-official-source-refresh-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-upload-bundle-official-source-refresh-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        if (-not $AllowDraft) {
            throw "Official source refresh generation failed. See $stderr"
        }
        return [pscustomobject]@{
            json = ""
            markdown = ""
            ready = $false
            details = "exit=$($proc.ExitCode); stdout=$stdout; stderr=$stderr"
            sourceFingerprints = $null
        }
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "official-source-refresh-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $json = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $json) {
        $json = @($after | Select-Object -First 1)
    }
    if (-not $json) {
        return [pscustomobject]@{
            json = ""
            markdown = ""
            ready = $false
            details = "official source refresh JSON missing; stdout=$stdout; stderr=$stderr"
            sourceFingerprints = $null
        }
    }

    $data = Get-Content -LiteralPath $json.FullName -Raw | ConvertFrom-Json
    return [pscustomobject]@{
        json = $json.FullName
        markdown = [System.IO.Path]::ChangeExtension($json.FullName, ".md")
        ready = [bool]$data.readyForOfficialSourceSnapshot
        details = if ($data.readyForOfficialSourceSnapshot) { "READY: $($json.FullName)" } else { "DRAFT; missing=$(@($data.missingRequiredChecks) -join ', ')" }
        sourceFingerprints = $data.sourceFingerprints
    }
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
    if ($EnvFile) { $args += @("-EnvFile", $EnvFile) }
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

function Invoke-AutofillSnippet([string]$PayloadJson) {
    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "devpost-autofill-snippet-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $payloadJsonArg = $PayloadJson
    try {
        $payloadJsonArg = Resolve-Path -LiteralPath $PayloadJson -Relative
    }
    catch {
        $payloadJsonArg = $PayloadJson
    }
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-devpost-autofill-snippet.ps1",
        "-RepoUrl", $RepoUrl,
        "-OutputDir", $OutputDir,
        "-PayloadJson", $payloadJsonArg,
        "-AllowDraft"
    )
    if ($DemoVideoUrl) { $args += @("-DemoVideoUrl", $DemoVideoUrl) }
    if ($BackendUrl) { $args += @("-BackendUrl", $BackendUrl) }
    if ($BlogPostUrl) { $args += @("-BlogPostUrl", $BlogPostUrl) }

    $stdout = Join-Path $OutputDir "final-upload-bundle-autofill-snippet-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-upload-bundle-autofill-snippet-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        throw "Devpost autofill snippet generation failed. See $stderr"
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "devpost-autofill-snippet-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $json = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $json) {
        $json = @($after | Select-Object -First 1)
    }
    if (-not $json) {
        throw "Devpost autofill snippet JSON was not found."
    }

    $data = Get-Content -LiteralPath $json.FullName -Raw | ConvertFrom-Json
    return [pscustomobject]@{
        json = $json.FullName
        markdown = [string]$data.markdown
        javascript = [string]$data.snippetJavaScript
        ready = [bool]$data.readyForAutofillSnippet
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

function Invoke-OfficialRulesGate {
    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "official-rules-gate-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-official-rules-gate.ps1",
        "-RepoUrl", $RepoUrl,
        "-OutputDir", $OutputDir,
        "-AllowDraft"
    )
    if ($DemoVideoUrl) { $args += @("-DemoVideoUrl", $DemoVideoUrl) }
    if ($BackendUrl) { $args += @("-BackendUrl", $BackendUrl) }
    if ($BlogPostUrl) { $args += @("-BlogPostUrl", $BlogPostUrl) }
    if ($SkipBackendDraft) { $args += "-SkipBackendDraft" }
    if ($SkipExternalUrlChecks) { $args += "-SkipExternalUrlChecks" }
    if ($SkipLocalVideoChecks) { $args += "-SkipLocalVideoChecks" }

    $stdout = Join-Path $OutputDir "final-upload-bundle-official-rules-gate-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-upload-bundle-official-rules-gate-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        throw "Official rules gate generation failed. See $stderr"
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "official-rules-gate-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $json = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $json) {
        $json = @($after | Select-Object -First 1)
    }
    if (-not $json) {
        throw "Official rules gate JSON was not found."
    }

    $data = Get-Content -LiteralPath $json.FullName -Raw | ConvertFrom-Json
    return [pscustomobject]@{
        json = $json.FullName
        markdown = [System.IO.Path]::ChangeExtension($json.FullName, ".md")
        ready = [bool]$data.readyForOfficialRules
        missing = @($data.missingRequired)
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

function Invoke-VideoPublicationHandoff {
    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "video-publication-handoff-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-video-publication-handoff.ps1",
        "-OutputDir", $OutputDir,
        "-LocalVideoPath", $LocalDemoVideoPath,
        "-AllowDraft"
    )
    if ($DemoVideoUrl) { $args += @("-DemoVideoUrl", $DemoVideoUrl) }

    $stdout = Join-Path $OutputDir "final-upload-bundle-video-publication-handoff-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-upload-bundle-video-publication-handoff-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        throw "Video publication handoff generation failed. See $stderr"
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "video-publication-handoff-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $json = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $json) {
        $json = @($after | Select-Object -First 1)
    }
    if (-not $json) {
        throw "Video publication handoff JSON was not found."
    }

    $data = Get-Content -LiteralPath $json.FullName -Raw | ConvertFrom-Json
    return [pscustomobject]@{
        json = $json.FullName
        markdown = [string]$data.reportMarkdown
        readyForManualUpload = [bool]$data.readyForManualUpload
        readyForDevpostVideoField = [bool]$data.readyForDevpostVideoField
    }
}

function Invoke-ExternalHandoff {
    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "external-handoff-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-final-external-handoff.ps1",
        "-RepoUrl", $RepoUrl,
        "-RepoName", $RepoName,
        "-OutputDir", $OutputDir,
        "-LocalVideoPath", $LocalDemoVideoPath,
        "-SkipActionBoard"
    )
    if ($DemoVideoUrl) { $args += @("-DemoVideoUrl", $DemoVideoUrl) }
    if ($BackendUrl) { $args += @("-BackendUrl", $BackendUrl) }
    if ($BlogPostUrl) { $args += @("-BlogPostUrl", $BlogPostUrl) }
    if ($EnvFile) { $args += @("-EnvFile", $EnvFile) }
    if ($SkipExternalUrlChecks) { $args += "-SkipExternalUrlChecks" }
    if ($SkipGitHubSecrets) { $args += "-SkipGitHubSecrets" }
    if ($AllowDraft) { $args += "-AllowDraft" }

    $stdout = Join-Path $OutputDir "final-upload-bundle-external-handoff-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-upload-bundle-external-handoff-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        if (-not $AllowDraft) {
            throw "Final external handoff generation failed. See $stderr"
        }
        return [pscustomobject]@{
            json = ""
            markdown = ""
            zip = ""
            ready = $false
            blockers = @("external_handoff_generation_failed")
            details = "exit=$($proc.ExitCode); stdout=$stdout; stderr=$stderr"
        }
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "external-handoff-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $json = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $json) {
        $json = @($after | Select-Object -First 1)
    }
    if (-not $json) {
        return [pscustomobject]@{
            json = ""
            markdown = ""
            zip = ""
            ready = $false
            blockers = @("external_handoff_json_missing")
            details = "stdout=$stdout; stderr=$stderr"
        }
    }

    $data = Get-Content -LiteralPath $json.FullName -Raw | ConvertFrom-Json
    return [pscustomobject]@{
        json = $json.FullName
        markdown = [System.IO.Path]::ChangeExtension($json.FullName, ".md")
        zip = [string]$data.zipPath
        ready = [bool]$data.readyForExternalHandoff
        blockers = @($data.blockers)
        details = if ($data.readyForExternalHandoff) { "READY: $($json.FullName)" } else { "DRAFT; blockers=$(@($data.blockers) -join ', ')" }
    }
}

$deadlineGuard = Invoke-DeadlineGuard
$liveInputs = Invoke-LiveInputsIntake
$releaseConfig = Invoke-ReleaseConfigAudit
$githubCiProof = Invoke-GitHubCiProof
$videoPublicationHandoff = Invoke-VideoPublicationHandoff
$packet = Invoke-Packet
$handoff = Invoke-Handoff
$draftPayload = Invoke-DraftPayload
$autofillSnippet = Invoke-AutofillSnippet -PayloadJson $draftPayload.json
$judgingScorecard = Invoke-JudgingScorecard
$officialSourceRefresh = Invoke-OfficialSourceRefresh
$officialRulesGate = Invoke-OfficialRulesGate
$cloudHandoff = Invoke-CloudCredentialsHandoff
$actionBoard = Invoke-ActionBoard
$externalHandoff = Invoke-ExternalHandoff

Add-ExternalRequirement -Name "public_demo_video_url" -Ok (-not [string]::IsNullOrWhiteSpace($DemoVideoUrl)) -Details $(if ($DemoVideoUrl) { $DemoVideoUrl } else { "missing" })
Add-ExternalRequirement -Name "submission_deadline_guard_ready" -Ok $deadlineGuard.ready -Details $deadlineGuard.details
Add-ExternalRequirement -Name "live_inputs_intake_ready" -Ok $liveInputs.ready -Details $liveInputs.details
Add-ExternalRequirement -Name "release_config_audit_ready" -Ok $releaseConfig.ready -Details $releaseConfig.details
Add-ExternalRequirement -Name "github_ci_proof_ready" -Ok $githubCiProof.ready -Details $githubCiProof.details
Add-ExternalRequirement -Name "video_publication_handoff_ready" -Ok $videoPublicationHandoff.readyForManualUpload -Details $(if ($videoPublicationHandoff.readyForManualUpload) { "READY for manual upload" } else { "DRAFT" }) -Required $false
Add-ExternalRequirement -Name "deployed_backend_url" -Ok (-not [string]::IsNullOrWhiteSpace($BackendUrl)) -Details $(if ($BackendUrl) { $BackendUrl } else { "missing" })
Add-ExternalRequirement -Name "devpost_packet_ready" -Ok $packet.ready -Details $(if ($packet.ready) { "READY" } else { "DRAFT; missing=$($packet.failedRequired -join ', ')" })
Add-ExternalRequirement -Name "devpost_handoff_ready" -Ok $handoff.ready -Details $(if ($handoff.ready) { "READY" } else { "DRAFT; missing=$($handoff.blockers -join ', ')" }) -Required $false
Add-ExternalRequirement -Name "devpost_draft_payload_ready" -Ok $draftPayload.ready -Details $(if ($draftPayload.ready) { "READY" } else { "DRAFT; publicTextReady=$($draftPayload.publicTextReady); missing=$($draftPayload.failures -join ', ')" })
Add-ExternalRequirement -Name "devpost_autofill_snippet_ready" -Ok $autofillSnippet.ready -Details $(if ($autofillSnippet.ready) { "READY" } else { "DRAFT" }) -Required $false
Add-ExternalRequirement -Name "judging_scorecard_ready" -Ok $judgingScorecard.ready -Details $(if ($judgingScorecard.ready) { "READY" } else { "DRAFT; missing=$($judgingScorecard.missing -join ', ')" })
Add-ExternalRequirement -Name "official_source_refresh_ready" -Ok $officialSourceRefresh.ready -Details $officialSourceRefresh.details
Add-ExternalRequirement -Name "official_rules_gate_ready" -Ok $officialRulesGate.ready -Details $(if ($officialRulesGate.ready) { "READY" } else { "DRAFT; missing=$($officialRulesGate.missing -join ', ')" })
Add-ExternalRequirement -Name "cloud_credentials_handoff_ready" -Ok $cloudHandoff.ready -Details $(if ($cloudHandoff.ready) { "READY" } else { "DRAFT; missing=$($cloudHandoff.blockers -join ', ')" }) -Required $false
Add-ExternalRequirement -Name "external_handoff_ready" -Ok $externalHandoff.ready -Details $externalHandoff.details -Required $false
Add-Item -Name "architecture_diagram" -Path $ArchitectureUploadPath
Add-Item -Name "video_upload_handoff" -Path "docs/qwencloud-video-upload-handoff.md"
Add-Item -Name "devpost_video_url_policy_script" -Path "scripts/qwencloud-devpost-video-url.ps1" -Required $false
Add-Item -Name "video_thumbnail_png" -Path "docs/assets/qwencloud-video-thumbnail.png" -Required $false
Add-Item -Name "video_thumbnail_svg" -Path "docs/assets/qwencloud-video-thumbnail.svg" -Required $false
Add-Item -Name "video_thumbnail_export_script" -Path "scripts/qwencloud-export-video-thumbnail.ps1" -Required $false
Add-Item -Name "demo_video_captions_srt" -Path "docs/qwencloud-demo-video-captions.srt" -Required $false
Add-Item -Name "demo_video_transcript" -Path "docs/qwencloud-demo-video-transcript.md" -Required $false
Add-Item -Name "video_upload_status_script" -Path "scripts/qwencloud-video-upload-status.ps1" -Required $false
Add-Item -Name "video_publication_handoff_script" -Path "scripts/qwencloud-video-publication-handoff.ps1" -Required $false
Add-Item -Name "video_publication_handoff_markdown" -Path $videoPublicationHandoff.markdown
Add-Item -Name "video_publication_handoff_json" -Path $videoPublicationHandoff.json
Add-Item -Name "demo_video_render_script" -Path "scripts/qwencloud-render-demo-video.ps1" -Required $false
Add-LatestItem -Name "latest_demo_video_render_markdown" -Filter "demo-video-render-*.md"
Add-LatestItem -Name "latest_demo_video_render_json" -Filter "demo-video-render-*.json"
Add-LatestItem -Name "latest_video_upload_status_markdown" -Filter "video-upload-status-*.md"
Add-LatestItem -Name "latest_video_upload_status_json" -Filter "video-upload-status-*.json"
Add-Item -Name "frontend_build_proof_script" -Path "scripts/qwencloud-frontend-build-proof.ps1" -Required $false
Add-Item -Name "frontend_api_health_mapping" -Path "frontend/src/app/core/dream-api.service.ts" -Required $false
Add-Item -Name "hackathon_demo_route_source" -Path "frontend/src/app/features/hackathon-demo/hackathon-demo.component.ts" -Required $false
Add-Item -Name "hackathon_demo_route_template" -Path "frontend/src/app/features/hackathon-demo/hackathon-demo.component.html" -Required $false
Add-Item -Name "hackathon_demo_route_styles" -Path "frontend/src/app/features/hackathon-demo/hackathon-demo.component.scss" -Required $false
Add-Item -Name "hackathon_demo_route_tests" -Path "frontend/src/app/features/hackathon-demo/hackathon-demo.component.spec.ts" -Required $false
Add-Item -Name "seeded_demo_artifact_script" -Path "scripts/qwencloud_seed_demo_artifact.py" -Required $false
Add-LatestItem -Name "latest_seeded_demo_artifact_zip" -Filter "seeded-demo-artifact-*.zip"
Add-Item -Name "judge_rehearsal_script" -Path "scripts/qwencloud-judge-rehearsal.ps1" -Required $false
Add-LatestItem -Name "latest_judge_rehearsal_markdown" -Filter "judge-rehearsal-*.md"
Add-LatestItem -Name "latest_judge_rehearsal_json" -Filter "judge-rehearsal-*.json"
Add-LatestItem -Name "latest_frontend_build_proof_markdown" -Filter "frontend-build-proof-*.md"
Add-LatestItem -Name "latest_frontend_build_proof_json" -Filter "frontend-build-proof-*.json"
Add-LatestItem -Name "latest_frontend_install_stdout" -Filter "frontend-npm-ci-*.out"
Add-LatestItem -Name "latest_frontend_install_stderr" -Filter "frontend-npm-ci-*.err"
Add-LatestItem -Name "latest_frontend_build_stdout" -Filter "frontend-npm-build-*.out"
Add-LatestItem -Name "latest_frontend_build_stderr" -Filter "frontend-npm-build-*.err"
Add-LatestItem -Name "latest_frontend_test_stdout" -Filter "frontend-npm-test-*.out"
Add-LatestItem -Name "latest_frontend_test_stderr" -Filter "frontend-npm-test-*.err"
Add-Item -Name "final_action_board_script" -Path "scripts/qwencloud-final-action-board.ps1" -Required $false
Add-Item -Name "final_sprint_script" -Path "scripts/qwencloud-final-sprint.ps1" -Required $false
Add-Item -Name "final_external_handoff_script" -Path "scripts/qwencloud-final-external-handoff.ps1" -Required $false
Add-Item -Name "deadline_guard_script" -Path "scripts/qwencloud-deadline-guard.ps1" -Required $false
Add-Item -Name "deadline_guard_markdown" -Path $deadlineGuard.markdown
Add-Item -Name "deadline_guard_json" -Path $deadlineGuard.json
Add-Item -Name "live_inputs_intake_script" -Path "scripts/qwencloud-live-inputs-intake.ps1" -Required $false
Add-Item -Name "live_inputs_intake_markdown" -Path $liveInputs.markdown
Add-Item -Name "live_inputs_intake_json" -Path $liveInputs.json
Add-Item -Name "release_config_audit_script" -Path "scripts/qwencloud-release-config-audit.ps1" -Required $false
Add-Item -Name "release_config_audit_markdown" -Path $releaseConfig.markdown
Add-Item -Name "release_config_audit_json" -Path $releaseConfig.json
Add-Item -Name "github_ci_proof_script" -Path "scripts/qwencloud-github-ci-proof.ps1" -Required $false
Add-Item -Name "github_ci_proof_markdown" -Path $githubCiProof.markdown
Add-Item -Name "github_ci_proof_json" -Path $githubCiProof.json
Add-Item -Name "final_action_board_markdown" -Path $actionBoard.markdown -Required $false
Add-Item -Name "final_action_board_json" -Path $actionBoard.json -Required $false
Add-Item -Name "final_external_handoff_markdown" -Path $externalHandoff.markdown -Required $false
Add-Item -Name "final_external_handoff_json" -Path $externalHandoff.json -Required $false
Add-Item -Name "final_external_handoff_zip" -Path $externalHandoff.zip -Required $false
Add-LatestItem -Name "latest_final_sprint_markdown" -Filter "final-sprint-*.md"
Add-LatestItem -Name "latest_final_sprint_json" -Filter "final-sprint-*.json"
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
Add-Item -Name "devpost_autofill_snippet_markdown" -Path $autofillSnippet.markdown
Add-Item -Name "devpost_autofill_snippet_json" -Path $autofillSnippet.json
Add-Item -Name "devpost_autofill_snippet_javascript" -Path $autofillSnippet.javascript
Add-Item -Name "devpost_autofill_snippet_script" -Path "scripts/qwencloud-devpost-autofill-snippet.ps1" -Required $false
Add-Item -Name "official_rules_gate_markdown" -Path $officialRulesGate.markdown
Add-Item -Name "official_rules_gate_json" -Path $officialRulesGate.json
Add-Item -Name "official_rules_gate_script" -Path "scripts/qwencloud-official-rules-gate.ps1" -Required $false
Add-Item -Name "official_source_refresh_script" -Path "scripts/qwencloud-official-source-refresh.ps1" -Required $false
Add-Item -Name "official_source_refresh_markdown" -Path $officialSourceRefresh.markdown
Add-Item -Name "official_source_refresh_json" -Path $officialSourceRefresh.json
Add-Item -Name "official_requirements_snapshot" -Path "docs/qwencloud-official-requirements-snapshot.md" -Required $false
Add-LatestItem -Name "latest_official_source_refresh_markdown" -Filter "official-source-refresh-*.md"
Add-LatestItem -Name "latest_official_source_refresh_json" -Filter "official-source-refresh-*.json"
Add-Item -Name "testing_and_rights_notes" -Path "docs/qwencloud-testing-and-rights-notes.md" -Required $false
Add-Item -Name "post_submit_verification_script" -Path "scripts/qwencloud-post-submit-verification.ps1" -Required $false
Add-Item -Name "local_proof_powershell_script" -Path "scripts/qwencloud-run-local-proof.ps1" -Required $false
Add-Item -Name "local_proof_bash_script" -Path "scripts/qwencloud-run-local-proof.sh" -Required $false
Add-LatestItem -Name "latest_post_submit_verification_markdown" -Filter "devpost-post-submit-verification-*.md"
Add-LatestItem -Name "latest_post_submit_verification_json" -Filter "devpost-post-submit-verification-*.json"
Add-Item -Name "judging_scorecard_markdown" -Path $judgingScorecard.markdown
Add-Item -Name "judging_scorecard_json" -Path $judgingScorecard.json
Add-Item -Name "judging_scorecard_script" -Path "scripts/qwencloud-judging-scorecard.ps1" -Required $false
Add-Item -Name "judging_evidence_matrix" -Path "docs/qwencloud-judging-evidence-matrix.md"
Add-Item -Name "cloud_credentials_handoff_markdown" -Path $cloudHandoff.markdown
Add-Item -Name "cloud_credentials_template" -Path $cloudHandoff.template
Add-Item -Name "cloud_credentials_handoff_json" -Path $cloudHandoff.json
Add-Item -Name "github_secrets_handoff_script" -Path "scripts/qwencloud-github-secrets-handoff.ps1" -Required $false
Add-Item -Name "github_release_artifact_ingest_script" -Path "scripts/qwencloud-github-release-artifact-ingest.ps1" -Required $false
Add-Item -Name "github_release_summary_script" -Path "scripts/qwencloud-release-summary.ps1" -Required $false
Add-Item -Name "github_release_workflow" -Path ".github/workflows/qwencloud-release.yml" -Required $false
Add-Item -Name "github_release_workflow_handoff" -Path "docs/qwencloud-github-release-workflow.md" -Required $false
Add-LatestItem -Name "latest_github_release_artifact_ingest_markdown" -Filter "github-release-artifact-ingest-*.md"
Add-LatestItem -Name "latest_github_release_artifact_ingest_json" -Filter "github-release-artifact-ingest-*.json"
Add-LatestItem -Name "latest_deploy_preflight_markdown" -Filter "deploy-preflight-*.md"
Add-LatestItem -Name "latest_deploy_preflight_json" -Filter "deploy-preflight-*.json"
Add-LatestItem -Name "latest_docker_build_stdout" -Filter "docker-build-*.out"
Add-LatestItem -Name "latest_docker_build_stderr" -Filter "docker-build-*.err"
Add-LatestItem -Name "latest_docker_run_stdout" -Filter "docker-run-*.out"
Add-LatestItem -Name "latest_docker_run_stderr" -Filter "docker-run-*.err"

$ready = $missing.Count -eq 0
$gitCommit = Invoke-GitText -Arguments @("rev-parse", "HEAD")
$gitBranch = Invoke-GitText -Arguments @("rev-parse", "--abbrev-ref", "HEAD")
$gitStatus = Invoke-GitText -Arguments @("status", "--porcelain")
$gitBranchLine = (Invoke-GitText -Arguments @("status", "-sb") -split "`r?`n" | Select-Object -First 1)
$gitWorktreeClean = [string]::IsNullOrWhiteSpace($gitStatus)
$gitRemoteSynced = (-not [string]::IsNullOrWhiteSpace($gitBranchLine)) -and
    ($gitBranchLine -match "\.\.\.") -and
    ($gitBranchLine -notmatch "\[(ahead|behind)")

$manifest = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    readyForUpload = $ready
    allowDraft = [bool]$AllowDraft
    repoUrl = $RepoUrl
    gitCommit = $gitCommit
    gitBranch = $gitBranch
    gitWorktreeClean = $gitWorktreeClean
    gitRemoteSynced = $gitRemoteSynced
    demoVideoUrl = $DemoVideoUrl
    backendUrl = $BackendUrl
    blogPostUrl = $BlogPostUrl
    envFile = $EnvFile
    importedEnvNames = $importedEnvNames
    officialSourceFingerprints = $officialSourceRefresh.sourceFingerprints
    releaseSummaryPackaging = "not_bundled_generate_after_zip_hash"
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
    "- Git commit: $(if ($gitCommit) { $gitCommit } else { '<unknown>' })",
    "- Git branch: $(if ($gitBranch) { $gitBranch } else { '<unknown>' })",
    "- Git worktree clean: $gitWorktreeClean",
    "- Git remote synced: $gitRemoteSynced",
    "- Demo video URL: $(if ($DemoVideoUrl) { $DemoVideoUrl } else { '<missing>' })",
    "- Backend URL: $(if ($BackendUrl) { $BackendUrl } else { '<missing>' })",
    "- Env file imported: $(if ($EnvFile) { $EnvFile } else { '<none>' })",
    "- Bundle zip: $zipPath",
    "- Release summary: generate after this bundle; it is intentionally not bundled because it records the bundle ZIP SHA256.",
    "",
    "## Items",
    "",
    "| Item | Required | Exists | SHA256 | Details |",
    "|---|---:|---:|---|---|"
)
foreach ($item in $items) {
    $required = if ($item.required) { "yes" } else { "no" }
    $exists = if ($item.exists) { "yes" } else { "no" }
    $sha256 = if ($item.sourceSha256) { $item.sourceSha256 } else { "" }
    $lines += "| $($item.name) | $required | $exists | $sha256 | $($item.details -replace '\|', '/') |"
}

$hashedUploadItems = @($items | Where-Object { $_.exists -and $_.bundledPath -and $_.sourceSha256 })
if ($hashedUploadItems.Count -gt 0) {
    $lines += @(
        "",
        "## Upload Integrity",
        "",
        "Use these hashes to confirm the files selected in Devpost match this final bundle before submitting.",
        "",
        "| Upload Item | Size Bytes | SHA256 |",
        "|---|---:|---|"
    )
    foreach ($item in $hashedUploadItems) {
        $lines += "| $($item.name) | $($item.sizeBytes) | $($item.sourceSha256) |"
    }
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
