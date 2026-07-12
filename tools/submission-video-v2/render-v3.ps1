# SPDX-License-Identifier: Apache-2.0

param(
    [string]$Python = "C:\Users\wangz\AppData\Local\Programs\Python\Python313\python.exe",
    [string]$EnvFile = "",
    [string]$BaseUrl = "https://dream-a-runtime-mdvperjjet.ap-southeast-1.fcapp.run",
    [string]$Output = "..\..\artifacts\qwencloud-proof\video-v3\dream-v3-full-candidate.mp4",
    [switch]$SkipNarration,
    [switch]$SkipCapture,
    [switch]$SkipRender
)

$ErrorActionPreference = "Stop"
$projectDir = $PSScriptRoot
$repoDir = [IO.Path]::GetFullPath((Join-Path $projectDir "..\.."))
$generatedDir = Join-Path $projectDir "public\generated"
$v3GeneratedDir = Join-Path $generatedDir "v3"
$outDir = Join-Path $projectDir "out"
$resolvedOutput = if ([IO.Path]::IsPathRooted($Output)) {
    [IO.Path]::GetFullPath($Output)
}
else {
    [IO.Path]::GetFullPath((Join-Path $projectDir $Output))
}
$finalDir = Split-Path -Parent $resolvedOutput

if ([string]::IsNullOrWhiteSpace($EnvFile)) {
    $siblingEnv = Join-Path (Split-Path -Parent $repoDir) "DREAM new\.env.qwencloud.local"
    if (Test-Path -LiteralPath $siblingEnv) { $EnvFile = $siblingEnv }
}

New-Item -ItemType Directory -Force $generatedDir, $v3GeneratedDir, $outDir, $finalDir | Out-Null
Copy-Item -LiteralPath (Join-Path $repoDir "docs\assets\qwencloud-architecture.png") `
    -Destination (Join-Path $v3GeneratedDir "qwencloud-architecture.png") -Force

Push-Location $projectDir
try {
    if (-not $SkipCapture) {
        node scripts\capture-demo.mjs $BaseUrl
        if ($LASTEXITCODE -ne 0) { throw "Fresh public demo capture failed." }
    }

    if (-not $SkipNarration) {
        $narrationArgs = @("scripts\generate-v3-narration.py", "--force")
        if (-not [string]::IsNullOrWhiteSpace($EnvFile)) {
            $narrationArgs += @("--env-file", $EnvFile)
        }
        & $Python @narrationArgs
        if ($LASTEXITCODE -ne 0) { throw "V3 Qwen narration generation failed." }
    }

    node scripts\validate-v3.mjs
    if ($LASTEXITCODE -ne 0) { throw "V3 generated-asset validation failed." }

    if (-not $SkipRender) {
        npm run render:v3
        if ($LASTEXITCODE -ne 0) { throw "V3 Remotion render failed." }
    }

    $raw = Join-Path $outDir "dream-v3-full-raw.mp4"
    if (-not (Test-Path -LiteralPath $raw)) { throw "Raw V3 render is missing: $raw" }

    $previousErrorPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $measurement = (& ffmpeg -hide_banner -i $raw `
        -af "loudnorm=I=-14:TP=-1.5:LRA=7:print_format=json" `
        -f null NUL 2>&1) -join "`n"
    $measurementExitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorPreference
    if ($measurementExitCode -ne 0) { throw "V3 loudness measurement failed." }
    $measurementMatch = [regex]::Match($measurement, '\{\s*"input_i"[\s\S]*?\}')
    if (-not $measurementMatch.Success) { throw "Could not measure V3 loudness." }
    $loudness = $measurementMatch.Value | ConvertFrom-Json
    $loudnessFilter = "loudnorm=I=-14:TP=-1.5:LRA=7:" +
        "measured_I=$($loudness.input_i):measured_TP=$($loudness.input_tp):" +
        "measured_LRA=$($loudness.input_lra):measured_thresh=$($loudness.input_thresh):" +
        "offset=$($loudness.target_offset):linear=true:print_format=summary,aresample=48000"
    & ffmpeg -hide_banner -loglevel error -y -i $raw `
        -af $loudnessFilter `
        -c:v copy -c:a aac -b:a 192k -movflags +faststart $resolvedOutput
    if ($LASTEXITCODE -ne 0) { throw "V3 candidate mastering failed." }

    $validationPath = Join-Path $finalDir "dream-v3-full-candidate-validation.json"
    $validation = node scripts\validate-v3.mjs $resolvedOutput
    if ($LASTEXITCODE -ne 0) { throw "V3 final-candidate validation failed." }
    $validation | Set-Content -LiteralPath $validationPath -Encoding utf8

    $contactSheet = Join-Path $finalDir "dream-v3-full-candidate-contact-sheet.png"
    & ffmpeg -hide_banner -loglevel error -y -i $resolvedOutput `
        -vf "fps=1/10,scale=360:-1,tile=5x3:padding=8:margin=8:color=white" `
        -frames:v 1 $contactSheet
    if ($LASTEXITCODE -ne 0) { throw "V3 contact sheet generation failed." }

    $qaDir = Join-Path $finalDir "qa-frames"
    New-Item -ItemType Directory -Force $qaDir | Out-Null
    foreach ($second in @(5, 20, 29, 38, 49, 61, 76, 91, 106, 122, 138, 148)) {
        $framePath = Join-Path $qaDir ("frame-{0:D3}.png" -f $second)
        & ffmpeg -hide_banner -loglevel error -y -ss $second -i $resolvedOutput -frames:v 1 $framePath
        if ($LASTEXITCODE -ne 0) { throw "V3 QA frame extraction failed at $second seconds." }
    }

    Copy-Item -LiteralPath (Join-Path $generatedDir "capture-manifest.json") `
        -Destination (Join-Path $finalDir "capture-manifest.json") -Force
    Copy-Item -LiteralPath (Join-Path $v3GeneratedDir "narration-manifest.json") `
        -Destination (Join-Path $finalDir "narration-manifest.json") -Force

    Write-Host "V3 candidate: $resolvedOutput"
    Write-Host "Validation: $validationPath"
    Write-Host "Contact sheet: $contactSheet"
}
finally {
    Pop-Location
}
