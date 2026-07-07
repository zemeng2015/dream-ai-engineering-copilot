# SPDX-License-Identifier: Apache-2.0

from fastapi.testclient import TestClient

from dream.api.app import create_app


def test_api_health_endpoint(monkeypatch) -> None:
    monkeypatch.delenv("DREAM_CONFIG_FILE", raising=False)
    monkeypatch.delenv("DREAM_ARTIFACT_ROOT", raising=False)
    monkeypatch.delenv("ALIBABA_CLOUD_REGION", raising=False)
    monkeypatch.delenv("ALIBABA_CLOUD_SERVICE", raising=False)

    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "dream-memoryagent-api"
    assert payload["track"] == "Track 1: MemoryAgent"
    assert payload["llm_provider"] == "mock"
    assert payload["proof_file"] == "deploy/alibaba/serverless-devs.yaml"


def test_api_health_reflects_alibaba_deployment_when_env_set(
    monkeypatch, tmp_path
) -> None:
    # set qwen config with explicit env flag; local execution still returns mock mode fields
    config_path = tmp_path / "dream.yaml"
    config_path.write_text(
        "mode: public-demo\nllm:\n  provider: qwen-cloud\n  model: qwen3.7-plus\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DREAM_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("DASHSCOPE_API_KEY", "qwen-demo-key")
    monkeypatch.setenv("ALIBABA_CLOUD_REGION", "ap-southeast-1")
    monkeypatch.setenv("ALIBABA_CLOUD_SERVICE", "Function Compute custom container")

    client = TestClient(create_app())

    response = client.get("/health")
    payload = response.json()

    assert response.status_code == 200
    assert payload["deployment_target"] == "Alibaba Cloud Function Compute custom container"
    assert payload["alibaba_cloud_region"] == "ap-southeast-1"
    assert payload["alibaba_cloud_service"] == "Function Compute custom container"


def test_qwencloud_showcase_reports_static_evidence_without_live_backend(monkeypatch) -> None:
    monkeypatch.delenv("DREAM_CONFIG_FILE", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("ALIBABA_CLOUD_REGION", raising=False)
    monkeypatch.delenv("ALIBABA_CLOUD_SERVICE", raising=False)

    client = TestClient(create_app())

    response = client.get("/qwencloud/showcase")
    payload = response.json()

    assert response.status_code == 200
    assert payload["project_title"].startswith("DREAM: Qwen Cloud MemoryAgent")
    assert payload["track"] == "Track 1: MemoryAgent"
    assert payload["runtime"]["llm_provider"] == "mock"
    assert payload["runtime"]["qwen_cloud_ready"] is False
    assert payload["runtime"]["alibaba_runtime_ready"] is False
    assert payload["runtime"]["live_backend_ready"] is False
    assert payload["scorecard"]["weighted_current_evidence_ready"] == 55
    assert payload["scorecard"]["weighted_static_evidence_ready"] == 100
    assert payload["scorecard"]["missing_external_inputs"] == [
        "deployed_backend_url",
        "public_demo_video_url",
    ]
    assert [step["route"] for step in payload["judge_flow"]] == [
        "/memory",
        "/requirements",
        "/context/case_async_status",
        "/codebase",
        "/audit",
    ]
    assert "DASHSCOPE_API_KEY" not in str(payload)


def test_qwencloud_showcase_upgrades_when_qwen_alibaba_runtime_is_configured(
    monkeypatch, tmp_path
) -> None:
    config_path = tmp_path / "dream.yaml"
    config_path.write_text(
        "mode: public-demo\nllm:\n  provider: qwen-cloud\n  model: qwen3.7-plus\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DREAM_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("DASHSCOPE_API_KEY", "qwen-demo-key")
    monkeypatch.setenv("ALIBABA_CLOUD_REGION", "ap-southeast-1")
    monkeypatch.setenv("ALIBABA_CLOUD_SERVICE", "Function Compute custom container")

    client = TestClient(create_app())

    response = client.get("/qwencloud/showcase")
    payload = response.json()

    assert response.status_code == 200
    assert payload["runtime"]["llm_provider"] == "qwen-cloud"
    assert payload["runtime"]["qwen_cloud_ready"] is True
    assert payload["runtime"]["alibaba_runtime_ready"] is True
    assert payload["runtime"]["live_backend_ready"] is True
    assert payload["scorecard"]["weighted_current_evidence_ready"] == 85
    assert payload["scorecard"]["live_backend_points"] == 30
    assert payload["scorecard"]["missing_external_inputs"] == ["public_demo_video_url"]


def test_api_health_cors_allows_hackathon_demo_fallback_port(monkeypatch) -> None:
    monkeypatch.delenv("DREAM_CORS_ORIGINS", raising=False)

    client = TestClient(create_app())

    response = client.options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:4310",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:4310"


def test_api_cors_allows_configured_frontend_origin(monkeypatch) -> None:
    monkeypatch.setenv("DREAM_CORS_ORIGINS", "https://demo.example.com")

    client = TestClient(create_app())

    response = client.options(
        "/health",
        headers={
            "Origin": "https://demo.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://demo.example.com"
