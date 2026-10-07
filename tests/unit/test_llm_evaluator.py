import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.evaluators.llm_deepseek import DeepSeekEvaluatorAdapter
from src.domain.models.job import JobRaw, SourcePlatform
from src.domain.ports.evaluator import LLMEvaluatorError


def _make_job(title: str = "Senior Python Engineer", description: str = "Python FastAPI remote") -> JobRaw:
    return JobRaw(
        id="lever_test123",
        platform=SourcePlatform.LEVER,
        external_id="test123",
        title=title,
        company="testcorp",
        url="https://jobs.lever.co/testcorp/test123",
        location="Remote",
        raw_description=description,
    )


def _mock_client(response_data: dict) -> AsyncMock:
    """Build a mock httpx.AsyncClient that returns a DeepSeek-shaped response."""
    content = json.dumps(response_data)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    return mock_client


@pytest.mark.asyncio
async def test_actionable_senior_role_returns_high_score():
    llm_payload = {
        "fit_score": 85.0,
        "salary_match": True,
        "requires_spoken_english": False,
        "tech_stack_detected": ["python", "fastapi", "docker"],
        "pros": ["Stack alineado", "Rol senior", "Remoto"],
        "red_flags": [],
        "is_actionable": True,
        "reasoning": "Rol senior con stack alineado y modalidad remota.",
    }
    adapter = DeepSeekEvaluatorAdapter(api_key="fake-key", client=_mock_client(llm_payload))
    result = await adapter.evaluate(_make_job())

    assert result.is_actionable is True
    assert result.fit_score == 85.0
    assert result.requires_spoken_english is False
    assert "python" in result.tech_stack_detected


@pytest.mark.asyncio
async def test_junior_role_is_not_actionable():
    llm_payload = {
        "fit_score": 25.0,
        "salary_match": False,
        "requires_spoken_english": False,
        "tech_stack_detected": ["python"],
        "pros": [],
        "red_flags": ["Rol junior — menos de 3 años requeridos"],
        "is_actionable": False,
        "reasoning": "Rol junior descartado por seniority.",
    }
    adapter = DeepSeekEvaluatorAdapter(api_key="fake-key", client=_mock_client(llm_payload))
    result = await adapter.evaluate(_make_job(title="Junior Python Developer"))

    assert result.is_actionable is False
    assert result.fit_score <= 30.0
    assert len(result.red_flags) > 0


@pytest.mark.asyncio
async def test_spoken_english_required_is_not_actionable():
    llm_payload = {
        "fit_score": 60.0,
        "salary_match": True,
        "requires_spoken_english": True,
        "tech_stack_detected": ["python", "react"],
        "pros": ["Stack alineado"],
        "red_flags": ["Requiere inglés hablado fluido — excluyente"],
        "is_actionable": False,
        "reasoning": "Requiere inglés conversacional, excluyente para el candidato.",
    }
    adapter = DeepSeekEvaluatorAdapter(api_key="fake-key", client=_mock_client(llm_payload))
    result = await adapter.evaluate(_make_job(description="Fluent spoken English required for daily standups"))

    assert result.requires_spoken_english is True
    assert result.is_actionable is False


@pytest.mark.asyncio
async def test_http_error_raises_llm_evaluator_error():
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Rate limit exceeded"
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    adapter = DeepSeekEvaluatorAdapter(api_key="fake-key", client=mock_client)
    with pytest.raises(LLMEvaluatorError, match="HTTP 429"):
        await adapter.evaluate(_make_job())


@pytest.mark.asyncio
async def test_invalid_json_response_raises_llm_evaluator_error():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "not valid json {"}}]
    }
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    adapter = DeepSeekEvaluatorAdapter(api_key="fake-key", client=mock_client)
    with pytest.raises(LLMEvaluatorError, match="non-JSON"):
        await adapter.evaluate(_make_job())
