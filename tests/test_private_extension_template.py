# SPDX-License-Identifier: Apache-2.0

from dream.core.paths import PROJECT_ROOT


def test_private_extension_template_files_exist() -> None:
    root = PROJECT_ROOT / "examples" / "private-extension-template"
    expected = [
        "README.md",
        "pyproject.toml",
        ".gitignore",
        "config/dream.private.example.yaml",
        "private_plugins/__init__.py",
        "private_plugins/custom_llm_provider.py",
        "private_plugins/custom_redaction_provider.py",
        "private_plugins/custom_prompt_policy.py",
        "knowledge_packs/team_template/team.yaml",
        "knowledge_packs/team_template/docs/architecture/sample-architecture.md",
        "knowledge_packs/team_template/docs/runbooks/sample-runbook.md",
        "knowledge_packs/team_template/docs/testing/sample-test-guidelines.md",
        "knowledge_packs/team_template/docs/pr-review/sample-review-checklist.md",
    ]

    for relative_path in expected:
        assert (root / relative_path).exists(), relative_path


def test_private_extension_template_uses_only_fake_names() -> None:
    root = PROJECT_ROOT / "examples" / "private-extension-template"
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in root.rglob("*")
        if path.is_file()
    )

    assert "PrivateDemo" in combined
    assert "TeamTemplate" in combined
    assert "ExampleLLM" in combined
