import re

from app.models.jd_models import ParsedJdModel


SKILL_TERMS: dict[str, str] = {
    "java": "Java",
    "spring boot": "Spring Boot",
    "microservices": "Microservices",
    "python": "Python",
    "fastapi": "FastAPI",
    "kafka": "Kafka",
    "mongodb": "MongoDB",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "react": "React",
    "typescript": "TypeScript",
    "aws": "AWS",
    "gcp": "GCP",
    "azure": "Azure",
    "sql": "SQL",
    "postgresql": "PostgreSQL",
    "redis": "Redis",
    "langchain": "LangChain",
    "langgraph": "LangGraph",
}

TECH_TERMS: dict[str, str] = {
    "java 17": "Java 17",
    "spring boot 3": "Spring Boot 3",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "mongodb": "MongoDB",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "react": "React",
    "fastapi": "FastAPI",
    "kafka": "Kafka",
}

DOMAIN_TERMS: dict[str, list[str]] = {
    "FinTech": ["fintech", "payments", "banking", "trading"],
    "HealthTech": ["health", "clinical", "ehr", "hospital"],
    "EdTech": ["education", "learning", "lms", "student"],
    "E-commerce": ["ecommerce", "e-commerce", "marketplace", "checkout"],
    "SaaS": ["saas", "b2b platform", "multi-tenant"],
}

RESPONSIBILITY_HINTS = (
    "build",
    "design",
    "develop",
    "maintain",
    "lead",
    "implement",
    "optimize",
    "mentor",
    "collaborate",
    "own",
)

QUALIFICATION_HINTS = (
    "bachelor",
    "master",
    "degree",
    "qualification",
    "certification",
)

YEARS_PATTERN = re.compile(r"(\d{1,2})(?:\s*(?:-|to)\s*(\d{1,2}))?\+?\s*(?:years?|yrs?)", re.IGNORECASE)


def parse_jd_heuristic(jd_text: str) -> ParsedJdModel:
    normalized = " ".join(jd_text.split())
    lowered = normalized.lower()

    skills = _extract_terms(lowered, SKILL_TERMS)
    technologies = _extract_terms(lowered, TECH_TERMS)
    responsibilities = _extract_responsibilities(jd_text)
    qualifications = _extract_qualifications(jd_text)
    experience_level = _extract_experience_level(lowered)
    domain = _extract_domain(lowered)
    summary = _build_summary(normalized)

    return ParsedJdModel(
        skills=skills,
        responsibilities=responsibilities,
        experienceLevel=experience_level,
        qualifications=qualifications,
        technologies=technologies,
        domain=domain,
        summary=summary,
    )


def _extract_terms(text: str, term_map: dict[str, str]) -> list[str]:
    found: list[str] = []
    for needle, label in term_map.items():
        if needle in text and label not in found:
            found.append(label)
    return found


def _extract_responsibilities(raw_text: str) -> list[str]:
    candidates = re.split(r"[\n\.]+", raw_text)
    responsibilities: list[str] = []
    for line in candidates:
        item = line.strip(" -*\t")
        if len(item) < 12 or len(item) > 220:
            continue
        lowered = item.lower()
        if any(hint in lowered for hint in RESPONSIBILITY_HINTS):
            responsibilities.append(item)
        if len(responsibilities) == 5:
            break
    return responsibilities


def _extract_qualifications(raw_text: str) -> list[str]:
    lines = [ln.strip(" -*\t") for ln in raw_text.splitlines()]
    qualifications: list[str] = []
    for line in lines:
        lowered = line.lower()
        if any(hint in lowered for hint in QUALIFICATION_HINTS):
            qualifications.append(line)
        if len(qualifications) == 4:
            break
    return qualifications


def _extract_experience_level(text: str) -> str:
    years_match = YEARS_PATTERN.search(text)
    if years_match:
        low = int(years_match.group(1))
        high = int(years_match.group(2)) if years_match.group(2) else low
        avg = (low + high) / 2
        if avg <= 2:
            return "Junior (0-2 years)"
        if avg <= 5:
            return "Mid (3-5 years)"
        if avg <= 9:
            return "Senior (6-9 years)"
        return "Lead (10+ years)"

    if "principal" in text or "staff" in text or "lead" in text:
        return "Lead"
    if "senior" in text:
        return "Senior"
    if "mid" in text:
        return "Mid"
    if "junior" in text:
        return "Junior"
    return "Not specified"


def _extract_domain(text: str) -> str:
    for domain, hints in DOMAIN_TERMS.items():
        if any(h in text for h in hints):
            return domain
    return "General"


def _build_summary(normalized: str) -> str:
    if len(normalized) <= 320:
        return normalized
    return f"{normalized[:317].rstrip()}..."
