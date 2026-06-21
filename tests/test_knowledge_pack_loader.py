# SPDX-License-Identifier: Apache-2.0

from dream.knowledge.pack_loader import KnowledgePackLoader


def test_load_demo_team_knowledge_pack() -> None:
    loader = KnowledgePackLoader()

    pack = loader.load("demo_team")

    assert pack.team_id == "demo_team"
    assert pack.team_name == "Demo Forecast Team"
    assert "ForecastDemo" in pack.applications
    assert "BatchJobDemo" in pack.applications
    assert "OutputPreviewDemo" in pack.applications
    assert "dfp-demo-repo" in pack.repositories
    assert "docs/domain" in pack.document_paths
    assert "docs/incidents" in pack.document_paths
    assert "docs/historical-jira" in pack.document_paths
    assert "docs/concepts" in pack.document_paths
    assert "demo_team" in loader.list_team_ids()
