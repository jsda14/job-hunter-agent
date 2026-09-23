from abc import ABC, abstractmethod

from src.domain.models.job import JobEvaluation, JobRaw


class PitchGeneratorPort(ABC):
    """Port defining the interface for generating tailored application pitches."""

    @abstractmethod
    async def generate_pitch(self, job: JobRaw, evaluation: JobEvaluation) -> str:
        """Generate a tailored pitch for a given job and its evaluation.

        Args:
            job: The canonical JobRaw instance.
            evaluation: The evaluated job results.

        Returns:
            A persuasive, tailored pitch string.
        """
        raise NotImplementedError
