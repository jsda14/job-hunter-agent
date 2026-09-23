import pytest
from datetime import datetime, timezone
from src.domain.models.job import JobRaw, SourcePlatform
from src.adapters.evaluators.rule_based import RuleBasedEvaluatorAdapter


def create_job(description: str, title: str = "Senior Engineer") -> JobRaw:
    return JobRaw(
        id="lever_test_1",
        platform=SourcePlatform.LEVER,
        external_id="test_1",
        title=title,
        company="GlobalTech",
        url="https://jobs.lever.co/globaltech/test_1",
        location="Remote - Colombia",
        raw_description=description,
        posted_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_evaluator_rejects_strict_spoken_english():
    evaluator = RuleBasedEvaluatorAdapter()
    job = create_job(
        "We need a Senior Python and React developer. Fluent English required for daily calls."
    )

    evaluation = await evaluator.evaluate(job)

    assert evaluation.requires_spoken_english is True
    assert evaluation.is_actionable is False
    assert any("inglés hablado" in flag.lower() for flag in evaluation.red_flags)


@pytest.mark.asyncio
async def test_evaluator_approves_matching_stack_without_spoken_english():
    evaluator = RuleBasedEvaluatorAdapter()
    job = create_job(
        "Buscamos desarrollador Full-Stack con Python, FastAPI, React y experiencia en Clean Architecture."
    )

    evaluation = await evaluator.evaluate(job)

    assert evaluation.requires_spoken_english is False
    assert evaluation.is_actionable is True
    assert evaluation.fit_score >= 70.0
    assert "python" in [t.lower() for t in evaluation.tech_stack_detected]
    assert "fastapi" in [t.lower() for t in evaluation.tech_stack_detected]