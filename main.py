import asyncio
from pathlib import Path

from src.adapters.evaluators.pitch_generator import RuleBasedPitchGeneratorAdapter
from src.adapters.evaluators.rule_based import RuleBasedEvaluatorAdapter
from src.adapters.harvesters.composite import CompositeHarvesterAdapter
from src.adapters.harvesters.greenhouse import GreenhouseHarvesterAdapter
from src.adapters.harvesters.lever import LeverHarvesterAdapter
from src.adapters.loaders.json_targets import JsonTargetLoaderAdapter
from src.adapters.notifiers.console import ConsoleNotifierAdapter
from src.adapters.repositories.sqlite import SQLiteJobRepositoryAdapter
from src.domain.models.job import SourcePlatform
from src.domain.use_cases.hunt_jobs import JobHunterUseCase


async def main() -> None:
    # 1. Dependency instantiation
    composite_harvester = CompositeHarvesterAdapter({
        SourcePlatform.LEVER: LeverHarvesterAdapter(),
        SourcePlatform.GREENHOUSE: GreenhouseHarvesterAdapter(),
    })
    evaluator = RuleBasedEvaluatorAdapter()
    pitch_generator = RuleBasedPitchGeneratorAdapter()
    notifier = ConsoleNotifierAdapter()
    target_loader = JsonTargetLoaderAdapter()
    repository = SQLiteJobRepositoryAdapter("data/job_hunter.db")

    # 2. Use case orchestration with deduplication
    use_case = JobHunterUseCase(
        harvester=composite_harvester,
        evaluator=evaluator,
        pitch_generator=pitch_generator,
        repository=repository,
    )

    # 3. Load target companies from configuration
    config_file = Path("companies.json")
    targets = target_loader.load_targets(config_file)
    target_names = [f"{t.name or t.company_slug} ({t.platform.value})" for t in targets]

    print(f"[*] Iniciando prospeccion de vacantes para: {', '.join(target_names)}...\n")
    actionable_jobs = await use_case.execute(targets)

    # 4. Notify results
    total_notified = await notifier.notify(actionable_jobs)
    print(f"\n[+] Proceso finalizado. Total de vacantes accionables notificadas: {total_notified}")


if __name__ == "__main__":
    asyncio.run(main())
