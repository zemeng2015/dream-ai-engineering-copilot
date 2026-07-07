# SPDX-License-Identifier: Apache-2.0

param(
    [Parameter(Mandatory = $false)]
    [string]$FrontendDir = "frontend",
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [string]$DistDir = "frontend/dist/frontend/browser",
    [switch]$SkipInstall,
    [switch]$RunTests,
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$reportJson = Join-Path $OutputDir "frontend-build-proof-$timestamp.json"
$reportMd = Join-Path $OutputDir "frontend-build-proof-$timestamp.md"
$checks = @()

function Add-Check([string]$Name, [bool]$Ok, [string]$Details, [bool]$Required = $true) {
    $script:checks += [ordered]@{
        name = $Name
        ok = $Ok
        required = $Required
        details = $Details
    }
}

function Get-CommandSource([string[]]$Names) {
    foreach ($name in $Names) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
    }
    return ""
}

function Invoke-LoggedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory
    )

    $stdout = Join-Path $OutputDir "$Name-$timestamp.out"
    $stderr = Join-Path $OutputDir "$Name-$timestamp.err"
    $started = Get-Date
    $proc = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory `
        -NoNewWindow `
        -Wait `
        -PassThru `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr
    $duration = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)

    return [ordered]@{
        name = $Name
        filePath = $FilePath
        arguments = $Arguments
        workingDirectory = $WorkingDirectory
        exitCode = $proc.ExitCode
        ok = ($proc.ExitCode -eq 0)
        durationSeconds = $duration
        stdout = $stdout
        stderr = $stderr
    }
}

function Read-ToolVersion([string]$Command, [string[]]$Arguments) {
    try {
        $output = & $Command @Arguments 2>$null
        if ($LASTEXITCODE -ne 0) { return "" }
        return (($output | Out-String).Trim())
    }
    catch {
        return ""
    }
}

$frontendPath = if (Test-Path -LiteralPath $FrontendDir) { (Resolve-Path -LiteralPath $FrontendDir).Path } else { $FrontendDir }
$distPath = if (Test-Path -LiteralPath $DistDir) { (Resolve-Path -LiteralPath $DistDir).Path } else { $DistDir }
$packageJson = Join-Path $frontendPath "package.json"
$packageLock = Join-Path $frontendPath "package-lock.json"
$nodeModules = Join-Path $frontendPath "node_modules"
$distIndex = Join-Path $distPath "index.html"

$npm = Get-CommandSource -Names @("npm.cmd", "npm")
$node = Get-CommandSource -Names @("node.exe", "node")

Add-Check -Name "frontend_dir_exists" -Ok (Test-Path -LiteralPath $frontendPath) -Details $frontendPath
Add-Check -Name "package_json_exists" -Ok (Test-Path -LiteralPath $packageJson) -Details $packageJson
Add-Check -Name "package_lock_exists" -Ok (Test-Path -LiteralPath $packageLock) -Details $packageLock
Add-Check -Name "node_available" -Ok (-not [string]::IsNullOrWhiteSpace($node)) -Details $(if ($node) { "$node; version=$(Read-ToolVersion -Command $node -Arguments @('--version'))" } else { "missing" })
Add-Check -Name "npm_available" -Ok (-not [string]::IsNullOrWhiteSpace($npm)) -Details $(if ($npm) { "$npm; version=$(Read-ToolVersion -Command $npm -Arguments @('--version'))" } else { "missing" })

$processes = @()
if ((Test-Path -LiteralPath $frontendPath) -and (-not [string]::IsNullOrWhiteSpace($npm))) {
    $needsInstall = -not (Test-Path -LiteralPath $nodeModules)
    if ($needsInstall -and $SkipInstall) {
        Add-Check -Name "frontend_dependencies" -Ok $false -Details "node_modules missing and -SkipInstall set"
    }
    elseif ($needsInstall) {
        $install = Invoke-LoggedProcess -Name "frontend-npm-ci" -FilePath $npm -Arguments @("ci") -WorkingDirectory $frontendPath
        $processes += $install
        Add-Check -Name "frontend_npm_ci" -Ok $install.ok -Details "exit=$($install.exitCode); stdout=$($install.stdout); stderr=$($install.stderr)"
    }
    else {
        Add-Check -Name "frontend_dependencies" -Ok $true -Details "node_modules present" -Required $false
    }

    if (Test-Path -LiteralPath $nodeModules) {
        $build = Invoke-LoggedProcess -Name "frontend-npm-build" -FilePath $npm -Arguments @("run", "build") -WorkingDirectory $frontendPath
        $processes += $build
        Add-Check -Name "frontend_npm_build" -Ok $build.ok -Details "exit=$($build.exitCode); stdout=$($build.stdout); stderr=$($build.stderr)"

        if ($RunTests) {
            $tests = Invoke-LoggedProcess -Name "frontend-npm-test" -FilePath $npm -Arguments @("test", "--", "--watch=false", "--browsers=ChromeHeadless") -WorkingDirectory $frontendPath
            $processes += $tests
            Add-Check -Name "frontend_npm_test_headless" -Ok $tests.ok -Details "exit=$($tests.exitCode); stdout=$($tests.stdout); stderr=$($tests.stderr)"
        }
    }
}

Add-Check -Name "frontend_dist_index_exists" -Ok (Test-Path -LiteralPath $distIndex) -Details $distIndex

$requiredFailures = @($checks | Where-Object { $_.required -and -not $_.ok })
$ready = $requiredFailures.Count -eq 0
$status = if ($ready) { "READY" } else { "DRAFT" }

$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = $status
    readyForFrontendDemo = $ready
    frontendDir = $frontendPath
    distDir = $distPath
    distIndex = $distIndex
    runTests = [bool]$RunTests
    skipInstall = [bool]$SkipInstall
    node = $node
    npm = $npm
    processes = $processes
    checks = $checks
    reportJson = $reportJson
    reportMarkdown = $reportMd
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Frontend Build Proof ($timestamp)",
    "",
    "- Status: $status",
    "- Ready for frontend demo: $ready",
    "- Frontend dir: ``$frontendPath``",
    "- Dist dir: ``$distPath``",
    "- Dist index: ``$distIndex``",
    "- Run tests: $([bool]$RunTests)",
    "",
    "## Process Runs",
    "",
    "| Step | Exit | Seconds | Stdout | Stderr |",
    "|---|---:|---:|---|---|"
)
if ($processes.Count -eq 0) {
    $lines += "| <none> |  |  |  |  |"
}
else {
    foreach ($proc in $processes) {
        $lines += "| $($proc.name) | $($proc.exitCode) | $($proc.durationSeconds) | $($proc.stdout) | $($proc.stderr) |"
    }
}

$lines += @(
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
        "## Missing Required Items",
        ""
    )
    foreach ($failure in $requiredFailures) {
        $lines += "- $($failure.name): $($failure.details)"
    }
}

Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($ready) {
    Write-Host "Frontend build proof READY: $reportMd"
}
else {
    Write-Host "Frontend build proof DRAFT: $reportMd" -ForegroundColor Yellow
    Write-Host "Missing required items: $($requiredFailures.name -join ', ')"
}
Write-Host "JSON: $reportJson"

if (-not $ready -and -not $AllowDraft) {
    exit 1
}
