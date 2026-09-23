from datetime import datetime, timezone
import inspect
from typing import List, Optional

import httpx

from src.domain.models.job import JobRaw, SourcePlatform
from src.domain.ports.harvester import HarvesterConnectionError, JobHarvesterPort


class LeverHarvesterAdapter(JobHarvesterPort):
    """Adapter for harvesting job postings from the Lever public API."""

    def __init__(self, client: Optional[httpx.AsyncClient] = None) -> None:
        self._client = client

    async def fetch_jobs(self, company_slug: str) -> List[JobRaw]:
        url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"

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
            raise HarvesterConnectionError(f"Error harvesting jobs from Lever for '{company_slug}': {exc}") from exc

        if not isinstance(data, list):
            raise HarvesterConnectionError(f"Expected list response from Lever, got {type(data)}")

        jobs: List[JobRaw] = []
        for posting in data:
            if not isinstance(posting, dict):
                continue

            posting_id = posting.get("id")
            title = posting.get("text")
            hosted_url = posting.get("hostedUrl")

            # Ignore jobs missing essential identifier, title or url
            if not posting_id or not title or not hosted_url:
                continue

            # Location: fallback to "Remote" if not present
            categories = posting.get("categories") or {}
            location = categories.get("location") if isinstance(categories, dict) else None
            if not location:
                location = "Remote"

            # Raw description: concatenate descriptionPlain and items from lists
            description_plain = posting.get("descriptionPlain") or ""
            desc_parts = [description_plain] if description_plain else []

            for item in posting.get("lists") or []:
                if isinstance(item, dict):
                    item_text = item.get("text") or ""
                    item_content = item.get("content") or ""
                    combined = "\n".join(part for part in [item_text, item_content] if part)
                    if combined:
                        desc_parts.append(combined)
                elif isinstance(item, str) and item:
                    desc_parts.append(item)

            raw_description = "\n\n".join(desc_parts).strip()
            if not raw_description:
                raw_description = title

            # Posted at timestamp conversion
            created_at = posting.get("createdAt")
            posted_at = None
            if isinstance(created_at, (int, float)):
                posted_at = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)

            try:
                job = JobRaw(
                    id=f"lever_{posting_id}",
                    platform=SourcePlatform.LEVER,
                    external_id=str(posting_id),
                    title=title,
                    company=company_slug,
                    url=hosted_url,
                    location=location,
                    raw_description=raw_description,
                    posted_at=posted_at,
                )
                jobs.append(job)
            except Exception:
                # Discard cleanly if invalid
                continue

        return jobs
