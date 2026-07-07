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
    [string]$EnvFile = "",
    [switch]$SkipPacket,
    [switch]$SkipBackendDraft,
    [switch]$SkipExternalUrlChecks,
    [switch]$SkipLocalVideoChecks,
    [switch]$AllowDraftPacket
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
. (Join-Path $PSScriptRoot "qwencloud-env.ps1")
$importedEnvNames = @()
if (-not [string]::IsNullOrWhiteSpace($EnvFile)) {
    $importedEnvNames = @(Import-QwenCloudEnvFile -Path $EnvFile)
}
$reportJson = Join-Path $OutputDir "final-readiness-$timestamp.json"
$reportMd = Join-Path $OutputDir "final-readiness-$timestamp.md"
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

function Has-Env([string]$Name) {
    return Test-QwenCloudEnvValuePresent -Name $Name
}

function Get-PowerShellExe {
    $pwsh = Get-Command "pwsh" -ErrorAction SilentlyContinue
    if ($pwsh) { return $pwsh.Source }

    $powershell = Get-Command "powershell" -ErrorAction SilentlyContinue
    if ($powershell) { return $powershell.Source }

    throw "PowerShell executable not found."
}

function Test-File([string]$Path, [int]$MinBytes = 1) {
    if (-not (Test-Path $Path)) {
        return [pscustomobject]@{ ok = $false; details = "missing: $Path" }
    }
    $item = Get-Item $Path
    return [pscustomobject]@{
        ok = $item.Length -ge $MinBytes
        details = "path=$Path; size=$($item.Length)"
    }
}

function Test-ServerlessDevsDefaultAccess {
    if (-not (Has-Command "s")) {
        return [pscustomobject]@{ ok = $false; details = "s command missing" }
    }

    try {
        $output = (& s config get -a default 2>&1) -join "`n"
        $ok = $output -notmatch "not yet|not found|not.*configured|configured key information"
        $details = if ($ok) { "default access configured" } else { "default access not configured" }
        return [pscustomobject]@{ ok = $ok; details = $details }
    }
    catch {
        return [pscustomobject]@{ ok = $false; details = $_.Exception.Message }
    }
}

function Test-DockerDaemon {
    if (-not (Has-Command "docker")) {
        return [pscustomobject]@{ ok = $false; details = "docker command missing" }
    }

    try {
        $stdout = Join-Path $OutputDir "final-readiness-docker-info-$timestamp.out"
        $stderr = Join-Path $OutputDir "final-readiness-docker-info-$timestamp.err"
        $proc = Start-Process -FilePath "docker" -ArgumentList @("info") -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
        return [pscustomobject]@{ ok = ($proc.ExitCode -eq 0); details = "exit=$($proc.ExitCode); stdout=$stdout; stderr=$stderr" }
    }
    catch {
        return [pscustomobject]@{ ok = $false; details = $_.Exception.Message }
    }
}

function Test-LatestDeployPreflight {
    $candidates = @(Get-ChildItem -LiteralPath $OutputDir -Filter "deploy-preflight-*.json" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 20)
    $head = ""
    try {
        $head = (git rev-parse HEAD).Trim()
    }
    catch {
        $head = ""
    }
    if ($candidates.Count -eq 0) {
        return [pscustomobject]@{
            ok = $false
            details = "missing deploy-preflight-*.json; run scripts/qwencloud-deploy-preflight.ps1 -EnvFile .env.qwencloud.local -BuildImage -SmokeContainer -AllowDraft"
        }
    }

    $latestDetails = ""
    foreach ($candidate in $candidates) {
        try {
            $preflight = Get-Content -LiteralPath $candidate.FullName -Raw | ConvertFrom-Json
            $buildCheck = @($preflight.checks | Where-Object { $_.name -eq "docker.build" } | Select-Object -First 1)
            $smokeCheck = @($preflight.checks | Where-Object { $_.name -eq "docker.smoke_container" } | Select-Object -First 1)
            $showcaseCheck = @($preflight.checks | Where-Object { $_.name -eq "docker.smoke_showcase" } | Select-Object -First 1)
            $preflightCommit = [string]$preflight.gitCommit
            $commitMatchesHead = (-not [string]::IsNullOrWhiteSpace($head)) -and ($preflightCommit -eq $head)
            $details = "path=$($candidate.FullName); gitCommit=$preflightCommit; head=$head; commitMatchesHead=$commitMatchesHead; buildImage=$($preflight.buildImage); smokeContainer=$($preflight.smokeContainer); docker.build=$($buildCheck.ok); docker.smoke_container=$($smokeCheck.ok); docker.smoke_showcase=$($showcaseCheck.ok)"
            if ([string]::IsNullOrWhiteSpace($latestDetails)) {
                $latestDetails = $details
            }
            if ([bool]$preflight.buildImage -and [bool]$preflight.smokeContainer -and [bool]$buildCheck.ok -and [bool]$smokeCheck.ok -and [bool]$showcaseCheck.ok -and $commitMatchesHead) {
                return [pscustomobject]@{
                    ok = $true
                    details = $details
                }
            }
        }
        catch {
            if ([string]::IsNullOrWhiteSpace($latestDetails)) {
                $latestDetails = "failed to parse $($candidate.FullName): $($_.Exception.Message)"
            }
        }
    }

    return [pscustomobject]@{
        ok = $false
        details = "no recent complete build+smoke preflight found; latest=$latestDetails"
    }
}

