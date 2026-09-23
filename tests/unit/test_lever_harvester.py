import pytest
import httpx
from unittest.mock import AsyncMock, patch
from tests.harness.fixtures.lever_payload import SAMPLE_LEVER_RESPONSE

from src.domain.ports.harvester import HarvesterConnectionError
from src.adapters.harvesters.lever import LeverHarvesterAdapter
from src.domain.models.job import SourcePlatform


@pytest.mark.asyncio
async def test_lever_harvester_success():
    adapter = LeverHarvesterAdapter()

    # Mockeamos httpx.AsyncClient para no tocar internet en unit tests
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_LEVER_RESPONSE
        mock_response.raise_for_status = AsyncMock()
        mock_get.return_value = mock_response

        jobs = await adapter.fetch_jobs("techcorp")

        assert len(jobs) == 1
        job = jobs[0]
        assert job.id == "lever_lever-uuid-999"
        assert job.platform == SourcePlatform.LEVER
        assert job.external_id == "lever-uuid-999"
        assert job.title == "Senior Python Engineer"
        assert job.company == "techcorp"
        assert "Requirements" in job.raw_description
        assert job.posted_at is not None


@pytest.mark.asyncio
async def test_lever_harvester_http_error():
    adapter = LeverHarvesterAdapter()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=AsyncMock(), response=mock_response
        )
        mock_get.return_value = mock_response

        with pytest.raises(HarvesterConnectionError):
            await adapter.fetch_jobs("nonexistent_company")