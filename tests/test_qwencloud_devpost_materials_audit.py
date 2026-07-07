# SPDX-License-Identifier: Apache-2.0

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "qwencloud-devpost-materials-audit.ps1"
REPO_URL = "https://github.com/zemeng2015/dream-ai-engineering-copilot"
DEMO_URL = "https://youtu.be/dreamdemo123"
BACKEND_URL = "https://dream-qwencloud.example.com"


def _powershell_command() -> list[str]:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if not executable:
        pytest.skip("PowerShell is not available")

    command = [executable, "-NoProfile"]
    if os.name == "nt" and Path(executable).name.lower().startswith("powershell"):
        command += ["-ExecutionPolicy", "Bypass"]
    return command


def _check(report: dict, name: str) -> dict:
    return next(item for item in report["checks"] if item["name"] == name)


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _base_materials(tmp_path: Path, *, unsafe: bool = False) -> dict[str, Path]:
    output_dir = tmp_path / "qwencloud-proof"
    output_dir.mkdir()

    architecture = tmp_path / "architecture.png"
    screenshot = tmp_path / "alibaba.png"
    proof_video = tmp_path / "alibaba-proof.mp4"
    local_video = tmp_path / "demo.mp4"
    for path in [architecture, screenshot, proof_video, local_video]:
        path.write_bytes(b"fixture")

    demo_url = "<public-video-url>" if unsafe else DEMO_URL
    backend_url = "<deployed-backend-url>" if unsafe else BACKEND_URL
    description = (
        "TODO leak DASHSCOPE_API_KEY=dashscope_sk_testleakyvalue123"
        if unsafe
        else (
            "DREAM is a Qwen Cloud MemoryAgent for source-backed engineering "
            "intelligence on Alibaba Cloud. Track 1: MemoryAgent."
        )
    )

    packet = {
        "readyForDevpost": not unsafe,
        "project": {
            "title": "DREAM: Qwen Cloud MemoryAgent for Source-Backed Engineering Intelligence",
            "track": "Track 1: MemoryAgent",
            "repoUrl": REPO_URL,
            "demoVideoUrl": demo_url,
            "backendUrl": backend_url,
            "blogPostUrl": "",
        },
        "uploadAssets": {
            "architectureDiagram": str(architecture),
            "alibabaDeploymentScreenshot": str(screenshot),
            "alibabaDeploymentProofVideo": str(proof_video),
            "localDemoVideo": str(local_video),
        },
        "devpostAdditionalInfo": {
            "selectedTrack": "Track 1: MemoryAgent",
            "repositoryUrl": REPO_URL,
            "alibabaProofCodeFile": f"{REPO_URL}/blob/main/deploy/alibaba/serverless-devs.yaml",
            "aiToolsUsed": "Qwen Cloud, Alibaba Cloud, and local audit automation.",
            "learningLevel": "Significant",
        },
        "links": {
            "testingAndRightsNotes": (
                f"{REPO_URL}/blob/main/docs/qwencloud-testing-and-rights-notes.md"
            ),
            "deploymentProof": f"{REPO_URL}/blob/main/deploy/alibaba/serverless-devs.yaml",
        },
        "checks": [],
    }

    fields = [
        {
            "elementId": "software_description",
            "label": "About the project",
            "value": description,
            "inputKind": "textarea",
            "required": True,
            "safeForNonLegalDraftSave": True,
        },
        {
            "elementId": "software_tag_list",
            "label": "Built with",
            "value": "Qwen Cloud, Alibaba Cloud Function Compute, FastAPI, Angular",
            "inputKind": "tag_list",
            "required": True,
            "safeForNonLegalDraftSave": True,
        },
        {
            "elementId": "software_urls_attributes_0_url",
            "label": "Try it out",
            "value": backend_url,
            "inputKind": "url",
            "required": True,
            "safeForNonLegalDraftSave": True,
        },
        {
            "elementId": "software_video_url",
            "label": "Video demo link",
            "value": demo_url,
            "inputKind": "url",
            "required": True,
            "safeForNonLegalDraftSave": True,
        },
        {
            "elementId": (
                "participants_submission_requirements_submission_field_values_"
                "attributes_6_value"
            ),
            "label": "Selected Track",
            "value": "Track 1: MemoryAgent",
            "inputKind": "select",
            "required": True,
            "safeForNonLegalDraftSave": True,
        },
        {
            "elementId": (
                "participants_submission_requirements_submission_field_values_"
                "attributes_7_value"
            ),
            "label": "Code repository URL",
            "value": REPO_URL,
            "inputKind": "text",
            "required": True,
            "safeForNonLegalDraftSave": True,
        },
        {
            "elementId": (
                "participants_submission_requirements_submission_field_values_"
                "attributes_8_value"
            ),
            "label": "Alibaba deployment proof code URL",
            "value": f"{REPO_URL}/blob/main/deploy/alibaba/serverless-devs.yaml",
            "inputKind": "text",
            "required": True,
            "safeForNonLegalDraftSave": True,
        },
    ]
    fields += [
        {
            "elementId": f"legal_{index}",
            "label": "Legal attestation",
            "value": "",
            "inputKind": "checkbox",
            "required": True,
            "safeForNonLegalDraftSave": False,
        }
        for index in range(3)
    ]

    payload = {
        "status": "DRAFT" if unsafe else "READY",
        "readyForPublicTextAutofill": not unsafe,
        "readyForFinalDevpostFields": not unsafe,
        "externalWriteRequiresActionTimeConfirmation": True,
        "repoUrl": REPO_URL,
        "demoVideoUrl": demo_url,
        "backendUrl": backend_url,
        "uploadAssets": {
            "architectureDiagram": {
                "path": str(architecture),
                "exists": True,
                "size": architecture.stat().st_size,
            },
            "alibabaDeploymentScreenshot": {
                "path": str(screenshot),
                "exists": True,
                "size": screenshot.stat().st_size,
            },
        },
        "fields": fields,
        "checks": [],
        "requiredFailures": [] if not unsafe else ["demo_video_url_devpost_rules_platform"],
    }

    handoff = {
        "status": "DRAFT" if unsafe else "READY",
        "readyForDevpostFinalSubmit": not unsafe,
        "repoUrl": REPO_URL,
        "demoVideoUrl": demo_url,
        "backendUrl": backend_url,
        "blockers": [] if not unsafe else ["public_demo_video_url", "deployed_backend_url"],
        "uploadItems": [
            {"name": "architecture_diagram", "path": str(architecture), "exists": True},
            {"name": "alibaba_deployment_screenshot", "path": str(screenshot), "exists": True},
            {"name": "alibaba_backend_proof_recording", "path": str(proof_video), "exists": True},
        ],
        "copyFields": {
            "projectTitle": (
                "DREAM: Qwen Cloud MemoryAgent for Source-Backed Engineering "
                "Intelligence"
            ),
            "track": "Track 1: MemoryAgent",
            "shortPitch": (
                "DREAM uses Qwen Cloud and Alibaba Cloud for source-backed "
                "MemoryAgent workflows."
            ),
            "description": description,
            "builtWith": "Qwen Cloud, Alibaba Cloud Function Compute, FastAPI, Angular",
            "repoUrl": REPO_URL,
            "demoVideoUrl": demo_url,
            "backendUrl": backend_url,
            "deploymentProofCodeFile": f"{REPO_URL}/blob/main/deploy/alibaba/serverless-devs.yaml",
        },
        "actionTimeConfirmations": [
            "Confirm age.",
            "Confirm jurisdiction.",
            "Confirm sponsor eligibility.",
            "Confirm official rules.",
        ],
    }

    autofill = {
        "readyForAutofillSnippet": True,
        "externalWriteRequiresActionTimeConfirmation": True,
        "safeFieldCount": 7,
        "excludedFieldCount": 3,
        "warnings": [
            (
                "This snippet does not click Save, upload files, check legal "
                "attestations, or final-submit."
            ),
        ],
        "safeFields": fields[:7],
        "excludedFields": fields[7:],
    }

    return {
        "output_dir": output_dir,
        "packet": _write_json(output_dir / "packet.json", packet),
        "payload": _write_json(output_dir / "payload.json", payload),
        "handoff": _write_json(output_dir / "handoff.json", handoff),
        "autofill": _write_json(output_dir / "autofill.json", autofill),
    }