function Get-VideoMetadata([string]$Path) {
    if (-not (Test-Path $Path)) { return $null }
    if (-not (Has-Command "ffprobe")) { return $null }

    $probeJson = & ffprobe -v error -show_entries format=duration,size,format_name -show_streams -of json $Path
    $probe = $probeJson | ConvertFrom-Json
    $stream = @($probe.streams | Where-Object { $_.codec_type -eq "video" } | Select-Object -First 1)
    return [pscustomobject]@{
        duration = [double]$probe.format.duration
        size = [int64]$probe.format.size
        format = $probe.format.format_name
        width = if ($stream) { [int]$stream.width } else { 0 }
        height = if ($stream) { [int]$stream.height } else { 0 }
        codec = if ($stream) { [string]$stream.codec_name } else { "" }
    }
}

function Test-HeadCiSuccess {
    if (-not (Has-Command "gh")) {
        return [pscustomobject]@{ ok = $false; details = "gh command missing" }
    }

    try {
        $head = (git rev-parse HEAD).Trim()
        $runsJson = gh run list --branch main --limit 10 --json headSha,status,conclusion,url,displayTitle
        $runs = $runsJson | ConvertFrom-Json
        $run = @($runs | Where-Object { $_.headSha -eq $head } | Select-Object -First 1)
        if (-not $run) {
            return [pscustomobject]@{ ok = $false; details = "no CI run found for HEAD $head" }
        }
        return [pscustomobject]@{ ok = ($run.status -eq "completed" -and $run.conclusion -eq "success"); details = "$($run.displayTitle); status=$($run.status); conclusion=$($run.conclusion); $($run.url)" }
    }
    catch {
        return [pscustomobject]@{ ok = $false; details = $_.Exception.Message }
    }
}

function Invoke-DeadlineGuard {
    if (-not (Test-Path "scripts/qwencloud-deadline-guard.ps1")) {
        return [pscustomobject]@{
            ok = $false
            details = "missing scripts/qwencloud-deadline-guard.ps1"
        }
    }

    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "deadline-guard-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-deadline-guard.ps1",
        "-OutputDir", $OutputDir,
        "-AllowDraft"
    )

    $stdout = Join-Path $OutputDir "final-readiness-deadline-guard-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-readiness-deadline-guard-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        return [pscustomobject]@{ ok = $false; details = "exit=$($proc.ExitCode); stdout=$stdout; stderr=$stderr" }
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "deadline-guard-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $newest = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $newest) {
        $newest = @($after | Select-Object -First 1)
    }
    if (-not $newest) {
        return [pscustomobject]@{ ok = $false; details = "deadline guard JSON not found; stdout=$stdout; stderr=$stderr" }
    }

    $guard = Get-Content -LiteralPath $newest.FullName -Raw | ConvertFrom-Json
    $failedRequired = @($guard.checks | Where-Object { $_.required -and -not $_.ok } | ForEach-Object { $_.name })
    return [pscustomobject]@{
        ok = [bool]$guard.readyForSubmissionWindow
        details = if ($guard.readyForSubmissionWindow) { "deadline guard READY: $($newest.FullName); urgency=$($guard.urgency); hoursRemaining=$($guard.hoursRemaining)" } else { "deadline guard DRAFT: $($newest.FullName); missing=$($failedRequired -join ', ')" }
    }
}

