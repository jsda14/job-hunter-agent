import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone

from src.domain.models.job import JobRaw, SourcePlatform, JobEvaluation
from src.domain.ports.harvester import JobHarvesterPort, HarvesterConnectionError
from src.domain.ports.evaluator import JobEvaluatorPort
from src.domain.ports.pitch_generator import PitchGeneratorPort
from src.domain.use_cases.hunt_jobs import JobHunterUseCase


def make_job(external_id: str, title: str) -> JobRaw:
    return JobRaw(
        id=f"lever_{external_id}",
        platform=SourcePlatform.LEVER,
        external_id=external_id,
        title=title,
        company="TargetCorp",
        url=f"https://jobs.lever.co/targetcorp/{external_id}",
        location="Remote - Colombia",
        raw_description="Python, FastAPI and React required.",
        posted_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_usecase_orchestrates_flow_and_filters_only_actionable():
    # Mocks de puertos
    harvester_mock = AsyncMock(spec=JobHarvesterPort)
    evaluator_mock = AsyncMock(spec=JobEvaluatorPort)
    pitch_gen_mock = AsyncMock(spec=PitchGeneratorPort)

    job_1 = make_job("1", "Actionable Senior Engineer")
    job_2 = make_job("2", "Rejected Spoken English Job")

    harvester_mock.fetch_jobs.return_value = [job_1, job_2]

    # Evaluaciones mockeadas
    eval_1 = JobEvaluation(
        job_id=job_1.id,
        fit_score=90.0,
        salary_match=True,
        requires_spoken_english=False,
        tech_stack_detected=["fastapi", "react"],
        pros=["Great fit"],
        red_flags=[],
        is_actionable=True,
    )
    eval_2 = JobEvaluation(
        job_id=job_2.id,
        fit_score=30.0,
        salary_match=True,
        requires_spoken_english=True,
        tech_stack_detected=[],
        pros=[],
        red_flags=["Spoken English"],
        is_actionable=False,
    )

    evaluator_mock.evaluate.side_effect = [eval_1, eval_2]
    pitch_gen_mock.generate_pitch.return_value = "Hola equipo, tengo experiencia sólida en FastAPI y React..."

    # Ejecución
    use_case = JobHunterUseCase(
        harvester=harvester_mock,
        evaluator=evaluator_mock,
        pitch_generator=pitch_gen_mock,
    )

    results = await use_case.execute(["targetcorp"])

    # Verificaciones
    assert len(results) == 1
    matched_job, matched_eval = results[0]
    assert matched_job.id == job_1.id
    assert matched_eval.is_actionable is True
    assert matched_eval.tailored_pitch == "Hola equipo, tengo experiencia sólida en FastAPI y React..."
    pitch_gen_mock.generate_pitch.assert_awaited_once_with(job_1, eval_1)


@pytest.mark.asyncio
async def test_usecase_survives_harvester_connection_error():
    harvester_mock = AsyncMock(spec=JobHarvesterPort)
    evaluator_mock = AsyncMock(spec=JobEvaluatorPort)
    pitch_gen_mock = AsyncMock(spec=PitchGeneratorPort)

    # Empresa 1 falla, Empresa 2 responde
    job_ok = make_job("ok_1", "Senior Dev")
    harvester_mock.fetch_jobs.side_effect = [
        HarvesterConnectionError("Lever down"),
        [job_ok],
    ]

    eval_ok = JobEvaluation(
        job_id=job_ok.id,
        fit_score=80.0,
        salary_match=True,
        requires_spoken_english=False,
        tech_stack_detected=["python"],
        pros=[],
        red_flags=[],
        is_actionable=True,
    )
    evaluator_mock.evaluate.return_value = eval_ok
    pitch_gen_mock.generate_pitch.return_value = "Pitch generado"

    use_case = JobHunterUseCase(
        harvester=harvester_mock,
        evaluator=evaluator_mock,
        pitch_generator=pitch_gen_mock,
    )

    results = await use_case.execute(["failing_co", "working_co"])

    assert len(results) == 1
    assert results[0][0].id == job_ok.id