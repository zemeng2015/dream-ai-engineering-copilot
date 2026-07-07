param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$TeamId = "demo_team",
    [string]$Request = "Users need to know why a forecast job is stuck running",
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [switch]$SkipDraft
)

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

function Save-Json {
    param(
        [string]$Path,
        [object]$Payload
    )

    $Payload | ConvertTo-Json -Depth 20 | Out-File -FilePath $Path -Encoding utf8
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$healthPath = Join-Path $OutputDir "health-$timestamp.json"
$showcasePath = Join-Path $OutputDir "showcase-$timestamp.json"
$draftPath = Join-Path $OutputDir "requirements-draft-$timestamp.json"

try {
    Write-Host "Collecting health proof..."
    $health = Invoke-RestMethod -Method Get -Uri "$BaseUrl/health" -TimeoutSec 20 -ErrorAction Stop
    Save-Json -Path $healthPath -Payload $health

    Write-Host "Collecting showcase proof..."
    $showcase = Invoke-RestMethod -Method Get -Uri "$BaseUrl/qwencloud/showcase" -TimeoutSec 20 -ErrorAction Stop
    Save-Json -Path $showcasePath -Payload $showcase

    if (-not $SkipDraft) {
        Write-Host "Collecting draft proof..."
        $body = @{
            team_id = $TeamId
            rough_business_request = $Request
            llm_provider = "qwen-cloud"
        } | ConvertTo-Json
        $draft = Invoke-RestMethod -Method Post `
            -Uri "$BaseUrl/requirements/draft" `
            -Body $body `
            -ContentType "application/json" `
            -TimeoutSec 30 `
            -ErrorAction Stop
        Save-Json -Path $draftPath -Payload $draft
    }

    Write-Host "Proof package created:"
    Write-Host "  health:    $healthPath"
    Write-Host "  showcase:  $showcasePath"
    if ($SkipDraft) {
        Write-Host "  draft:     skipped"
    } else {
        Write-Host "  draft:     $draftPath"
    }
} catch {
    Write-Error "Proof collection failed: $($_.Exception.Message)"
    exit 1
}