function Invoke-LiveInputsIntake {
    if (-not (Test-Path "scripts/qwencloud-live-inputs-intake.ps1")) {
        return [pscustomobject]@{
            ok = $false
            details = "missing scripts/qwencloud-live-inputs-intake.ps1"
        }
    }

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

    $stdout = Join-Path $OutputDir "final-readiness-live-inputs-intake-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-readiness-live-inputs-intake-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        return [pscustomobject]@{ ok = $false; details = "exit=$($proc.ExitCode); stdout=$stdout; stderr=$stderr" }
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "live-inputs-intake-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $newest = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $newest) {
        $newest = @($after | Select-Object -First 1)
    }
    if (-not $newest) {
        return [pscustomobject]@{ ok = $false; details = "live inputs intake JSON not found; stdout=$stdout; stderr=$stderr" }
    }

    $intake = Get-Content -LiteralPath $newest.FullName -Raw | ConvertFrom-Json
    $failedRequired = @($intake.missingRequiredChecks)
    return [pscustomobject]@{
        ok = [bool]$intake.readyForLiveInputs
        details = if ($intake.readyForLiveInputs) { "live inputs READY: $($newest.FullName)" } else { "live inputs DRAFT: $($newest.FullName); missing=$($failedRequired -join ', ')" }
    }
}

function Invoke-ReleaseConfigAudit {
    if (-not (Test-Path "scripts/qwencloud-release-config-audit.ps1")) {
        return [pscustomobject]@{
            ok = $false
            details = "missing scripts/qwencloud-release-config-audit.ps1"
        }
    }

    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "release-config-audit-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-release-config-audit.ps1",
        "-OutputDir", $OutputDir,
        "-AllowDraft"
    )
    if ($EnvFile) { $args += @("-EnvFile", $EnvFile) }

    $stdout = Join-Path $OutputDir "final-readiness-release-config-audit-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-readiness-release-config-audit-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        return [pscustomobject]@{ ok = $false; details = "exit=$($proc.ExitCode); stdout=$stdout; stderr=$stderr" }
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "release-config-audit-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $newest = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $newest) {
        $newest = @($after | Select-Object -First 1)
    }
    if (-not $newest) {
        return [pscustomobject]@{ ok = $false; details = "release config audit JSON not found; stdout=$stdout; stderr=$stderr" }
    }

    $audit = Get-Content -LiteralPath $newest.FullName -Raw | ConvertFrom-Json
    $failedRequired = @($audit.missingRequiredChecks)
    return [pscustomobject]@{
        ok = [bool]$audit.readyForReleaseConfig
        details = if ($audit.readyForReleaseConfig) { "release config audit READY: $($newest.FullName)" } else { "release config audit DRAFT: $($newest.FullName); missing=$($failedRequired -join ', ')" }
    }
}

function Invoke-GitHubCiProof {
    if (-not (Test-Path "scripts/qwencloud-github-ci-proof.ps1")) {
        return [pscustomobject]@{
            ok = $false
            details = "missing scripts/qwencloud-github-ci-proof.ps1"
        }
    }

    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "github-ci-proof-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-github-ci-proof.ps1",
        "-RepoUrl", $RepoUrl,
        "-OutputDir", $OutputDir,
        "-Branch", "main",
        "-AllowDraft"
    )

    $stdout = Join-Path $OutputDir "final-readiness-github-ci-proof-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-readiness-github-ci-proof-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        return [pscustomobject]@{ ok = $false; details = "exit=$($proc.ExitCode); stdout=$stdout; stderr=$stderr" }
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "github-ci-proof-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $newest = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $newest) {
        $newest = @($after | Select-Object -First 1)
    }
    if (-not $newest) {
        return [pscustomobject]@{ ok = $false; details = "github CI proof JSON not found; stdout=$stdout; stderr=$stderr" }
    }

    $proof = Get-Content -LiteralPath $newest.FullName -Raw | ConvertFrom-Json
    $failedRequired = @($proof.checks | Where-Object { $_.required -and -not $_.ok } | ForEach-Object { $_.name })
    return [pscustomobject]@{
        ok = [bool]$proof.readyForGitHubCiProof
        details = if ($proof.readyForGitHubCiProof) { "GitHub CI proof READY: $($newest.FullName)" } else { "GitHub CI proof DRAFT: $($newest.FullName); missing=$($failedRequired -join ', ')" }
    }
}

