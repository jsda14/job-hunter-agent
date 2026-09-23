from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel, Field

from src.domain.models.job import JobRaw, SourcePlatform


class HarvesterConnectionError(Exception):
    """Exception raised when an external harvesting service fails or cannot be reached."""
    pass


class UnsupportedPlatformError(Exception):
    """Exception raised when harvesting is requested for an unregistered platform."""
    pass


class CompanyTarget(BaseModel):
    """Structured harvesting target associating a company slug with its ATS platform."""
    company_slug: str = Field(min_length=1, description="Company slug or identifier in the ATS")
    platform: SourcePlatform = Field(description="ATS platform hosting the job posting")
    name: Optional[str] = Field(default=None, description="Human-readable company name")


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
