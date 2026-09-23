from typing import List, Tuple

from src.domain.models.job import JobEvaluation, JobRaw
from src.domain.ports.notifier import JobNotifierPort


class ConsoleNotifierAdapter(JobNotifierPort):
    """Adapter for outputting actionable jobs to console output."""

    async def notify(self, jobs: List[Tuple[JobRaw, JobEvaluation]]) -> int:
        if not jobs:
            print("No se encontraron vacantes accionables.")
            return 0

        for job, evaluation in jobs:
            stack_str = ", ".join(evaluation.tech_stack_detected) if evaluation.tech_stack_detected else "N/A"
            pitch_str = evaluation.tailored_pitch or "Sin pitch generado"

            card = (
                f"\n==================================================\n"
                f"[VACANTE] {job.title}\n"
                f"[EMPRESA] {job.company}\n"
                f"[URL]     {job.url}\n"
                f"[FIT]     {evaluation.fit_score:.1f}%\n"
                f"[STACK]   {stack_str}\n"
                f"[PITCH]\n{pitch_str}\n"
                f"=================================================="
            )
            print(card)

        return len(jobs)
