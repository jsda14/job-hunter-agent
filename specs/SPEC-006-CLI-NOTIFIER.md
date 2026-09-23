# SPEC-006: Console Notifier Adapter & CLI Runner

## 1. Propósito
Definir el puerto `JobNotifierPort`, su implementación determinista `ConsoleNotifierAdapter` y el script de entrada `main.py` que consume empresas objetivo y ejecuta la prospección completa.

## 2. Definición del Puerto (`src/domain/ports/notifier.py`)
- Método: `async def notify(self, jobs: list[tuple[JobRaw, JobEvaluation]]) -> int`
- Retorna el conteo de notificaciones emitidas con éxito.

## 3. Adaptador de Consola (`src/adapters/notifiers/console.py`)
- Clase `ConsoleNotifierAdapter` que implemente `JobNotifierPort`.
- Si la lista de ofertas está vacía: imprime un aviso neutro y retorna 0.
- Por cada tupla `(job, evaluation)`:
  * Imprime una tarjeta legible con: Título, Empresa, URL, Fit Score, Stack Detectado y el Tailored Pitch.
  * Retorna la cantidad de elementos procesados.

## 4. Entrypoint (`main.py`)
- Conecta dependencias: `LeverHarvesterAdapter`, `RuleBasedEvaluatorAdapter`, `RuleBasedPitchGeneratorAdapter`, `ConsoleNotifierAdapter`.
- Instancia `JobHunterUseCase`.
- Ejecuta la prospección sobre una lista configurable de empresas (e.g. `["mercadolibre", "nubank", "rappi"]`).