from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.job import JobEvaluation, JobRaw


class JobRepositoryPort(ABC):
    """Port defining the interface for job persistence and deduplication."""

    @abstractmethod
    async def is_seen(self, job_id: str) -> bool:
        """Check if a job_id has already been processed and recorded.

        Args:
            job_id: Canonical job identifier (e.g. 'lever_123', 'greenhouse_456').

        Returns:
            True if job_id already exists in repository; False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    async def save_job(self, job: JobRaw, evaluation: Optional[JobEvaluation] = None) -> None:
        """Record or update a job posting and its evaluation in the repository.

        Args:
            job: Canonical JobRaw instance.
            evaluation: Optional JobEvaluation instance generated for the job.
        """
        raise NotImplementedError

    @abstractmethod
    async def filter_unseen(self, jobs: List[JobRaw]) -> List[JobRaw]:
        """Filter a list of job postings, returning only those not yet in the repository.

        Args:
            jobs: List of JobRaw instances to verify.

        Returns:
            List of previously unseen JobRaw instances, preserving original order.
        """
        raise NotImplementedError
