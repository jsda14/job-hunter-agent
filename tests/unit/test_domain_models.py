import pytest
from pydantic import ValidationError
from tests.harness.fixtures.sample_jobs import SAMPLE_JOB_DICT

# Importamos desde donde el dominio DEBERÍA existir según la spec
from src.domain.models.job import JobRaw, SourcePlatform, JobEvaluation


def test_job_raw_creation_valid():
    job = JobRaw(
        id=f"{SAMPLE_JOB_DICT['platform']}_{SAMPLE_JOB_DICT['external_id']}",
        **SAMPLE_JOB_DICT
    )
    assert job.id == "lever_abc-123-xyz"
    assert job.platform == SourcePlatform.LEVER
    assert job.company == "Fintech Solutions"


def test_job_raw_invalid_url():
    invalid_data = SAMPLE_JOB_DICT.copy()
    invalid_data["url"] = "not-a-valid-url"
    with pytest.raises(ValidationError):
        JobRaw(id="lever_123", **invalid_data)


def test_job_evaluation_invariants():
    # Invariante 1: fit_score no puede ser mayor a 100 ni menor a 0
    with pytest.raises(ValidationError):
        JobEvaluation(
            job_id="lever_123",
            fit_score=105.0,
            salary_match=True,
            requires_spoken_english=False,
            tech_stack_detected=["Python"],
            pros=["FastAPI"],
            red_flags=[],
            is_actionable=True
        )

    # Invariante 2: si requires_spoken_english es True, no puede ser actionable
    with pytest.raises(ValueError, match="Spoken English jobs cannot be actionable"):
        JobEvaluation(
            job_id="lever_123",
            fit_score=85.0,
            salary_match=True,
            requires_spoken_english=True,
            tech_stack_detected=["Python"],
            pros=[],
            red_flags=["Daily meetings in English"],
            is_actionable=True
        )