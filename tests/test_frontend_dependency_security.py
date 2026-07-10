# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND = PROJECT_ROOT / "frontend"


def test_frontend_uses_supported_angular_and_lower_dependency_builders() -> None:
    package = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))
    workspace = json.loads((FRONTEND / "angular.json").read_text(encoding="utf-8"))

    angular_packages = [
        "@angular/common",
        "@angular/compiler",
        "@angular/core",
        "@angular/forms",
        "@angular/platform-browser",
        "@angular/platform-browser-dynamic",
        "@angular/router",
    ]
    assert all(package["dependencies"][name].startswith("^21.") for name in angular_packages)
    assert package["devDependencies"]["@angular/compiler-cli"].startswith("^21.")
    assert package["devDependencies"]["@angular/cli"].startswith("^21.")
    assert package["devDependencies"]["@angular/build"].startswith("^21.")
    assert "@angular-devkit/build-angular" not in package["devDependencies"]
    assert package["engines"]["node"] == "^20.19.0 || ^22.12.0 || ^24.0.0"

    targets = workspace["projects"]["frontend"]["architect"]
    assert targets["build"]["builder"] == "@angular/build:application"
    assert targets["serve"]["builder"] == "@angular/build:dev-server"
    assert targets["extract-i18n"]["builder"] == "@angular/build:extract-i18n"
    assert targets["test"]["builder"] == "@angular/build:karma"


def test_ci_enforces_frontend_audit_build_and_browser_tests() -> None:
    workflow_path = PROJECT_ROOT / ".github/workflows/ci.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    frontend_job = workflow["jobs"]["frontend"]
    commands = [step.get("run", "") for step in frontend_job["steps"]]

    assert frontend_job["defaults"]["run"]["working-directory"] == "frontend"
    assert "npm ci" in commands
    assert "npm audit --omit=dev" in commands
    assert "npm audit" in commands
    assert "npm run build" in commands
    assert "npm test -- --watch=false --browsers=ChromeHeadless" in commands
