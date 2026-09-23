import pytest
from datetime import datetime, timezone
from src.domain.models.job import JobRaw, SourcePlatform, JobEvaluation
from src.adapters.notifiers.console import ConsoleNotifierAdapter


def create_notifiable_tuple() -> tuple[JobRaw, JobEvaluation]:
    job = JobRaw(
        id="lever_notif_1",
        platform=SourcePlatform.LEVER,
        external_id="notif_1",
        title="Staff AI Engineer",
        company="FintechCorp",
        url="https://jobs.lever.co/fintechcorp/notif_1",
        location="Remote - Colombia",
        raw_description="Build agents and high-throughput backends.",
        posted_at=datetime.now(timezone.utc),
    )
    evaluation = JobEvaluation(
        job_id=job.id,
        fit_score=95.0,
        salary_match=True,
        requires_spoken_english=False,
        tech_stack_detected=["python", "fastapi", "ai agents"],
        pros=["High match"],
        red_flags=[],
        is_actionable=True,
        tailored_pitch="Pitch de prueba persuasivo listo para postular."
    )
    return job, evaluation


@pytest.mark.asyncio
async def test_console_notifier_outputs_actionable_jobs(capsys):
    notifier = ConsoleNotifierAdapter()
    job, eval_ = create_notifiable_tuple()

    count = await notifier.notify([(job, eval_)])

    captured = capsys.readouterr()
    assert count == 1
    assert "Staff AI Engineer" in captured.out
    assert "FintechCorp" in captured.out
    assert "95.0%" in captured.out
    assert "Pitch de prueba persuasivo" in captured.out


@pytest.mark.asyncio
async def test_console_notifier_empty_list(capsys):
    notifier = ConsoleNotifierAdapter()
    count = await notifier.notify([])

    captured = capsys.readouterr()
    assert count == 0
    assert "No se encontraron vacantes accionables" in captured.out