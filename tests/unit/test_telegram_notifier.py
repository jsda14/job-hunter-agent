import os
from unittest.mock import AsyncMock, patch
import httpx
import pytest

from src.domain.models.job import JobEvaluation, JobRaw, SourcePlatform
from src.domain.ports.notifier import (
    NotifierConfigurationError,
    NotifierDeliveryError,
)
from src.adapters.notifiers.telegram import TelegramNotifierAdapter


@pytest.fixture
def sample_job():
    raw_job = JobRaw(
        id="lever-123",
        platform=SourcePlatform.LEVER,
        external_id="123",
        title="Senior Python Backend Engineer",
        company="Kavak",
        url="https://jobs.lever.co/kavak/123",
        location="Remote",
        raw_description="We are seeking a Senior Python Engineer.",
    )
    evaluation = JobEvaluation(
        job_id="lever-123",
        fit_score=92.5,
        salary_match=True,
        requires_spoken_english=False,
        is_actionable=True,
        tech_stack_detected=["Python", "FastAPI", "PostgreSQL"],
        tailored_pitch="He desarrollado plataformas escalables con FastAPI y Python.",
    )
    return raw_job, evaluation


@pytest.mark.asyncio
async def test_telegram_notifier_success_with_injected_client(sample_job):
    raw_job, evaluation = sample_job
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = httpx.Response(
        200,
        json={"ok": True, "result": {"message_id": 999}},
        request=httpx.Request("POST", "https://api.telegram.org/bottest_token/sendMessage"),
    )

    adapter = TelegramNotifierAdapter(
        bot_token="test_token",
        chat_id="123456789",
        client=mock_client,
    )

    count = await adapter.notify([(raw_job, evaluation)])

    assert count == 1
    assert mock_client.post.call_count == 1
    call_args = mock_client.post.call_args
    assert call_args[0][0] == "https://api.telegram.org/bottest_token/sendMessage"
    payload = call_args[1]["json"]
    assert payload["chat_id"] == "123456789"
    assert payload["parse_mode"] == "HTML"
    assert payload["disable_web_page_preview"] is True

    text = payload["text"]
    assert "Senior Python Backend Engineer" in text
    assert "Kavak" in text
    assert "https://jobs.lever.co/kavak/123" in text
    assert "92.5%" in text
    assert "Python, FastAPI, PostgreSQL" in text
    assert "<pre>He desarrollado plataformas escalables con FastAPI y Python.</pre>" in text


