# SPDX-License-Identifier: Apache-2.0

param(
    [Parameter(Mandatory = $false)]
    [string]$ArenaInitialPath = "docs/assets/qwencloud-arena-initial.png",
    [Parameter(Mandatory = $false)]
    [string]$ArenaSuccessTopPath = "docs/assets/qwencloud-arena-success-top.png",
    [Parameter(Mandatory = $false)]
    [string]$ArenaSuccessDetailPath = "docs/assets/qwencloud-arena-success-detail.png",
    [Parameter(Mandatory = $false)]
    [string]$ArenaBenchmarkPath = "docs/assets/qwencloud-arena-benchmark.png",
    [Parameter(Mandatory = $false)]
    [string]$ArchitecturePath = "docs/assets/qwencloud-architecture.png",
    [Parameter(Mandatory = $false)]
    [string]$AlibabaScreenshotPath = "artifacts/qwencloud-proof/alibaba-deployment-screenshot.png",
    [Parameter(Mandatory = $false)]
    [string]$OutputVideo = "artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4",
    [Parameter(Mandatory = $false)]
    [string]$WorkDir = "artifacts/qwencloud-proof/video-render",
    [Parameter(Mandatory = $false)]
    [string]$ReportDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [string]$NarrationCaptionPath = "docs/qwencloud-demo-video-captions.srt",
    [Parameter(Mandatory = $false)]
    [string]$NarrationVoice = "Microsoft Zira Desktop",
    [switch]$SkipNarration
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$memoryHubPath = "docs/frontend-runbook/regression-20260703-memory-ui/screenshots/02-memory-management.png"
$retrievalTracePath = "docs/frontend-runbook/regression-20260703-memory-ui/screenshots/07-retrieval-trace.png"
$jiraDraftPath = "docs/frontend-runbook/regression-20260703-memory-ui/screenshots/10-jira-draft.png"

function Get-FileSha256([string]$Path) {
    if (-not (Test-Path $Path)) { return "" }
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Get-AssetRecord([string]$Name, [string]$Path) {
    return [ordered]@{
        name = $Name
        path = $Path
        exists = Test-Path $Path
        sha256 = Get-FileSha256 -Path $Path
    }
}

function Convert-SrtTimeToMilliseconds([string]$Value) {
    $normalized = $Value.Trim().Replace(",", ".")
    $time = [TimeSpan]::ParseExact(
        $normalized,
        "hh\:mm\:ss\.fff",
        [System.Globalization.CultureInfo]::InvariantCulture
    )
    return [int][Math]::Round($time.TotalMilliseconds)
}

function Get-NarrationCues([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Narration caption file was not found: $Path"
    }

    $cues = @()
    $blocks = (Get-Content -LiteralPath $Path -Raw) -split "\r?\n\r?\n"
    foreach ($block in $blocks) {
        $lines = @($block -split "\r?\n")
        if ($lines.Count -lt 3) { continue }
        if ($lines[1] -notmatch "^(?<start>\d{2}:\d{2}:\d{2},\d{3})\s+-->\s+(?<end>\d{2}:\d{2}:\d{2},\d{3})$") {
            continue
        }
        $text = (($lines[2..($lines.Count - 1)] -join " ") -replace "\s+", " ").Trim()
        if ([string]::IsNullOrWhiteSpace($text)) { continue }
        $cues += [pscustomobject]@{
            startMs = Convert-SrtTimeToMilliseconds -Value $matches.start
            endMs = Convert-SrtTimeToMilliseconds -Value $matches.end
            text = $text
        }
    }
    return $cues
}

function Add-TtsNarration {
    param(
        [Parameter(Mandatory = $true)][string]$InputPath,
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [Parameter(Mandatory = $true)][double]$Duration,
        [Parameter(Mandatory = $true)][string]$CaptionPath,
        [Parameter(Mandatory = $true)][string]$VoiceName
    )

    Add-Type -AssemblyName System.Speech
    $cues = @(Get-NarrationCues -Path $CaptionPath)
    if ($cues.Count -eq 0) {
        throw "No narration cues were parsed from $CaptionPath"
    }

    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $clipPaths = @()
    $voiceUsed = $synth.Voice.Name
    try {
        $installedVoices = @($synth.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name })
        if ($installedVoices -contains $VoiceName) {
            $synth.SelectVoice($VoiceName)
            $voiceUsed = $VoiceName
        }
        $synth.Rate = 1
        $synth.Volume = 100
        for ($index = 0; $index -lt $cues.Count; $index++) {
            $clipPath = Join-Path $WorkDir ("narration-{0:D2}.wav" -f ($index + 1))
            $synth.SetOutputToWaveFile($clipPath)
            $synth.Speak($cues[$index].text)
            $synth.SetOutputToNull()
            $clipPaths += $clipPath
        }
    }
    finally {
        $synth.Dispose()
    }

    $ffmpegArgs = @("-hide_banner", "-loglevel", "error", "-y", "-i", $InputPath)
    foreach ($clipPath in $clipPaths) {
        $ffmpegArgs += @("-i", $clipPath)
    }

    $filters = @()
    $mixInputs = ""
    for ($index = 0; $index -lt $clipPaths.Count; $index++) {
        $inputIndex = $index + 1
        $label = "voice$index"
        $delay = $cues[$index].startMs
        $filters += "[$($inputIndex):a]adelay=$delay|$delay,volume=1.0[$label]"
        $mixInputs += "[$label]"
    }
    $filters += "$mixInputs" + "amix=inputs=$($clipPaths.Count):duration=longest:normalize=0,apad[aout]"
    $ffmpegArgs += @(
        "-filter_complex", ($filters -join ";"),
        "-map", "0:v:0",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-t", ([string]$Duration),
        "-movflags", "+faststart",
        $OutputPath
    )
    & ffmpeg @ffmpegArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to add TTS narration to $OutputPath"
    }

    return [pscustomobject]@{
        generated = $true
        cueCount = $cues.Count
        voice = $voiceUsed
        issue = ""
    }
}

