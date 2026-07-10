# SPDX-License-Identifier: Apache-2.0

from dream.core.paths import KNOWLEDGE_PACKS_DIR
from dream.knowledge import Chunker, MarkdownDocumentLoader, SimpleRetriever
from dream.knowledge.pack_loader import KnowledgePackLoader


def test_keyword_retrieval_returns_job_execution_chunks() -> None:
    pack = KnowledgePackLoader().load("demo_team")
    documents = MarkdownDocumentLoader().load_for_pack(pack, KNOWLEDGE_PACKS_DIR / "demo_team")
    chunks = Chunker().chunk_all(documents)

    results = SimpleRetriever(chunks).search(
        "job execution failure",
        team_id="demo_team",
        top_k=8,
    )

    assert results
    assert any(
        "Job Execution" in chunk.title
        or "Execution" in chunk.title
        or "Execution" in chunk.content
        for chunk in results
    )
    assert results == SimpleRetriever(chunks).search(
        "job execution failure",
        team_id="demo_team",
        top_k=8,
    )


def test_dfp_dataset_searches_return_expected_memory() -> None:
    pack = KnowledgePackLoader().load("demo_team")
    documents = MarkdownDocumentLoader().load_for_pack(pack, KNOWLEDGE_PACKS_DIR / "demo_team")
    chunks = Chunker().chunk_all(documents)
    retriever = SimpleRetriever(chunks)

    execution_results = retriever.search("execution status", team_id="demo_team", top_k=8)
    duplicate_results = retriever.search("duplicate output", team_id="demo_team", top_k=8)
    partial_results = retriever.search("partial completion", team_id="demo_team", top_k=8)

    assert any(
        "Status Tracking" in chunk.title or "Execution Status" in chunk.title
        for chunk in execution_results
    )
    assert any(
        "Duplicate output" in chunk.content or "Output Collection" in chunk.title
        for chunk in duplicate_results
    )
    assert any(
        "Partial completion" in chunk.content or "Partial" in chunk.title
        for chunk in partial_results
    )


def test_scored_search_preserves_domain_relevance_over_common_words() -> None:
    pack = KnowledgePackLoader().load("demo_team")
    documents = MarkdownDocumentLoader().load_for_pack(
        pack, KNOWLEDGE_PACKS_DIR / "demo_team"
    )
    chunks = Chunker().chunk_all(documents)

    results = SimpleRetriever(chunks).search_scored(
        "Reject invalid task configuration before execution and show validation errors to users",
        team_id="demo_team",
        top_k=5,
    )

    assert results
    assert any("INC-106" in chunk.source_path for _, chunk in results[:3])
    assert results == sorted(results, key=lambda item: -item[0])
