from __future__ import annotations

from typing import Optional

from pydantic import TypeAdapter

from app.db.documents import CandidateDocument
from app.errors import InvalidFileError
from app.models.candidate_models import CandidateResponse
from app.services.candidate_service import to_response


CSV_HEADER = (
    "id,name,email,source,sourceUsername,profileUrl,skills,location,"
    "matchScore,skillMatch,experienceMatch,overallFit,runId,sourcedAt,openToWork,signals"
)
_MEDIA_TYPES = {"csv": "text/csv", "json": "application/json"}
# Spreadsheet apps evaluate cells starting with these as formulas. Candidate
# fields come from public profiles, i.e. from whoever wrote the profile.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

_candidate_list = TypeAdapter(list[CandidateResponse])


def resolve_format(export_format: Optional[str]) -> str:
    if export_format is None or not export_format.strip():
        raise InvalidFileError("Export format is required (csv or json)")
    normalized = export_format.lower()
    if normalized not in _MEDIA_TYPES:
        raise InvalidFileError(f"Unsupported export format: {export_format}. Allowed: csv, json")
    return normalized


def media_type(export_format: str) -> str:
    return _MEDIA_TYPES[export_format]


def render(export_format: str, candidates: list[CandidateDocument]) -> bytes:
    if export_format == "csv":
        return _render_csv(candidates)
    return _candidate_list.dump_json([to_response(candidate) for candidate in candidates])


def _render_csv(candidates: list[CandidateDocument]) -> bytes:
    lines = [CSV_HEADER]
    lines.extend(_csv_row(candidate) for candidate in candidates)
    return ("\n".join(lines) + "\n").encode("utf-8")


def _csv_row(candidate: CandidateDocument) -> str:
    breakdown = candidate.scoreBreakdown
    return ",".join(
        [
            _quote(str(candidate.id)),
            _quote(candidate.name),
            _quote(candidate.email),
            _quote(candidate.source.value),
            _quote(candidate.sourceUsername),
            _quote(candidate.profileUrl),
            _quote("|".join(candidate.skills)),
            _quote(candidate.location),
            str(candidate.matchScore),
            str(breakdown.skillMatch),
            str(breakdown.experienceMatch),
            str(breakdown.overallFit),
            _quote(candidate.runId),
            candidate.sourcedAt.isoformat().replace("+00:00", "Z"),
            "true" if candidate.openToWork else "false",
            _quote("|".join(candidate.signals)),
        ]
    )


def _quote(value: Optional[str]) -> str:
    if value is None:
        return ""
    if value.startswith(_FORMULA_PREFIXES):
        value = "'" + value
    return '"' + value.replace('"', '""') + '"'
