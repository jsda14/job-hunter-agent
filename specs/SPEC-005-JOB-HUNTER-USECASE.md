# SPEC-005: Job Hunter Orchestrator Use Case

## 1. Propósito
Definir el caso de uso central del dominio (`JobHunterUseCase`) que orquesta el ciclo de vida completo: recolección desde harvesters, evaluación semántica y enriquecimiento de pitches para ofertas accionables.

## 2. Definición del Caso de Uso (`src/domain/use_cases/hunt_jobs.py`)
- Clase: `JobHunterUseCase`
- Inyección de dependencias (Constructor):
  * `harvester: JobHarvesterPort`
  * `evaluator: JobEvaluatorPort`
  * `pitch_generator: PitchGeneratorPort`
- Método principal:
  `async def execute(self, company_slugs: list[str]) -> list[tuple[JobRaw, JobEvaluation]]`

## 3. Reglas de Orquestación e Invariantes
1. Debe iterar o ejecutar la recolección para cada empresa en `company_slugs`.
2. Si una empresa falla (`HarvesterConnectionError`), el caso de uso no debe colapsar; debe continuar con las demás empresas.
3. Para cada oferta capturada:
   - Ejecuta `evaluation = await evaluator.evaluate(job)`
   - Si `evaluation.is_actionable` es `True`:
     * Genera el pitch: `pitch = await pitch_generator.generate_pitch(job, evaluation)`
     * Asigna `evaluation.tailored_pitch = pitch`
     * Agrega el par `(job, evaluation)` a la lista de resultados.
4. El método debe retornar exclusivamente los pares donde `is_actionable` sea `True`.