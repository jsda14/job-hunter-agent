import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone

from src.domain.models.job import JobRaw, SourcePlatform
from src.domain.ports.harvester import (
    JobHarvesterPort,
    HarvesterConnectionError,
    UnsupportedPlatformError,
    CompanyTarget,
)
from src.adapters.harvesters.composite import CompositeHarvesterAdapter


def make_dummy_job(job_id: str, platform: SourcePlatform, company: str) -> JobRaw:
    return JobRaw(
        id=f"{platform.value}_{job_id}",
        platform=platform,
        external_id=job_id,
        title="Senior Software Engineer",
        company=company,
        url=f"https://jobs.example.com/{company}/{job_id}",
        location="Remote",
        raw_description="Looking for Python engineers.",
        posted_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_composite_harvester_dispatches_and_consolidates_multiplatform():
    """RN-01, RN-04: Despacho a harvesters respectivos y consolidación en una sola lista de JobRaw."""
    lever_mock = AsyncMock(spec=JobHarvesterPort)
    gh_mock = AsyncMock(spec=JobHarvesterPort)

    job_lever = make_dummy_job("101", SourcePlatform.LEVER, "techcorp")
    job_gh = make_dummy_job("202", SourcePlatform.GREENHOUSE, "nubank")

    lever_mock.fetch_jobs.return_value = [job_lever]
    gh_mock.fetch_jobs.return_value = [job_gh]

    composite = CompositeHarvesterAdapter({
        SourcePlatform.LEVER: lever_mock,
        SourcePlatform.GREENHOUSE: gh_mock,
    })

    targets = [
        CompanyTarget(company_slug="techcorp", platform=SourcePlatform.LEVER),
        CompanyTarget(company_slug="nubank", platform=SourcePlatform.GREENHOUSE),
    ]

    results = await composite.fetch_jobs_from_targets(targets)

    assert len(results) == 2
    assert results[0] == job_lever
    assert results[1] == job_gh
    lever_mock.fetch_jobs.assert_awaited_once_with("techcorp")
    gh_mock.fetch_jobs.assert_awaited_once_with("nubank")


@pytest.mark.asyncio
async def test_composite_harvester_dynamic_registration_and_overwrite():
    """RN-02: Registro dinámico mediante register() y sobrescritura de adaptadores."""
    lever_mock_1 = AsyncMock(spec=JobHarvesterPort)
    lever_mock_2 = AsyncMock(spec=JobHarvesterPort)

    job_1 = make_dummy_job("1", SourcePlatform.LEVER, "co1")
    job_2 = make_dummy_job("2", SourcePlatform.LEVER, "co1")

    lever_mock_1.fetch_jobs.return_value = [job_1]
    lever_mock_2.fetch_jobs.return_value = [job_2]

    composite = CompositeHarvesterAdapter()
    composite.register(SourcePlatform.LEVER, lever_mock_1)

    target = [CompanyTarget(company_slug="co1", platform=SourcePlatform.LEVER)]
    res_1 = await composite.fetch_jobs_from_targets(target)
    assert res_1 == [job_1]
    lever_mock_1.fetch_jobs.assert_awaited_once_with("co1")

    # Sobrescritura con nuevo harvester
    composite.register(SourcePlatform.LEVER, lever_mock_2)
    res_2 = await composite.fetch_jobs_from_targets(target)
    assert res_2 == [job_2]
    lever_mock_2.fetch_jobs.assert_awaited_once_with("co1")


@pytest.mark.asyncio
async def test_composite_harvester_fault_isolation_on_connection_error():
    """RN-03: Si un objetivo lanza HarvesterConnectionError, los demás objetivos continúan con éxito."""
    lever_mock = AsyncMock(spec=JobHarvesterPort)
    gh_mock = AsyncMock(spec=JobHarvesterPort)

    lever_mock.fetch_jobs.side_effect = HarvesterConnectionError("Lever endpoint timeout")
    job_gh = make_dummy_job("303", SourcePlatform.GREENHOUSE, "rappi")
    gh_mock.fetch_jobs.return_value = [job_gh]

    composite = CompositeHarvesterAdapter({
        SourcePlatform.LEVER: lever_mock,
        SourcePlatform.GREENHOUSE: gh_mock,
    })

    targets = [
        CompanyTarget(company_slug="failing_corp", platform=SourcePlatform.LEVER),
        CompanyTarget(company_slug="rappi", platform=SourcePlatform.GREENHOUSE),
    ]

    results = await composite.fetch_jobs_from_targets(targets)

    assert len(results) == 1
    assert results[0] == job_gh
    lever_mock.fetch_jobs.assert_awaited_once_with("failing_corp")
    gh_mock.fetch_jobs.assert_awaited_once_with("rappi")


@pytest.mark.asyncio
async def test_composite_harvester_raises_unsupported_platform_error():
    """RN-05: Si se solicita una plataforma no registrada en el composite, lanza UnsupportedPlatformError."""
    lever_mock = AsyncMock(spec=JobHarvesterPort)
    composite = CompositeHarvesterAdapter({
        SourcePlatform.LEVER: lever_mock,
    })

    targets = [
        CompanyTarget(company_slug="ashby_corp", platform=SourcePlatform.ASHBY),
    ]

    with pytest.raises(UnsupportedPlatformError):
        await composite.fetch_jobs_from_targets(targets)


@pytest.mark.asyncio
async def test_composite_harvester_empty_targets_returns_empty_list():
    """CB-01: Lista de targets vacía retorna [] inmediatamente."""
    composite = CompositeHarvesterAdapter()
    results = await composite.fetch_jobs_from_targets([])
    assert results == []


@pytest.mark.asyncio
async def test_composite_harvester_all_targets_failing_returns_empty_list():
    """CB-02: Si todos los objetivos fallan con HarvesterConnectionError, retorna []."""
    lever_mock = AsyncMock(spec=JobHarvesterPort)
    gh_mock = AsyncMock(spec=JobHarvesterPort)

    lever_mock.fetch_jobs.side_effect = HarvesterConnectionError("Lever down")
    gh_mock.fetch_jobs.side_effect = HarvesterConnectionError("Greenhouse down")

    composite = CompositeHarvesterAdapter({
        SourcePlatform.LEVER: lever_mock,
        SourcePlatform.GREENHOUSE: gh_mock,
    })

    targets = [
        CompanyTarget(company_slug="lever_co", platform=SourcePlatform.LEVER),
        CompanyTarget(company_slug="gh_co", platform=SourcePlatform.GREENHOUSE),
    ]

    results = await composite.fetch_jobs_from_targets(targets)
    assert results == []
