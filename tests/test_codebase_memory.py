# SPDX-License-Identifier: Apache-2.0

import shutil

from dream.audit.logger import AuditLogger
from dream.audit.repository import AuditRepository
from dream.codebase import (
    CodebaseIndexer,
    CodebaseIndexRepository,
    CodebaseRetriever,
    CodebaseScanner,
)
from dream.codebase.java_extractor import extract_java
from dream.core.paths import PROJECT_ROOT


def test_codebase_scanner_ignores_common_directories() -> None:
    repo_path = PROJECT_ROOT / "artifacts" / "scanner-ignore-test"
    if repo_path.exists():
        shutil.rmtree(repo_path)
    (repo_path / "src").mkdir(parents=True)
    (repo_path / "node_modules" / "ignored").mkdir(parents=True)
    (repo_path / "src" / "Keep.java").write_text("class Keep {}", encoding="utf-8")
    (repo_path / "node_modules" / "ignored" / "Skip.java").write_text(
        "class Skip {}", encoding="utf-8"
    )

    try:
        files = CodebaseScanner().scan(repo_path)
    finally:
        shutil.rmtree(repo_path)

    paths = {file_node.path for file_node in files}
    assert "src/Keep.java" in paths
    assert "node_modules/ignored/Skip.java" not in paths


def test_java_extractor_extracts_classes_methods_and_endpoints() -> None:
    content = """
@RestController
class JobExecutionController {
    @GetMapping("/{jobId}/status")
    public JobStatus getJobStatus(String jobId) {
        return JobStatus.RUNNING;
    }
}
"""

    symbols, _ = extract_java("JobExecutionController.java", content)

    assert any(
        symbol.name == "JobExecutionController" and symbol.kind == "class" for symbol in symbols
    )
    assert any(symbol.name == "getJobStatus" and symbol.kind == "endpoint" for symbol in symbols)


def test_codebase_indexer_writes_json_and_maps_tests(tmp_path) -> None:
    repository = CodebaseIndexRepository(tmp_path / "artifacts")
    audit_logger = AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite"))
    indexer = CodebaseIndexer(repository=repository, audit_logger=audit_logger)

    index = indexer.index(
        team_id="demo_team",
        repo_path="examples/java-demo-repo",
        repo_name="java-demo-repo",
    )

    index_path = repository.index_path("demo_team", "java-demo-repo")
    assert index_path.exists()
    assert any(file_node.path.endswith("JobExecutionService.java") for file_node in index.files)
    assert any(symbol.name == "JobExecutionService" for symbol in index.symbols)
    assert any(
        mapping.source_file.endswith("JobExecutionService.java")
        and mapping.test_file.endswith("JobExecutionServiceTest.java")
        for mapping in index.tests
    )


def test_codebase_retriever_finds_job_execution_service(tmp_path) -> None:
    repository = CodebaseIndexRepository(tmp_path / "artifacts")
    audit_logger = AuditLogger(repository=AuditRepository(tmp_path / "audit.sqlite"))
    CodebaseIndexer(repository=repository, audit_logger=audit_logger).index(
        team_id="demo_team",
        repo_path="examples/java-demo-repo",
        repo_name="java-demo-repo",
    )

    results = CodebaseRetriever(repository=repository).search(
        team_id="demo_team",
        repo_name="java-demo-repo",
        query="job execution",
        top_k=10,
    )

    assert any("JobExecutionService.java" in result.source_path for result in results)
