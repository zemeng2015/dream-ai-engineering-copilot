# SPDX-License-Identifier: Apache-2.0

param(
    [Parameter(Mandatory = $false)]
    [string]$EnvFile = "",
    [Parameter(Mandatory = $false)]
    [string]$BaseUrl = "https://dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run",
    [Parameter(Mandatory = $false)]
    [string]$OutputVideo = "artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4",
    [switch]$SkipNarration,
    [switch]$SkipCapture,
    [switch]$SkipRender
)

$ErrorActionPreference = "Stop"
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$renderer = Join-Path $repoRoot "tools\submission-video-v2\render-v3.ps1"
if (-not (Test-Path -LiteralPath $renderer)) {
    throw "V3 Remotion renderer was not found: $renderer"
}

$resolvedOutput = if ([IO.Path]::IsPathRooted($OutputVideo)) {
    [IO.Path]::GetFullPath($OutputVideo)
}
else {
    [IO.Path]::GetFullPath((Join-Path $repoRoot $OutputVideo))
}

& $renderer `
    -EnvFile $EnvFile `
    -BaseUrl $BaseUrl `
    -Output $resolvedOutput `
    -SkipNarration:$SkipNarration `
    -SkipCapture:$SkipCapture `
    -SkipRender:$SkipRender
if ($LASTEXITCODE -ne 0) {
    throw "DREAM V3 demo-video rendering failed."
}

Write-Host "Canonical demo video: $resolvedOutput"