function Test-RepoPublication([string]$Url) {
    if (-not (Has-Command "gh")) {
        return [pscustomobject]@{
            publicOk = $false
            licenseOk = $false
            details = "gh command missing"
        }
    }
    if ($Url -notmatch "^https://github.com/(?<owner>[^/]+)/(?<repo>[^/]+?)(\.git)?$") {
        return [pscustomobject]@{
            publicOk = $false
            licenseOk = $false
            details = "not a normalized GitHub HTTPS repo URL: $Url"
        }
    }

    $repoName = "$($matches.owner)/$($matches.repo)"
    try {
        $json = gh repo view $repoName --json nameWithOwner,visibility,isPrivate,url,licenseInfo
        $repo = $json | ConvertFrom-Json
        $licenseKey = if ($repo.licenseInfo) { [string]$repo.licenseInfo.key } else { "" }
        return [pscustomobject]@{
            publicOk = ($repo.visibility -eq "PUBLIC" -and -not [bool]$repo.isPrivate)
            licenseOk = ($licenseKey -eq "apache-2.0")
            details = "repo=$($repo.nameWithOwner); visibility=$($repo.visibility); isPrivate=$($repo.isPrivate); license=$licenseKey; url=$($repo.url)"
        }
    }
    catch {
        return [pscustomobject]@{
            publicOk = $false
            licenseOk = $false
            details = $_.Exception.Message
        }
    }
}

function Invoke-SubmissionPacket {
    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "devpost-submission-packet-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)

    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-hackathon-submission-packet.ps1",
        "-RepoUrl", $RepoUrl,
        "-OutputDir", $OutputDir
    )
    if ($DemoVideoUrl) { $args += @("-DemoVideoUrl", $DemoVideoUrl) }
    if ($BackendUrl) { $args += @("-BackendUrl", $BackendUrl) }
    if ($BlogPostUrl) { $args += @("-BlogPostUrl", $BlogPostUrl) }
    if ($SkipBackendDraft) { $args += "-SkipBackendDraft" }
    if ($SkipExternalUrlChecks) { $args += "-SkipExternalUrlChecks" }
    if ($AllowDraftPacket -or [string]::IsNullOrWhiteSpace($DemoVideoUrl) -or [string]::IsNullOrWhiteSpace($BackendUrl)) {
        $args += "-AllowDraft"
    }

    $stdout = Join-Path $OutputDir "final-readiness-packet-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-readiness-packet-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        return [pscustomobject]@{ ok = $false; details = "exit=$($proc.ExitCode); stdout=$stdout; stderr=$stderr"; packet = $null }
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "devpost-submission-packet-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $newest = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $newest) {
        $newest = @($after | Select-Object -First 1)
    }
    if (-not $newest) {
        return [pscustomobject]@{ ok = $false; details = "packet JSON not found; stdout=$stdout; stderr=$stderr"; packet = $null }
    }

    $packet = Get-Content -LiteralPath $newest.FullName -Raw | ConvertFrom-Json
    $failedRequired = @($packet.checks | Where-Object { $_.required -and -not $_.ok } | ForEach-Object { $_.name })
    return [pscustomobject]@{
        ok = [bool]$packet.readyForDevpost
        details = if ($packet.readyForDevpost) { "packet READY: $($newest.FullName)" } else { "packet DRAFT: $($newest.FullName); missing=$($failedRequired -join ', ')" }
        packet = $packet
    }
}

function Invoke-AlibabaProofIntegrity {
    if (-not (Test-Path "scripts/qwencloud-validate-alibaba-proof.ps1")) {
        return [pscustomobject]@{
            ok = $false
            details = "missing scripts/qwencloud-validate-alibaba-proof.ps1"
        }
    }

    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "alibaba-proof-integrity-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-validate-alibaba-proof.ps1",
        "-OutputDir", $OutputDir,
        "-AllowDraft"
    )
    if ($BackendUrl) { $args += @("-BackendUrl", $BackendUrl) }

    $stdout = Join-Path $OutputDir "final-readiness-alibaba-proof-integrity-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-readiness-alibaba-proof-integrity-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        return [pscustomobject]@{ ok = $false; details = "exit=$($proc.ExitCode); stdout=$stdout; stderr=$stderr" }
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "alibaba-proof-integrity-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $newest = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $newest) {
        $newest = @($after | Select-Object -First 1)
    }
    if (-not $newest) {
        return [pscustomobject]@{ ok = $false; details = "integrity JSON not found; stdout=$stdout; stderr=$stderr" }
    }

    $proof = Get-Content -LiteralPath $newest.FullName -Raw | ConvertFrom-Json
    $failedRequired = @($proof.checks | Where-Object { $_.required -and -not $_.ok } | ForEach-Object { $_.name })
    return [pscustomobject]@{
        ok = [bool]$proof.readyForDevpostAlibabaProof
        details = if ($proof.readyForDevpostAlibabaProof) { "proof integrity READY: $($newest.FullName)" } else { "proof integrity DRAFT: $($newest.FullName); missing=$($failedRequired -join ', ')" }
    }
}

