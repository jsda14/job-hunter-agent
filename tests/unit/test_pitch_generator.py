import pytest
from datetime import datetime, timezone
from src.domain.models.job import JobRaw, SourcePlatform, JobEvaluation
from src.adapters.evaluators.pitch_generator import RuleBasedPitchGeneratorAdapter


def create_job_and_eval(stack: list[str], title: str = "Senior Engineer") -> tuple[JobRaw, JobEvaluation]:
    job = JobRaw(
        id="lever_pitch_1",
        platform=SourcePlatform.LEVER,
        external_id="pitch_1",
        title=title,
        company="FintechCorp",
        url="https://jobs.lever.co/fintechcorp/pitch_1",
        location="Remote - Colombia",
        raw_description="Looking for an engineer to build scalable backend and AI services.",
        posted_at=datetime.now(timezone.utc),
    )
    evaluation = JobEvaluation(
        job_id=job.id,
        fit_score=85.0,
        salary_match=True,
        requires_spoken_english=False,
        tech_stack_detected=stack,
        pros=["Great tech match"],
        red_flags=[],
        is_actionable=True
    )
    return job, evaluation


@pytest.mark.asyncio
async def test_pitch_generator_selects_ai_project_when_fastapi_or_rag():
    generator = RuleBasedPitchGeneratorAdapter()
    job, evaluation = create_job_and_eval(["fastapi", "rag"])

    pitch = await generator.generate_pitch(job, evaluation)

    assert "observabilidad bancaria" in pitch.lower()
    assert "redis streams" in pitch.lower()
    assert len(pitch) > 100


@pytest.mark.asyncio
async def test_pitch_generator_selects_frontend_telemetry_project_when_react():
    generator = RuleBasedPitchGeneratorAdapter()
    job, evaluation = create_job_and_eval(["react"])

    pitch = await generator.generate_pitch(job, evaluation)

    assert "w&t offshore" in pitch.lower() or "telemetría" in pitch.lower()
    assert len(pitch) > 100