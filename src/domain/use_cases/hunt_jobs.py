from typing import List, Tuple

from src.domain.models.job import JobEvaluation, JobRaw
from src.domain.ports.evaluator import JobEvaluatorPort
from src.domain.ports.harvester import HarvesterConnectionError, JobHarvesterPort
from src.domain.ports.pitch_generator import PitchGeneratorPort


class JobHunterUseCase:
    """Core orchestrator use case to harvest, evaluate and enrich actionable jobs."""

    def __init__(
        self,
        harvester: JobHarvesterPort,
        evaluator: JobEvaluatorPort,
        pitch_generator: PitchGeneratorPort,
    ) -> None:
        self.harvester = harvester
        self.evaluator = evaluator
        self.pitch_generator = pitch_generator

    async def execute(
        self, company_slugs: List[str]
    ) -> List[Tuple[JobRaw, JobEvaluation]]:
        """Harvest jobs from target companies, evaluate against criteria, and enrich actionable jobs with pitches.

        Args:
            company_slugs: List of company slugs to fetch postings from.

        Returns:
            List of (JobRaw, JobEvaluation) tuples for all actionable job postings.
        """
        actionable_results: List[Tuple[JobRaw, JobEvaluation]] = []

        for company_slug in company_slugs:
            try:
                jobs = await self.harvester.fetch_jobs(company_slug)
            except HarvesterConnectionError:
                # Log or swallow connection errors gracefully to allow other companies to proceed
                continue

            for job in jobs:
                evaluation = await self.evaluator.evaluate(job)
                if evaluation.is_actionable:
                    pitch = await self.pitch_generator.generate_pitch(job, evaluation)
                    evaluation.tailored_pitch = pitch
                    actionable_results.append((job, evaluation))

        return actionable_results