@pytest.mark.asyncio
async def test_telegram_notifier_missing_credentials_raises_configuration_error(sample_job, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    # Ambos faltantes
    adapter = TelegramNotifierAdapter()
    with pytest.raises(NotifierConfigurationError):
        await adapter.notify([sample_job])

    # Solo chat_id presente
    adapter_no_token = TelegramNotifierAdapter(bot_token=None, chat_id="12345")
    with pytest.raises(NotifierConfigurationError):
        await adapter_no_token.notify([sample_job])

    # Solo bot_token presente
    adapter_no_chat = TelegramNotifierAdapter(bot_token="my_token", chat_id=None)
    with pytest.raises(NotifierConfigurationError):
        await adapter_no_chat.notify([sample_job])

    # Credenciales compuestas únicamente por espacios en blanco
    adapter_whitespace = TelegramNotifierAdapter(bot_token="   ", chat_id="   ")
    with pytest.raises(NotifierConfigurationError):
        await adapter_whitespace.notify([sample_job])


@pytest.mark.asyncio
async def test_telegram_notifier_empty_jobs_returns_zero_immediately(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    adapter = TelegramNotifierAdapter(bot_token=None, chat_id=None)
    count = await adapter.notify([])
    assert count == 0


@pytest.mark.asyncio
async def test_telegram_notifier_env_var_fallback(sample_job, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "env_bot_token_abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "env_chat_id_999")

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = httpx.Response(
        200,
        json={"ok": True},
        request=httpx.Request("POST", "https://api.telegram.org/botenv_bot_token_abc/sendMessage"),
    )

    adapter = TelegramNotifierAdapter(client=mock_client)
    assert adapter.bot_token == "env_bot_token_abc"
    assert adapter.chat_id == "env_chat_id_999"

    count = await adapter.notify([sample_job])
    assert count == 1
    assert mock_client.post.call_args[0][0] == "https://api.telegram.org/botenv_bot_token_abc/sendMessage"


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code,err_desc", [
    (400, "Bad Request: can't parse entities"),
    (401, "Unauthorized: invalid bot token"),
    (403, "Forbidden: bot was blocked by the user"),
    (500, "Internal Server Error"),
])
async def test_telegram_notifier_http_error_raises_delivery_error(sample_job, status_code, err_desc):
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = httpx.Response(
        status_code,
        json={"ok": False, "description": err_desc},
        request=httpx.Request("POST", "https://api.telegram.org/bottoken/sendMessage"),
    )

    adapter = TelegramNotifierAdapter(
        bot_token="dummy_token",
        chat_id="123456",
        client=mock_client,
    )

    with pytest.raises(NotifierDeliveryError):
        await adapter.notify([sample_job])


@pytest.mark.asyncio
async def test_telegram_notifier_network_timeout_raises_delivery_error(sample_job):
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.side_effect = httpx.ConnectTimeout("Connection timed out to telegram")

    adapter = TelegramNotifierAdapter(
        bot_token="dummy_token",
        chat_id="123456",
        client=mock_client,
    )

    with pytest.raises(NotifierDeliveryError):
        await adapter.notify([sample_job])


@pytest.mark.asyncio
async def test_telegram_notifier_html_sanitization():
    raw_job = JobRaw(
        id="lever-x",
        platform=SourcePlatform.LEVER,
        external_id="x",
        title="Tech Lead <C++ & C# / AI Systems>",
        company="R&D Labs <Global>",
        url="https://jobs.lever.co/rnd/1",
        location="Remote",
        raw_description="Desc",
    )
    evaluation = JobEvaluation(
        job_id="lever-x",
        fit_score=90.0,
        salary_match=True,
        requires_spoken_english=False,
        is_actionable=True,
        tech_stack_detected=["C++", "C#"],
        tailored_pitch="Experience using <iostream> & 'threading' with pointers -> fast code.",
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = httpx.Response(
        200,
        json={"ok": True},
        request=httpx.Request("POST", "https://api.telegram.org/bottoken/sendMessage"),
    )

    adapter = TelegramNotifierAdapter(
        bot_token="dummy_token",
        chat_id="123456",
        client=mock_client,
    )

    await adapter.notify([(raw_job, evaluation)])

    payload = mock_client.post.call_args[1]["json"]
    text = payload["text"]

    # Verifica sanitización de entidades
    assert "&lt;C++ &amp; C# / AI Systems&gt;" in text
    assert "<C++ & C# / AI Systems>" not in text
    assert "&lt;Global&gt;" in text
    assert "&lt;iostream&gt; &amp; 'threading'" in text


@pytest.mark.asyncio
async def test_telegram_notifier_fallback_pitch_when_none(sample_job):
    raw_job, evaluation = sample_job
    evaluation.tailored_pitch = None

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = httpx.Response(
        200,
        json={"ok": True},
        request=httpx.Request("POST", "https://api.telegram.org/bottoken/sendMessage"),
    )

    adapter = TelegramNotifierAdapter(
        bot_token="dummy_token",
        chat_id="123456",
        client=mock_client,
    )

    await adapter.notify([(raw_job, evaluation)])

    payload = mock_client.post.call_args[1]["json"]
    text = payload["text"]
    assert "Sin pitch generado" in text


@pytest.mark.asyncio
async def test_telegram_notifier_creates_own_client_when_none_injected(sample_job):
    raw_job, evaluation = sample_job

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_instance.post.return_value = httpx.Response(
            200,
            json={"ok": True},
            request=httpx.Request("POST", "https://api.telegram.org/bottoken/sendMessage"),
        )
        mock_client_cls.return_value = mock_instance

        adapter = TelegramNotifierAdapter(
            bot_token="dummy_token",
            chat_id="123456",
            client=None,
        )

        count = await adapter.notify([(raw_job, evaluation)])
        assert count == 1
        assert mock_instance.post.await_count == 1
