# SPDX-License-Identifier: Apache-2.0

import pytest

from dream.memory import EngineeringMemoryRetriever


@pytest.mark.parametrize(
    ("query", "expected_reference"),
    [
        ("Reject invalid task configuration before execution", "INC-106"),
        ("Recover a workflow after partial task completion", "INC-105"),
        ("Keep jobs reproducible with workflow versioning", "DFP-105"),
        ("Preview very large outputs with pagination", "DFP-103"),
    ],
)
def test_balanced_memory_ranking_tracks_the_request_domain(
    query: str, expected_reference: str
) -> None:
    evidence = EngineeringMemoryRetriever().search(
        team_id="demo_team",
        repo_name="dfp-demo-repo",
        query=query,
        top_k=12,
    )

    evidence_text = "\n".join(
        f"{item.source_path}\n{item.title}\n{item.excerpt}" for item in evidence
    )
    assert expected_reference in evidence_text
