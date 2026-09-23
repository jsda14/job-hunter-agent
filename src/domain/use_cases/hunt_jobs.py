from typing import Any, List, Tuple, Union

from src.domain.models.job import JobEvaluation, JobRaw
from src.domain.ports.evaluator import JobEvaluatorPort
from src.domain.ports.harvester import CompanyTarget, HarvesterConnectionError, JobHarvesterPort
from src.domain.ports.pitch_generator import PitchGeneratorPort


class JobHunterUseCase:
    """Core orchestrator use case to harvest, evaluate and enrich actionable jobs."""

    def __init__(
        self,
        harvester: Any,
        evaluator: JobEvaluatorPort,
        pitch_generator: PitchGeneratorPort,
    ) -> None:
        self.harvester = harvester
        self.evaluator = evaluator
        self.pitch_generator = pitch_generator

    async def execute(
        self, targets: Union[List[str], List[CompanyTarget]]
    ) -> List[Tuple[JobRaw, JobEvaluation]]:
        """Harvest jobs from target companies, evaluate against criteria, and enrich actionable jobs with pitches.

        Args:
            targets: List of company slugs (List[str]) or list of structured CompanyTarget instances.

        Returns:
            List of (JobRaw, JobEvaluation) tuples for all actionable job postings.
        """
        if not targets:
            return []

        actionable_results: List[Tuple[JobRaw, JobEvaluation]] = []
        collected_jobs: List[JobRaw] = []

        first_target = targets[0]
        if isinstance(first_target, CompanyTarget):
            # Delegar directamente al composite si soporta fetch_jobs_from_targets
            if hasattr(self.harvester, "fetch_jobs_from_targets"):
                collected_jobs = await self.harvester.fetch_jobs_from_targets(targets)
            else:
                for target in targets:
                    try:
                        jobs = await self.harvester.fetch_jobs(target.company_slug)
                        collected_jobs.extend(jobs)
                    except HarvesterConnectionError:
                        continue
        else:
            # Recolección tradicional con lista de strings (company_slugs)
            for company_slug in targets:
                try:
                    jobs = await self.harvester.fetch_jobs(company_slug)
                    collected_jobs.extend(jobs)
                except HarvesterConnectionError:
                    continue

        for job in collected_jobs:
            evaluation = await self.evaluator.evaluate(job)
            if evaluation.is_actionable:
                pitch = await self.pitch_generator.generate_pitch(job, evaluation)
                evaluation.tailored_pitch = pitch
                actionable_results.append((job, evaluation))

        return actionable_results
