from __future__ import annotations

import json

from app.models.jd_models import ParsedJdModel


JD_PARSE_SCHEMA = {
    "skills": ["string"],
    "responsibilities": ["string"],
    "experienceLevel": "string",
    "qualifications": ["string"],
    "technologies": ["string"],
    "domain": "string",
    "summary": "string",
}


QUERY_SCHEMA = {
    "queriesByPlatform": {
        "GITHUB": ["string"],
        "STACKOVERFLOW": ["string"],
        "LEETCODE": ["string"],
        "PEOPLES_DATA": ["string"],
    }
}


def build_parse_jd_prompts(jd_text: str) -> tuple[str, str]:
    system_prompt = (
        "You are TalentLens AI, a senior technical recruiter assistant. "
        "Extract structured hiring requirements from job descriptions with high precision. "
        "Return only valid JSON matching the requested schema. "
        "Never add markdown, code fences, commentary, or extra keys."
    )

    user_prompt = (
        "Task: Parse the following job description and return normalized JSON.\n\n"
        "Rules:\n"
        "1. Use concise phrases for lists.\n"
        "2. Keep only relevant skills/technologies.\n"
        "3. If data is missing, use sensible defaults.\n"
        "4. Output must exactly match this JSON shape:\n"
        f"{json.dumps(JD_PARSE_SCHEMA, ensure_ascii=True, indent=2)}\n\n"
        "Job Description:\n"
        f"{jd_text.strip()}"
    )
    return system_prompt, user_prompt


def build_generate_queries_prompts(parsed_jd: ParsedJdModel, platforms: list[str]) -> tuple[str, str]:
    normalized_platforms = [item.strip().upper() for item in platforms if item and item.strip()]

    system_prompt = (
        "You are TalentLens AI, an expert sourcing strategist. "
        "Generate focused, high-recall search queries for public developer profiles. "
        "Return only valid JSON matching the requested schema. "
        "No markdown or extra text."
    )

    user_prompt = (
        "Task: Generate platform-specific sourcing queries from parsed JD data.\n\n"
        "Rules:\n"
        "1. Return up to 3 queries per platform.\n"
        "2. Prioritize exact skill and technology alignment.\n"
        "3. Keep queries concise and practical for profile search.\n"
        "4. Include only requested platforms.\n"
        "5. Output must exactly match this JSON shape:\n"
        f"{json.dumps(QUERY_SCHEMA, ensure_ascii=True, indent=2)}\n\n"
        "Parsed JD JSON:\n"
        f"{json.dumps(parsed_jd.model_dump(mode='json'), ensure_ascii=True, indent=2)}\n\n"
        "Requested Platforms:\n"
        f"{json.dumps(normalized_platforms, ensure_ascii=True)}"
    )
    return system_prompt, user_prompt
