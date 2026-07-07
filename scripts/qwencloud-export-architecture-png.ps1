param(
    [Parameter(Mandatory = $false)]
    [string]$InputSvg = "docs/assets/qwencloud-architecture.svg",
    [Parameter(Mandatory = $false)]
    [string]$OutputPng = "docs/assets/qwencloud-architecture.png",
    [Parameter(Mandatory = $false)]
    [int]$Width = 1280,
    [Parameter(Mandatory = $false)]
    [int]$Height = 720
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $InputSvg)) {
    throw "Input SVG not found: $InputSvg"
}

$browserCandidates = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles(x86)\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles(x86)\Microsoft\Edge\Application\msedge.exe"
)

$browser = $browserCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $browser) {
    throw "Chrome or Edge is required to export the architecture PNG."
}

$resolvedSvg = (Resolve-Path $InputSvg).Path
$resolvedOutput = Join-Path (Get-Location) $OutputPng
$outputDir = Split-Path -Parent $resolvedOutput
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

if (Test-Path $resolvedOutput) {
    Remove-Item -LiteralPath $resolvedOutput -Force
}

$tempOutput = Join-Path ([System.IO.Path]::GetTempPath()) "dream-qwencloud-architecture-$([System.Guid]::NewGuid().ToString('N')).png"
$tempProfile = Join-Path ([System.IO.Path]::GetTempPath()) "dream-qwencloud-chrome-$([System.Guid]::NewGuid().ToString('N'))"
$svgUri = [System.Uri]::new($resolvedSvg).AbsoluteUri
$args = @(
    "--headless=new",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "--user-data-dir=$tempProfile",
    "--hide-scrollbars",
    "--window-size=$Width,$Height",
    "--screenshot=$tempOutput",
    $svgUri
)

$stdout = Join-Path "artifacts/qwencloud-proof" "architecture-png-export.out"
$stderr = Join-Path "artifacts/qwencloud-proof" "architecture-png-export.err"
New-Item -ItemType Directory -Path (Split-Path -Parent $stdout) -Force | Out-Null
$proc = Start-Process -FilePath $browser -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
if ($proc.ExitCode -ne 0) {
    throw "Architecture PNG export failed. See $stderr"
}

if (-not (Test-Path $tempOutput)) {
    throw "Architecture PNG was not created: $tempOutput"
}

Move-Item -LiteralPath $tempOutput -Destination $resolvedOutput -Force
if (Test-Path $tempProfile) {
    Remove-Item -LiteralPath $tempProfile -Recurse -Force
}

$file = Get-Item -LiteralPath $resolvedOutput
if ($file.Length -le 0) {
    throw "Architecture PNG is empty: $resolvedOutput"
}

Write-Host "Architecture PNG exported: $OutputPng ($($file.Length) bytes)"
