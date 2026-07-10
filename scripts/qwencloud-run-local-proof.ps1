param(
    [string]$ConfigPath = "examples/config/dream.qwen.yaml",
    [string]$ApiKey = $env:DASHSCOPE_API_KEY,
    [string]$QwenBaseUrl = $env:QWEN_BASE_URL,
    [string]$QwenModel = $env:QWEN_MODEL,
    [int]$Port = 8012,
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [string]$TeamId = "demo_team",
    [string]$Request = "Users need to know why a forecast job is stuck running",
    [switch]$SkipDraft,
    [switch]$AllowDirty
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$baseUrl = "http://127.0.0.1:$Port"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$apiOut = Join-Path $OutputDir "local-proof-api-$timestamp.out"
$apiErr = Join-Path $OutputDir "local-proof-api-$timestamp.err"
$reportJson = Join-Path $OutputDir "local-proof-$timestamp.json"
$reportMd = Join-Path $OutputDir "local-proof-$timestamp.md"
$steps = @()
$apiProcess = $null
$powerShellExe = $null
$oldEnv = @{
    DREAM_CONFIG_FILE = $env:DREAM_CONFIG_FILE
    DASHSCOPE_API_KEY = $env:DASHSCOPE_API_KEY
    QWEN_BASE_URL = $env:QWEN_BASE_URL
    QWEN_MODEL = $env:QWEN_MODEL
}

function Get-PowerShellExe {
    $pwsh = Get-Command "pwsh" -ErrorAction SilentlyContinue
    if ($pwsh) {
        return $pwsh.Source
    }
    $windowsPowerShell = Get-Command "powershell" -ErrorAction SilentlyContinue
    if ($windowsPowerShell) {
        return $windowsPowerShell.Source
    }
    throw "PowerShell executable not found."
}

function Add-Step([string]$Name, [string]$Status, [string]$Details) {
    $script:steps += [ordered]@{
        name = $Name
        status = $Status
        details = $Details
    }
}

function Invoke-LoggedScript {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$ScriptPath,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $stdout = Join-Path $OutputDir "$Name-$timestamp.out"
    $stderr = Join-Path $OutputDir "$Name-$timestamp.err"
    $processArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $ScriptPath) + $Arguments
    $proc = Start-Process -FilePath $script:powerShellExe -ArgumentList $processArgs -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        Add-Step -Name $Name -Status "fail" -Details "stdout=$stdout; stderr=$stderr"
        throw "$Name failed with exit code $($proc.ExitCode). See $stderr"
    }
    Add-Step -Name $Name -Status "pass" -Details "stdout=$stdout; stderr=$stderr"
}

function Write-Report([string]$Overall, [string]$ErrorMessage = "") {
    $result = [ordered]@{
        generatedAt = (Get-Date).ToUniversalTime().ToString("o")
        overall = $Overall
        baseUrl = $baseUrl
        port = $Port
        configPath = $ConfigPath
        qwenBaseUrl = $env:QWEN_BASE_URL
        qwenModel = $env:QWEN_MODEL
        skipDraft = [bool]$SkipDraft
        allowDirty = [bool]$AllowDirty
        error = $ErrorMessage
        apiStdout = $apiOut
        apiStderr = $apiErr
        steps = $steps
    }
    Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

    $lines = @(
        "# Qwen Cloud Local Proof ($timestamp)",
        "",
        "- Overall: $Overall",
        "- Base URL: $baseUrl",
        "- Config: $ConfigPath",
        "- Qwen base URL: $($env:QWEN_BASE_URL)",
        "- Qwen model: $($env:QWEN_MODEL)",
        "- Draft proof skipped: $([bool]$SkipDraft)",
        "- Dirty worktree allowed: $([bool]$AllowDirty)",
        "- API stdout: $apiOut",
        "- API stderr: $apiErr",
        ""
    )
    if ($ErrorMessage) {
        $lines += "- Error: $ErrorMessage"
        $lines += ""
    }
    $lines += @(
        "## Steps",
        "",
        "| Step | Status | Details |",
        "|---|---|---|"
    )
    foreach ($step in $steps) {
        $lines += "| $($step.name) | $($step.status) | $($step.details -replace '\|', '/') |"
    }
    Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8
}

