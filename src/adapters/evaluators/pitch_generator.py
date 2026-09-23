from src.domain.models.job import JobEvaluation, JobRaw
from src.domain.ports.pitch_generator import PitchGeneratorPort


class RuleBasedPitchGeneratorAdapter(PitchGeneratorPort):
    """Generates tailored pitches highlighting relevant past projects based on detected tech stack."""

    async def generate_pitch(self, job: JobRaw, evaluation: JobEvaluation) -> str:
        detected_stack = {tech.lower() for tech in evaluation.tech_stack_detected}

        # Rule 1: AI & Backend emphasis (fastapi, rag, ai agents)
        if any(tech in detected_stack for tech in ("fastapi", "rag", "ai agents")):
            return (
                f"Hola equipo de {job.company}, me entusiasma la vacante de {job.title}. "
                f"Cuento con amplia experiencia en Python y arquitecturas basadas en IA, destacando la construcción de un "
                f"microservicio de observabilidad bancaria con agentic loop, RAG semántico en ChromaDB y colas Redis Streams con cobertura de pruebas. "
                f"Mi enfoque garantiza alta confiabilidad, resiliencia y código mantenible. "
                f"Quedo a su disposición para coordinar una conversación técnica y profundizar en cómo aportar valor inmediato al equipo."
            )

        # Rule 2: Frontend & Real-time telemetry emphasis (react, telemetry, charts)
        if any(tech in detected_stack for tech in ("react", "telemetry", "charts")):
            return (
                f"Hola equipo de {job.company}, me entusiasma la vacante de {job.title}. "
                f"Tengo sólida trayectoria en diseño y construcción de interfaces robustas, destacando el liderazgo en la arquitectura "
                f"frontend con React y telemetría en tiempo real para visualización masiva de datos en el sector petrolero (W&T Offshore). "
                f"Mi enfoque combina alto rendimiento, experiencia de usuario fluida y código limpio. "
                f"Quedo a su disposición para coordinar una conversación técnica y profundizar en cómo sumar valor a sus objetivos."
            )

        # Rule 3: High concurrency & Clean Architecture fallback (Avianca)
        return (
            f"Hola equipo de {job.company}, me entusiasma la vacante de {job.title}. "
            f"Cuento con sólida experiencia en sistemas transaccionales de alta concurrencia y arquitectura limpia probada en flujos críticos "
            f"para aerolíneas (Avianca), garantizando escalabilidad, resiliencia y calidad de software bajo estándares rigurosos. "
            f"Estaré encantado de coordinar una conversación técnica para detallar cómo mis habilidades pueden contribuir al éxito del proyecto."
        )
