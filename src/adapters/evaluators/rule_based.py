import re
from typing import List

from src.domain.models.job import JobEvaluation, JobRaw
from src.domain.ports.evaluator import JobEvaluatorPort

SPOKEN_ENGLISH_TRIGGERS: List[str] = [
    "fluent english",
    "c1 english",
    "native english",
    "excellent verbal english",
    "fluent spoken english",
]

AUDITED_TECH_STACK: List[str] = [
    "python",
    "fastapi",
    "react",
    "angular",
    "ai agents",
    "rag",
    "docker",
    "clean architecture",
    "hexagonal",
]


class RuleBasedEvaluatorAdapter(JobEvaluatorPort):
    """Rule-based heuristic evaluator checking job postings against candidate profile."""

    async def evaluate(self, job: JobRaw) -> JobEvaluation:
        description = job.raw_description

        # 1. Detection of strict spoken English
        requires_spoken_english = False
        red_flags: List[str] = []
        for trigger in SPOKEN_ENGLISH_TRIGGERS:
            pattern = rf"\b{re.escape(trigger)}\b"
            if re.search(pattern, description, re.IGNORECASE):
                requires_spoken_english = True
                red_flags.append("Requiere inglés hablado fluido (excluyente)")
                break

        # 2. Detection of tech stack
        tech_stack_detected: List[str] = []
        pros: List[str] = []
        for tech in AUDITED_TECH_STACK:
            pattern = rf"\b{re.escape(tech)}\b"
            if re.search(pattern, description, re.IGNORECASE):
                tech_stack_detected.append(tech)
                pros.append(f"Experiencia coincidente en {tech}")

        # 3. Calculation of fit_score
        fit_score = 50.0 + (len(tech_stack_detected) * 10.0)
        fit_score = min(100.0, fit_score)

        if requires_spoken_english:
            fit_score = max(0.0, fit_score - 40.0)
            is_actionable = False
        else:
            is_actionable = fit_score >= 70.0

        tailored_pitch = None
        if is_actionable:
            tailored_pitch = (
                f"Perfil altamente alineado con las tecnologías requeridas: "
                f"{', '.join(tech_stack_detected)}."
            )

        return JobEvaluation(
            job_id=job.id,
            fit_score=fit_score,
            salary_match=True,
            requires_spoken_english=requires_spoken_english,
            tech_stack_detected=tech_stack_detected,
            pros=pros,
            red_flags=red_flags,
            is_actionable=is_actionable,
            tailored_pitch=tailored_pitch,
        )