def test_devpost_materials_audit_accepts_ready_materials(tmp_path: Path) -> None:
    paths = _base_materials(tmp_path)

    result = subprocess.run(
        _powershell_command()
        + [
            "-File",
            str(SCRIPT),
            "-OutputDir",
            str(paths["output_dir"]),
            "-PacketJson",
            str(paths["packet"]),
            "-PayloadJson",
            str(paths["payload"]),
            "-HandoffJson",
            str(paths["handoff"]),
            "-AutofillJson",
            str(paths["autofill"]),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(
        sorted(paths["output_dir"].glob("devpost-materials-audit-*.json"))[0].read_text(
            encoding="utf-8-sig"
        )
    )

    assert report["status"] == "READY"
    assert report["readyForDevpostMaterials"] is True
    assert report["requiredFailures"] == []
    assert _check(report, "placeholder_free_public_copy")["ok"] is True
    assert _check(report, "secret_free_public_copy")["ok"] is True
    assert _check(report, "demo_video_url_devpost_rules_platform")["ok"] is True


def test_devpost_materials_audit_rejects_placeholders_and_secret_like_values(
    tmp_path: Path,
) -> None:
    paths = _base_materials(tmp_path, unsafe=True)

    result = subprocess.run(
        _powershell_command()
        + [
            "-File",
            str(SCRIPT),
            "-OutputDir",
            str(paths["output_dir"]),
            "-PacketJson",
            str(paths["packet"]),
            "-PayloadJson",
            str(paths["payload"]),
            "-HandoffJson",
            str(paths["handoff"]),
            "-AutofillJson",
            str(paths["autofill"]),
            "-AllowDraft",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    raw_report = sorted(paths["output_dir"].glob("devpost-materials-audit-*.json"))[
        0
    ].read_text(encoding="utf-8-sig")
    report = json.loads(raw_report)

    assert report["status"] == "DRAFT"
    assert report["readyForDevpostMaterials"] is False
    assert _check(report, "placeholder_free_public_copy")["ok"] is False
    assert _check(report, "secret_free_public_copy")["ok"] is False
    assert _check(report, "demo_video_url_devpost_rules_platform")["ok"] is False
    assert _check(report, "backend_url_present")["ok"] is False
    assert "dashscope_sk_testleakyvalue123" not in raw_report


def test_devpost_materials_audit_registered_in_final_flow() -> None:
    script_name = "scripts/qwencloud-devpost-materials-audit.ps1"
    assert SCRIPT.exists()

    final_readiness = (ROOT / "scripts" / "qwencloud-final-readiness.ps1").read_text(
        encoding="utf-8-sig"
    )
    final_bundle = (ROOT / "scripts" / "qwencloud-final-upload-bundle.ps1").read_text(
        encoding="utf-8-sig"
    )
    final_action_board = (
        ROOT / "scripts" / "qwencloud-final-action-board.ps1"
    ).read_text(encoding="utf-8-sig")
    finalizer = (ROOT / "scripts" / "qwencloud-finalize-after-urls.ps1").read_text(
        encoding="utf-8-sig"
    )
    final_sprint = (ROOT / "scripts" / "qwencloud-final-sprint.ps1").read_text(
        encoding="utf-8-sig"
    )

    assert script_name in final_readiness
    assert "Invoke-DevpostMaterialsAudit" in final_readiness
    assert "devpost_materials_audit_ready" in final_readiness
    assert script_name in final_bundle
    assert "Invoke-DevpostMaterialsAudit" in final_bundle
    assert "devpost_materials_audit_ready" in final_bundle
    assert "devpost_materials_audit_markdown" in final_bundle
    assert "devpost_materials_audit_json" in final_bundle
    assert "devpost-materials-audit" in final_action_board
    assert "devpostMaterialsAuditReady" in final_action_board
    assert "Clear Devpost materials audit" in final_action_board
    assert script_name in finalizer
    assert 'Invoke-Step -Name "devpost-materials-audit"' in finalizer
    assert "devpostMaterialsAuditJson" in finalizer
    assert "devpost-materials-ready" in finalizer
    assert "Devpost materials audit ready" in finalizer
    assert "devpostMaterialsAuditReady" in final_sprint
    assert "devpostMaterialsAuditJson" in final_sprint
    assert "Clear Devpost materials audit" in final_sprint
