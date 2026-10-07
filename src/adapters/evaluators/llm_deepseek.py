import json
import os
from typing import Optional

import httpx

from src.domain.models.job import JobEvaluation, JobRaw
from src.domain.ports.evaluator import JobEvaluatorPort, LLMEvaluatorError

_SYSTEM_PROMPT = """Eres un evaluador experto de vacantes de trabajo para el siguiente candidato:
- Seniority: Senior (5+ años). DESCARTA: junior, trainee, intern, menos de 3 años de experiencia requerida.
- Stack técnico: Python, FastAPI, React, Angular, AI Agents, RAG, Docker, Clean Architecture, Hexagonal Architecture.
- Restricción idioma: inglés técnico escrito OK. Inglés hablado fluido en reuniones síncronas = EXCLUYENTE.
- Modalidad: remoto desde Colombia. Presencial fuera de Bogotá = EXCLUYENTE.
- Salario mínimo: USD 3,000/mes o equivalente.

Analiza la vacante y responde ÚNICAMENTE con un JSON válido con esta estructura exacta:
{
  "fit_score": <float entre 0.0 y 100.0>,
  "salary_match": <true|false>,
  "requires_spoken_english": <true|false>,
  "tech_stack_detected": [<lista de strings con tecnologías encontradas>],
  "pros": [<lista de strings con aspectos positivos>],
  "red_flags": [<lista de strings con aspectos negativos o excluyentes>],
  "is_actionable": <true|false>,
  "reasoning": "<una oración explicando el veredicto>"
}

Reglas estrictas:
- is_actionable = true SOLO si fit_score >= 70 Y requires_spoken_english = false Y no hay red flags excluyentes.
- Si el rol es junior/trainee/intern: fit_score <= 30, is_actionable = false.
- Si requiere presencial fuera de Bogotá: is_actionable = false, agrega red flag.
- Si requiere inglés hablado fluido: requires_spoken_english = true, is_actionable = false."""

_DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
_MODEL = "deepseek-chat"


class DeepSeekEvaluatorAdapter(JobEvaluatorPort):
    """LLM-based job evaluator using DeepSeek Chat for semantic analysis."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self._client = client

    async def evaluate(self, job: JobRaw) -> JobEvaluation:
        user_prompt = (
            f"Título: {job.title}\n"
            f"Empresa: {job.company}\n"
            f"Ubicación: {job.location}\n\n"
            f"Descripción:\n{job.raw_description[:3000]}"
        )

        payload = {
            "model": _MODEL,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 500,
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            if self._client is not None:
                response = await self._client.post(_DEEPSEEK_URL, json=payload, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(_DEEPSEEK_URL, json=payload, headers=headers)

            if response.status_code >= 400:
                raise LLMEvaluatorError(
                    f"DeepSeek API returned HTTP {response.status_code}: {response.text}"
                )

            raw_json = response.json()
            content = raw_json["choices"][0]["message"]["content"]

        except httpx.RequestError as exc:
            raise LLMEvaluatorError(f"Network error calling DeepSeek API: {exc}") from exc
        except (KeyError, IndexError) as exc:
            raise LLMEvaluatorError(f"Unexpected DeepSeek response structure: {exc}") from exc

        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMEvaluatorError(f"DeepSeek returned non-JSON content: {content!r}") from exc

        try:
            return JobEvaluation(
                job_id=job.id,
                fit_score=float(data.get("fit_score", 0.0)),
                salary_match=bool(data.get("salary_match", False)),
                requires_spoken_english=bool(data.get("requires_spoken_english", False)),
                tech_stack_detected=list(data.get("tech_stack_detected", [])),
                pros=list(data.get("pros", [])),
                red_flags=list(data.get("red_flags", [])),
                is_actionable=bool(data.get("is_actionable", False)),
            )
        except Exception as exc:
            raise LLMEvaluatorError(f"Failed to build JobEvaluation from LLM response: {exc}") from exc
