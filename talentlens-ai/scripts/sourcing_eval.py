"""Measure sourcing quality against fixed JDs, so changes to sourcing are compared on numbers.

Runs the sourcing workflow directly against the real platform APIs. It needs no
database and, by default, no LLM: adapters derive their search terms from the
parsed JD themselves. Run from talentlens-ai/:

    uv run python -m scripts.sourcing_eval                                  # every available platform, each alone
    uv run python -m scripts.sourcing_eval --platforms GITHUB,HACKERNEWS --jds backend,ml
    uv run python -m scripts.sourcing_eval --llm                            # use the configured LLM for queries
    uv run python -m scripts.sourcing_eval --combined                       # also run each JD's suggested mix

Credentials (GITHUB_TOKEN, STACKEXCHANGE_KEY, ...) come from the environment or .env.
Each platform/JD pair is one real sourcing run's worth of API calls.

Prints Markdown rows for the evaluation table in specs/Sourcing-Improvements-Plan.md.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings
from app.models.candidate_models import RankedCandidateModel, SourcePlatform, SourcingRequestPayloadModel
from app.models.jd_models import ParsedJdModel
from app.services.sources.registry import available_platforms, suggest_platforms
from app.services.sourcing_workflow_service import SourcingWorkflowService


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "eval_jds"


class _NoLlm:
    """Empty queries: each adapter falls back to the terms it derives from the JD."""

    name = "none"

    def generate_queries(self, parsed_jd: ParsedJdModel, platforms: list[str]) -> dict[str, list[str]]:
        return {platform: [] for platform in platforms}


def _settings() -> Settings:
    # Only the sourcing credentials matter here; the datastores are never touched.
    return Settings(
        DATABASE_URL="postgresql://unused:unused@localhost/unused",
        MONGODB_URI="mongodb://localhost:27017",
        JWT_SECRET="unused-by-the-evaluation-script-0123456789",
    )


def _row(phase: str, jd: str, label: str, candidates: list[RankedCandidateModel], seconds: float) -> str:
    scores = [candidate.matchScore for candidate in candidates]
    cells = [
        phase, jd, label, str(len(candidates)),
        str(sum(1 for candidate in candidates if candidate.scoreBreakdown.skillMatch >= 50)),
        str(round(statistics.median(scores))) if scores else "-",
        str(sum(1 for candidate in candidates if candidate.openToWork)),
        str(sum(1 for candidate in candidates if candidate.email)),
        f"{seconds:.0f}s",
    ]
    return "| " + " | ".join(cells) + " |"


async def _run(workflow: SourcingWorkflowService, parsed: ParsedJdModel, platforms: list[SourcePlatform]):
    payload = SourcingRequestPayloadModel(
        taskId="eval", searchId="eval", runId="eval", parsedJd=parsed, platforms=platforms,
        timestamp=datetime.now(timezone.utc),
    )
    started = time.monotonic()
    result = await workflow.run(payload)
    return result, time.monotonic() - started


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--platforms", help="comma-separated, default: every available platform")
    parser.add_argument("--jds", help=f"comma-separated fixture names from {FIXTURES.name}/, default: all")
    parser.add_argument("--llm", action="store_true", help="generate queries with the configured LLM provider")
    parser.add_argument("--combined", action="store_true", help="also run each JD's suggested platform mix")
    parser.add_argument("--phase", default="-", help="label for the Phase column")
    args = parser.parse_args()

    settings = _settings()
    available = available_platforms(settings)
    platforms = [SourcePlatform(name.strip().upper()) for name in args.platforms.split(",")] if args.platforms else available
    for platform in platforms:
        if platform not in available:
            raise SystemExit(f"{platform.value} is not configured (see app/services/sources/registry.py)")

    names = [name.strip() for name in args.jds.split(",")] if args.jds else sorted(p.stem for p in FIXTURES.glob("*.json"))
    jds = {name: ParsedJdModel.model_validate(json.loads((FIXTURES / f"{name}.json").read_text())) for name in names}

    if args.llm:
        from app.dependencies import get_llm_provider

        provider = get_llm_provider()
    else:
        provider = _NoLlm()
    workflow = SourcingWorkflowService(provider, settings)

    print("| Phase | JD | Platform | Returned | skillMatch ≥ 50 | Median score | Open to work | With email | Time |")
    print("|---|---|---|---|---|---|---|---|---|")
    for name, parsed in jds.items():
        for platform in platforms:
            result, seconds = await _run(workflow, parsed, [platform])
            print(_row(args.phase, name, platform.value, result.candidates, seconds), flush=True)
            if result.error:
                print(f"<!-- {name}/{platform.value}: {result.error} -->", flush=True)
        if args.combined:
            mix = suggest_platforms(parsed, settings)
            result, seconds = await _run(workflow, parsed, mix)
            counts = {platform.value: 0 for platform in mix}
            for candidate in result.candidates:
                counts[candidate.source.value] += 1
            label = "mix: " + ", ".join(f"{platform} {count}" for platform, count in counts.items())
            print(_row(args.phase, name, label, result.candidates, seconds), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
