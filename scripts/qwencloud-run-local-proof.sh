#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail

CONFIG_PATH="examples/config/dream.qwen.yaml"
PORT="8012"
BASE_URL=""
OUTPUT_DIR="artifacts/qwencloud-proof"
TEAM_ID="demo_team"
REQUEST="Users need to know why a forecast job is stuck running"
SKIP_DRAFT=0
ALLOW_DIRTY=0
STARTUP_TIMEOUT=45
PYTHON_BIN="${PYTHON:-python}"
API_PID=""

usage() {
  cat <<'EOF'
Usage: scripts/qwencloud-run-local-proof.sh [options]

Starts a local DREAM API in Qwen Cloud mode, verifies the Track 1 MemoryAgent
/health proof, runs minimal pytest smoke coverage, and writes JSON/Markdown
proof reports under artifacts/qwencloud-proof.

Options:
  --config-path PATH      Qwen-mode config path (default: examples/config/dream.qwen.yaml)
  --port PORT             Local API port when starting uvicorn (default: 8012)
  --base-url URL          Verify an already-running API instead of starting uvicorn
  --output-dir PATH       Proof artifact output directory (default: artifacts/qwencloud-proof)
  --team-id VALUE         Draft proof team id (default: demo_team)
  --request TEXT          Draft proof request text
  --startup-timeout SEC   Seconds to wait for /health (default: 45)
  --python PATH           Python executable (default: $PYTHON or python)
  --skip-draft            Do not call Qwen-backed /requirements/draft
  --allow-dirty           Allow a dirty git worktree while developing
  -h, --help              Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config-path)
      CONFIG_PATH="${2:?--config-path requires a value}"
      shift 2
      ;;
    --port)
      PORT="${2:?--port requires a value}"
      shift 2
      ;;
    --base-url)
      BASE_URL="${2:?--base-url requires a value}"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="${2:?--output-dir requires a value}"
      shift 2
      ;;
    --team-id)
      TEAM_ID="${2:?--team-id requires a value}"
      shift 2
      ;;
    --request)
      REQUEST="${2:?--request requires a value}"
      shift 2
      ;;
    --startup-timeout)
      STARTUP_TIMEOUT="${2:?--startup-timeout requires a value}"
      shift 2
      ;;
    --python)
      PYTHON_BIN="${2:?--python requires a value}"
      shift 2
      ;;
    --skip-draft)
      SKIP_DRAFT=1
      shift
      ;;
    --allow-dirty)
      ALLOW_DIRTY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." >/dev/null 2>&1 && pwd)"
cd "$REPO_ROOT"

if [[ -z "$BASE_URL" ]]; then
  BASE_URL="http://127.0.0.1:$PORT"
fi

mkdir -p "$OUTPUT_DIR"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
API_OUT="$OUTPUT_DIR/local-proof-bash-api-$TIMESTAMP.out"
API_ERR="$OUTPUT_DIR/local-proof-bash-api-$TIMESTAMP.err"
PYTEST_OUT="$OUTPUT_DIR/local-proof-bash-pytest-$TIMESTAMP.out"
PYTEST_ERR="$OUTPUT_DIR/local-proof-bash-pytest-$TIMESTAMP.err"
DRAFT_JSON="$OUTPUT_DIR/local-proof-bash-draft-$TIMESTAMP.json"
DRAFT_ERR="$OUTPUT_DIR/local-proof-bash-draft-$TIMESTAMP.err"
HEALTH_JSON="$OUTPUT_DIR/local-proof-bash-health-$TIMESTAMP.json"
REPORT_JSON="$OUTPUT_DIR/local-proof-bash-$TIMESTAMP.json"
REPORT_MD="$OUTPUT_DIR/local-proof-bash-$TIMESTAMP.md"
STEPS_TSV="$OUTPUT_DIR/local-proof-bash-$TIMESTAMP.steps.tsv"
: > "$STEPS_TSV"

add_step() {
  local name="$1"
  local status="$2"
  local details="${3:-}"
  details="${details//$'\t'/ }"
  details="${details//$'\r'/ }"
  details="${details//$'\n'/ }"
  printf '%s\t%s\t%s\n' "$name" "$status" "$details" >> "$STEPS_TSV"
}

