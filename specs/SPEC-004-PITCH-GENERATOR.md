# SPEC-004: Tailored Pitch Generator Port & Rule-Based Generator

## 1. Propósito
Definir el puerto `PitchGeneratorPort` y un generador determinista (`RuleBasedPitchGeneratorAdapter`) que produzca un texto de presentación altamente persuasivo adaptado al stack dominante de la oferta.

## 2. Definición del Puerto (`src/domain/ports/pitch_generator.py`)
- Método: `async def generate_pitch(self, job: JobRaw, evaluation: JobEvaluation) -> str`

## 3. Lógica del Adaptador (`src/adapters/evaluators/pitch_generator.py`)

### Reglas de Selección de Proyectos Estrella:
- **Eje IA & Backend:** Si `fastapi`, `ai agents` o `rag` están en `evaluation.tech_stack_detected`:
  * Enfatizar: Microservicio de observabilidad bancaria con agentic loop, RAG semántico en ChromaDB y colas Redis Streams.
- **Eje Frontend & Big Data:** Si `react` o `telemetry` o `charts` están en `evaluation.tech_stack_detected`:
  * Enfatizar: Dashboard analítico petrolero para W&T Offshore con React y telemetría en tiempo real.
- **Eje Resiliencia & Escala:** Si no coincide con los anteriores o pide alta disponibilidad:
  * Enfatizar: Arquitectura limpia y sistemas de misión crítica en producción para flujos transaccionales y check-in masivo de aerolíneas (Avianca).

### Estructura de Salida:
1. Saludo y gancho técnico alineado al rol.
2. Evidencia de impacto directo referenciando el proyecto seleccionado con métricas concretas.
3. Llamado a la acción (CTA) invitando a ver el repositorio o coordinar una conversación técnica.