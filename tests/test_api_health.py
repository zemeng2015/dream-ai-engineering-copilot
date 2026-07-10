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
    assert payload["proof_file"] == "deploy/alibaba/serverless-devs-runtime.yaml"


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


def test_api_health_reflects_custom_runtime_proof_file(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / "dream.yaml"
    config_path.write_text(
        "mode: public-demo\nllm:\n  provider: qwen-cloud\n  model: qwen3.7-plus\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DREAM_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("DASHSCOPE_API_KEY", "qwen-demo-key")
    monkeypatch.setenv("ALIBABA_CLOUD_REGION", "cn-hangzhou")
    monkeypatch.setenv("ALIBABA_CLOUD_SERVICE", "Function Compute custom runtime")
    monkeypatch.setenv(
        "ALIBABA_CLOUD_PROOF_FILE", "deploy/alibaba/serverless-devs-runtime.yaml"
    )

    client = TestClient(create_app())

    response = client.get("/health")
    payload = response.json()

    assert response.status_code == 200
    assert payload["deployment_target"] == "Alibaba Cloud Function Compute custom runtime"
    assert payload["alibaba_cloud_region"] == "cn-hangzhou"
    assert payload["proof_file"] == "deploy/alibaba/serverless-devs-runtime.yaml"


def test_qwencloud_showcase_reports_static_evidence_without_live_backend(monkeypatch) -> None:
    monkeypatch.delenv("DREAM_CONFIG_FILE", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("ALIBABA_CLOUD_REGION", raising=False)
    monkeypatch.delenv("ALIBABA_CLOUD_SERVICE", raising=False)
    monkeypatch.delenv("QWEN_PUBLIC_DEMO_VIDEO_URL", raising=False)

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
    assert payload["benchmark"]["status"] == "ready"
    assert payload["benchmark"]["provider"] == "qwen-cloud"
    assert payload["benchmark"]["model"] == "qwen3.7-plus"
    assert payload["benchmark"]["case_count"] == 7
    assert payload["benchmark"]["baseline_score"] == 25.3
    assert payload["benchmark"]["dream_score"] == 48.7
    assert payload["benchmark"]["score_delta"] == 23.4
    assert payload["benchmark"]["dream_wins"] == 7
    assert payload["benchmark"]["exact_retrieval_recall_at_12"] == 0.356
    assert payload["benchmark"]["report_path"] == "docs/qwen-memory-ab-benchmark.md"
    assert payload["experience_benchmark"]["status"] == "ready"
    assert payload["experience_benchmark"]["provider"] == "qwen-cloud"
    assert payload["experience_benchmark"]["model"] == "qwen3.7-plus"
    assert payload["experience_benchmark"]["case_count"] == 24
    assert payload["experience_benchmark"]["decision_count"] == 37
    assert payload["experience_benchmark"]["passed_cases"] == 24
    assert payload["experience_benchmark"]["overall_score"] == 100.0
    assert payload["experience_benchmark"]["critical_memory_recall"] == 1.0
    assert payload["experience_benchmark"]["forbidden_memory_leak_rate"] == 0.0
    deployment_evidence = next(
        item
        for item in payload["evidence"]
        if item["name"] == "Alibaba Function Compute deployment"
    )
    assert len(deployment_evidence["proof_paths"]) == len(
        set(deployment_evidence["proof_paths"])
    )
    assert (
        "scripts/qwencloud-alibaba-runtime-release.ps1"
        in deployment_evidence["proof_paths"]
    )
    experience_evidence = next(
        item
        for item in payload["evidence"]
        if item["name"] == "Cross-session Qwen experience benchmark"
    )
    assert "examples/experience-benchmark/scenarios.yaml" in experience_evidence[
        "proof_paths"
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
    monkeypatch.delenv("QWEN_PUBLIC_DEMO_VIDEO_URL", raising=False)

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


def test_qwencloud_showcase_reaches_full_score_when_public_video_is_configured(
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
    monkeypatch.setenv("ALIBABA_CLOUD_SERVICE", "Function Compute custom runtime")
    monkeypatch.setenv("QWEN_PUBLIC_DEMO_VIDEO_URL", "https://youtu.be/ZdnO9mAulSs")

    payload = TestClient(create_app()).get("/qwencloud/showcase").json()

    assert payload["scorecard"]["weighted_current_evidence_ready"] == 100
    assert payload["scorecard"]["public_video_points"] == 15
    assert payload["scorecard"]["public_video_url"] == "https://youtu.be/ZdnO9mAulSs"
    assert payload["scorecard"]["missing_external_inputs"] == []


def test_qwencloud_showcase_accepts_custom_runtime_proof(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / "dream.yaml"
    config_path.write_text(
        "mode: public-demo\nllm:\n  provider: qwen-cloud\n  model: qwen3.7-plus\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DREAM_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("DASHSCOPE_API_KEY", "qwen-demo-key")
    monkeypatch.setenv("ALIBABA_CLOUD_REGION", "cn-hangzhou")
    monkeypatch.setenv("ALIBABA_CLOUD_SERVICE", "Function Compute custom runtime")
    monkeypatch.setenv(
        "ALIBABA_CLOUD_PROOF_FILE", "deploy/alibaba/serverless-devs-runtime.yaml"
    )

    client = TestClient(create_app())

    response = client.get("/qwencloud/showcase")
    payload = response.json()

    assert response.status_code == 200
    assert payload["runtime"]["qwen_cloud_ready"] is True
    assert payload["runtime"]["alibaba_runtime_ready"] is True
    assert payload["runtime"]["live_backend_ready"] is True
    assert payload["runtime"]["proof_file"] == "deploy/alibaba/serverless-devs-runtime.yaml"


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


def test_api_serves_same_origin_angular_app_without_shadowing_api(
    monkeypatch, tmp_path
) -> None:
    frontend_dist = tmp_path / "frontend"
    frontend_dist.mkdir()
    (frontend_dist / "index.html").write_text(
        "<html><body>DREAM judge app</body></html>", encoding="utf-8"
    )
    (frontend_dist / "main.js").write_text(
        "globalThis.dreamLoaded = true;", encoding="utf-8"
    )
    monkeypatch.setenv("DREAM_FRONTEND_DIST", str(frontend_dist))

    client = TestClient(create_app())

    health_response = client.get("/health")
    route_response = client.get("/hackathon-demo")
    asset_response = client.get("/main.js")

    assert health_response.status_code == 200
    assert health_response.json()["service"] == "dream-memoryagent-api"
    assert route_response.status_code == 200
    assert "DREAM judge app" in route_response.text
    assert asset_response.status_code == 200
    assert asset_response.text == "globalThis.dreamLoaded = true;"


def test_api_frontend_route_never_serves_files_outside_dist(monkeypatch, tmp_path) -> None:
    frontend_dist = tmp_path / "frontend"
    frontend_dist.mkdir()
    (frontend_dist / "index.html").write_text("DREAM index", encoding="utf-8")
    (tmp_path / "private.txt").write_text("must-not-leak", encoding="utf-8")
    monkeypatch.setenv("DREAM_FRONTEND_DIST", str(frontend_dist))

    client = TestClient(create_app())
    response = client.get("/%2E%2E/private.txt", follow_redirects=False)

    assert "must-not-leak" not in response.text
