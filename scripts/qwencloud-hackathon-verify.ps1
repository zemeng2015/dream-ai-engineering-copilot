param(
    [string]$BaseUrl = "http://localhost:8000",
    [switch]$SkipDraft
)

function Assert-JsonField {
    param(
        $Payload,
        [string]$Field
    )
    if (-not ($Payload.PSObject.Properties.Name -contains $Field)) {
        Write-Error "Health response missing '$Field'"
        exit 1
    }
}

$health = Invoke-RestMethod -Method Get -Uri "$BaseUrl/health"
Assert-JsonField -Payload $health -Field "llm_provider"
Assert-JsonField -Payload $health -Field "track"
Assert-JsonField -Payload $health -Field "proof_file"

if ($health.llm_provider -ne "qwen-cloud") {
    Write-Warning "llm_provider is '$($health.llm_provider)' instead of 'qwen-cloud'."
    exit 1
}

if ($health.track -ne "Track 1: MemoryAgent") {
    Write-Warning "track is '$($health.track)' instead of 'Track 1: MemoryAgent'."
    exit 1
}

if ($health.proof_file -notmatch "deploy/alibaba/serverless-devs.yaml") {
    Write-Warning "proof_file not expected: $($health.proof_file)"
    exit 1
}

Write-Output "Health proof passed."

$showcase = Invoke-RestMethod -Method Get -Uri "$BaseUrl/qwencloud/showcase"
Assert-JsonField -Payload $showcase -Field "track"
Assert-JsonField -Payload $showcase -Field "runtime"
Assert-JsonField -Payload $showcase -Field "scorecard"

if ($showcase.track -ne "Track 1: MemoryAgent") {
    Write-Warning "showcase track is '$($showcase.track)' instead of 'Track 1: MemoryAgent'."
    exit 1
}

if ($showcase.runtime.status -ne "ok") {
    Write-Warning "showcase runtime status is '$($showcase.runtime.status)' instead of 'ok'."
    exit 1
}

if ($showcase.runtime.llm_provider -ne "qwen-cloud") {
    Write-Warning "showcase runtime provider is '$($showcase.runtime.llm_provider)' instead of 'qwen-cloud'."
    exit 1
}

if ([int]$showcase.scorecard.weighted_static_evidence_ready -ne 100) {
    Write-Warning "showcase static evidence is '$($showcase.scorecard.weighted_static_evidence_ready)' instead of 100."
    exit 1
}

Write-Output "Showcase proof passed."

if ($SkipDraft) {
    Write-Output "Draft proof skipped."
    exit 0
}

$draftBody = @{
    team_id = "demo_team"
    rough_business_request = "Users need to know why a forecast job is stuck running"
    llm_provider = "qwen-cloud"
} | ConvertTo-Json
$draft = Invoke-RestMethod -Method Post -Uri "$BaseUrl/requirements/draft" -Body $draftBody -ContentType "application/json"
if (-not $draft.markdown) {
    Write-Error "Requirement draft response missing markdown"
    exit 1
}
Write-Output "Draft proof passed."
