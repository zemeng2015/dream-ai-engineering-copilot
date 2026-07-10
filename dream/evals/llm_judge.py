# SPDX-License-Identifier: Apache-2.0

import hashlib
import json
from time import perf_counter
from typing import Any

from dream.dlp import ensure_dlp_guarded_provider
from dream.evals.models import EvaluationScorecard, LLMJudgeResult
from dream.llm import BaseLLMProvider, LLMRequest

PROMPT_VERSION = "llm-judge-v1"
MAX_MARKDOWN_CHARS = 12000


class LLMJudgeRunner:
    def judge(
        self,
        *,
        provider: BaseLLMProvider,
        scorecard: EvaluationScorecard,
        markdown: str,
        sources: list[str],
    ) -> LLMJudgeResult:
        provider = ensure_dlp_guarded_provider(provider)
        prompt = self._prompt(scorecard=scorecard, markdown=markdown, sources=sources)
        input_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        started_at = perf_counter()
        try:
            response = provider.complete(
                LLMRequest(
                    prompt=prompt,
                    metadata={
                        "use_case": "llm_judge_eval",
                        "target_type": scorecard.target_type,
                        "evaluation_id": scorecard.evaluation_id,
                        "resource_id": scorecard.evaluation_id,
                        "team_id": scorecard.team_id or "_unknown",
                        "prompt_version": PROMPT_VERSION,
                    },
                )
            )
            duration_ms = round((perf_counter() - started_at) * 1000)
            parsed = _parse_json_object(response.text)
            _validate_judge_payload(parsed)
            return LLMJudgeResult(
                status="completed",
                provider=response.provider_name,
                model=response.model_name,
                prompt_version=PROMPT_VERSION,
                input_hash=input_hash,
                duration_ms=duration_ms,
                readiness=_string_or_none(parsed.get("readiness")),
                confidence=_confidence(parsed.get("confidence")),
                summary=_string_or_none(parsed.get("summary")),
                risks=_string_list(parsed.get("risks")),
                missing_evidence=_string_list(parsed.get("missing_evidence")),
                recommendations=_string_list(parsed.get("recommendations")),
                raw_response=_truncate(response.text),
                token_usage=response.token_usage,
            )
        except Exception as exc:  # noqa: BLE001 - judge must not break deterministic eval.
            duration_ms = round((perf_counter() - started_at) * 1000)
            return LLMJudgeResult(
                status="failed",
                provider=getattr(provider, "provider_name", None),
                model=getattr(provider, "model_name", None),
                prompt_version=PROMPT_VERSION,
                input_hash=input_hash,
                duration_ms=duration_ms,
                warning=f"LLM judge failed: {exc}",
            )

    def _prompt(
        self,
        *,
        scorecard: EvaluationScorecard,
        markdown: str,
        sources: list[str],
    ) -> str:
        payload = {
            "target_type": scorecard.target_type,
            "target_id": scorecard.target_id,
            "case_id": scorecard.case_id,
            "deterministic_score": scorecard.overall_score,
            "deterministic_grade": scorecard.grade,
            "deterministic_pass_status": scorecard.pass_status,
            "dimensions": [
                {
                    "name": dimension.name,
                    "score": dimension.score,
                    "passed": dimension.passed,
                    "missing_items": dimension.missing_items,
                    "recommendations": dimension.recommendations,
                }
                for dimension in scorecard.dimensions
            ],
            "missing_critical_items": scorecard.missing_critical_items,
            "hallucination_warnings": scorecard.hallucination_warnings,
            "source_coverage": scorecard.source_coverage,
            "sources": sources,
            "artifact_markdown": markdown[:MAX_MARKDOWN_CHARS],
        }
        return (
            "You are an LLM judge for DREAM engineering workflow output. "
            "Review the generated artifact against the deterministic scorecard and cited sources. "
            "Do not invent evidence. Return only a JSON object with these fields: "
            "summary string, readiness one of ready|needs_review|blocked, "
            "confidence number from 0 to 1, "
            "risks string array, missing_evidence string array, recommendations string array.\n\n"
            f"Evaluation payload:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )


def _parse_json_object(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("LLM judge response did not include a JSON object.") from None
        parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("LLM judge response JSON was not an object.")
    return parsed


def _validate_judge_payload(parsed: dict[str, Any]) -> None:
    required_keys = {
        "summary",
        "readiness",
        "confidence",
        "risks",
        "missing_evidence",
        "recommendations",
    }
    if not required_keys.intersection(parsed):
        raise ValueError("LLM judge response did not include judge assessment fields.")


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _confidence(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, round(confidence, 2)))


def _truncate(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."
