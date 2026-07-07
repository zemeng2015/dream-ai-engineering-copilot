param(
    [Parameter(Mandatory = $false)]
    [string]$InputVideo = "docs/frontend-runbook/regression-20260703-memory-ui/dream-ui-demo.mp4",
    [Parameter(Mandatory = $false)]
    [string]$OutputVideo = "artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4",
    [Parameter(Mandatory = $false)]
    [string]$WorkDir = "artifacts/qwencloud-proof/video-render"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    throw "ffmpeg is required to render the final Devpost demo video."
}

if (-not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    throw "ffprobe is required to verify the final Devpost demo video."
}

if (-not (Test-Path $InputVideo)) {
    throw "Input video was not found: $InputVideo"
}

New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null
$intro = Join-Path $WorkDir "intro.mp4"
$main = Join-Path $WorkDir "main-captioned.mp4"
$outro = Join-Path $WorkDir "outro.mp4"
$concatFile = Join-Path $WorkDir "concat.txt"
$introAss = Join-Path $WorkDir "intro.ass"
$mainAss = Join-Path $WorkDir "main.ass"
$outroAss = Join-Path $WorkDir "outro.ass"

function Write-AssFile([string]$Path, [string[]]$Dialogues) {
    $header = @(
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1280",
        "PlayResY: 720",
        "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
        "Style: Title,Arial,42,&H00F5F9FC,&H000000FF,&H0002384B,&HE602384B,-1,0,0,0,100,100,0,0,3,2,0,5,48,48,48,1",
        "Style: Body,Arial,25,&H00F5F9FC,&H000000FF,&H0002384B,&HE602384B,0,0,0,0,100,100,0,0,3,2,0,5,54,54,54,1",
        "Style: Caption,Arial,24,&H00FFFFFF,&H000000FF,&H0002384B,&HE602384B,0,0,0,0,100,100,0,0,3,2,0,2,72,72,48,1",
        "",
        "[Events]",
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text"
    )
    Set-Content -Path $Path -Value (($header + $Dialogues) -join "`r`n") -Encoding UTF8
}

Write-AssFile -Path $introAss -Dialogues @(
    "Dialogue: 0,0:00:00.00,0:00:07.00,Title,,0,0,0,,{\pos(640,245)}DREAM Qwen Cloud MemoryAgent",
    "Dialogue: 0,0:00:00.00,0:00:07.00,Body,,0,0,0,,{\pos(640,315)}Track 1 source-backed memory for engineering teams",
    "Dialogue: 0,0:00:00.00,0:00:07.00,Body,,0,0,0,,{\pos(640,360)}Qwen Cloud generation plus governed retrieval, audit, and human review"
)

Write-AssFile -Path $mainAss -Dialogues @(
    "Dialogue: 0,0:00:00.00,0:00:06.00,Caption,,0,0,0,,DREAM turns scattered engineering context into persistent memory",
    "Dialogue: 0,0:00:06.00,0:00:13.00,Caption,,0,0,0,,Memory Hub keeps source intake, parsed sections, review state, and evidence visible",
    "Dialogue: 0,0:00:13.00,0:00:21.00,Caption,,0,0,0,,Knowledge intake promotes only reviewed source cards into reusable memory",
    "Dialogue: 0,0:00:21.00,0:00:30.00,Caption,,0,0,0,,Retrieval paths explain why docs, incidents, code, tests, Jira, and PRs were selected",
    "Dialogue: 0,0:00:30.00,0:00:39.00,Caption,,0,0,0,,Requirement workflows turn retrieved memory into review-ready Jira drafts",
    "Dialogue: 0,0:00:39.00,0:00:49.00,Caption,,0,0,0,,Runtime settings expose backend mode before local or Alibaba Cloud execution"
)

Write-AssFile -Path $outroAss -Dialogues @(
    "Dialogue: 0,0:00:00.00,0:00:09.00,Title,,0,0,0,,{\pos(640,210)}Submission proof",
    "Dialogue: 0,0:00:00.00,0:00:09.00,Body,,0,0,0,,{\pos(640,290)}Repo  github.com/zemeng2015/dream-ai-engineering-copilot",
    "Dialogue: 0,0:00:00.00,0:00:09.00,Body,,0,0,0,,{\pos(640,335)}Track  Track 1 MemoryAgent",
    "Dialogue: 0,0:00:00.00,0:00:09.00,Body,,0,0,0,,{\pos(640,380)}Qwen config  examples/config/dream.qwen.yaml",
    "Dialogue: 0,0:00:00.00,0:00:09.00,Body,,0,0,0,,{\pos(640,425)}Architecture  docs/assets/qwencloud-architecture.svg",
    "Dialogue: 0,0:00:00.00,0:00:09.00,Body,,0,0,0,,{\pos(640,470)}Alibaba proof  deploy/alibaba/serverless-devs.yaml"
)

$introAssPath = $introAss.Replace("\", "/")
$mainAssPath = $mainAss.Replace("\", "/")
$outroAssPath = $outroAss.Replace("\", "/")

& ffmpeg -hide_banner -loglevel error -y -f lavfi -i "color=c=0x062b3a:s=1280x720:d=7:r=24" -vf "subtitles='$introAssPath'" -c:v libx264 -pix_fmt yuv420p -an $intro
if ($LASTEXITCODE -ne 0) { throw "Failed to render intro segment." }

& ffmpeg -hide_banner -loglevel error -y -i $InputVideo -vf "subtitles='$mainAssPath'" -r 24 -c:v libx264 -pix_fmt yuv420p -an $main
if ($LASTEXITCODE -ne 0) { throw "Failed to render captioned main segment." }

& ffmpeg -hide_banner -loglevel error -y -f lavfi -i "color=c=0x062b3a:s=1280x720:d=9:r=24" -vf "subtitles='$outroAssPath'" -c:v libx264 -pix_fmt yuv420p -an $outro
if ($LASTEXITCODE -ne 0) { throw "Failed to render outro segment." }

$concatLines = @(
    "file 'intro.mp4'",
    "file 'main-captioned.mp4'",
    "file 'outro.mp4'"
)
Set-Content -Path $concatFile -Value ($concatLines -join "`n") -Encoding ASCII

& ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i $concatFile -c copy -movflags +faststart $OutputVideo
if ($LASTEXITCODE -ne 0) { throw "Failed to concatenate final video." }

$probeJson = & ffprobe -v error -show_entries format=duration,size -of json $OutputVideo
$probe = $probeJson | ConvertFrom-Json
if ([double]$probe.format.duration -ge 180) {
    throw "Final demo video must stay under 180 seconds. Duration: $($probe.format.duration)"
}

Write-Host "Final Devpost demo video rendered: $OutputVideo"
Write-Host $probeJson
