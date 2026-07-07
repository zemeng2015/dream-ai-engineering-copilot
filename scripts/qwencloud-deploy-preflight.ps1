param(
    [Parameter(Mandatory = $false)]
    [string]$ProjectRoot = (Get-Location).Path,
    [Parameter(Mandatory = $false)]
    [string]$ImageTag = "dream-qwencloud-memoryagent:local",
    [Parameter(Mandatory = $false)]
    [int]$SmokePort = 8011,
    [Parameter(Mandatory = $false)]
    [string]$EnvFile = "",
    [switch]$BuildImage,
    [switch]$SmokeContainer
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$artifactDir = Join-Path $ProjectRoot "artifacts/qwencloud-proof"
New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null
. (Join-Path $PSScriptRoot "qwencloud-env.ps1")
$importedEnvNames = @()
if (-not [string]::IsNullOrWhiteSpace($EnvFile)) {
    $importedEnvNames = @(Import-QwenCloudEnvFile -Path $EnvFile)
}
$outJson = Join-Path $artifactDir "deploy-preflight-$timestamp.json"
$outMd = Join-Path $artifactDir "deploy-preflight-$timestamp.md"
$checks = @()
$ready = $true

function Add-Check([string]$Name, [bool]$Ok, [string]$Details, [bool]$Required = $true) {
    $script:checks += [ordered]@{
        name = $Name
        ok = $Ok
        required = $Required
        details = $Details
    }

    if ($Required -and -not $Ok) {
        $script:ready = $false
    }
}

function Has-Command([string]$Name) {
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Has-Env([string]$Name) {
    return Test-QwenCloudEnvValuePresent -Name $Name
}

function Test-ServerlessDevsDefaultAccess {
    try {
        $output = (& s config get -a default 2>&1) -join "`n"
        return $output -notmatch "not yet|not found|not.*configured|configured key information"
    }
    catch {
        return $false
    }
}

$existing = Get-Location
Set-Location $ProjectRoot

try {
    $requiredFiles = @(
        "Dockerfile",
        "deploy/alibaba/serverless-devs.yaml",
        "deploy/alibaba/README.md",
        "examples/config/dream.qwen.yaml",
        "scripts/qwencloud-hackathon-verify.ps1",
        "scripts/qwencloud-hackathon-proof.ps1",
        "scripts/qwencloud-hackathon-submit-gate.ps1"
    )

    foreach ($path in $requiredFiles) {
        Add-Check -Name "file.$path" -Ok (Test-Path $path) -Details $path
    }

    Add-Check -Name "tool.python" -Ok (Has-Command "python") -Details "Required for local smoke and fallback debugging."

    $hasDocker = Has-Command "docker"
    Add-Check -Name "tool.docker" -Ok $hasDocker -Details "Required for custom-container build and smoke."

    $dockerDaemonOk = $false
    if ($hasDocker) {
        try {
            $dockerOut = Join-Path $artifactDir "docker-info-$timestamp.out"
            $dockerErr = Join-Path $artifactDir "docker-info-$timestamp.err"
            $dockerInfo = Start-Process -FilePath "docker" -ArgumentList "info" -NoNewWindow -Wait -PassThru -RedirectStandardOutput $dockerOut -RedirectStandardError $dockerErr
            $dockerDaemonOk = $dockerInfo.ExitCode -eq 0
        }
        catch {
            $dockerDaemonOk = $false
        }
    }
    Add-Check -Name "tool.docker_daemon" -Ok $dockerDaemonOk -Details "Docker daemon must be running for image build and smoke."

    $hasServerlessDevs = Has-Command "s"
    Add-Check -Name "tool.serverless_devs_s" -Ok $hasServerlessDevs -Details "Install with: npm install -g @serverless-devs/s"
    Add-Check -Name "tool.serverless_devs_default_access" -Ok ($hasServerlessDevs -and (Test-ServerlessDevsDefaultAccess)) -Details "Run: s config add"

    Add-Check -Name "env.DASHSCOPE_API_KEY" -Ok (Has-Env "DASHSCOPE_API_KEY") -Details "Required for live Qwen Cloud generation on the deployed backend."
    Add-Check -Name "env.ALIBABA_CLOUD_REGION" -Ok (Has-Env "ALIBABA_CLOUD_REGION") -Details "Example: ap-southeast-1"
    Add-Check -Name "env.ALIBABA_CLOUD_CONTAINER_IMAGE" -Ok (Has-Env "ALIBABA_CLOUD_CONTAINER_IMAGE") -Details "Alibaba Cloud Container Registry image URI."
    Add-Check -Name "env.QWEN_BASE_URL" -Ok (Has-Env "QWEN_BASE_URL") -Details "Defaults in yaml if unset; recommended for explicit proof." -Required $false
    Add-Check -Name "env.QWEN_MODEL" -Ok (Has-Env "QWEN_MODEL") -Details "Defaults in yaml if unset; recommended for explicit proof." -Required $false

    if ($BuildImage) {
        if ($hasDocker -and $dockerDaemonOk) {
            $buildOut = Join-Path $artifactDir "docker-build-$timestamp.out"
            $buildErr = Join-Path $artifactDir "docker-build-$timestamp.err"
            $build = Start-Process -FilePath "docker" -ArgumentList @("build", "-t", $ImageTag, ".") -NoNewWindow -Wait -PassThru -RedirectStandardOutput $buildOut -RedirectStandardError $buildErr
            Add-Check -Name "docker.build" -Ok ($build.ExitCode -eq 0) -Details "docker build -t $ImageTag ."
        }
        else {
            Add-Check -Name "docker.build" -Ok $false -Details "Docker CLI or daemon unavailable."
        }
    }
    else {
        Add-Check -Name "docker.build" -Ok $true -Details "Skipped. Re-run with -BuildImage." -Required $false
    }

    if ($SmokeContainer) {
        $containerName = "dream-qwencloud-memoryagent-smoke"
        $smokeOk = $false
        $smokeDetails = "GET http://127.0.0.1:$SmokePort/health from $ImageTag"
        if ($hasDocker -and $dockerDaemonOk) {
            try {
                try {
                    & docker rm -f $containerName 2>$null | Out-Null
                }
                catch {
                    # Previous smoke container may not exist.
                }

                $dockerArgs = @(
                    "run", "--rm", "-d",
                    "-p", "$($SmokePort):8000",
                    "--name", $containerName,
                    "-e", "DREAM_CONFIG_FILE=/app/examples/config/dream.qwen.yaml",
                    "-e", "QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
                    "-e", "QWEN_MODEL=qwen3.7-plus",
                    $ImageTag
                )
                $runOut = Join-Path $artifactDir "docker-run-$timestamp.out"
                $runErr = Join-Path $artifactDir "docker-run-$timestamp.err"
                $run = Start-Process -FilePath "docker" -ArgumentList $dockerArgs -NoNewWindow -Wait -PassThru -RedirectStandardOutput $runOut -RedirectStandardError $runErr
                if ($run.ExitCode -eq 0) {
                    $deadline = (Get-Date).AddSeconds(45)
                    do {
                        try {
                            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$SmokePort/health" -TimeoutSec 5
                            if (
                                $health.status -eq "ok" -and
                                $health.track -eq "Track 1: MemoryAgent" -and
                                $health.llm_provider -eq "qwen-cloud" -and
                                $health.proof_file -eq "deploy/alibaba/serverless-devs.yaml"
                            ) {
                                $smokeOk = $true
                                break
                            }
                        }
                        catch {
                            Start-Sleep -Seconds 2
                        }
                    } while ((Get-Date) -lt $deadline)
                }
            }
            finally {
                try {
                    & docker stop $containerName 2>$null | Out-Null
                }
                catch {
                    # Container may have exited before cleanup.
                }
            }
        }
        Add-Check -Name "docker.smoke_container" -Ok $smokeOk -Details $smokeDetails
    }
    else {
        Add-Check -Name "docker.smoke_container" -Ok $true -Details "Skipped. Re-run with -SmokeContainer." -Required $false
    }
}
finally {
    Set-Location $existing
}

$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    projectRoot = $ProjectRoot
    readyForDeploy = $ready
    buildImage = [bool]$BuildImage
    smokeContainer = [bool]$SmokeContainer
    imageTag = $ImageTag
    envFile = $EnvFile
    importedEnvNames = $importedEnvNames
    checks = $checks
}

Set-Content -Path $outJson -Value ($result | ConvertTo-Json -Depth 10) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Alibaba Deploy Preflight ($timestamp)",
    "",
    "- Ready for deploy: $ready",
    "- Docker build requested: $([bool]$BuildImage)",
    "- Container smoke requested: $([bool]$SmokeContainer)",
    "- Image tag: $ImageTag",
    "- Env file imported: $(if ($EnvFile) { $EnvFile } else { '<none>' })",
    "",
    "## Checks",
    ""
)

foreach ($check in $checks) {
    $status = if ($check.ok) { "PASS" } else { "FAIL" }
    $required = if ($check.required) { "required" } else { "optional" }
    $lines += "- $status [$required] $($check.name): $($check.details)"
}

$lines += @(
    "",
    "## Next deploy commands",
    "",
    '```powershell',
    'npm install -g @serverless-devs/s',
    's config add',
    'scripts/qwencloud-deploy-preflight.ps1 -EnvFile .env.qwencloud.local -BuildImage -SmokeContainer',
    'docker tag dream-qwencloud-memoryagent:local $env:ALIBABA_CLOUD_CONTAINER_IMAGE',
    'docker push $env:ALIBABA_CLOUD_CONTAINER_IMAGE',
    's deploy -t deploy/alibaba/serverless-devs.yaml -y',
    'scripts/qwencloud-hackathon-verify.ps1 -BaseUrl "https://<function-compute-endpoint>"',
    '```'
)

Set-Content -Path $outMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($ready) {
    Write-Host "Deploy preflight passed: $outJson"
}
else {
    Write-Host "Deploy preflight found missing required inputs: $outJson" -ForegroundColor Yellow
    exit 1
}
