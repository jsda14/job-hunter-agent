# SPEC-003: Job Evaluator Port & Rule-Based Matcher

## 1. Propósito
Definir el puerto `JobEvaluatorPort` y una implementación base con reglas heurísticas deterministas (`RuleBasedEvaluatorAdapter`) que procese un `JobRaw` y determine si es apto (`is_actionable`) según las restricciones de perfil del candidato.

## 2. Perfil del Candidato (Target)
- Stack Primario: Python, FastAPI, React, Angular, TypeScript, AI Agents, RAG, Clean/Hexagonal Architecture.
- Restricción crítica: No llamadas síncronas en inglés fluido (B1 técnico / asíncrono aceptable; B2/C1 hablado estricto es excluyente).
- Ubicación: Remoto desde Colombia o híbrido/presencial solo en Bogotá.

## 3. Definición del Puerto (`src/domain/ports/evaluator.py`)
- Método: `async def evaluate(self, job: JobRaw) -> JobEvaluation`

## 4. Reglas Heurísticas (`src/adapters/evaluators/rule_based.py`)

### Detección de Inglés Conversacional Excluyente:
- Palabras clave disparadoras:
  `["fluent english", "c1 english", "native english", "excellent verbal english", "fluent spoken english"]`
- Si alguna coincide en `job.raw_description` (case-insensitive):
  * `requires_spoken_english = True`
  * `red_flags` debe incluir: `"Requiere inglés hablado fluido (excluyente)"`
  * `is_actionable = False`

### Detección de Stack Técnico Coincidente:
- Palabras clave auditadas:
  `["python", "fastapi", "react", "angular", "ai agents", "rag", "docker", "clean architecture", "hexagonal"]`
- Añadir a `tech_stack_detected` todas las coincidencias encontradas.

### Cálculo del `fit_score`:
- Base inicial: 50.0 puntos.
- Cada tecnología coincidente suma +10.0 puntos (tope máximo 100.0).
- Si `requires_spoken_english` es True, penaliza restando 40.0 puntos.
- Si el stack coincide en al menos 2 tecnologías clave y `requires_spoken_english` es False:
  * `fit_score = min(100.0, base + bonus)`
  * Si `fit_score >= 70.0`, marcar `is_actionable = True`.