function Write-AssFile([string]$Path, [string[]]$Dialogues) {
    $header = @(
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1280",
        "PlayResY: 720",
        "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
        "Style: Title,Arial,44,&H00F5F9FC,&H000000FF,&H0002384B,&HE602384B,-1,0,0,0,100,100,0,0,3,2,0,5,48,48,48,1",
        "Style: Body,Arial,27,&H00F5F9FC,&H000000FF,&H0002384B,&HE602384B,0,0,0,0,100,100,0,0,3,2,0,5,54,54,54,1",
        "Style: TopBar,Arial,28,&H00FFFFFF,&H000000FF,&H000B2538,&HE60B2538,-1,0,0,0,100,100,0,0,3,2,0,8,44,44,34,1",
        "Style: LowerThird,Arial,26,&H00FFFFFF,&H000000FF,&H0002384B,&HE602384B,-1,0,0,0,100,100,0,0,3,2,0,2,50,50,38,1",
        "",
        "[Events]",
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text"
    )
    Set-Content -Path $Path -Value (($header + $Dialogues) -join "`r`n") -Encoding UTF8
}

function Render-ColorSegment([string]$OutputPath, [double]$Duration, [string]$AssPath) {
    $assFilterPath = $AssPath.Replace("\", "/")
    & ffmpeg -hide_banner -loglevel error -y -f lavfi -i "color=c=0x062b3a:s=1280x720:d=${Duration}:r=24" -vf "subtitles='$assFilterPath'" -c:v libx264 -pix_fmt yuv420p -an $OutputPath
    if ($LASTEXITCODE -ne 0) { throw "Failed to render color segment: $OutputPath" }
}

function Render-ImageSegment {
    param(
        [Parameter(Mandatory = $true)][string]$InputPath,
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [Parameter(Mandatory = $true)][double]$Duration,
        [Parameter(Mandatory = $true)][string]$AssPath,
        [string]$Crop = ""
    )
    $assFilterPath = $AssPath.Replace("\", "/")
    $filters = @()
    if (-not [string]::IsNullOrWhiteSpace($Crop)) { $filters += $Crop }
    $filters += "scale=1280:720:force_original_aspect_ratio=decrease"
    $filters += "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=0x062b3a"
    $filters += "subtitles='$assFilterPath'"
    & ffmpeg -hide_banner -loglevel error -y -loop 1 -t $Duration -i $InputPath -vf ($filters -join ",") -r 24 -c:v libx264 -pix_fmt yuv420p -an $OutputPath
    if ($LASTEXITCODE -ne 0) { throw "Failed to render image segment: $OutputPath" }
}

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    throw "ffmpeg is required to render the final Devpost demo video."
}
if (-not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    throw "ffprobe is required to verify the final Devpost demo video."
}

$sourceAssets = @(
    Get-AssetRecord -Name "arena_initial" -Path $ArenaInitialPath
    Get-AssetRecord -Name "arena_success_top" -Path $ArenaSuccessTopPath
    Get-AssetRecord -Name "arena_success_detail" -Path $ArenaSuccessDetailPath
    Get-AssetRecord -Name "arena_benchmark" -Path $ArenaBenchmarkPath
    Get-AssetRecord -Name "architecture_diagram" -Path $ArchitecturePath
    Get-AssetRecord -Name "memory_hub" -Path $memoryHubPath
    Get-AssetRecord -Name "retrieval_trace" -Path $retrievalTracePath
    Get-AssetRecord -Name "jira_draft" -Path $jiraDraftPath
    Get-AssetRecord -Name "alibaba_deployment_screenshot" -Path $AlibabaScreenshotPath
    Get-AssetRecord -Name "narration_captions" -Path $NarrationCaptionPath
)
$missingAssets = @($sourceAssets | Where-Object { -not $_.exists })
if ($missingAssets.Count -gt 0) {
    throw "Required demo video assets are missing: $(@($missingAssets | ForEach-Object { $_.path }) -join ', ')"
}

New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null
New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null

$segments = @(
    [ordered]@{ name = "intro"; duration = 7; kind = "color"; asset = ""; crop = ""; dialogues = @(
        "Dialogue: 0,0:00:00.00,0:00:07.00,Title,,0,0,0,,{\pos(640,215)}DREAM Qwen Cloud MemoryAgent",
        "Dialogue: 0,0:00:00.00,0:00:07.00,Body,,0,0,0,,{\pos(640,300)}Most agents forget. Stale guidance survives. Context budgets overflow.",
        "Dialogue: 0,0:00:00.00,0:00:07.00,Body,,0,0,0,,{\pos(640,370)}DREAM keeps one governed truth across sessions.",
        "Dialogue: 0,0:00:00.00,0:00:07.00,Body,,0,0,0,,{\pos(640,455)}Track 1 MemoryAgent | Qwen Cloud | Alibaba Function Compute"
    ) }
    [ordered]@{ name = "architecture"; duration = 9; kind = "image"; asset = $ArchitecturePath; crop = ""; dialogues = @() }
    [ordered]@{ name = "arena-initial"; duration = 10; kind = "image"; asset = $ArenaInitialPath; crop = ""; dialogues = @(
        "Dialogue: 0,0:00:00.00,0:00:10.00,TopBar,,0,0,0,,Session 1 | Qwen recognizes a durable preference and returns remember"
    ) }
    [ordered]@{ name = "arena-supersede"; duration = 12; kind = "image"; asset = $ArenaSuccessTopPath; crop = ""; dialogues = @(
        "Dialogue: 0,0:00:00.00,0:00:12.00,TopBar,,0,0,0,,Session 2 | Qwen returns supersede and DREAM retires the stale truth"
    ) }
    [ordered]@{ name = "arena-budget"; duration = 10; kind = "image"; asset = $ArenaSuccessDetailPath; crop = ""; dialogues = @(
        "Dialogue: 0,0:00:00.00,0:00:10.00,LowerThird,,0,0,0,,Session 3 | No prompt history | hard recall budget: 64 tokens"
    ) }
    [ordered]@{ name = "arena-recall"; duration = 11; kind = "image"; asset = $ArenaSuccessDetailPath; crop = "crop=430:565:835:65"; dialogues = @(
        "Dialogue: 0,0:00:00.00,0:00:11.00,TopBar,,0,0,0,,Current truth recalled in 19 / 64 tokens",
        "Dialogue: 0,0:00:00.00,0:00:11.00,LowerThird,,0,0,0,,20% canary for 45 minutes | old value leaked: no"
    ) }
    [ordered]@{ name = "feedback"; duration = 7; kind = "image"; asset = $ArenaSuccessDetailPath; crop = "crop=430:565:835:65"; dialogues = @(
        "Dialogue: 0,0:00:00.00,0:00:07.00,TopBar,,0,0,0,,Helpful + correct feedback returns to future ranking"
    ) }
    [ordered]@{ name = "benchmark"; duration = 18; kind = "image"; asset = $ArenaBenchmarkPath; crop = ""; dialogues = @(
        "Dialogue: 0,0:00:00.00,0:00:18.00,TopBar,,0,0,0,,37 real Qwen decisions across 24 lifecycle cases"
    ) }
    [ordered]@{ name = "benchmark-proof"; duration = 16; kind = "color"; asset = ""; crop = ""; dialogues = @(
        "Dialogue: 0,0:00:00.00,0:00:16.00,Title,,0,0,0,,{\pos(640,155)}Reproducible lifecycle proof",
        "Dialogue: 0,0:00:00.00,0:00:16.00,Body,,0,0,0,,{\pos(360,270)}24 / 24 cases passed",
        "Dialogue: 0,0:00:00.00,0:00:16.00,Body,,0,0,0,,{\pos(920,270)}100% critical recall",
        "Dialogue: 0,0:00:00.00,0:00:16.00,Body,,0,0,0,,{\pos(360,365)}0% forbidden leak",
        "Dialogue: 0,0:00:00.00,0:00:16.00,Body,,0,0,0,,{\pos(920,365)}100% budget compliance",
        "Dialogue: 0,0:00:00.00,0:00:16.00,Body,,0,0,0,,{\pos(640,485)}Conflict | TTL | explicit forgetting | duplicates | limited context"
    ) }
    [ordered]@{ name = "memory-hub"; duration = 8; kind = "image"; asset = $memoryHubPath; crop = ""; dialogues = @(
        "Dialogue: 0,0:00:00.00,0:00:08.00,TopBar,,0,0,0,,Organizational claims retain source proof and human approval"
    ) }
    [ordered]@{ name = "retrieval-trace"; duration = 8; kind = "image"; asset = $retrievalTracePath; crop = ""; dialogues = @(
        "Dialogue: 0,0:00:00.00,0:00:08.00,TopBar,,0,0,0,,Unresolved conflicts are blocked before retrieval"
    ) }
    [ordered]@{ name = "jira-draft"; duration = 12; kind = "image"; asset = $jiraDraftPath; crop = ""; dialogues = @(
        "Dialogue: 0,0:00:00.00,0:00:12.00,TopBar,,0,0,0,,Approved truth enters requirements, impact maps, briefs, and Jira drafts",
        "Dialogue: 0,0:00:00.00,0:00:12.00,LowerThird,,0,0,0,,Reviewer and source provenance stay attached"
    ) }
    [ordered]@{ name = "alibaba-proof"; duration = 12; kind = "image"; asset = $AlibabaScreenshotPath; crop = ""; dialogues = @(
        "Dialogue: 0,0:00:00.00,0:00:12.00,TopBar,,0,0,0,,Alibaba Function Compute | Singapore | qwen3.7-plus",
        "Dialogue: 0,0:00:00.00,0:00:12.00,LowerThird,,0,0,0,,Public runtime verification: all checks passed"
    ) }
    [ordered]@{ name = "repo-proof"; duration = 9; kind = "color"; asset = ""; crop = ""; dialogues = @(
        "Dialogue: 0,0:00:00.00,0:00:09.00,Title,,0,0,0,,{\pos(640,170)}Everything is reproducible",
        "Dialogue: 0,0:00:00.00,0:00:09.00,Body,,0,0,0,,{\pos(640,275)}Benchmark summary + full report + test suite",
        "Dialogue: 0,0:00:00.00,0:00:09.00,Body,,0,0,0,,{\pos(640,335)}Alibaba deployment template + proof capture",
        "Dialogue: 0,0:00:00.00,0:00:09.00,Body,,0,0,0,,{\pos(640,420)}github.com/zemeng2015/dream-ai-engineering-copilot",
        "Dialogue: 0,0:00:00.00,0:00:09.00,Body,,0,0,0,,{\pos(640,475)}branch: codex/champion-memory-loop"
    ) }
    [ordered]@{ name = "outro"; duration = 11; kind = "color"; asset = ""; crop = ""; dialogues = @(
        "Dialogue: 0,0:00:00.00,0:00:11.00,Title,,0,0,0,,{\pos(640,175)}DREAM remembers the right experience",
        "Dialogue: 0,0:00:00.00,0:00:11.00,Body,,0,0,0,,{\pos(640,280)}Replace old truth",
        "Dialogue: 0,0:00:00.00,0:00:11.00,Body,,0,0,0,,{\pos(640,335)}Forget safely",
        "Dialogue: 0,0:00:00.00,0:00:11.00,Body,,0,0,0,,{\pos(640,390)}Recall under a hard budget",
        "Dialogue: 0,0:00:00.00,0:00:11.00,Body,,0,0,0,,{\pos(640,445)}Explain every selected memory",
        "Dialogue: 0,0:00:00.00,0:00:11.00,Body,,0,0,0,,{\pos(640,525)}Qwen Cloud Track 1 MemoryAgent"
    ) }
)

$concatLines = @()
foreach ($segment in $segments) {
    $assPath = Join-Path $WorkDir "$($segment.name).ass"
    $videoPath = Join-Path $WorkDir "$($segment.name).mp4"
    Write-AssFile -Path $assPath -Dialogues $segment.dialogues
    if ($segment.kind -eq "color") {
        Render-ColorSegment -OutputPath $videoPath -Duration $segment.duration -AssPath $assPath
    }
    else {
        Render-ImageSegment -InputPath $segment.asset -OutputPath $videoPath -Duration $segment.duration -AssPath $assPath -Crop $segment.crop
    }
    $concatLines += "file '$($segment.name).mp4'"
}

$concatFile = Join-Path $WorkDir "concat.txt"
$silentOutput = Join-Path $WorkDir "final-silent.mp4"
Set-Content -Path $concatFile -Value ($concatLines -join "`n") -Encoding ASCII
& ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i $concatFile -c copy -movflags +faststart $silentOutput
if ($LASTEXITCODE -ne 0) { throw "Failed to concatenate final video." }

$silentProbeJson = & ffprobe -v error -show_entries format=duration -of json $silentOutput
$silentProbe = $silentProbeJson | ConvertFrom-Json
$narration = [pscustomobject]@{
    generated = $false
    cueCount = 0
    voice = ""
    issue = if ($SkipNarration) { "skipped by -SkipNarration" } else { "" }
}
if ($SkipNarration) {
    Copy-Item -LiteralPath $silentOutput -Destination $OutputVideo -Force
}
else {
    try {
        $narration = Add-TtsNarration `
            -InputPath $silentOutput `
            -OutputPath $OutputVideo `
            -Duration ([double]$silentProbe.format.duration) `
            -CaptionPath $NarrationCaptionPath `
            -VoiceName $NarrationVoice
    }
    catch {
        $narration = [pscustomobject]@{
            generated = $false
            cueCount = 0
            voice = ""
            issue = $_.Exception.Message
        }
        Write-Warning "Narration unavailable; keeping the captioned silent video. $($narration.issue)"
        Copy-Item -LiteralPath $silentOutput -Destination $OutputVideo -Force
    }
}

$probeJson = & ffprobe -v error -show_entries format=duration,size,format_name -show_streams -of json $OutputVideo
$probe = $probeJson | ConvertFrom-Json
if ([double]$probe.format.duration -ge 180) {
    throw "Final demo video must stay under 180 seconds. Duration: $($probe.format.duration)"
}

$videoStream = @($probe.streams | Where-Object { $_.codec_type -eq "video" } | Select-Object -First 1)
$audioStream = @($probe.streams | Where-Object { $_.codec_type -eq "audio" } | Select-Object -First 1)
$reportJson = Join-Path $ReportDir "demo-video-render-$timestamp.json"
$reportMd = Join-Path $ReportDir "demo-video-render-$timestamp.md"
$outputHash = Get-FileSha256 -Path $OutputVideo
$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    outputVideo = $OutputVideo
    outputSha256 = $outputHash
    durationSeconds = [double]$probe.format.duration
    sizeBytes = [int64]$probe.format.size
    format = [string]$probe.format.format_name
    width = if ($videoStream) { [int]$videoStream.width } else { 0 }
    height = if ($videoStream) { [int]$videoStream.height } else { 0 }
    codec = if ($videoStream) { [string]$videoStream.codec_name } else { "" }
    audioCodec = if ($audioStream) { [string]$audioStream.codec_name } else { "" }
    narrationGenerated = [bool]$narration.generated
    narrationCueCount = [int]$narration.cueCount
    narrationVoice = [string]$narration.voice
    narrationIssue = [string]$narration.issue
    underDevpostLimit = ([double]$probe.format.duration -lt 180)
    sourceAssets = $sourceAssets
    segmentCount = $segments.Count
    reportJson = $reportJson
    reportMarkdown = $reportMd
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Demo Video Render ($timestamp)",
    "",
    "- Output video: ``$OutputVideo``",
    "- SHA256: ``$outputHash``",
    "- Duration: $($result.durationSeconds) seconds",
    "- Resolution: $($result.width)x$($result.height)",
    "- Codec: $($result.codec)",
    "- Audio codec: $(if ($result.audioCodec) { $result.audioCodec } else { '<none>' })",
    "- TTS narration: $(if ($result.narrationGenerated) { 'yes' } else { 'no' })",
    "- Narration cues: $($result.narrationCueCount)",
    "- Narration voice: $(if ($result.narrationVoice) { $result.narrationVoice } else { '<none>' })",
    "- Narration issue: $(if ($result.narrationIssue) { $result.narrationIssue } else { '<none>' })",
    "- Devpost limit: $(if ($result.underDevpostLimit) { 'PASS (< 180 seconds)' } else { 'FAIL' })",
    "",
    "## Source Assets",
    "",
    "| Asset | Exists | SHA256 | Path |",
    "|---|---:|---|---|"
)
foreach ($asset in $sourceAssets) {
    $lines += "| $($asset.name) | $(if ($asset.exists) { 'yes' } else { 'no' }) | $($asset.sha256) | $($asset.path) |"
}
Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

Write-Host "Final Devpost demo video rendered: $OutputVideo"
Write-Host $probeJson
Write-Host "Render report: $reportMd"
