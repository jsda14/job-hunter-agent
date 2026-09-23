from typing import Any, List, Optional, Tuple, Union

from src.domain.models.job import JobEvaluation, JobRaw
from src.domain.ports.evaluator import JobEvaluatorPort
from src.domain.ports.harvester import CompanyTarget, HarvesterConnectionError, JobHarvesterPort
from src.domain.ports.pitch_generator import PitchGeneratorPort
from src.domain.ports.repository import JobRepositoryPort


class JobHunterUseCase:
    """Core orchestrator use case to harvest, evaluate and enrich actionable jobs."""

    def __init__(
        self,
        harvester: Any,
        evaluator: JobEvaluatorPort,
        pitch_generator: PitchGeneratorPort,
        repository: Optional[JobRepositoryPort] = None,
    ) -> None:
        self.harvester = harvester
        self.evaluator = evaluator
        self.pitch_generator = pitch_generator
        self.repository = repository

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

        # RN-05: Filtrado de vacantes previamente no vistas si hay repositorio
        if self.repository is not None:
            collected_jobs = await self.repository.filter_unseen(collected_jobs)

        for job in collected_jobs:
            evaluation = await self.evaluator.evaluate(job)
            if evaluation.is_actionable:
                pitch = await self.pitch_generator.generate_pitch(job, evaluation)
                evaluation.tailored_pitch = pitch
                actionable_results.append((job, evaluation))

            # RN-05: Registrar vacante procesada en el repositorio
            if self.repository is not None:
                await self.repository.save_job(job, evaluation)

        return actionable_results
