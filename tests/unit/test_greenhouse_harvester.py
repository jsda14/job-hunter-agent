import pytest
import httpx
from datetime import timezone
from unittest.mock import AsyncMock, patch

from tests.harness.fixtures.greenhouse_payload import SAMPLE_GREENHOUSE_RESPONSE
from src.domain.ports.harvester import HarvesterConnectionError
from src.domain.models.job import SourcePlatform
from src.adapters.harvesters.greenhouse import GreenhouseHarvesterAdapter


@pytest.mark.asyncio
async def test_greenhouse_harvester_success():
    """RN-01, RN-02, RN-04, RN-05: Mapeo correcto de campos, plataforma GREENHOUSE, saneamiento HTML y parseo UTC."""
    adapter = GreenhouseHarvesterAdapter()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_GREENHOUSE_RESPONSE
        mock_response.raise_for_status = AsyncMock()
        mock_get.return_value = mock_response

        jobs = await adapter.fetch_jobs("nubank")

        # RN-01: Verificación de URL llamada con content=true
        mock_get.assert_called_once_with(
            "https://boards-api.greenhouse.io/v1/boards/nubank/jobs?content=true"
        )

        assert len(jobs) == 1
        job = jobs[0]

        # RN-02: Mapeo canónico a JobRaw
        assert job.id == "greenhouse_4829102"
        assert job.platform == SourcePlatform.GREENHOUSE
        assert job.external_id == "4829102"
        assert job.title == "Staff Backend Engineer - Python"
        assert job.company == "nubank"
        assert str(job.url) == "https://boards.greenhouse.io/nubank/jobs/4829102"
        assert job.location == "Bogota, Colombia"

        # RN-04: Saneamiento de etiquetas HTML
        assert "<p>" not in job.raw_description
        assert "</p>" not in job.raw_description
        assert "&lt;" not in job.raw_description
        assert "We are looking for a Staff Engineer with Python and FastAPI experience." in job.raw_description

        # RN-05: Conversión de updated_at a UTC
        assert job.posted_at is not None
        assert job.posted_at.tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_greenhouse_harvester_fallbacks():
    """RN-03, RN-05: Fallback de location nulo a 'Remote', posted_at nulo a None y raw_description vacía a title."""
    adapter = GreenhouseHarvesterAdapter()

    payload_with_nulls = {
        "jobs": [
            {
                "id": 999111,
                "title": "Software Engineer",
                "absolute_url": "https://boards.greenhouse.io/nubank/jobs/999111",
                "location": None,
                "updated_at": None,
                "content": "",
            }
        ]
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = payload_with_nulls
        mock_response.raise_for_status = AsyncMock()
        mock_get.return_value = mock_response

        jobs = await adapter.fetch_jobs("nubank")

        assert len(jobs) == 1
        job = jobs[0]
        # RN-03: Fallback location
        assert job.location == "Remote"
        # RN-05: Fallback posted_at
        assert job.posted_at is None
        # RN-04: Fallback raw_description si content viene vacío
        assert job.raw_description == "Software Engineer"


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [404, 500])
async def test_greenhouse_harvester_http_error(status_code):
    """RN-06: Captura de errores HTTP (404/500) y relanzamiento como HarvesterConnectionError."""
    adapter = GreenhouseHarvesterAdapter()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = status_code
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"Error {status_code}", request=AsyncMock(), response=mock_response
        )
        mock_get.return_value = mock_response

        with pytest.raises(HarvesterConnectionError):
            await adapter.fetch_jobs("nonexistent_company")


@pytest.mark.asyncio
async def test_greenhouse_harvester_empty_jobs_returns_empty_list():
    """CB-01: Tablero sin vacantes activas ('jobs': []) retorna lista vacía sin error."""
    adapter = GreenhouseHarvesterAdapter()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"jobs": []}
        mock_response.raise_for_status = AsyncMock()
        mock_get.return_value = mock_response

        jobs = await adapter.fetch_jobs("empty_board")
        assert jobs == []


@pytest.mark.asyncio
async def test_greenhouse_harvester_invalid_payload_raises_connection_error():
    """CB-02: Formato de respuesta inesperado (sin clave 'jobs' o no diccionario) lanza HarvesterConnectionError."""
    adapter = GreenhouseHarvesterAdapter()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "Invalid board requested"}
        mock_response.raise_for_status = AsyncMock()
        mock_get.return_value = mock_response

        with pytest.raises(HarvesterConnectionError):
            await adapter.fetch_jobs("invalid_payload")