write_report() {
  local overall="$1"
  local error_message="${2:-}"
  LOCAL_PROOF_OVERALL="$overall" \
  LOCAL_PROOF_ERROR="$error_message" \
  LOCAL_PROOF_TIMESTAMP="$TIMESTAMP" \
  LOCAL_PROOF_BASE_URL="$BASE_URL" \
  LOCAL_PROOF_PORT="$PORT" \
  LOCAL_PROOF_CONFIG_PATH="$CONFIG_PATH" \
  LOCAL_PROOF_SKIP_DRAFT="$SKIP_DRAFT" \
  LOCAL_PROOF_ALLOW_DIRTY="$ALLOW_DIRTY" \
  LOCAL_PROOF_API_OUT="$API_OUT" \
  LOCAL_PROOF_API_ERR="$API_ERR" \
  LOCAL_PROOF_PYTEST_OUT="$PYTEST_OUT" \
  LOCAL_PROOF_PYTEST_ERR="$PYTEST_ERR" \
  LOCAL_PROOF_DRAFT_JSON="$DRAFT_JSON" \
  LOCAL_PROOF_DRAFT_ERR="$DRAFT_ERR" \
  LOCAL_PROOF_HEALTH_JSON="$HEALTH_JSON" \
  "$PYTHON_BIN" - "$REPORT_JSON" "$REPORT_MD" "$STEPS_TSV" <<'PY'
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys

report_json = pathlib.Path(sys.argv[1])
report_md = pathlib.Path(sys.argv[2])
steps_tsv = pathlib.Path(sys.argv[3])


def env_bool(name: str) -> bool:
    return os.environ.get(name) == "1"


def load_json(path: str) -> dict[str, object] | None:
    candidate = pathlib.Path(path)
    if not candidate.exists():
        return None
    try:
        return json.loads(candidate.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # pragma: no cover - report should survive malformed evidence
        return {"error": str(exc), "path": str(candidate)}


steps: list[dict[str, str]] = []
if steps_tsv.exists():
    for line in steps_tsv.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3:
            steps.append({"name": parts[0], "status": parts[1], "details": parts[2]})

health = load_json(os.environ["LOCAL_PROOF_HEALTH_JSON"])
draft = load_json(os.environ["LOCAL_PROOF_DRAFT_JSON"])

result = {
    "generatedAt": dt.datetime.now(dt.UTC).isoformat(),
    "overall": os.environ["LOCAL_PROOF_OVERALL"],
    "baseUrl": os.environ["LOCAL_PROOF_BASE_URL"],
    "port": os.environ["LOCAL_PROOF_PORT"],
    "configPath": os.environ["LOCAL_PROOF_CONFIG_PATH"],
    "qwenBaseUrl": os.environ.get("QWEN_BASE_URL", ""),
    "qwenModel": os.environ.get("QWEN_MODEL", ""),
    "skipDraft": env_bool("LOCAL_PROOF_SKIP_DRAFT"),
    "allowDirty": env_bool("LOCAL_PROOF_ALLOW_DIRTY"),
    "error": os.environ["LOCAL_PROOF_ERROR"],
    "apiStdout": os.environ["LOCAL_PROOF_API_OUT"],
    "apiStderr": os.environ["LOCAL_PROOF_API_ERR"],
    "pytestStdout": os.environ["LOCAL_PROOF_PYTEST_OUT"],
    "pytestStderr": os.environ["LOCAL_PROOF_PYTEST_ERR"],
    "draftJson": os.environ["LOCAL_PROOF_DRAFT_JSON"],
    "draftStderr": os.environ["LOCAL_PROOF_DRAFT_ERR"],
    "healthJson": os.environ["LOCAL_PROOF_HEALTH_JSON"],
    "healthProof": health,
    "draftProof": draft,
    "steps": steps,
}
report_json.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")


def table_cell(value: object) -> str:
    return str(value).replace("|", "/")


lines = [
    f"# Qwen Cloud Bash Local Proof ({os.environ['LOCAL_PROOF_TIMESTAMP']})",
    "",
    f"- Overall: {result['overall']}",
    f"- Base URL: {result['baseUrl']}",
    f"- Config: {result['configPath']}",
    f"- Qwen base URL: {result['qwenBaseUrl']}",
    f"- Qwen model: {result['qwenModel']}",
    f"- Draft proof skipped: {result['skipDraft']}",
    f"- Dirty worktree allowed: {result['allowDirty']}",
    f"- API stdout: {result['apiStdout']}",
    f"- API stderr: {result['apiStderr']}",
    f"- Pytest stdout: {result['pytestStdout']}",
    f"- Pytest stderr: {result['pytestStderr']}",
]
if result["error"]:
    lines.extend(["", f"- Error: {result['error']}"])
if health:
    lines.extend(
        [
            "",
            "## Health Proof",
            "",
            f"- Track: {health.get('track', '<missing>')}",
            f"- LLM provider: {health.get('llm_provider', '<missing>')}",
            f"- Proof file: {health.get('proof_file', '<missing>')}",
            f"- Deployment target: {health.get('deployment_target', '<missing>')}",
        ]
    )
lines.extend(["", "## Steps", "", "| Step | Status | Details |", "|---|---|---|"])
for step in steps:
    lines.append(
        f"| {table_cell(step['name'])} | {table_cell(step['status'])} | {table_cell(step['details'])} |"
    )

report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
}

fail() {
  local message="$1"
  add_step "local_proof_error" "fail" "$message"
  write_report "fail" "$message" || true
  echo "Local proof failed: $message" >&2
  echo "Report: $REPORT_MD" >&2
  exit 1
}

cleanup() {
  if [[ -n "${API_PID:-}" ]] && kill -0 "$API_PID" 2>/dev/null; then
    kill "$API_PID" 2>/dev/null || true
    wait "$API_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

check_health() {
  "$PYTHON_BIN" - "$BASE_URL" <<'PY'
import json
import sys
from urllib.request import urlopen

base_url = sys.argv[1].rstrip("/")
with urlopen(f"{base_url}/health", timeout=5) as response:
    payload = json.loads(response.read().decode("utf-8"))

expected = {
    "status": "ok",
    "track": "Track 1: MemoryAgent",
    "llm_provider": "qwen-cloud",
    "proof_file": "deploy/alibaba/serverless-devs-runtime.yaml",
}
for key, value in expected.items():
    if payload.get(key) != value:
        print(json.dumps(payload, indent=2, sort_keys=True))
        raise SystemExit(2)
print(json.dumps(payload, indent=2, sort_keys=True))
PY
}

run_draft_proof() {
  "$PYTHON_BIN" - "$BASE_URL" "$TEAM_ID" "$REQUEST" <<'PY'
import json
import sys
from urllib.request import Request, urlopen

base_url = sys.argv[1].rstrip("/")
team_id = sys.argv[2]
request_text = sys.argv[3]
payload = {
    "team_id": team_id,
    "rough_business_request": request_text,
    "llm_provider": "qwen-cloud",
}
body = json.dumps(payload).encode("utf-8")
request = Request(
    f"{base_url}/requirements/draft",
    data=body,
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urlopen(request, timeout=60) as response:
    draft = json.loads(response.read().decode("utf-8"))
if not draft.get("markdown"):
    raise SystemExit("Requirement draft response missing markdown")
print(json.dumps(draft, indent=2, sort_keys=True))
PY
}

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python executable not found: $PYTHON_BIN" >&2
  exit 127
fi
add_step "tool.python" "pass" "$("$PYTHON_BIN" --version 2>&1)"

required_files=(
  "$CONFIG_PATH"
  "deploy/alibaba/serverless-devs-runtime.yaml"
  "dream/llm/qwen_cloud.py"
  "tests/test_api_health.py"
  "tests/test_qwen_cloud_provider.py"
)
missing_files=()
for path in "${required_files[@]}"; do
  if [[ ! -e "$path" ]]; then
    missing_files+=("$path")
  fi
done
if [[ ${#missing_files[@]} -gt 0 ]]; then
  fail "Required local proof file is missing: ${missing_files[*]}"
fi
add_step "required_files" "pass" "config, Alibaba proof template, provider, and smoke tests found"

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git_status="$(git status --porcelain)"
  if [[ -n "$git_status" && "$ALLOW_DIRTY" -ne 1 ]]; then
    add_step "git_worktree_clean" "fail" "dirty worktree; pass --allow-dirty only for local development"
    fail "Git worktree is dirty. Commit/stash changes or pass --allow-dirty while developing."
  fi
  add_step "git_worktree_clean" "pass" "$(if [[ -z "$git_status" ]]; then echo clean; else echo dirty_allowed; fi)"
else
  add_step "git_worktree_clean" "skip" "git unavailable or not inside a worktree"
fi

if [[ "$SKIP_DRAFT" -eq 0 && -z "${DASHSCOPE_API_KEY:-}" && -z "${QWEN_API_KEY:-}" ]]; then
  fail "DASHSCOPE_API_KEY or QWEN_API_KEY is required for full draft proof. Re-run with --skip-draft for health-only local proof."
fi

export DREAM_CONFIG_FILE="$CONFIG_PATH"
export QWEN_BASE_URL="${QWEN_BASE_URL:-https://dashscope-intl.aliyuncs.com/compatible-mode/v1}"
export QWEN_MODEL="${QWEN_MODEL:-qwen3.7-plus}"
if [[ "$SKIP_DRAFT" -eq 1 && -z "${DASHSCOPE_API_KEY:-}" && -z "${QWEN_API_KEY:-}" ]]; then
  export DASHSCOPE_API_KEY="local-proof-placeholder"
fi
add_step "env" "pass" "DREAM_CONFIG_FILE, QWEN_BASE_URL, and QWEN_MODEL set"

if [[ "$BASE_URL" == "http://127.0.0.1:$PORT" || "$BASE_URL" == "http://localhost:$PORT" ]]; then
  "$PYTHON_BIN" -m uvicorn dream.api.app:app --host 127.0.0.1 --port "$PORT" >"$API_OUT" 2>"$API_ERR" &
  API_PID="$!"
  add_step "start_api" "pass" "pid=$API_PID; stdout=$API_OUT; stderr=$API_ERR"
else
  add_step "start_api" "skip" "using already-running API at $BASE_URL"
fi

deadline=$((SECONDS + STARTUP_TIMEOUT))
health_ok=0
while (( SECONDS < deadline )); do
  if [[ -n "${API_PID:-}" ]] && ! kill -0 "$API_PID" 2>/dev/null; then
    fail "Local API exited before becoming healthy. See $API_ERR"
  fi
  if health_output="$(check_health 2>>"$API_ERR")"; then
    printf '%s\n' "$health_output" > "$HEALTH_JSON"
    health_ok=1
    break
  else
    printf '%s\n' "$health_output" > "$HEALTH_JSON.last" || true
  fi
  sleep 2
done

if [[ "$health_ok" -ne 1 ]]; then
  fail "Local API did not return Qwen Cloud hackathon health proof at $BASE_URL/health."
fi
add_step "health_wait" "pass" "track=Track 1: MemoryAgent; provider=qwen-cloud; proof_file=deploy/alibaba/serverless-devs-runtime.yaml"

if "$PYTHON_BIN" -m pytest tests/test_api_health.py tests/test_qwen_cloud_provider.py >"$PYTEST_OUT" 2>"$PYTEST_ERR"; then
  add_step "pytest_smoke" "pass" "tests/test_api_health.py tests/test_qwen_cloud_provider.py"
else
  add_step "pytest_smoke" "fail" "stdout=$PYTEST_OUT; stderr=$PYTEST_ERR"
  fail "Pytest smoke failed. See $PYTEST_ERR"
fi

if [[ "$SKIP_DRAFT" -eq 1 ]]; then
  add_step "draft_proof" "skip" "skipped by --skip-draft"
else
  if run_draft_proof >"$DRAFT_JSON" 2>"$DRAFT_ERR"; then
    add_step "draft_proof" "pass" "markdown returned by /requirements/draft"
  else
    add_step "draft_proof" "fail" "stdout=$DRAFT_JSON; stderr=$DRAFT_ERR"
    fail "Draft proof failed. See $DRAFT_ERR"
  fi
fi

write_report "pass"
echo "Local proof passed. Report: $REPORT_MD"
echo "JSON: $REPORT_JSON"
