# SPDX-License-Identifier: Apache-2.0

from dream.core.paths import KNOWLEDGE_PACKS_DIR
from dream.knowledge.chunker import Chunker
from dream.knowledge.markdown_loader import MarkdownDocumentLoader
from dream.knowledge.pack_loader import KnowledgePackLoader


def test_load_markdown_documents_for_pack() -> None:
    pack = KnowledgePackLoader().load("demo_team")
    documents = MarkdownDocumentLoader().load_for_pack(pack, KNOWLEDGE_PACKS_DIR / "demo_team")

    titles = {document.title for document in documents}

    assert "Job Execution Lifecycle" in titles
    assert "Status Tracking Design" in titles
    assert any("INC-103-status-stuck-running.md" in document.source_path for document in documents)
    assert "Unit Test Guidelines" in titles
    assert all(document.metadata["team_id"] == "demo_team" for document in documents)
    assert any(document.metadata["doc_type"] == "domain" for document in documents)
    assert any(document.metadata["doc_type"] == "incident" for document in documents)
    assert any(document.metadata["app"] == "ForecastDemo" for document in documents)


def test_chunking_markdown_by_heading() -> None:
    pack = KnowledgePackLoader().load("demo_team")
    documents = MarkdownDocumentLoader().load_for_pack(pack, KNOWLEDGE_PACKS_DIR / "demo_team")
    job_doc = next(document for document in documents if document.title == "Status Tracking Design")

    chunks = Chunker().chunk(job_doc)

    assert len(chunks) >= 3
    assert {chunk.title for chunk in chunks} >= {
        "Status Tracking Design",
        "Key Behaviors",
        "Failure Modes",
    }