try {
    foreach ($path in @($ConfigPath, "scripts/qwencloud-hackathon-verify.ps1", "scripts/qwencloud-hackathon-proof.ps1", "scripts/qwencloud-hackathon-submit-gate.ps1", "scripts/qwencloud-hackathon-audit.ps1")) {
        if (-not (Test-Path $path)) {
            throw "Required local proof file is missing: $path"
        }
    }
    Add-Step -Name "required_files" -Status "pass" -Details "local proof scripts found"

    $powerShellExe = Get-PowerShellExe
    Add-Step -Name "tool.powershell" -Status "pass" -Details $powerShellExe

    if (-not $SkipDraft -and [string]::IsNullOrWhiteSpace($ApiKey)) {
        throw "DASHSCOPE_API_KEY is required for full draft proof. Re-run with -SkipDraft for health-only local proof."
    }

    $env:DREAM_CONFIG_FILE = $ConfigPath
    if ($ApiKey) { $env:DASHSCOPE_API_KEY = $ApiKey }
    if ($QwenBaseUrl) {
        $env:QWEN_BASE_URL = $QwenBaseUrl
    } else {
        $env:QWEN_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    }
    if ($QwenModel) {
        $env:QWEN_MODEL = $QwenModel
    } else {
        $env:QWEN_MODEL = "qwen3.7-plus"
    }
    Add-Step -Name "env" -Status "pass" -Details "DREAM_CONFIG_FILE, QWEN_BASE_URL, and QWEN_MODEL set for child API"

    $apiProcess = Start-Process -FilePath "python" -ArgumentList @("-m", "uvicorn", "dream.api.app:app", "--host", "127.0.0.1", "--port", "$Port") -NoNewWindow -PassThru -RedirectStandardOutput $apiOut -RedirectStandardError $apiErr
    Add-Step -Name "start_api" -Status "pass" -Details "pid=$($apiProcess.Id); stdout=$apiOut; stderr=$apiErr"

    $health = $null
    $deadline = (Get-Date).AddSeconds(45)
    do {
        if ($apiProcess.HasExited) {
            throw "Local API exited before becoming healthy. See $apiErr"
        }
        try {
            $health = Invoke-RestMethod -Method Get -Uri "$baseUrl/health" -TimeoutSec 5 -ErrorAction Stop
            if (
                $health.status -eq "ok" -and
                $health.track -eq "Track 1: MemoryAgent" -and
                $health.llm_provider -eq "qwen-cloud" -and
                $health.proof_file -eq "deploy/alibaba/serverless-devs-runtime.yaml"
            ) {
                break
            }
            $health = $null
        }
        catch {
            Start-Sleep -Seconds 2
        }
    } while ((Get-Date) -lt $deadline)

    if (-not $health) {
        throw "Local API did not return Qwen Cloud hackathon health proof at $baseUrl/health."
    }
    Add-Step -Name "health_wait" -Status "pass" -Details "track=$($health.track); provider=$($health.llm_provider); proof_file=$($health.proof_file)"

    $commonArgs = @("-BaseUrl", $baseUrl)
    if ($SkipDraft) {
        Invoke-LoggedScript -Name "verify" -ScriptPath "scripts/qwencloud-hackathon-verify.ps1" -Arguments ($commonArgs + @("-SkipDraft"))
        Invoke-LoggedScript -Name "proof" -ScriptPath "scripts/qwencloud-hackathon-proof.ps1" -Arguments ($commonArgs + @("-SkipDraft", "-OutputDir", $OutputDir))
        Invoke-LoggedScript -Name "submit-gate" -ScriptPath "scripts/qwencloud-hackathon-submit-gate.ps1" -Arguments ($commonArgs + @("-SkipDraft", "-OutputDir", $OutputDir))
        $auditArgs = $commonArgs + @("-SkipDraft", "-OutputDir", $OutputDir)
        if ($AllowDirty) { $auditArgs += "-AllowDirty" }
        Invoke-LoggedScript -Name "audit" -ScriptPath "scripts/qwencloud-hackathon-audit.ps1" -Arguments $auditArgs
    } else {
        $draftArgs = $commonArgs + @("-TeamId", $TeamId, "-Request", $Request)
        Invoke-LoggedScript -Name "verify" -ScriptPath "scripts/qwencloud-hackathon-verify.ps1" -Arguments $commonArgs
        Invoke-LoggedScript -Name "proof" -ScriptPath "scripts/qwencloud-hackathon-proof.ps1" -Arguments ($draftArgs + @("-OutputDir", $OutputDir))
        Invoke-LoggedScript -Name "submit-gate" -ScriptPath "scripts/qwencloud-hackathon-submit-gate.ps1" -Arguments ($draftArgs + @("-OutputDir", $OutputDir))
        $auditArgs = $draftArgs + @("-OutputDir", $OutputDir)
        if ($AllowDirty) { $auditArgs += "-AllowDirty" }
        Invoke-LoggedScript -Name "audit" -ScriptPath "scripts/qwencloud-hackathon-audit.ps1" -Arguments $auditArgs
    }

    Write-Report -Overall "pass"
    Write-Host "Local proof passed. Report: $reportMd"
    Write-Host "JSON: $reportJson"
}
catch {
    Add-Step -Name "local_proof_error" -Status "fail" -Details $_.Exception.Message
    Write-Report -Overall "fail" -ErrorMessage $_.Exception.Message
    Write-Error $_.Exception.Message
    Write-Host "Local proof report: $reportMd"
    exit 1
}
finally {
    if ($apiProcess -and -not $apiProcess.HasExited) {
        Stop-Process -Id $apiProcess.Id -Force
    }

    $env:DREAM_CONFIG_FILE = $oldEnv.DREAM_CONFIG_FILE
    $env:DASHSCOPE_API_KEY = $oldEnv.DASHSCOPE_API_KEY
    $env:QWEN_BASE_URL = $oldEnv.QWEN_BASE_URL
    $env:QWEN_MODEL = $oldEnv.QWEN_MODEL
}
