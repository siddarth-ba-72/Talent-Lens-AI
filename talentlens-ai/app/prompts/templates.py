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


# What each platform's queries must look like. Adapters also derive terms from
# the parsed JD themselves, so these only need to add precision.
PLATFORM_QUERY_RULES: dict[str, str] = {
    "GITHUB": "GitHub user-search strings using qualifiers, e.g. \"language:go repos:>5 followers:>20\"",
    "STACKOVERFLOW": "Stack Overflow tag names, lowercase and hyphenated, e.g. \"apache-kafka\"",
    "HACKERNEWS": "single technology keywords, e.g. \"kafka\"",
    "DEVTO": "dev.to tags, lowercase letters and digits only, e.g. \"nextjs\"",
    "HUGGINGFACE": "Hugging Face library or task tags, e.g. \"pytorch\", \"text-classification\"",
    "NPM": "npm package keywords, e.g. \"graphql\"",
    "CRATES": "crates.io search keywords, e.g. \"async\"",
    "GITLAB": "GitLab project topics, lowercase and hyphenated, e.g. \"kubernetes\"",
    "OPENALEX": "2-4 word research phrases, e.g. \"stream processing\"",
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

    schema = {"queriesByPlatform": {platform: ["string"] for platform in normalized_platforms}}
    formats = "".join(
        f"   - {platform}: {PLATFORM_QUERY_RULES.get(platform, 'short keywords')}\n" for platform in normalized_platforms
    )

    user_prompt = (
        "Task: Generate platform-specific sourcing queries from parsed JD data.\n\n"
        "Rules:\n"
        "1. Return up to 3 queries per platform.\n"
        "2. Prioritize exact skill and technology alignment.\n"
        "3. Keep queries concise and practical for profile search.\n"
        "4. Include only requested platforms.\n"
        "5. Each platform's queries must use its format:\n"
        f"{formats}"
        "6. Output must exactly match this JSON shape:\n"
        f"{json.dumps(schema, ensure_ascii=True, indent=2)}\n\n"
        "Parsed JD JSON:\n"
        f"{json.dumps(parsed_jd.model_dump(mode='json'), ensure_ascii=True, indent=2)}\n\n"
        "Requested Platforms:\n"
        f"{json.dumps(normalized_platforms, ensure_ascii=True)}"
    )
    return system_prompt, user_prompt
