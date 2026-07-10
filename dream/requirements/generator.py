# SPDX-License-Identifier: Apache-2.0

from uuid import uuid4

from dream.audit.logger import AuditLogger
from dream.core.paths import display_path, resolve_artifact_path
from dream.dlp import ensure_dlp_guarded_provider
from dream.knowledge import Chunker, KnowledgePackLoader, MarkdownDocumentLoader, SimpleRetriever
from dream.llm import BaseLLMProvider, LLMRequest, MockLLMProvider
from dream.requirements.models import RequirementDraftRequest, RequirementDraftResponse
from dream.requirements.templates import render_requirement_draft


class RequirementDraftGenerator:
    def __init__(
        self,
        *,
        pack_loader: KnowledgePackLoader | None = None,
        doc_loader: MarkdownDocumentLoader | None = None,
        chunker: Chunker | None = None,
        llm_provider: BaseLLMProvider | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.pack_loader = pack_loader or KnowledgePackLoader()
        self.doc_loader = doc_loader or MarkdownDocumentLoader()
        self.chunker = chunker or Chunker()
        self.llm_provider = ensure_dlp_guarded_provider(llm_provider or MockLLMProvider())
        self.audit_logger = audit_logger or AuditLogger()

    def draft(self, request: RequirementDraftRequest) -> RequirementDraftResponse:
        run_id = f"req-{uuid4().hex[:12]}"
        pack = self.pack_loader.load(request.team_id)
        pack_dir = self.pack_loader.pack_dir(pack.team_id)
        documents = self.doc_loader.load_for_pack(pack, pack_dir)
        chunks = self.chunker.chunk_all(documents)
        retrieved = SimpleRetriever(chunks).search(
            request.rough_business_request,
            team_id=request.team_id,
            app=request.app,
            component=request.component,
            top_k=request.top_k,
        )
        warnings = []
        if not retrieved and (request.app or request.component):
            retrieved = SimpleRetriever(chunks).search(
                request.rough_business_request,
                team_id=request.team_id,
                top_k=request.top_k,
            )
            if retrieved:
                warnings.append(
                    "No chunks matched the app/component filters; retried with team-level context."
                )
        if not retrieved:
            warnings.append("No matching knowledge chunks were retrieved.")
        prompt = render_requirement_draft(request, retrieved)
        llm_response = self.llm_provider.complete(
            LLMRequest(
                prompt=prompt,
                metadata={
                    "team_id": request.team_id,
                    "resource_id": run_id,
                    "use_case": "requirement_draft",
                    "classification": "internal",
                },
            )
        )
        markdown = llm_response.text
        output_path = resolve_artifact_path(f"requirement-draft-{run_id}.md")
        output_path.write_text(markdown, encoding="utf-8")
        sources_used = sorted({chunk.source_path for chunk in retrieved})
        self.audit_logger.log_generation(
            run_id=run_id,
            use_case="requirement_draft",
            team_id=request.team_id,
            input_payload=request.model_dump(),
            retrieved_source_paths=sources_used,
            model_provider=llm_response.provider_name,
            model_name=llm_response.model_name,
            output_path=display_path(output_path),
            status="success",
            warnings=warnings,
        )
        return RequirementDraftResponse(
            run_id=run_id,
            markdown=markdown,
            sources_used=sources_used,
            warnings=warnings,
        )
