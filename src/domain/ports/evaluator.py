from abc import ABC, abstractmethod

from src.domain.models.job import JobEvaluation, JobRaw


class JobEvaluatorPort(ABC):
    """Port defining the interface for evaluating job postings against candidate profile."""

    @abstractmethod
    async def evaluate(self, job: JobRaw) -> JobEvaluation:
        """Evaluate a raw job posting and return a structured evaluation.

        Args:
            job: The canonical JobRaw instance.

        Returns:
            A canonical JobEvaluation instance.
        """
        raise NotImplementedError
