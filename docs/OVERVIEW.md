# Job Hunter Agent — Visión General del Proyecto

## 1. Objetivo del proyecto

**Job Hunter Agent** es un sistema automatizado de prospección de empleo. Dado un conjunto de empresas objetivo (identificadas por su *slug* en un ATS — Applicant Tracking System), el sistema:

1. **Recolecta** (harvest) todas las vacantes publicadas por esas empresas.
2. **Evalúa** cada vacante contra un perfil de candidato predefinido, calculando un puntaje de encaje (`fit_score`) y detectando factores excluyentes (p. ej. requisito de inglés hablado fluido).
3. **Filtra** únicamente las vacantes "accionables" (`is_actionable = True`, es decir, con `fit_score >= 70.0` y sin bloqueos).
4. **Genera un pitch de postulación** personalizado y persuasivo para cada vacante accionable, adaptado al stack tecnológico detectado en la oferta.
5. **Notifica** el resultado final (por consola, en esta primera iteración) con toda la información lista para actuar: título, empresa, URL, fit score, stack detectado y pitch redactado.

El propósito de negocio es eliminar el trabajo manual repetitivo de revisar decenas de portales de empleo, leer cada descripción y redactar una carta de presentación distinta para cada una — dejando al humano solo la decisión final de postularse.

## 2. Alcance de esta iteración (SPEC-001 a SPEC-010)

