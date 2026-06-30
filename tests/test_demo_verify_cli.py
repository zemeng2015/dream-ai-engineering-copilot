# SPDX-License-Identifier: Apache-2.0

from typer.testing import CliRunner

from dream.cli.main import app


def test_demo_verify_command(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DREAM_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("DREAM_AUDIT_DB_PATH", str(tmp_path / "dream.sqlite"))
    runner = CliRunner()

    result = runner.invoke(app, ["demo", "verify"])

    assert result.exit_code == 0, result.output
    assert "DREAM Demo Verification: PASS" in result.output
