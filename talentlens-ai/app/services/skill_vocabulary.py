"""Canonical skill names, so JD terms and profile skills from different platforms compare equal.

`canonical()` maps "Golang", "go", "PostgreSQL" / "postgres" and "Java 17" onto one
spelling each. Platforms then need their own tag spelling (Stack Overflow tags,
GitHub topics, dev.to tags), which the `as_*` helpers produce.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from app.models.jd_models import ParsedJdModel


# How many JD terms a candidate is scored against. A public profile shows a
# handful of technologies; scoring against 20 would cap everyone near zero.
MAX_JD_TERMS = 10
# Longer phrases ("stakeholder communication", "design scalable REST services")
# never appear verbatim on a profile, so they are left out of matching.
MAX_TERM_WORDS = 3
# With at least this many technologies, a JD is matched on those alone: its
# "skills" are mostly practices and soft skills that no profile lists.
MIN_TECHNOLOGIES = 3

ALIASES: dict[str, str] = {
    # Languages
    "golang": "go",
    "js": "javascript",
    "ecmascript": "javascript",
    "es6": "javascript",
    "ts": "typescript",
    "py": "python",
    "cpp": "c++",
    "c-plus-plus": "c++",
    "csharp": "c#",
    "c-sharp": "c#",
    "fsharp": "f#",
    "objc": "objective-c",
    "dotnet": ".net",
    ".net-core": ".net",
    "jupyter-notebook": "jupyter",
    "bash": "shell",
    # Web
    "node": "node.js",
    "nodejs": "node.js",
    "reactjs": "react",
    "react.js": "react",
    "vuejs": "vue",
    "vue.js": "vue",
    "nextjs": "next.js",
    "nuxtjs": "nuxt",
    "nuxt.js": "nuxt",
    "angularjs": "angular",
    "expressjs": "express",
    "express.js": "express",
    "nest.js": "nestjs",
    "sveltejs": "svelte",
    "tailwind": "tailwindcss",
    "tailwind-css": "tailwindcss",
    "rest": "rest-api",
    "restful": "rest-api",
    "restful-api": "rest-api",
    "rest-apis": "rest-api",
    "restful-apis": "rest-api",
    "graph-ql": "graphql",
    "springboot": "spring-boot",
    "rails": "ruby-on-rails",
    "ror": "ruby-on-rails",
    # Data stores and messaging
    "postgres": "postgresql",
    "psql": "postgresql",
    "mongo": "mongodb",
    "elastic-search": "elasticsearch",
    "apache-kafka": "kafka",
    "apache-spark": "spark",
    "apache-airflow": "airflow",
    "apache-flink": "flink",
    "apache-hadoop": "hadoop",
    "rabbit-mq": "rabbitmq",
    # Cloud and ops
    "amazon-web-services": "aws",
    "google-cloud": "gcp",
    "google-cloud-platform": "gcp",
    "microsoft-azure": "azure",
    "k8s": "kubernetes",
    "ci/cd": "ci-cd",
    "cicd": "ci-cd",
    "microservice": "microservices",
    "micro-services": "microservices",
    # ML
    "ml": "machine-learning",
    "machinelearning": "machine-learning",
    "deeplearning": "deep-learning",
    "dl": "deep-learning",
    "torch": "pytorch",
    "sklearn": "scikit-learn",
    "scikit": "scikit-learn",
    "natural-language-processing": "nlp",
    "llms": "llm",
    "large-language-models": "llm",
    "large-language-model": "llm",
    "genai": "generative-ai",
    "gen-ai": "generative-ai",
    "hugging-face": "huggingface",
    "huggingface-transformers": "transformers",
    "retrieval-augmented-generation": "rag",
}

# Version numbers glued onto these names ("python3", "html5", "c++17") are dropped.
# Other glued digits are part of the name ("d3", "s3", "ec2", "web3").
_GLUED_VERSION = re.compile(r"^(python|java|php|perl|angular|vue|ruby|swift|html|css|scala|c\+\+)v?\d+(?:\.\d+)*$")
# A separated version ("java 17", "python-3.12", "python-3.x", "spring-boot-3") is dropped.
_SEPARATED_VERSION = re.compile(r"-v?\d+(?:\.(?:\d+|x))*$")
_PARENTHETICAL = re.compile(r"\s*\([^)]*\)")

# GitHub `language:` qualifiers for canonical language names.
GITHUB_LANGUAGES: dict[str, str] = {
    "python": "python", "java": "java", "go": "go", "javascript": "javascript", "typescript": "typescript",
    "c#": "csharp", "c++": "cpp", "c": "c", "rust": "rust", "ruby": "ruby", "php": "php", "kotlin": "kotlin",
    "swift": "swift", "scala": "scala", "elixir": "elixir", "haskell": "haskell", "dart": "dart", "r": "r",
    "julia": "julia", "shell": "shell", "lua": "lua", "perl": "perl", "clojure": "clojure", "erlang": "erlang",
    "objective-c": "objective-c", "groovy": "groovy", "vue": "vue", "ocaml": "ocaml", "f#": "fsharp",
}

# Spellings that GitHub/GitLab topics and dev.to tags use instead of the canonical one.
_TOPIC_SPELLING = {"node.js": "nodejs", "next.js": "nextjs", "c#": "csharp", "c++": "cpp", ".net": "dotnet"}
_DEVTO_SPELLING = {"node.js": "node", "postgresql": "postgres", "c#": "csharp", "c++": "cpp", ".net": "dotnet"}

# Term groups used to suggest platforms for a JD.
ML_TERMS = frozenset({
    "machine-learning", "deep-learning", "pytorch", "tensorflow", "jax", "keras", "transformers", "llm", "nlp",
    "computer-vision", "huggingface", "scikit-learn", "mlops", "generative-ai", "diffusion", "rag", "langchain",
    "reinforcement-learning", "embeddings", "fine-tuning", "speech-recognition",
})
JS_TERMS = frozenset({
    "javascript", "typescript", "node.js", "react", "next.js", "vue", "angular", "svelte", "express", "nestjs",
    "react-native", "npm", "webpack", "vite", "deno", "bun", "nuxt",
})
DEVOPS_TERMS = frozenset({
    "gitlab", "gitlab-ci", "devops", "ci-cd", "terraform", "ansible", "helm", "sre", "platform-engineering",
})


def canonical(term: str) -> str:
    """One spelling per skill: lowercase, hyphenated, aliases applied, versions dropped."""
    value = _PARENTHETICAL.sub(" ", term or "").strip().lower()
    value = re.sub(r"[\s_]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-").rstrip(".")
    if value in ALIASES:
        return ALIASES[value]

    glued = _GLUED_VERSION.match(value)
    if glued:
        value = glued.group(1)
    else:
        stripped = _SEPARATED_VERSION.sub("", value)
        if len(stripped) >= 1 and stripped != value and re.search(r"[a-z]", stripped):
            value = stripped
    return ALIASES.get(value, value)


def canonical_list(terms: Iterable[str], limit: int | None = None) -> list[str]:
    """Canonical forms, de-duplicated in order; terms without letters are dropped."""
    seen: dict[str, None] = {}
    for term in terms:
        value = canonical(term) if term else ""
        if value and re.search(r"[a-z]", value) and len(value) <= 40:
            seen.setdefault(value, None)
        if limit is not None and len(seen) >= limit:
            break
    return list(seen)


def is_matchable(term: str) -> bool:
    return 0 < len(canonical(term).split("-")) <= MAX_TERM_WORDS


def matchable_terms(terms: Iterable[str]) -> list[str]:
    """The JD terms a candidate is scored against (canonical, short, at most MAX_JD_TERMS)."""
    return canonical_list((term for term in terms if is_matchable(term)), limit=MAX_JD_TERMS)


def jd_terms(parsed_jd: ParsedJdModel) -> list[str]:
    """The terms candidates are matched on: the JD's technologies, topped up with its skills when it names few."""
    technologies = matchable_terms(parsed_jd.technologies)
    if len(technologies) >= MIN_TECHNOLOGIES:
        return technologies
    return matchable_terms([*parsed_jd.technologies, *parsed_jd.skills])


def jd_text(parsed_jd: ParsedJdModel) -> str:
    """The JD's free-text fields, lowercased, for keyword checks."""
    parts = [
        parsed_jd.summary, parsed_jd.domain, parsed_jd.experienceLevel,
        *parsed_jd.responsibilities, *parsed_jd.qualifications,
    ]
    return " ".join(part for part in parts if part).lower()


def as_topic(term: str) -> str:
    """GitHub / GitLab topic spelling: lowercase letters, digits and hyphens."""
    value = canonical(term)
    return _TOPIC_SPELLING.get(value) or re.sub(r"[^a-z0-9-]", "", value)


def as_so_tag(term: str) -> str:
    """Stack Overflow resolves its own synonyms (`kafka` -> `apache-kafka`), so the canonical form works."""
    return canonical(term)


def as_devto_tag(term: str) -> str:
    """dev.to tags are lowercase letters and digits only."""
    value = canonical(term)
    return _DEVTO_SPELLING.get(value) or re.sub(r"[^a-z0-9]", "", value)


def single_terms(queries: Iterable[str]) -> list[str]:
    """LLM queries that are a single tag or keyword (the fallback query is a space-joined phrase)."""
    return [query.strip() for query in queries if query and query.strip() and len(query.split()) == 1]
