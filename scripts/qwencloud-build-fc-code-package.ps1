# SPDX-License-Identifier: Apache-2.0

param(
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-fc-code",
    [Parameter(Mandatory = $false)]
    [string]$PythonVersion = "3.12",
    [Parameter(Mandatory = $false)]
    [string]$PythonAbi = "cp312",
    [Parameter(Mandatory = $false)]
    [string]$TargetPlatform = "manylinux2014_x86_64",
    [Parameter(Mandatory = $false)]
    [string]$Runtime = "custom.debian11",
    [switch]$SkipPipInstall,
    [switch]$SkipFrontendBuild
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$repoRootFull = [System.IO.Path]::GetFullPath($repoRoot)

function Resolve-RepoChildPath([string]$Path) {
    $candidate = if ([System.IO.Path]::IsPathRooted($Path)) {
        $Path
    }
    else {
        Join-Path $repoRoot $Path
    }

    return [System.IO.Path]::GetFullPath($candidate)
}

function Assert-RepoChildPath([string]$Path) {
    $full = Resolve-RepoChildPath -Path $Path
    $comparison = [System.StringComparison]::OrdinalIgnoreCase
    if (
        -not $full.Equals($repoRootFull, $comparison) -and
        -not $full.StartsWith($repoRootFull + [System.IO.Path]::DirectorySeparatorChar, $comparison)
    ) {
        throw "OutputDir must stay inside the repository: $full"
    }
    return $full
}

function Copy-RepoItem([string]$Source, [string]$Destination) {
    $sourcePath = Join-Path $repoRoot $Source
    if (-not (Test-Path -LiteralPath $sourcePath)) {
        throw "Required package source missing: $Source"
    }
    Copy-Item -LiteralPath $sourcePath -Destination $Destination -Recurse -Force
}

$frontendRoot = Join-Path $repoRoot "frontend"
$frontendDist = Join-Path $frontendRoot "dist/frontend/browser"
$requirementsLock = Join-Path $repoRoot "deploy/alibaba/requirements-fc312.lock.txt"
if (-not (Test-Path -LiteralPath $requirementsLock -PathType Leaf)) {
    throw "Function Compute dependency lock is missing: $requirementsLock"
}
if ($SkipPipInstall) {
    throw "-SkipPipInstall is unsafe for a clean FC package; dependencies are always rebuilt."
}
if (-not $SkipFrontendBuild) {
    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if ($null -eq $npm) {
        throw "npm is required to build the judge-facing Angular application."
    }

    Push-Location $frontendRoot
    try {
        & $npm.Source run build
        if ($LASTEXITCODE -ne 0) {
            throw "Angular production build failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}

$frontendIndex = Join-Path $frontendDist "index.html"
if (-not (Test-Path -LiteralPath $frontendIndex -PathType Leaf)) {
    throw "Angular production output missing: $frontendIndex"
}

$outputPath = Assert-RepoChildPath -Path $OutputDir
if (Test-Path -LiteralPath $outputPath) {
    Remove-Item -LiteralPath $outputPath -Recurse -Force
}
New-Item -ItemType Directory -Path $outputPath -Force | Out-Null

$dependencies = @(
    Get-Content -LiteralPath $requirementsLock |
        Where-Object { $_.Trim() -and -not $_.Trim().StartsWith("#") } |
        ForEach-Object { $_.Trim() }
)

$pipArgs = @(
    "-m", "pip", "install",
    "--upgrade",
    "--target", $outputPath,
    "--platform", $TargetPlatform,
    "--implementation", "cp",
    "--python-version", $PythonVersion,
    "--abi", $PythonAbi,
    "--only-binary=:all:",
    "--no-compile",
    "--requirement", $requirementsLock
)
& python @pipArgs
if ($LASTEXITCODE -ne 0) {
    throw "pip install for Function Compute code package failed with exit code $LASTEXITCODE"
}

Copy-RepoItem -Source "dream" -Destination $outputPath
Copy-RepoItem -Source "knowledge_packs" -Destination $outputPath

$frontendPackageRoot = Join-Path $outputPath "frontend/dist/frontend"
New-Item -ItemType Directory -Path $frontendPackageRoot -Force | Out-Null
Copy-RepoItem -Source "frontend/dist/frontend/browser" -Destination $frontendPackageRoot
$packagedFrontend = Join-Path $frontendPackageRoot "browser"
$frontendFileCount = @(Get-ChildItem -LiteralPath $packagedFrontend -Recurse -File).Count

$examplesDir = Join-Path $outputPath "examples"
New-Item -ItemType Directory -Path $examplesDir -Force | Out-Null
Copy-RepoItem -Source "examples/config" -Destination $examplesDir

foreach ($file in @("pyproject.toml", "README.md", "LICENSE", "NOTICE", "VERSION")) {
    Copy-RepoItem -Source $file -Destination $outputPath
}

$docsAssetsPackage = Join-Path $outputPath "docs/assets"
New-Item -ItemType Directory -Path $docsAssetsPackage -Force | Out-Null
Copy-RepoItem -Source "docs/assets/qwen-memory-ab-benchmark-summary.json" -Destination $docsAssetsPackage
Copy-RepoItem -Source "docs/qwen-memory-ab-benchmark.md" -Destination (Join-Path $outputPath "docs")
Copy-RepoItem -Source "docs/assets/qwen-experience-memory-benchmark-summary.json" -Destination $docsAssetsPackage
Copy-RepoItem -Source "docs/assets/qwen-experience-memory-benchmark-report.json" -Destination $docsAssetsPackage
Copy-RepoItem -Source "docs/qwen-experience-memory-benchmark.md" -Destination (Join-Path $outputPath "docs")

$deployPackage = Join-Path $outputPath "deploy/alibaba"
New-Item -ItemType Directory -Path $deployPackage -Force | Out-Null
Copy-RepoItem -Source "deploy/alibaba/requirements-fc312.lock.txt" -Destination $deployPackage
Copy-RepoItem -Source "deploy/alibaba/serverless-devs-runtime.yaml" -Destination $deployPackage

$bootstrapPath = Join-Path $outputPath "bootstrap"
$bootstrapLines = @(
    '#!/usr/bin/env bash',
    'set -euo pipefail',
    'CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"',
    'cd "${CODE_ROOT}"',
    'export PYTHONPATH="${CODE_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"',
    'export PORT="${FC_CUSTOM_LISTEN_PORT:-${PORT:-9000}}"',
    'PYTHON_BIN="${PYTHON_BIN:-}"',
    'if [[ -z "${PYTHON_BIN}" ]]; then',
    '  if [[ -x /var/fc/lang/python3.12/bin/python3 ]]; then',
    '    PYTHON_BIN=/var/fc/lang/python3.12/bin/python3',
    '  elif [[ -x /usr/bin/python3 ]]; then',
    '    PYTHON_BIN=/usr/bin/python3',
    '  else',
    '    PYTHON_BIN="$(command -v python3)"',
    '  fi',
    'fi',
    'exec "${PYTHON_BIN}" -m uvicorn dream.api.app:app --host 0.0.0.0 --port "${PORT}"'
)
[System.IO.File]::WriteAllText(
    $bootstrapPath,
    ($bootstrapLines -join "`n") + "`n",
    [System.Text.UTF8Encoding]::new($false)
)

$manifest = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    runtime = $Runtime
    python = $PythonVersion
    targetPlatform = $TargetPlatform
    outputDir = "."
    dependencies = $dependencies
    requirementsLock = "deploy/alibaba/requirements-fc312.lock.txt"
    requirementsLockSha256 = (Get-FileHash -LiteralPath $requirementsLock -Algorithm SHA256).Hash.ToLowerInvariant()
    deploymentProof = "deploy/alibaba/serverless-devs-runtime.yaml"
    entrypoint = "/bin/bash /code/bootstrap"
    frontendIncluded = $true
    frontendPath = "frontend/dist/frontend/browser"
    frontendFileCount = $frontendFileCount
}
Set-Content -Path (Join-Path $outputPath "dream-fc-package.json") -Value ($manifest | ConvertTo-Json -Depth 8) -Encoding UTF8

foreach ($requiredPackagePath in @(
    "fastapi/__init__.py",
    "uvicorn/__init__.py",
    "dream/api/app.py",
    "frontend/dist/frontend/browser/index.html",
    "docs/assets/qwen-memory-ab-benchmark-summary.json",
    "docs/qwen-memory-ab-benchmark.md",
    "docs/assets/qwen-experience-memory-benchmark-summary.json",
    "docs/assets/qwen-experience-memory-benchmark-report.json",
    "docs/qwen-experience-memory-benchmark.md",
    "deploy/alibaba/requirements-fc312.lock.txt",
    "deploy/alibaba/serverless-devs-runtime.yaml",
    "bootstrap",
    "dream-fc-package.json"
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $outputPath $requiredPackagePath) -PathType Leaf)) {
        throw "FC package validation failed; missing $requiredPackagePath"
    }
}
if (-not (Get-ChildItem -LiteralPath (Join-Path $outputPath "pydantic_core") -Filter "_pydantic_core*.so" -File)) {
    throw "FC package validation failed; Linux pydantic-core extension is missing."
}

Write-Host "Function Compute code package ready: $outputPath"