function Invoke-OfficialRulesGate {
    if (-not (Test-Path "scripts/qwencloud-official-rules-gate.ps1")) {
        return [pscustomobject]@{
            ok = $false
            details = "missing scripts/qwencloud-official-rules-gate.ps1"
        }
    }

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

    $stdout = Join-Path $OutputDir "final-readiness-official-rules-gate-$timestamp.out"
    $stderr = Join-Path $OutputDir "final-readiness-official-rules-gate-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        return [pscustomobject]@{ ok = $false; details = "exit=$($proc.ExitCode); stdout=$stdout; stderr=$stderr" }
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter "official-rules-gate-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $newest = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $newest) {
        $newest = @($after | Select-Object -First 1)
    }
    if (-not $newest) {
        return [pscustomobject]@{ ok = $false; details = "official rules gate JSON not found; stdout=$stdout; stderr=$stderr" }
    }

    $gate = Get-Content -LiteralPath $newest.FullName -Raw | ConvertFrom-Json
    $missingRequired = @($gate.missingRequired | ForEach-Object { $_ })
    return [pscustomobject]@{
        ok = [bool]$gate.readyForOfficialRules
        details = if ($gate.readyForOfficialRules) { "official rules READY: $($newest.FullName)" } else { "official rules DRAFT: $($newest.FullName); missing=$($missingRequired -join ', ')" }
    }
}

try {
    $gitStatus = @(git status --porcelain)
    Add-Check -Name "git_worktree_clean" -Ok ($gitStatus.Count -eq 0) -Details $(if ($gitStatus.Count -eq 0) { "clean" } else { "dirty" })
}
catch {
    Add-Check -Name "git_worktree_clean" -Ok $false -Details $_.Exception.Message
}

try {
    $sync = (git rev-list --left-right --count "HEAD...@{u}") -split "\s+"
    $ahead = [int]$sync[0]
    $behind = [int]$sync[1]
    Add-Check -Name "git_remote_synced" -Ok ($ahead -eq 0 -and $behind -eq 0) -Details "ahead=$ahead; behind=$behind"
}
catch {
    Add-Check -Name "git_remote_synced" -Ok $false -Details $_.Exception.Message
}

$ci = Test-HeadCiSuccess
Add-Check -Name "latest_head_ci_success" -Ok $ci.ok -Details $ci.details

$deadlineGuard = Invoke-DeadlineGuard
Add-Check -Name "submission_deadline_guard_ready" -Ok $deadlineGuard.ok -Details $deadlineGuard.details

$liveInputs = Invoke-LiveInputsIntake
Add-Check -Name "live_inputs_intake_ready" -Ok $liveInputs.ok -Details $liveInputs.details

$releaseConfig = Invoke-ReleaseConfigAudit
Add-Check -Name "release_config_audit_ready" -Ok $releaseConfig.ok -Details $releaseConfig.details

$githubCiProof = Invoke-GitHubCiProof
Add-Check -Name "github_ci_proof_ready" -Ok $githubCiProof.ok -Details $githubCiProof.details

$repoPublication = Test-RepoPublication -Url $RepoUrl
Add-Check -Name "repo_public" -Ok $repoPublication.publicOk -Details $repoPublication.details
Add-Check -Name "repo_license_apache_2_0" -Ok $repoPublication.licenseOk -Details $repoPublication.details

foreach ($tool in @("python", "docker", "s", "ffmpeg", "ffprobe", "gh")) {
    Add-Check -Name "tool.$tool" -Ok (Has-Command $tool) -Details $(if (Has-Command $tool) { (Get-Command $tool).Source } else { "missing" })
}

$docker = Test-DockerDaemon
Add-Check -Name "docker_daemon_ready" -Ok $docker.ok -Details $docker.details

