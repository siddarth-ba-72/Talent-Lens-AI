"""Authors of Hugging Face models in the JD's ML stack.

Free-text model search matches model *names* ("kafka" finds "KafkaLM"), so this
searches by library / task tag instead, and skips quantized re-uploads (which
dominate download counts) and organisations.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx

from app.models.candidate_models import SourcePlatform
from app.models.jd_models import ParsedJdModel
from app.services.skill_vocabulary import canonical, canonical_list, jd_terms, single_terms
from app.services.sources.base import (
    MAX_SIGNALS,
    RawCandidate,
    SourceToolAdapter,
    by_frequency,
    compact_number,
    merge_terms,
    truncate,
)


logger = logging.getLogger(__name__)

_API = "https://huggingface.co/api"
_MAX_FILTERS = 3
_MODELS_PER_FILTER = 50
_MAX_AUTHORS = 20
_MAX_SKILLS = 20
_CONCURRENCY = 5

LIBRARY_TAGS = frozenset({
    "pytorch", "tensorflow", "jax", "keras", "transformers", "diffusers", "sentence-transformers", "peft",
    "timm", "spacy", "flair", "onnx", "safetensors", "setfit", "stable-baselines3", "mlx", "scikit-learn",
    "fastai", "paddlepaddle", "speechbrain", "nemo", "gliner",
})
TASK_TAGS = frozenset({
    "text-generation", "text-classification", "token-classification", "question-answering", "summarization",
    "translation", "fill-mask", "feature-extraction", "sentence-similarity", "zero-shot-classification",
    "automatic-speech-recognition", "text-to-speech", "audio-classification", "image-classification",
    "object-detection", "image-segmentation", "text-to-image", "image-to-text", "image-text-to-text",
    "reinforcement-learning", "tabular-classification", "time-series-forecasting", "depth-estimation",
    "video-classification", "visual-question-answering",
})
# JD vocabulary that names an HF task.
_TERM_TASKS = {
    "llm": "text-generation",
    "generative-ai": "text-generation",
    "nlp": "text-classification",
    "ner": "token-classification",
    "named-entity-recognition": "token-classification",
    "rag": "sentence-similarity",
    "embeddings": "sentence-similarity",
    "semantic-search": "sentence-similarity",
    "computer-vision": "image-classification",
    "object-detection": "object-detection",
    "speech-recognition": "automatic-speech-recognition",
    "asr": "automatic-speech-recognition",
    "tts": "text-to-speech",
    "diffusion": "text-to-image",
    "stable-diffusion": "text-to-image",
    "machine-translation": "translation",
    "reinforcement-learning": "reinforcement-learning",
    "time-series": "time-series-forecasting",
    "huggingface": "transformers",
}
# Quantized or converted re-uploads of other people's models.
_REUPLOAD_MARKERS = ("gguf", "gptq", "awq", "exl2", "mlx-community", "-4bit", "-8bit")


class HuggingFaceSourceToolAdapter(SourceToolAdapter):
    def __init__(self, token: Optional[str], transport: Optional[httpx.AsyncBaseTransport] = None):
        super().__init__(SourcePlatform.HUGGINGFACE, transport)
        self._token = token

    async def fetch_candidates(self, query_terms: list[str], parsed_jd: ParsedJdModel) -> list[RawCandidate]:
        filters = hf_filters([*single_terms(query_terms), *jd_terms(parsed_jd)])
        if not filters:
            return []

        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
        async with self._client(headers=headers) as client:
            # author -> their models found for the JD's tags
            authors: dict[str, list[dict]] = {}
            for tag in filters:
                try:
                    response = await client.get(
                        f"{_API}/models",
                        params={"filter": tag, "sort": "likes", "direction": -1, "limit": _MODELS_PER_FILTER},
                    )
                    response.raise_for_status()
                except Exception as exc:
                    logger.warning("Hugging Face models for %s failed: %s", tag, exc)
                    continue
                for model in response.json():
                    model_id = model.get("id") or ""
                    if "/" not in model_id or _is_reupload(model):
                        continue
                    authors.setdefault(model_id.split("/", 1)[0], []).append(model)

            ranked = sorted(authors.items(), key=lambda entry: -sum(_likes(model) for model in entry[1]))

            semaphore = asyncio.Semaphore(_CONCURRENCY)

            async def load(author: str) -> Optional[tuple[dict, list[dict]]]:
                async with semaphore:
                    overview = await client.get(f"{_API}/users/{author}/overview")
                    if overview.status_code == 404:
                        return None  # an organisation, not a person
                    overview.raise_for_status()
                    models = await client.get(f"{_API}/models", params={"author": author, "limit": 50})
                    models.raise_for_status()
                    return overview.json(), models.json()

            # Look at a few more than needed: some top authors are organisations.
            shortlist = ranked[: _MAX_AUTHORS * 2]
            results = await asyncio.gather(*(load(author) for author, _ in shortlist), return_exceptions=True)

        candidates = []
        for (author, found), result in zip(shortlist, results):
            if result is None or isinstance(result, BaseException):
                continue
            candidates.append(_to_candidate(author, found, *result))
            if len(candidates) >= _MAX_AUTHORS:
                break
        logger.info("Hugging Face adapter fetched %d candidates for %s", len(candidates), filters)
        return candidates


def hf_filters(terms: list[str]) -> list[str]:
    """Library and task tags for the JD, most specific first."""
    tags: list[str] = []
    for term in terms:
        value = canonical(term)
        tag = value if value in LIBRARY_TAGS or value in TASK_TAGS else _TERM_TASKS.get(value)
        if tag:
            tags.append(tag)
    return merge_terms(tags, limit=_MAX_FILTERS)


def _is_reupload(model: dict) -> bool:
    haystack = " ".join([model.get("id") or "", *(model.get("tags") or [])]).lower()
    return any(marker in haystack for marker in _REUPLOAD_MARKERS)


def _likes(model: dict) -> int:
    return int(model.get("likes") or 0)


def _model_skills(model: dict) -> list[str]:
    tags = [*(model.get("tags") or []), model.get("library_name") or "", model.get("pipeline_tag") or ""]
    return canonical_list(tag for tag in tags if tag in LIBRARY_TAGS or tag in TASK_TAGS)


def _absolute(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    return url if url.startswith("http") else f"https://huggingface.co{url}"


def _to_candidate(author: str, found: list[dict], overview: dict, models: list[dict]) -> RawCandidate:
    own = [model for model in models if not _is_reupload(model)]
    skills = by_frequency([*(_model_skills(model) for model in [*found, *own]), ["python"]], _MAX_SKILLS)
    best = max(found, key=_likes)
    signals = [f"Author of {best['id']} ({compact_number(_likes(best))} likes)"]
    followers = int(overview.get("numFollowers") or 0)
    if followers >= 50:
        signals.append(f"{compact_number(followers)} followers on Hugging Face")
    orgs = [org.get("name") for org in overview.get("orgs") or [] if isinstance(org, dict) and org.get("name")]
    if orgs:
        signals.append(f"Member of {', '.join(orgs[:3])}")

    return RawCandidate(
        name=overview.get("fullname") or author,
        profile_url=f"https://huggingface.co/{author}",
        source_username=author,
        source=SourcePlatform.HUGGINGFACE,
        skills=skills,
        avatar_url=_absolute(overview.get("avatarUrl")),
        bio=truncate(overview.get("details"), 300),
        experience=None,
        signals=signals[:MAX_SIGNALS],
    )
