import pytest
from datetime import datetime, timezone

from src.domain.models.job import JobEvaluation, JobRaw, SourcePlatform
from src.adapters.repositories.sqlite import SQLiteJobRepositoryAdapter


def make_test_job(job_id: str, platform: SourcePlatform = SourcePlatform.LEVER) -> JobRaw:
    return JobRaw(
        id=f"{platform.value}_{job_id}",
        platform=platform,
        external_id=job_id,
        title="Software Engineer",
        company="TechCorp",
        url=f"https://jobs.example.com/{job_id}",
        location="Remote",
        raw_description="Python FastAPI engineer needed.",
        posted_at=datetime.now(timezone.utc),
    )


def make_test_evaluation(job_id: str, is_actionable: bool = True, fit_score: float = 85.0) -> JobEvaluation:
    return JobEvaluation(
        job_id=job_id,
        fit_score=fit_score,
        salary_match=True,
        requires_spoken_english=False,
        tech_stack_detected=["python", "fastapi"],
        pros=["Great stack match"],
        red_flags=[],
        is_actionable=is_actionable,
        tailored_pitch="Pitch de prueba para TechCorp",
    )


@pytest.mark.asyncio
async def test_is_seen_and_save_job():
    """RN-01, RN-02, RN-04: is_seen retorna False al inicio y True tras guardar con y sin evaluation."""
    repo = SQLiteJobRepositoryAdapter(":memory:")

    job_1 = make_test_job("101")
    job_2 = make_test_job("102")

    # Inicialmente no han sido vistas
    assert await repo.is_seen(job_1.id) is False
    assert await repo.is_seen(job_2.id) is False

    # Guardar job_1 sin evaluation
    await repo.save_job(job_1)
    assert await repo.is_seen(job_1.id) is True
    assert await repo.is_seen(job_2.id) is False

    # Guardar job_2 con evaluation
    eval_2 = make_test_evaluation(job_2.id, is_actionable=True, fit_score=90.0)
    await repo.save_job(job_2, eval_2)
    assert await repo.is_seen(job_2.id) is True


@pytest.mark.asyncio
async def test_filter_unseen_preserves_order_and_filters_duplicates():
    """RN-03: filter_unseen retorna únicamente las ofertas no registradas preservando el orden."""
    repo = SQLiteJobRepositoryAdapter(":memory:")

    job_a = make_test_job("a")
    job_b = make_test_job("b")
    job_c = make_test_job("c")

    # Guardar previamente job_b
    await repo.save_job(job_b)

    # Filtrar lote que contiene [job_a, job_b, job_c]
    unseen = await repo.filter_unseen([job_a, job_b, job_c])

    assert len(unseen) == 2
    assert unseen[0].id == job_a.id
    assert unseen[1].id == job_c.id


@pytest.mark.asyncio
async def test_save_job_idempotence():
    """RN-04: save_job dos veces con el mismo ID actualiza/reemplaza sin error."""
    repo = SQLiteJobRepositoryAdapter(":memory:")
    job = make_test_job("dup_1")

    # Guardar primera vez sin evaluation
    await repo.save_job(job)
    assert await repo.is_seen(job.id) is True

    # Guardar segunda vez con evaluation actualizada
    eval_updated = make_test_evaluation(job.id, is_actionable=True, fit_score=95.0)
    await repo.save_job(job, eval_updated)
    assert await repo.is_seen(job.id) is True


@pytest.mark.asyncio
async def test_filter_unseen_empty_list():
    """CB-02: filter_unseen con lista vacía retorna [] de inmediato."""
    repo = SQLiteJobRepositoryAdapter(":memory:")
    result = await repo.filter_unseen([])
    assert result == []