$deployPreflight = Test-LatestDeployPreflight
Add-Check -Name "latest_deploy_preflight_build_smoke" -Ok $deployPreflight.ok -Details $deployPreflight.details

$sAccess = Test-ServerlessDevsDefaultAccess
Add-Check -Name "serverless_devs_default_access" -Ok $sAccess.ok -Details $sAccess.details

foreach ($envName in @("DASHSCOPE_API_KEY", "ALIBABA_CLOUD_REGION", "ALIBABA_CLOUD_CONTAINER_IMAGE")) {
    Add-Check -Name "env.$envName" -Ok (Has-Env $envName) -Details $(if (Has-Env $envName) { "set" } else { "missing" })
}
foreach ($envName in @("QWEN_BASE_URL", "QWEN_MODEL")) {
    Add-Check -Name "env.$envName" -Ok (Has-Env $envName) -Details $(if (Has-Env $envName) { "set" } else { "optional default available" }) -Required $false
}

foreach ($path in @(
    "docs/assets/qwencloud-architecture.png",
    "docs/assets/qwencloud-video-thumbnail.svg",
    "docs/assets/qwencloud-video-thumbnail.png",
    "docs/qwencloud-demo-video-captions.srt",
    "docs/qwencloud-demo-video-transcript.md",
    "docs/qwencloud-video-upload-handoff.md",
    "docs/qwencloud-official-requirements-snapshot.md",
    "frontend/src/app/core/dream-api.service.ts",
    "frontend/src/app/features/hackathon-demo/hackathon-demo.component.ts",
    "frontend/src/app/features/hackathon-demo/hackathon-demo.component.html",
    "frontend/src/app/features/hackathon-demo/hackathon-demo.component.scss",
    "frontend/src/app/features/hackathon-demo/hackathon-demo.component.spec.ts",
    "scripts/qwencloud-frontend-build-proof.ps1",
    "scripts/qwencloud-render-demo-video.ps1",
    "scripts/qwencloud-export-video-thumbnail.ps1",
    "scripts/qwencloud-devpost-video-url.ps1",
    "scripts/qwencloud-video-publication-handoff.ps1",
    "scripts/qwencloud-video-upload-status.ps1",
    "deploy/alibaba/serverless-devs.yaml",
    "scripts/qwencloud-cloud-credentials-handoff.ps1",
    "scripts/qwencloud-github-secrets-handoff.ps1",
    "scripts/qwencloud-devpost-handoff.ps1",
    "scripts/qwencloud-alibaba-release.ps1",
    "scripts/qwencloud-finalize-after-urls.ps1",
    "scripts/qwencloud-final-sprint.ps1",
    "scripts/qwencloud-final-action-board.ps1",
    "scripts/qwencloud-post-submit-verification.ps1",
    "scripts/qwencloud-official-rules-gate.ps1",
    "scripts/qwencloud-deadline-guard.ps1",
    "scripts/qwencloud-live-inputs-intake.ps1",
    "scripts/qwencloud-github-ci-proof.ps1",
    "scripts/qwencloud-github-release-artifact-ingest.ps1",
    "scripts/qwencloud-release-summary.ps1",
    "scripts/qwencloud-release-config-audit.ps1",
    ".github/workflows/qwencloud-release.yml",
    "docs/qwencloud-github-release-workflow.md",
    "docs/qwencloud-testing-and-rights-notes.md",
    "scripts/qwencloud-render-alibaba-proof-video.ps1",
    "scripts/qwencloud-validate-alibaba-proof.ps1",
    "scripts/qwencloud-hackathon-submission-packet.ps1",
    "scripts/qwencloud-devpost-draft-payload.ps1",
    "scripts/qwencloud-devpost-autofill-snippet.ps1",
    "scripts/qwencloud-judging-scorecard.ps1",
    "scripts/qwencloud-run-local-proof.ps1",
    "scripts/qwencloud-run-local-proof.sh",
    "scripts/qwencloud_seed_demo_artifact.py",
    "scripts/qwencloud-judge-rehearsal.ps1",
    "scripts/qwencloud-final-external-handoff.ps1",
    "scripts/qwencloud-official-source-refresh.ps1"
)) {
    $fileCheck = Test-File -Path $path
    Add-Check -Name "file.$path" -Ok $fileCheck.ok -Details $fileCheck.details
}

