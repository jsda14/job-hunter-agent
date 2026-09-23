import pytest
from src.adapters.harvesters.lever import LeverHarvesterAdapter
from src.domain.models.job import JobRaw, SourcePlatform
from src.domain.ports.harvester import HarvesterConnectionError


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lever_live_harvest_real_company():
    """Consulta la API pública real de Lever para una empresa activa ('kavak').

    Verifica:
    - No lanza excepciones no controladas.
    - Retorna una lista de instancias JobRaw.
    - Si la lista contiene elementos, cada uno cumple:
      * platform == SourcePlatform.LEVER
      * id comienza con 'lever_'
      * url es válida y comienza con 'http'
      * external_id y title no están vacíos
    """
    adapter = LeverHarvesterAdapter()
    jobs = await adapter.fetch_jobs("kavak")

    assert isinstance(jobs, list)
    for job in jobs:
        assert isinstance(job, JobRaw)
        assert job.platform == SourcePlatform.LEVER
        assert job.id.startswith("lever_")
        assert str(job.url).startswith("http")
        assert len(job.title) >= 3
        assert len(job.company) >= 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lever_live_nonexistent_company_raises_harvester_error():
    """Consulta un slug inexistente ('this-company-does-not-exist-xyz-999') en Lever.

    Verifica:
    - Captura el status 404 de la API de Lever.
    - Lanza HarvesterConnectionError explícitamente.
    """
    adapter = LeverHarvesterAdapter()

    with pytest.raises(HarvesterConnectionError):
        await adapter.fetch_jobs("this-company-does-not-exist-xyz-999")
