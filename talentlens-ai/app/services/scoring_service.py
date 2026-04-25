from __future__ import annotations

import re
from typing import Optional


YEARS_PATTERN = re.compile(r"(\d{1,2})\+?\s*(?:years?|yrs?)", re.IGNORECASE)


def compute_skill_match(jd_skills: list[str], candidate_skills: list[str]) -> int:
    jd_set = {_normalize_token(item) for item in jd_skills if item}
    candidate_set = {_normalize_token(item) for item in candidate_skills if item}

    jd_set.discard("")
    candidate_set.discard("")

    if not jd_set:
        return 0

    overlap = len(jd_set.intersection(candidate_set))
    return max(0, min(100, round((overlap / len(jd_set)) * 100)))


def compute_experience_match(jd_experience: Optional[str], candidate_experience: Optional[str]) -> int:
    jd_level = _infer_level(jd_experience)
    candidate_level = _infer_level(candidate_experience)

    if jd_level == 0 or candidate_level == 0:
        return 50

    gap = abs(jd_level - candidate_level)
    if gap == 0:
        return 100
    if gap == 1:
        return 70
    if gap == 2:
        return 40
    return 20


def compute_match_score(skill_match: int, experience_match: int) -> int:
    weighted = round((0.6 * skill_match) + (0.4 * experience_match))
    return max(0, min(100, weighted))


def _normalize_token(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _infer_level(value: Optional[str]) -> int:
    if not value:
        return 0

    lowered = value.lower()
    if "lead" in lowered or "principal" in lowered or "staff" in lowered:
        return 4
    if "senior" in lowered:
        return 3
    if "mid" in lowered:
        return 2
    if "junior" in lowered:
        return 1

    years = YEARS_PATTERN.search(lowered)
    if not years:
        return 0

    value_years = int(years.group(1))
    if value_years <= 2:
        return 1
    if value_years <= 5:
        return 2
    if value_years <= 9:
        return 3
    return 4
