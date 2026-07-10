param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$TeamId = "demo_team",
    [string]$Request = "Users need to know why a forecast job is stuck running",
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [switch]$SkipDraft
)

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$proofPath = Join-Path $OutputDir "submission-gate-$timestamp.json"

function Read-ErrorBody {
    param(
        [Parameter(Mandatory = $true)][System.Net.WebResponse]$Response
    )
    try {
        $reader = New-Object IO.StreamReader($Response.GetResponseStream())
        $payload = $reader.ReadToEnd()
        $reader.Close()
        return $payload
    } catch {
        return ""
    }
}

function Assert-Equals {
    param(
        $Actual,
        [string]$Expected,
        [string]$Field
    )
    if ($Actual -ne $Expected) {
        throw "$Field mismatch: expected '$Expected', got '$Actual'."
    }
}

$proof = @{
    timestamp = (Get-Date).ToString("o")
    health = $null
    draft = $null
    checks = @{}
}

try {
    Write-Host "Collecting health proof..."
    $health = Invoke-RestMethod -Method Get -Uri "$BaseUrl/health" -TimeoutSec 20 -ErrorAction Stop
    $proof.health = $health
    Assert-Equals -Actual $health.llm_provider -Expected "qwen-cloud" -Field "llm_provider"
    Assert-Equals -Actual $health.track -Expected "Track 1: MemoryAgent" -Field "track"
    if (-not ($health.proof_file -like "deploy/alibaba/serverless-devs-runtime.yaml")) {
        throw "proof_file mismatch: expected deploy/alibaba/serverless-devs-runtime.yaml, got $($health.proof_file)."
    }
    $proof.checks.health = "pass"
    Write-Host "Health proof passed."

    if (-not $SkipDraft) {
        Write-Host "Collecting draft proof..."
        $body = @{
            team_id = $TeamId
            rough_business_request = $Request
            llm_provider = "qwen-cloud"
        } | ConvertTo-Json
        try {
            $draft = Invoke-RestMethod -Method Post `
                -Uri "$BaseUrl/requirements/draft" `
                -Body $body `
                -ContentType "application/json" `
                -TimeoutSec 30 `
                -ErrorAction Stop
            $proof.draft = $draft
            if (-not $draft.markdown) {
                throw "Draft response missing markdown."
            }
            $proof.checks.draft = "pass"
            Write-Host "Draft proof passed."
        } catch {
            $response = $_.Exception.Response
            if ($null -ne $response) {
                $errorBody = Read-ErrorBody -Response $response
                if ($errorBody) {
                    throw "Draft proof failed: $errorBody"
                }
            }
            throw "Draft proof failed: $($_.Exception.Message)"
        }
    } else {
        Write-Host "Skipping draft proof by request."
        $proof.checks.draft = "skipped"
    }

    $proof.checks.overall = "pass"
    $proof | ConvertTo-Json -Depth 20 | Out-File -FilePath $proofPath -Encoding utf8
    Write-Host "Submission gate passed."
    Write-Host "Proof file: $proofPath"
    Write-Host "Use these values on Devpost:"
    Write-Host "  $($proof.health.track)"
    Write-Host "  $($proof.health.llm_provider)"
    Write-Host "  proof file: $($proof.health.proof_file)"
} catch {
    $proof.checks.overall = "fail"
    $proof.error = $_.Exception.Message
    $proof | ConvertTo-Json -Depth 20 | Out-File -FilePath $proofPath -Encoding utf8
    Write-Error "Submission gate failed: $($_.Exception.Message)"
    Write-Host "Failure proof file: $proofPath"
    exit 1
}