$localDemoVideoPath = "artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4"
$localDemoVideoFile = Test-File -Path $localDemoVideoPath
Add-Check -Name "file.$localDemoVideoPath" -Ok ($SkipLocalVideoChecks -or $localDemoVideoFile.ok) -Details $(if ($SkipLocalVideoChecks) { "skipped by -SkipLocalVideoChecks; $($localDemoVideoFile.details)" } else { $localDemoVideoFile.details }) -Required (-not $SkipLocalVideoChecks)

if ($SkipLocalVideoChecks) {
    Add-Check -Name "demo_video_under_3_minutes" -Ok $true -Details "skipped by -SkipLocalVideoChecks; public video URL is validated by scripts/qwencloud-video-upload-status.ps1" -Required $false
}
else {
    $demoVideo = Get-VideoMetadata -Path $localDemoVideoPath
    if ($demoVideo) {
        Add-Check -Name "demo_video_under_3_minutes" -Ok ($demoVideo.duration -gt 0 -and $demoVideo.duration -lt 180) -Details "duration=$($demoVideo.duration); size=$($demoVideo.size); resolution=$($demoVideo.width)x$($demoVideo.height)"
    }
    else {
        Add-Check -Name "demo_video_under_3_minutes" -Ok $false -Details "ffprobe unavailable or demo video missing"
    }
}

foreach ($path in @(
    "artifacts/qwencloud-proof/alibaba-deployment-screenshot.png",
    "artifacts/qwencloud-proof/alibaba-deployment-proof.mp4"
)) {
    $fileCheck = Test-File -Path $path
    Add-Check -Name "file.$path" -Ok $fileCheck.ok -Details $fileCheck.details
}

$proofIntegrity = Invoke-AlibabaProofIntegrity
Add-Check -Name "alibaba_proof_integrity_ready" -Ok $proofIntegrity.ok -Details $proofIntegrity.details

$officialRulesGate = Invoke-OfficialRulesGate
Add-Check -Name "official_rules_gate_ready" -Ok $officialRulesGate.ok -Details $officialRulesGate.details

if (-not $SkipPacket) {
    $packetCheck = Invoke-SubmissionPacket
    Add-Check -Name "devpost_submission_packet_ready" -Ok $packetCheck.ok -Details $packetCheck.details
}
else {
    Add-Check -Name "devpost_submission_packet_ready" -Ok $true -Details "skipped by -SkipPacket" -Required $false
}

$requiredFailures = @($checks | Where-Object { $_.required -and -not $_.ok })
$ready = $requiredFailures.Count -eq 0
$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    readyForFinalSubmit = $ready
    repoUrl = $RepoUrl
    demoVideoUrl = $DemoVideoUrl
    backendUrl = $BackendUrl
    blogPostUrl = $BlogPostUrl
    envFile = $EnvFile
    importedEnvNames = $importedEnvNames
    skipLocalVideoChecks = [bool]$SkipLocalVideoChecks
    reportJson = $reportJson
    reportMarkdown = $reportMd
    checks = $checks
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Final Readiness ($timestamp)",
    "",
    "- Ready for final Devpost submit: $ready",
    "- Repo: $RepoUrl",
    "- Demo video URL: $(if ($DemoVideoUrl) { $DemoVideoUrl } else { '<missing>' })",
    "- Backend URL: $(if ($BackendUrl) { $BackendUrl } else { '<missing>' })",
    "- Blog/social URL: $(if ($BlogPostUrl) { $BlogPostUrl } else { '<optional>' })",
    "- Env file imported: $(if ($EnvFile) { $EnvFile } else { '<none>' })",
    "",
    "## Checks",
    "",
    "| Check | Required | Result | Details |",
    "|---|---:|---:|---|"
)

foreach ($check in $checks) {
    $resultText = if ($check.ok) { "PASS" } else { "FAIL" }
    $required = if ($check.required) { "yes" } else { "no" }
    $lines += "| $($check.name) | $required | $resultText | $($check.details -replace '\|', '/') |"
}

$lines += @(
    "",
    "## Next Command",
    "",
    '```powershell',
    'scripts/qwencloud-alibaba-release.ps1 -EnvFile .env.qwencloud.local -DemoVideoUrl "<public-video-url>"',
    '```'
)

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
    Write-Host "Final readiness READY: $reportMd"
}
else {
    Write-Host "Final readiness DRAFT: $reportMd" -ForegroundColor Yellow
    Write-Host "Missing required checks: $($requiredFailures.name -join ', ')"
    exit 1
}
