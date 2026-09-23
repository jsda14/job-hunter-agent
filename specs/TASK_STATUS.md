# TASK STATUS & PROJECT STATE

> **Fuente Única de Verdad (SSOT)** del estado del proyecto `job-hunter-agent`.
> Actualizado tras cada ciclo completado de SDD y Harness-Driven Development.

---

## 1. Métricas del Harness
* **Tests Unitarios:** 13 passed / 13 total (100% verde)
* **Tests de Integración:** 0 (Pendiente primer live harness)
* **Framework:** Pytest 9+ con pytest-asyncio
* **Tiempo de ejecución suite:** ~1.3s

---

## 2. Registro de Especificaciones (Specs Log)

| ID | Título | Estado | Tests Asociados | Cobertura / Notas |
|---|---|---|---|---|
| `SPEC-001` | Core Domain Contracts & Job Model | `Implemented` | `tests/unit/test_domain_models.py` (3 tests) | Invariantes de JobRaw y JobEvaluation |
| `SPEC-002` | Job Harvester Port & Lever Adapter | `Implemented` | `tests/unit/test_lever_harvester.py` (2 tests) | Manejo de HTTP mocks y HarvesterConnectionError |
| `SPEC-003` | Job Evaluator Port & Rule-Based Matcher | `Implemented` | `tests/unit/test_rule_based_evaluator.py` (2 tests) | Filtro de inglés conversacional y scoring base |
| `SPEC-004` | Tailored Pitch Generator Port & Adapter | `Implemented` | `tests/unit/test_pitch_generator.py` (2 tests) | Mapeo heurístico a proyectos reales |
| `SPEC-005` | Job Hunter Orchestrator Use Case | `Implemented` | `tests/unit/test_hunt_jobs_usecase.py` (2 tests) | Orquestación resiliente ante fallas |
| `SPEC-006` | Console Notifier Adapter & CLI Runner | `Implemented` | `tests/unit/test_console_notifier.py` (2 tests) | CLI entrypoint funcional en `main.py` |

---

## 3. Backlog de Especificaciones Pendientes (Roadmap Inmediato)

- [ ] **SPEC-007 (Integration Harness):** Prueba de integración en vivo contra un slug real de Lever para verificar el contrato contra internet.
- [ ] **SPEC-008 (Greenhouse Harvester Adapter):** Segundo adaptador de recolección para soportar empresas que usan Greenhouse (ej. Nubank y scale-ups regionales).
- [ ] **SPEC-009 (Semantic LLM Evaluator):** Evaluador avanzado usando Claude / Gemini para análisis semántico fino cuando la regla heurística no baste.

---

## 4. Deuda Técnica y Restricciones Conocidas
* Actualmente los slugs de empresas en `main.py` son estáticos en código; deben externalizarse a un archivo de configuración (`companies.json` o `.env`).