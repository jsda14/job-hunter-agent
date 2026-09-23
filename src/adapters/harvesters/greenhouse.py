from datetime import datetime, timezone
import html
import inspect
import re
from typing import List, Optional

import httpx

from src.domain.models.job import JobRaw, SourcePlatform
from src.domain.ports.harvester import HarvesterConnectionError, JobHarvesterPort


class GreenhouseHarvesterAdapter(JobHarvesterPort):
    """Adapter for harvesting job postings from the Greenhouse public API."""

    def __init__(self, client: Optional[httpx.AsyncClient] = None) -> None:
        self._client = client

    async def fetch_jobs(self, company_slug: str) -> List[JobRaw]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs?content=true"

        try:
            if self._client is not None:
                response = await self._client.get(url)
                status_res = response.raise_for_status()
                if inspect.isawaitable(status_res):
                    await status_res
                data = response.json()
                if inspect.isawaitable(data):
                    data = await data
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url)
                    status_res = response.raise_for_status()
                    if inspect.isawaitable(status_res):
                        await status_res
                    data = response.json()
                    if inspect.isawaitable(data):
                        data = await data
        except httpx.HTTPError as exc:
            raise HarvesterConnectionError(f"HTTP error fetching jobs for '{company_slug}': {exc}") from exc
        except Exception as exc:
            if isinstance(exc, HarvesterConnectionError):
                raise
            raise HarvesterConnectionError(f"Error harvesting jobs from Greenhouse for '{company_slug}': {exc}") from exc

        # CB-02: Formato de respuesta inesperado
        if not isinstance(data, dict) or "jobs" not in data or not isinstance(data.get("jobs"), list):
            raise HarvesterConnectionError(
                f"Expected dict response with 'jobs' list from Greenhouse, got {type(data)}"
            )

        jobs_list = data["jobs"]
        # CB-01: Tablero sin vacantes
        if not jobs_list:
            return []

        jobs: List[JobRaw] = []
        for job_data in jobs_list:
            if not isinstance(job_data, dict):
                continue

            job_id = job_data.get("id")
            title = job_data.get("title")
            absolute_url = job_data.get("absolute_url")

            # CB-03: Descartar ofertas incompletas silenciosamente
            if not job_id or not title or not absolute_url:
                continue

            # RN-03: Fallback de ubicación
            location_info = job_data.get("location")
            location = None
            if isinstance(location_info, dict):
                location = location_info.get("name")
            elif isinstance(location_info, str) and location_info.strip():
                location = location_info.strip()

            if not location:
                location = "Remote"

            # RN-04: Saneamiento de descripción (unescape HTML y remover tags)
            raw_content = job_data.get("content") or ""
            if raw_content:
                unescaped = html.unescape(raw_content)
                cleaned = re.sub(r"<[^<]+?>", "", unescaped).strip()
            else:
                cleaned = ""

            raw_description = cleaned if cleaned else title

            # RN-05: Parseo y fallback de fecha updated_at
            updated_at_str = job_data.get("updated_at")
            posted_at = None
            if updated_at_str and isinstance(updated_at_str, str):
                try:
                    dt = datetime.fromisoformat(updated_at_str)
                    posted_at = dt.astimezone(timezone.utc)
                except Exception:
                    posted_at = None

            try:
                job = JobRaw(
                    id=f"greenhouse_{job_id}",
                    platform=SourcePlatform.GREENHOUSE,
                    external_id=str(job_id),
                    title=title,
                    company=company_slug,
                    url=absolute_url,
                    location=location,
                    raw_description=raw_description,
                    posted_at=posted_at,
                )
                jobs.append(job)
            except Exception:
                continue

        return jobs