- **Fuentes de datos soportadas:** [Lever](https://www.lever.co/) y [Greenhouse](https://www.greenhouse.com/), a través de sus APIs públicas JSON.
  - Lever: `https://api.lever.co/v0/postings/{company_slug}?mode=json`
  - Greenhouse: `https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs?content=true`
- **Modelo de dominio preparado, pero sin adaptador todavía:** Ashby (existe como valor del enum `SourcePlatform`).
- **Configuración de empresas objetivo:** externalizada en `companies.json` (raíz del proyecto) — lista de objetos `{company_slug, platform, name}` que se lee y valida con `JsonTargetLoaderAdapter` al arrancar. No hay slugs hardcodeados en `main.py`.
- **Despacho multi-plataforma:** `CompositeHarvesterAdapter` actúa como router: recibe targets con su plataforma asociada (`CompanyTarget`) y delega la recolección al adaptador correcto (Lever o Greenhouse), consolidando todo en una lista única de `JobRaw`.
- **Evaluación:** basada en reglas determinísticas (regex sobre texto), no en IA/LLM. Es un heurístico explícito y auditable.
- **Generación de pitch:** también basada en reglas (if/else sobre stack detectado), no generativa por IA.
- **Notificación:** solo consola (stdout). No hay email, Slack, base de datos ni persistencia.
- **Entry point:** un script `main.py` que corre una vez y termina (no es un servicio corriendo en loop ni un cron).
- **Tests de integración en vivo** (`SPEC-007`): existe una suite `tests/integration/` marcada con `@pytest.mark.integration` que realiza llamadas HTTP reales contra la API de Lever para verificar normalización sin mocks. Se aíslan de la suite offline con `pytest -m "not integration"`.

Todo lo fuera de este alcance (Ashby, evaluación por LLM, notificación real, persistencia) sería una iteración futura, cada una con su propia spec.

## 3. Stack técnico

| Capa | Tecnología | Rol |
|---|---|---|
| Lenguaje | Python 3.11+ | Todo el proyecto |
| Validación de datos | [Pydantic v2](https://docs.pydantic.dev/) (`BaseModel`, `Field`, `HttpUrl`, `model_validator`) | Modelos de dominio autovalidados |
| Cliente HTTP | [httpx](https://www.python-httpx.org/) (`AsyncClient`) | Consumo de la API de Lever, 100% asíncrono |
| Concurrencia | `asyncio` | Todo el flujo (harvester → evaluator → pitch → notifier) es `async/await` de punta a punta |
| Testing | `pytest` + `pytest-asyncio` | Suite de tests unitarios con soporte nativo para funciones `async def test_...` |
| Config de tests | `pytest.ini` | `pythonpath = .` (imports absolutos desde la raíz), `testpaths = tests` |
| Gestión de dependencias | `requirements.txt` (venv estándar) | Sin Poetry/uv en esta iteración |

No hay frameworks web (no hay FastAPI expuesto todavía, aunque el evaluador *detecta* FastAPI como tecnología del lado del *empleador*), no hay ORM, no hay base de datos: es una aplicación de línea de comandos (CLI) de un solo uso.

## 4. Arquitectura: Hexagonal (Ports & Adapters)

El proyecto sigue estrictamente **arquitectura hexagonal** (también llamada Ports & Adapters), con una separación explícita en tres capas dentro de `src/`:

```
src/
├── domain/                      ← el núcleo, no depende de nada externo
│   ├── models/job.py             (entidades y value objects: JobRaw, JobEvaluation, SourcePlatform)
│   ├── ports/                    (interfaces abstractas — los "contratos")
│   │   ├── harvester.py          (JobHarvesterPort, CompanyTarget, HarvesterConnectionError, UnsupportedPlatformError)
│   │   ├── evaluator.py
│   │   ├── pitch_generator.py
│   │   ├── notifier.py
│   │   └── target_loader.py      (TargetLoaderPort, TargetLoaderError)
│   └── use_cases/
│       └── hunt_jobs.py          (JobHunterUseCase — acepta List[str] o List[CompanyTarget])
│
└── adapters/                    ← implementaciones concretas, "enchufables"
    ├── harvesters/
    │   ├── lever.py              (implementa JobHarvesterPort para Lever)
    │   ├── greenhouse.py         (implementa JobHarvesterPort para Greenhouse)
    │   └── composite.py          (CompositeHarvesterAdapter — router multi-plataforma)
    ├── evaluators/
    │   ├── rule_based.py         (implementa JobEvaluatorPort con reglas heurísticas)
    │   └── pitch_generator.py    (implementa PitchGeneratorPort con reglas por stack)
    ├── loaders/
    │   └── json_targets.py       (implementa TargetLoaderPort — lee companies.json)
    └── notifiers/
        └── console.py            (implementa JobNotifierPort para stdout)
```

**Regla de dependencia:** el código en `domain/` nunca importa nada de `adapters/`. Los adaptadores importan los puertos del dominio e implementan sus métodos. El dominio no sabe que existe `httpx`, ni Lever, ni JSON, ni la consola.

**Inyección de Dependencias por constructor:** `JobHunterUseCase` recibe `harvester`, `evaluator` y `pitch_generator` tipados por sus interfaces abstractas. `main.py` es la única capa de composición donde los adaptadores concretos se conectan entre sí.

**`CompanyTarget`** (DTO de dominio en `ports/harvester.py`): es el objeto tipado que reemplaza al string crudo como forma de expresar una empresa objetivo. Tiene `company_slug`, `platform` (un `SourcePlatform`), y `name` opcional para mostrar en logs. Vivir en el dominio (no en `adapters/`) lo hace reutilizable por cualquier adaptador sin importaciones circulares.

**`CompositeHarvesterAdapter`** no implementa `JobHarvesterPort` — tiene su propio método `fetch_jobs_from_targets(targets: List[CompanyTarget])`. El `JobHunterUseCase` lo detecta con `hasattr(harvester, "fetch_jobs_from_targets")` y delega directamente, manteniendo retrocompatibilidad total con la interfaz original `fetch_jobs(slug)` para los tests existentes.

## 5. Especificaciones (Spec-Driven Development)

El proyecto fue construido siguiendo **SDD (Spec-Driven Development)**: antes de escribir cualquier código de una pieza, existe un documento en `specs/` que define su contrato, sus reglas de negocio y sus invariantes. Cada spec mapea 1:1 a los archivos que terminó generando.

El estado actual de cada spec está registrado en `specs/TASK_STATUS.md`.

| Spec | Define | Archivos resultantes |
|---|---|---|
| `SPEC-001` | Modelos canónicos `JobRaw` y `JobEvaluation`, sus invariantes Pydantic | `src/domain/models/job.py` |
| `SPEC-002` | Puerto `JobHarvesterPort` + adaptador Lever + reglas de mapeo API→dominio | `src/domain/ports/harvester.py`, `src/adapters/harvesters/lever.py` |
| `SPEC-003` | Puerto `JobEvaluatorPort` + reglas heurísticas (stack, inglés, fit score) | `src/domain/ports/evaluator.py`, `src/adapters/evaluators/rule_based.py` |
| `SPEC-004` | Puerto `PitchGeneratorPort` + reglas de selección de proyecto estrella | `src/domain/ports/pitch_generator.py`, `src/adapters/evaluators/pitch_generator.py` |
| `SPEC-005` | `JobHunterUseCase` — orquestador central y tolerancia a fallos | `src/domain/use_cases/hunt_jobs.py` |
| `SPEC-006` | Puerto `JobNotifierPort` + adaptador consola + entrypoint inicial | `src/domain/ports/notifier.py`, `src/adapters/notifiers/console.py`, `main.py` |
| `SPEC-007` | Harness de integración en vivo contra la API real de Lever (marcado `@pytest.mark.integration`) | `tests/integration/test_lever_live.py`, `pytest.ini` actualizado |
| `SPEC-008` | Adaptador Greenhouse: normalización HTML, ISO UTC, fallbacks, manejo de errores | `src/adapters/harvesters/greenhouse.py`, `tests/harness/fixtures/greenhouse_payload.py`, `tests/unit/test_greenhouse_harvester.py` |
| `SPEC-009` | `CompositeHarvesterAdapter` + DTO `CompanyTarget` + `UnsupportedPlatformError` | `src/adapters/harvesters/composite.py`, `src/domain/ports/harvester.py` actualizado, `tests/unit/test_composite_harvester.py` |
| `SPEC-010` | `TargetLoaderPort` + `JsonTargetLoaderAdapter` + `companies.json` + orquestación multi-plataforma end-to-end | `src/domain/ports/target_loader.py`, `src/adapters/loaders/json_targets.py`, `companies.json`, `main.py` actualizado, `tests/unit/test_target_loader.py` |

Cada spec es la **fuente de verdad** de las reglas de negocio. Si hay una discrepancia entre lo que hace el código y lo que dice la spec, la spec gana y el código se corrige (o la spec se actualiza deliberadamente, nunca en silencio).

## 6. Testing (Harness)

**Estado actual del harness: 33 tests / 33 pasando al 100%** (31 unitarios + 2 integración).

### Suite unitaria (`tests/unit/`) — offline, sin red

| Archivo | Qué verifica | Tests |
|---|---|---|
| `test_domain_models.py` | Invariantes de Pydantic (`is_actionable=True` con `requires_spoken_english=True` debe fallar) | 3 |
| `test_lever_harvester.py` | Mapeo JSON→`JobRaw`, manejo de 404, campos faltantes | 2 |
| `test_greenhouse_harvester.py` | Normalización HTML, parseo ISO UTC, fallbacks de location/fecha, error HTTP | 6 |
| `test_composite_harvester.py` | Despacho multi-plataforma, aislamiento de fallos, `UnsupportedPlatformError`, lista vacía | 6 |
| `test_rule_based_evaluator.py` | Cálculo de `fit_score`, detección de red flags de inglés | 2 |
| `test_pitch_generator.py` | Selección correcta de pitch según stack detectado | 2 |
| `test_console_notifier.py` | Formato de salida y conteo retornado | 2 |
| `test_hunt_jobs_usecase.py` | Orquestación completa con fakes, tolerancia a fallo parcial, filtro de accionables | 2 |
| `test_target_loader.py` | Carga de `companies.json`, errores de archivo, JSON inválido, validación de `CompanyTarget` | 6 |

### Suite de integración (`tests/integration/`) — requiere internet

- `test_lever_live.py` — marcado con `@pytest.mark.integration`. Llama a la API real de Lever con un slug real y uno inexistente, sin mocks. Aislable con `pytest -m "not integration"` para desarrollo offline.

### Fixtures compartidas (`tests/harness/fixtures/`)

- `lever_payload.py` — payload JSON real de Lever con 1 vacante de muestra.
- `greenhouse_payload.py` — payload JSON real de Greenhouse con HTML escapado de muestra.
- `sample_jobs.py` — instancias `JobRaw` pre-construidas reutilizables en múltiples tests.

Correr solo los tests offline: `pytest -m "not integration"`. Correr todo: `pytest`.

## 7. Flujo end-to-end (resumen ejecutivo)

```
main.py
  ├─ JsonTargetLoaderAdapter.load_targets("companies.json")
  │    → [CompanyTarget(kavak, lever), CompanyTarget(nubank, greenhouse), ...]
  │
  ├─ CompositeHarvesterAdapter (Lever + Greenhouse registrados)
  │
  └─ JobHunterUseCase.execute(targets: List[CompanyTarget])
       │
       ├─ composite.fetch_jobs_from_targets(targets)
       │    for cada target:
       │      ├─ harvester[target.platform].fetch_jobs(target.company_slug) → [JobRaw, ...]
       │      │   (si falla: HarvesterConnectionError → skip, continúa con la siguiente empresa)
       │      └─ consolida todos los JobRaw en una lista única
       │
       └─ para cada JobRaw consolidado:
            ├─ evaluator.evaluate(job)              → JobEvaluation
            └─ si evaluation.is_actionable:
                 ├─ pitch_generator.generate_pitch(job, evaluation) → str
                 ├─ evaluation.tailored_pitch = pitch
                 └─ agrega (job, evaluation) a resultados accionables
  │
  └─ ConsoleNotifierAdapter.notify(resultados) → imprime tarjetas, retorna conteo
```

## 8. Cómo correr el proyecto

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la prospección completa
python main.py

# Correr la suite de tests
pytest
```

## 9. Estado actual y próximos pasos naturales

### Implementado (SPEC-001 a SPEC-010)
- ✅ Dominio completo: modelos, 5 puertos, 1 caso de uso.
- ✅ Adaptadores: Lever, Greenhouse, Composite (multi-plataforma), JsonTargetLoader, RuleBasedEvaluator, RuleBasedPitchGenerator, ConsoleNotifier.
- ✅ Configuración externalizada en `companies.json` — cero slugs hardcodeados.
- ✅ Harness completo: 33 tests (31 unitarios offline + 2 integración en vivo), 100% verde.

### Backlog inmediato (según `specs/TASK_STATUS.md`)
- ⏳ **SPEC-011 — Semantic LLM Evaluator:** adaptador `JobEvaluatorPort` que usa Claude/Gemini para análisis semántico fino — sin tocar el dominio ni el use case (ese es exactamente el punto de la arquitectura hexagonal).
- ⏳ **SPEC-012 — Ashby Harvester:** tercer adaptador de recolección; el enum `SourcePlatform.ASHBY` ya existe, solo falta el adaptador y su registro en el composite.

### Brechas para automatización real
- ⏳ Sin persistencia (cada corrida es *stateless* — no hay forma de saber qué vacantes ya se notificaron antes; sin esto hay renotificaciones en cada ejecución).
- ⏳ Sin notificador real (email/Slack/Telegram) — solo consola.
- ⏳ Sin scheduler ni trigger automático — actualmente es un script que se ejecuta manualmente.
