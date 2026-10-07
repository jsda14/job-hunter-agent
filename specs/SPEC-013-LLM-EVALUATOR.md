# SPEC-013: LLM-Based Job Evaluator (DeepSeek)

## 1. Propósito
Reemplazar el evaluador heurístico basado en regex (`RuleBasedEvaluatorAdapter`) por un evaluador semántico que use DeepSeek Chat para analizar cada vacante en profundidad, detectando seniority, modalidad, stack implícito, ajuste salarial y accionabilidad real contra el perfil del candidato.

## 2. Perfil del Candidato (Contexto para el LLM)
- **Nombre:** Jhon Delgado
- **Seniority:** Senior (5+ años). Descartar roles junior, trainee, intern o que pidan menos de 3 años.
- **Stack:** Python, FastAPI, React, Angular, AI Agents, RAG, Docker, Clean Architecture, Hexagonal.
- **Restricción idioma:** inglés escrito técnico OK (B2). Inglés hablado fluido en reuniones síncronas = excluyente.
- **Modalidad:** remoto desde Colombia. Híbrido/presencial solo Bogotá. Presencial en otro país = excluyente.
- **Salario:** mínimo $3,000 USD/mes o equivalente. Descartar si el texto sugiere compensación muy por debajo (ej. "startup pre-seed sin equity").

## 3. Puerto (`src/domain/ports/evaluator.py`)
Sin cambios — el nuevo adaptador implementa el mismo `JobEvaluatorPort` existente:
```python
async def evaluate(self, job: JobRaw) -> JobEvaluation
```

## 4. Adaptador (`src/adapters/evaluators/llm_deepseek.py`)
- Clase: `DeepSeekEvaluatorAdapter(JobEvaluatorPort)`
- Constructor: `__init__(self, api_key: Optional[str] = None, client: Optional[httpx.AsyncClient] = None)`
  - `api_key` lee `DEEPSEEK_API_KEY` del entorno si no se pasa explícitamente.
- Endpoint: `https://api.deepseek.com/chat/completions`
- Modelo: `deepseek-chat`
- El prompt del sistema contiene el perfil del candidato.
- El prompt del usuario contiene título, empresa y descripción de la vacante.
- La respuesta del LLM debe ser JSON estructurado con los campos de `JobEvaluation`.

## 5. Prompt del Sistema
```
Eres un evaluador experto de vacantes de trabajo para el siguiente candidato:
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
- Si requiere inglés hablado fluido: requires_spoken_english = true, is_actionable = false.
```

## 6. Reglas de Negocio
- Si la API de DeepSeek falla (timeout, error HTTP): relanzar como `LLMEvaluatorError` (nueva excepción de dominio en `evaluator.py`).
- Si el JSON de respuesta no es parseable: relanzar como `LLMEvaluatorError`.
- El campo `reasoning` del LLM no se persiste en `JobEvaluation` (no existe ese campo) — se descarta tras el parseo.
- `tailored_pitch` se deja como `None` — lo genera el `PitchGeneratorPort` en el paso siguiente.

## 7. Archivos afectados
- **Crear:** `src/adapters/evaluators/llm_deepseek.py`
- **Crear:** `tests/unit/test_llm_evaluator.py`
- **Modificar:** `src/domain/ports/evaluator.py` (agregar `LLMEvaluatorError`)
- **Modificar:** `main.py` (usar `DeepSeekEvaluatorAdapter` en lugar de `RuleBasedEvaluatorAdapter`)
- **Modificar:** `.github/workflows/hunt.yml` (agregar `DEEPSEEK_API_KEY` como env var)
- **Modificar:** `specs/TASK_STATUS.md`
