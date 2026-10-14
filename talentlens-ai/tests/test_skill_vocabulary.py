from __future__ import annotations

import pytest

from app.models.jd_models import ParsedJdModel
from app.services.scoring_service import compute_skill_match
from app.services.skill_vocabulary import (
    MAX_JD_TERMS,
    as_devto_tag,
    as_topic,
    canonical,
    jd_terms,
    matchable_terms,
)


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        ("Golang", "go"),
        ("PostgreSQL", "postgresql"),
        ("postgres", "postgresql"),
        ("Java 17", "java"),
        ("python3", "python"),
        ("python-3.x", "python"),
        ("C++23 (GCC 14-64, msys2)", "c++"),
        ("React.js", "react"),
        ("Amazon Web Services (AWS)", "aws"),
        ("k8s", "kubernetes"),
        ("apache-kafka", "kafka"),
        ("CI/CD", "ci-cd"),
        ("Spring Boot", "spring-boot"),
        ("HTML5", "html"),
        # Digits that are part of the name stay.
        ("d3", "d3"),
        ("S3", "s3"),
        ("ec2", "ec2"),
    ],
)
def test_canonical_spelling(term, expected):
    assert canonical(term) == expected


def test_matchable_terms_skip_long_phrases_and_duplicates():
    terms = ["Go", "golang", "Kafka", "excellent stakeholder communication skills", "PostgreSQL"]

    assert matchable_terms(terms) == ["go", "kafka", "postgresql"]


def test_matchable_terms_are_capped():
    assert len(matchable_terms([f"tool{index}x" for index in range(30)])) == MAX_JD_TERMS


def test_jd_terms_top_up_few_technologies_with_skills():
    parsed = ParsedJdModel(skills=["System design", "Go"], technologies=["Kafka", "Kubernetes"])

    assert jd_terms(parsed) == ["kafka", "kubernetes", "system-design", "go"]


def test_jd_terms_use_technologies_alone_when_there_are_enough():
    parsed = ParsedJdModel(
        skills=["Strong written communication", "Go"], technologies=["Go", "Kafka", "PostgreSQL"]
    )

    assert jd_terms(parsed) == ["go", "kafka", "postgresql"]


def test_skill_match_compares_canonical_forms():
    jd = ["Golang", "PostgreSQL", "Kafka", "excellent stakeholder communication skills"]

    # 2 of the 3 matchable terms; the long phrase is not counted against anyone.
    assert compute_skill_match(jd, ["go", "postgres", "docker"]) == 67
    assert compute_skill_match([], ["go"]) == 0


def test_platform_tag_spellings():
    assert as_topic("Node.js") == "nodejs"
    assert as_topic("C#") == "csharp"
    assert as_devto_tag("Next.js") == "nextjs"
    assert as_devto_tag("PostgreSQL") == "postgres"
