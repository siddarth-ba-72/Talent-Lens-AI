from __future__ import annotations

import logging
from typing import Any, Optional

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

from app.config import Settings
from app.models.jd_models import ParsedJdModel
from app.prompts.json_response import parse_json_object
from app.prompts.templates import build_generate_queries_prompts, build_parse_jd_prompts
from app.providers.base import LlmProvider
from app.services.jd_parser_core import parse_jd_heuristic


logger = logging.getLogger(__name__)


class GeminiProvider(LlmProvider):
    def __init__(self, settings: Settings):
        self._settings = settings
        self._enabled = bool(settings.gemini_api_key)
        if self._enabled:
            genai.configure(api_key=settings.gemini_api_key)

    @property
    def name(self) -> str:
        return "gemini"

    def parse_jd(self, jd_text: str) -> ParsedJdModel:
        system_prompt, user_prompt = build_parse_jd_prompts(jd_text)
        _log_prompt_preview(self._settings, self.name, "parse_jd", system_prompt, user_prompt)

        if self._enabled:
            try:
                payload = self._generate_json(system_prompt, user_prompt)
                return ParsedJdModel.model_validate(payload)
            except Exception as exc:
                logger.warning("Gemini parse_jd failed, using heuristic fallback: %s", exc)

        return parse_jd_heuristic(jd_text)

    def generate_queries(self, parsed_jd: ParsedJdModel, platforms: list[str]) -> dict[str, list[str]]:
        system_prompt, user_prompt = build_generate_queries_prompts(parsed_jd, platforms)
        _log_prompt_preview(self._settings, self.name, "generate_queries", system_prompt, user_prompt)

        if self._enabled:
            try:
                payload = self._generate_json(system_prompt, user_prompt)
                raw_queries = payload.get("queriesByPlatform")
                normalized = _normalize_queries(raw_queries, platforms)
                if normalized:
                    return normalized
            except Exception as exc:
                logger.warning("Gemini generate_queries failed, using fallback. Cause: %s",
                               exc.__cause__ or exc, exc_info=False)

        return _fallback_generate_queries(parsed_jd, platforms)

    def _generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        attempts = max(1, self._settings.llm_max_retries)
        last_error: Optional[Exception] = None

        for attempt in range(1, attempts + 1):
            try:
                model = genai.GenerativeModel(
                    model_name=self._settings.gemini_model,
                    system_instruction=system_prompt,
                )
                response = model.generate_content(
                    user_prompt,
                    generation_config={
                        "temperature": 0,
                    },
                )
                response_text = (getattr(response, "text", None) or "").strip()
                return parse_json_object(response_text)
            except ResourceExhausted as exc:
                # Quota exceeded — retrying immediately won't help, fail fast
                logger.warning(
                    "Gemini quota exhausted (attempt %d/%d), skipping retries: %s",
                    attempt, attempts, exc,
                )
                raise RuntimeError("Gemini quota exhausted") from exc
            except Exception as exc:
                logger.warning("Gemini attempt %d/%d failed: %s: %s",
                               attempt, attempts, type(exc).__name__, exc)
                last_error = exc

        raise RuntimeError(f"Gemini request failed after {attempts} retries") from last_error


def _fallback_generate_queries(parsed_jd: ParsedJdModel, platforms: list[str]) -> dict[str, list[str]]:
    base_terms = list(dict.fromkeys(parsed_jd.skills + parsed_jd.technologies))
    if not base_terms and parsed_jd.summary:
        base_terms = parsed_jd.summary.split()[:6]

    query_text = " ".join(base_terms[:5]).strip()
    if not query_text:
        query_text = "software engineer"

    queries: dict[str, list[str]] = {}
    for platform in platforms:
        queries[platform] = [query_text]
    return queries


def _normalize_queries(raw_queries: Any, platforms: list[str]) -> dict[str, list[str]]:
    if not isinstance(raw_queries, dict):
        return {}

    normalized: dict[str, list[str]] = {}
    for platform in platforms:
        candidate_values = raw_queries.get(platform)
        if candidate_values is None:
            candidate_values = raw_queries.get(platform.upper())

        if isinstance(candidate_values, str):
            candidate_values = [candidate_values]

        if not isinstance(candidate_values, list):
            continue

        entries = [item.strip() for item in candidate_values if isinstance(item, str) and item.strip()]
        if entries:
            normalized[platform] = entries[:3]
    return normalized


def _log_prompt_preview(settings: Settings, provider_name: str, operation: str, system_prompt: str, user_prompt: str) -> None:
    if not settings.llm_log_prompts:
        return

    logger.info(
        "LLM prompt (%s/%s): system=%s user_preview=%s",
        provider_name,
        operation,
        system_prompt,
        user_prompt[:1200],
    )
