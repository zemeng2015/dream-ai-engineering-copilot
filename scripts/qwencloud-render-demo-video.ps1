param(
    [Parameter(Mandatory = $false)]
    [string]$InputVideo = "docs/frontend-runbook/regression-20260703-memory-ui/dream-ui-demo.mp4",
    [Parameter(Mandatory = $false)]
    [string]$OutputVideo = "artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4",
    [Parameter(Mandatory = $false)]
    [string]$WorkDir = "artifacts/qwencloud-proof/video-render",
    [Parameter(Mandatory = $false)]
    [string]$ReportDir = "artifacts/qwencloud-proof"
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"

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
New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null
$intro = Join-Path $WorkDir "intro.mp4"
$problem = Join-Path $WorkDir "problem.mp4"
$architecture = Join-Path $WorkDir "architecture.mp4"
$memoryHub = Join-Path $WorkDir "memory-hub.mp4"
$knowledgeIntake = Join-Path $WorkDir "knowledge-intake.mp4"
$retrievalTrace = Join-Path $WorkDir "retrieval-trace.mp4"
$jiraDraft = Join-Path $WorkDir "jira-draft.mp4"
$evalAudit = Join-Path $WorkDir "eval-audit.mp4"
$main = Join-Path $WorkDir "main-captioned.mp4"
$proof = Join-Path $WorkDir "proof.mp4"
$outro = Join-Path $WorkDir "outro.mp4"
$concatFile = Join-Path $WorkDir "concat.txt"
$introAss = Join-Path $WorkDir "intro.ass"
$problemAss = Join-Path $WorkDir "problem.ass"
$architectureAss = Join-Path $WorkDir "architecture.ass"
$memoryHubAss = Join-Path $WorkDir "memory-hub.ass"
$knowledgeIntakeAss = Join-Path $WorkDir "knowledge-intake.ass"
$retrievalTraceAss = Join-Path $WorkDir "retrieval-trace.ass"
$jiraDraftAss = Join-Path $WorkDir "jira-draft.ass"
$evalAuditAss = Join-Path $WorkDir "eval-audit.ass"
$mainAss = Join-Path $WorkDir "main.ass"
$proofAss = Join-Path $WorkDir "proof.ass"
$outroAss = Join-Path $WorkDir "outro.ass"

$architecturePng = "docs/assets/qwencloud-architecture.png"
$screenshotsDir = "docs/frontend-runbook/regression-20260703-memory-ui/screenshots"
$memoryHubPng = Join-Path $screenshotsDir "02-memory-management.png"
$knowledgeIntakePng = Join-Path $screenshotsDir "04-knowledge-intake.png"
$retrievalTracePng = Join-Path $screenshotsDir "07-retrieval-trace.png"
$jiraDraftPng = Join-Path $screenshotsDir "10-jira-draft.png"
$evalAuditPng = Join-Path $screenshotsDir "13-eval-detail.png"

foreach ($asset in @($architecturePng, $memoryHubPng, $knowledgeIntakePng, $retrievalTracePng, $jiraDraftPng, $evalAuditPng)) {
    if (-not (Test-Path $asset)) {
        throw "Required demo video visual asset was not found: $asset"
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
        "Style: Title,Arial,42,&H00F5F9FC,&H000000FF,&H0002384B,&HE602384B,-1,0,0,0,100,100,0,0,3,2,0,5,48,48,48,1",
        "Style: Body,Arial,25,&H00F5F9FC,&H000000FF,&H0002384B,&HE602384B,0,0,0,0,100,100,0,0,3,2,0,5,54,54,54,1",
        "Style: Caption,Arial,24,&H00FFFFFF,&H000000FF,&H0002384B,&HE602384B,0,0,0,0,100,100,0,0,3,2,0,2,72,72,48,1",
        "Style: TopBar,Arial,27,&H00FFFFFF,&H000000FF,&H000B2538,&HE60B2538,-1,0,0,0,100,100,0,0,3,2,0,8,48,48,36,1",
        "Style: LowerThird,Arial,25,&H00FFFFFF,&H000000FF,&H0002384B,&HE602384B,-1,0,0,0,100,100,0,0,3,2,0,2,54,54,42,1",
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

function Render-ImageSegment([string]$InputPath, [string]$OutputPath, [double]$Duration, [string]$AssPath) {
    $assFilterPath = $AssPath.Replace("\", "/")
    & ffmpeg -hide_banner -loglevel error -y -loop 1 -t $Duration -i $InputPath -vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=0x062b3a,subtitles='$assFilterPath'" -r 24 -c:v libx264 -pix_fmt yuv420p -an $OutputPath
    if ($LASTEXITCODE -ne 0) { throw "Failed to render image segment: $OutputPath" }
}

Write-AssFile -Path $introAss -Dialogues @(
    "Dialogue: 0,0:00:00.00,0:00:08.00,Title,,0,0,0,,{\pos(640,230)}DREAM Qwen Cloud MemoryAgent",
    "Dialogue: 0,0:00:00.00,0:00:08.00,Body,,0,0,0,,{\pos(640,305)}Track 1 source-backed memory for engineering teams",
    "Dialogue: 0,0:00:00.00,0:00:08.00,Body,,0,0,0,,{\pos(640,350)}Qwen Cloud generation plus governed retrieval, audit, and human review",
    "Dialogue: 0,0:00:00.00,0:00:08.00,Body,,0,0,0,,{\pos(640,430)}Public repo, Alibaba packaging, final proof gates, and Devpost-ready evidence"
)

Write-AssFile -Path $problemAss -Dialogues @(
    "Dialogue: 0,0:00:00.00,0:00:12.00,Title,,0,0,0,,{\pos(640,180)}The problem",
    "Dialogue: 0,0:00:00.00,0:00:12.00,Body,,0,0,0,,{\pos(640,270)}AI engineering tools forget the evidence behind prior decisions.",
    "Dialogue: 0,0:00:00.00,0:00:12.00,Body,,0,0,0,,{\pos(640,320)}DREAM turns tickets, incidents, runbooks, code, PRs, and reviews into governed memory.",
    "Dialogue: 0,0:00:00.00,0:00:12.00,Body,,0,0,0,,{\pos(640,370)}Every generated output can point back to source-backed context."
)

Write-AssFile -Path $architectureAss -Dialogues @(
    "Dialogue: 0,0:00:00.00,0:00:14.00,TopBar,,0,0,0,,DREAM architecture: Qwen Cloud provider + governed memory + deployable API",
    "Dialogue: 0,0:00:00.00,0:00:14.00,LowerThird,,0,0,0,,Config selects qwen-cloud; FastAPI exposes proof; Alibaba Function Compute runs the custom container"
)

Write-AssFile -Path $memoryHubAss -Dialogues @(
    "Dialogue: 0,0:00:00.00,0:00:09.00,TopBar,,0,0,0,,Governed memory workspace",
    "Dialogue: 0,0:00:00.00,0:00:09.00,LowerThird,,0,0,0,,Teams can inspect source intake, memory status, evidence coverage, and review state before reusing context"
)

Write-AssFile -Path $knowledgeIntakeAss -Dialogues @(
    "Dialogue: 0,0:00:00.00,0:00:09.00,TopBar,,0,0,0,,Knowledge intake with review control",
    "Dialogue: 0,0:00:00.00,0:00:09.00,LowerThird,,0,0,0,,Raw docs become parsed source cards; stale or unreviewed claims can be quarantined instead of trusted blindly"
)

Write-AssFile -Path $retrievalTraceAss -Dialogues @(
    "Dialogue: 0,0:00:00.00,0:00:09.00,TopBar,,0,0,0,,Retrieval traces make Qwen outputs inspectable",
    "Dialogue: 0,0:00:00.00,0:00:09.00,LowerThird,,0,0,0,,Requirement context shows which docs, incidents, code, tests, Jira items, and PRs influenced the answer"
)

Write-AssFile -Path $jiraDraftAss -Dialogues @(
    "Dialogue: 0,0:00:00.00,0:00:09.00,TopBar,,0,0,0,,From memory to review-ready engineering work",
    "Dialogue: 0,0:00:00.00,0:00:09.00,LowerThird,,0,0,0,,DREAM turns retrieved evidence into questions, impact maps, engineering briefs, and Jira-ready drafts"
)

Write-AssFile -Path $evalAuditAss -Dialogues @(
    "Dialogue: 0,0:00:00.00,0:00:09.00,TopBar,,0,0,0,,Audit and evaluation loops",
    "Dialogue: 0,0:00:00.00,0:00:09.00,LowerThird,,0,0,0,,Every run can carry scores, source coverage, warnings, and human ratings so future memory improves"
)

Write-AssFile -Path $mainAss -Dialogues @(
    "Dialogue: 0,0:00:00.00,0:00:06.00,Caption,,0,0,0,,DREAM turns scattered engineering context into persistent memory",
    "Dialogue: 0,0:00:06.00,0:00:13.00,Caption,,0,0,0,,Memory Hub keeps source intake, parsed sections, review state, and evidence visible",
    "Dialogue: 0,0:00:13.00,0:00:21.00,Caption,,0,0,0,,Knowledge intake promotes only reviewed source cards into reusable memory",
    "Dialogue: 0,0:00:21.00,0:00:30.00,Caption,,0,0,0,,Retrieval paths explain why docs, incidents, code, tests, Jira, and PRs were selected",
    "Dialogue: 0,0:00:30.00,0:00:39.00,Caption,,0,0,0,,Requirement workflows turn retrieved memory into review-ready Jira drafts",
    "Dialogue: 0,0:00:39.00,0:00:49.00,Caption,,0,0,0,,Runtime settings expose backend mode before local or Alibaba Cloud execution"
)

Write-AssFile -Path $proofAss -Dialogues @(
    "Dialogue: 0,0:00:00.00,0:00:13.00,Title,,0,0,0,,{\pos(640,150)}Hackathon proof chain",
    "Dialogue: 0,0:00:00.00,0:00:13.00,Body,,0,0,0,,{\pos(640,245)}Qwen config: examples/config/dream.qwen.yaml",
    "Dialogue: 0,0:00:00.00,0:00:13.00,Body,,0,0,0,,{\pos(640,295)}Alibaba deployment file: deploy/alibaba/serverless-devs.yaml",
    "Dialogue: 0,0:00:00.00,0:00:13.00,Body,,0,0,0,,{\pos(640,345)}Final readiness gates validate CI, video, backend health, proof screenshot, and proof recording",
    "Dialogue: 0,0:00:00.00,0:00:13.00,Body,,0,0,0,,{\pos(640,430)}Judging alignment: innovation, technical depth, problem value, presentation"
)

Write-AssFile -Path $outroAss -Dialogues @(
    "Dialogue: 0,0:00:00.00,0:00:10.00,Title,,0,0,0,,{\pos(640,205)}DREAM makes engineering AI accountable",
    "Dialogue: 0,0:00:00.00,0:00:10.00,Body,,0,0,0,,{\pos(640,285)}Remember source truth",
    "Dialogue: 0,0:00:00.00,0:00:10.00,Body,,0,0,0,,{\pos(640,330)}Retrieve the right evidence",
    "Dialogue: 0,0:00:00.00,0:00:10.00,Body,,0,0,0,,{\pos(640,375)}Generate with Qwen Cloud",
    "Dialogue: 0,0:00:00.00,0:00:10.00,Body,,0,0,0,,{\pos(640,420)}Deploy and prove it on Alibaba Cloud",
    "Dialogue: 0,0:00:00.00,0:00:10.00,Body,,0,0,0,,{\pos(640,500)}github.com/zemeng2015/dream-ai-engineering-copilot"
)

$mainAssPath = $mainAss.Replace("\", "/")

Render-ColorSegment -OutputPath $intro -Duration 8 -AssPath $introAss
Render-ColorSegment -OutputPath $problem -Duration 12 -AssPath $problemAss
Render-ImageSegment -InputPath $architecturePng -OutputPath $architecture -Duration 14 -AssPath $architectureAss
Render-ImageSegment -InputPath $memoryHubPng -OutputPath $memoryHub -Duration 9 -AssPath $memoryHubAss
Render-ImageSegment -InputPath $knowledgeIntakePng -OutputPath $knowledgeIntake -Duration 9 -AssPath $knowledgeIntakeAss
Render-ImageSegment -InputPath $retrievalTracePng -OutputPath $retrievalTrace -Duration 9 -AssPath $retrievalTraceAss
Render-ImageSegment -InputPath $jiraDraftPng -OutputPath $jiraDraft -Duration 9 -AssPath $jiraDraftAss
Render-ImageSegment -InputPath $evalAuditPng -OutputPath $evalAudit -Duration 9 -AssPath $evalAuditAss

& ffmpeg -hide_banner -loglevel error -y -i $InputVideo -vf "subtitles='$mainAssPath'" -r 24 -c:v libx264 -pix_fmt yuv420p -an $main
if ($LASTEXITCODE -ne 0) { throw "Failed to render captioned main segment." }

Render-ColorSegment -OutputPath $proof -Duration 13 -AssPath $proofAss
Render-ColorSegment -OutputPath $outro -Duration 10 -AssPath $outroAss

$concatLines = @(
    "file 'intro.mp4'",
    "file 'problem.mp4'",
    "file 'architecture.mp4'",
    "file 'memory-hub.mp4'",
    "file 'knowledge-intake.mp4'",
    "file 'retrieval-trace.mp4'",
    "file 'jira-draft.mp4'",
    "file 'eval-audit.mp4'",
    "file 'main-captioned.mp4'",
    "file 'proof.mp4'",
    "file 'outro.mp4'"
)
Set-Content -Path $concatFile -Value ($concatLines -join "`n") -Encoding ASCII

& ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i $concatFile -c copy -movflags +faststart $OutputVideo
if ($LASTEXITCODE -ne 0) { throw "Failed to concatenate final video." }

$probeJson = & ffprobe -v error -show_entries format=duration,size,format_name -show_streams -of json $OutputVideo
$probe = $probeJson | ConvertFrom-Json
if ([double]$probe.format.duration -ge 180) {
    throw "Final demo video must stay under 180 seconds. Duration: $($probe.format.duration)"
}

$videoStream = @($probe.streams | Where-Object { $_.codec_type -eq "video" } | Select-Object -First 1)
$sourceAssets = @(
    Get-AssetRecord -Name "input_walkthrough_video" -Path $InputVideo
    Get-AssetRecord -Name "architecture_diagram" -Path $architecturePng
    Get-AssetRecord -Name "memory_hub_screenshot" -Path $memoryHubPng
    Get-AssetRecord -Name "knowledge_intake_screenshot" -Path $knowledgeIntakePng
    Get-AssetRecord -Name "retrieval_trace_screenshot" -Path $retrievalTracePng
    Get-AssetRecord -Name "jira_draft_screenshot" -Path $jiraDraftPng
    Get-AssetRecord -Name "eval_audit_screenshot" -Path $evalAuditPng
)

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
    underDevpostLimit = ([double]$probe.format.duration -lt 180)
    sourceAssets = $sourceAssets
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
