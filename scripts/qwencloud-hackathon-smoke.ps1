param(
    [string]$ConfigPath = "examples/config/dream.qwen.yaml",
    [string]$ApiKey = $env:DASHSCOPE_API_KEY,
    [string]$BaseUrl = $env:QWEN_BASE_URL,
    [string]$Model = $env:QWEN_MODEL,
    [string]$Prompt = "Return DREAM_QWEN_OK and one short phrase."
)

if (-not $ApiKey) {
    Write-Error "DASHSCOPE_API_KEY is not set. Run: `$env:DASHSCOPE_API_KEY='...'"
    exit 1
}

$env:DREAM_CONFIG_FILE = $ConfigPath
$env:DASHSCOPE_API_KEY = $ApiKey
if ($BaseUrl) { $env:QWEN_BASE_URL = $BaseUrl }
if ($Model) { $env:QWEN_MODEL = $Model }

Write-Host "1) Smoke test..."
python -m dream.cli.main llm smoke --provider qwen-cloud --prompt $Prompt

Write-Host "2) Start API manually in a new shell:"
Write-Host "uvicorn dream.api.app:app --reload --host 127.0.0.1 --port 8000"
Write-Host "Then verify:"
$verifyCommands = @'
curl http://localhost:8000/health
curl -X POST http://localhost:8000/requirements/draft -H "Content-Type: application/json" -d "{\"team_id\":\"demo_team\",\"rough_business_request\":\"Users need to know why a forecast job is stuck running while outputs are blocked\",\"llm_provider\":\"qwen-cloud\"}"
'@
Write-Host $verifyCommands
