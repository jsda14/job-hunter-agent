# TASK STATUS & PROJECT STATE

> **Fuente Única de Verdad (SSOT)** del estado del proyecto `job-hunter-agent`.
> Actualizado tras cada ciclo completado de SDD y Harness-Driven Development.

---

## 1. Métricas del Harness
* **Tests Unitarios:** 31 passed / 31 total (100% verde)
* **Tests de Integración:** 2 passed / 2 total (100% verde contra internet)
* **Tests Totales:** 33 passed / 33 total (100% verde)
* **Framework:** Pytest 9+ con pytest-asyncio
* **Tiempo de ejecución suite unitaria:** ~3.2s
* **Tiempo de ejecución suite integración:** ~4.0s

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
| `SPEC-007` | Lever Integration Harness & Live Network Test | `Implemented` | `tests/integration/test_lever_live.py` (2 tests) | Harness real contra internet con aislamiento por markers |
| `SPEC-008` | Greenhouse Harvester Adapter | `Implemented` | `tests/unit/test_greenhouse_harvester.py` (6 tests) | Normalización HTML, ISO UTC y fallbacks |
| `SPEC-009` | Composite Harvester Adapter & Multi-Platform Dispatcher | `Implemented` | `tests/unit/test_composite_harvester.py` (6 tests) | Despacho heterogéneo, aislamiento de fallos y agregación |
| `SPEC-010` | Targets Loader & End-to-End Orchestration | `Implemented` | `tests/unit/test_target_loader.py` (6 tests) | Externalización de configuración en `companies.json` y pipeline CLI |

---

## 3. Backlog de Especificaciones Pendientes (Roadmap Inmediato)

- [ ] **SPEC-011 (Semantic LLM Evaluator):** Evaluador avanzado usando Claude / Gemini para análisis semántico fino cuando la regla heurística no baste.
- [ ] **SPEC-012 (Ashby Harvester Adapter):** Tercer adaptador de recolección para soportar empresas que usan Ashby ATS.

---

## 4. Deuda Técnica y Restricciones Conocidas
* Resuelto en `SPEC-010`: Slugs de empresas externalizados en `companies.json` con validación tipada en `JsonTargetLoaderAdapter`.