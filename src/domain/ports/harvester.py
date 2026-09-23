from abc import ABC, abstractmethod
from typing import List

from src.domain.models.job import JobRaw


class HarvesterConnectionError(Exception):
    """Exception raised when an external harvesting service fails or cannot be reached."""
    pass


class JobHarvesterPort(ABC):
    """Port defining the interface for harvesting job postings."""

    @abstractmethod
    async def fetch_jobs(self, company_slug: str) -> List[JobRaw]:
        """Fetch and normalize job postings for a given company slug.

        Args:
            company_slug: Identifier/slug of the company in the ATS.

        Returns:
            A list of canonical JobRaw instances.

        Raises:
            HarvesterConnectionError: If network request fails or returns an error status code.
        """
        raise NotImplementedError
