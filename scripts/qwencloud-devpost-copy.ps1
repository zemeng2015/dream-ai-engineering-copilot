function Get-QwenCloudDevpostCopy {
    param(
        [Parameter(Mandatory = $false)]
        [string]$StoryPath = "docs/qwencloud-devpost-story.md"
    )

    if (-not (Test-Path -LiteralPath $StoryPath)) {
        throw "Canonical Devpost story is missing: $StoryPath"
    }

    $story = [System.IO.File]::ReadAllText((Resolve-Path -LiteralPath $StoryPath).Path).Trim()
    $requiredFragments = @(
        "Alibaba Tablestore",
        "cross-instance",
        "20/20",
        "19 of 64",
        "production-effectiveness claims"
    )
    $missingFragments = @($requiredFragments | Where-Object { $story -notmatch [regex]::Escape($_) })
    if ($missingFragments.Count -gt 0) {
        throw "Canonical Devpost story is missing V3 proof: $($missingFragments -join ', ')"
    }
    if ($story -match "(?i)SQLite") {
        throw "Canonical Devpost story still contains the retired SQLite competition narrative."
    }

    return [pscustomobject]@{
        projectTitle = "DREAM: Qwen Cloud MemoryAgent for Source-Backed Engineering Intelligence"
        track = "Track 1: MemoryAgent"
        shortPitch = "DREAM gives Qwen one current, reviewable truth across sessions with timely forgetting and recall under a hard context budget."
        builtWith = "Qwen Cloud, Alibaba Cloud Function Compute, Alibaba Cloud Tablestore, FastAPI, Typer, Angular, Docker, Python, TypeScript"
        preExistingExplanation = "Not applicable. The public DREAM memory platform release started on 06-21-26; Qwen Cloud Track 1 integration, Alibaba packaging, CI audit, architecture assets, and demo/submission materials were added during the hackathon submission period."
        story = $story
        storyPath = $StoryPath
        storySha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $StoryPath).Hash.ToLowerInvariant()
    }
}
