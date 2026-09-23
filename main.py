import asyncio
from typing import List

from src.adapters.evaluators.pitch_generator import RuleBasedPitchGeneratorAdapter
from src.adapters.evaluators.rule_based import RuleBasedEvaluatorAdapter
from src.adapters.harvesters.lever import LeverHarvesterAdapter
from src.adapters.notifiers.console import ConsoleNotifierAdapter
from src.domain.use_cases.hunt_jobs import JobHunterUseCase


async def main() -> None:
    # 1. Dependency instantiation
    harvester = LeverHarvesterAdapter()
    evaluator = RuleBasedEvaluatorAdapter()
    pitch_generator = RuleBasedPitchGeneratorAdapter()
    notifier = ConsoleNotifierAdapter()

    # 2. Use case orchestration
    use_case = JobHunterUseCase(
        harvester=harvester,
        evaluator=evaluator,
        pitch_generator=pitch_generator,
    )

    # 3. Target companies
    target_companies: List[str] = ["mercadolibre", "rappi", "nubank"]

    print(f"[*] Iniciando prospeccion de vacantes para: {', '.join(target_companies)}...\n")
    actionable_jobs = await use_case.execute(target_companies)

    # 4. Notify results
    total_notified = await notifier.notify(actionable_jobs)
    print(f"\n[+] Proceso finalizado. Total de vacantes accionables notificadas: {total_notified}")


if __name__ == "__main__":
    asyncio.run(main())
