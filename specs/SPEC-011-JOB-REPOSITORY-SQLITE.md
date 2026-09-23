# SPEC: SPEC-011 - SQLite Job Repository & Deduplication

> **Instrucciones para el Agente Codificador:**
> 1. No instales dependencias externas, librerías ni paquetes que no estén explícitamente autorizados en la sección 2.
> 2. No agregues campos adicionales, métodos auxiliares públicos ni endpoints fuera de los contratos descritos en la sección 3.
> 3. Implementa únicamente las tareas listadas en la sección 5 en orden secuencial. Si encuentras un bloqueo, detén la ejecución y solicita aclaración.
> 4. Al finalizar, ejecuta el arnés de pruebas unitarias (`pytest tests/unit/test_sqlite_repository.py`) y la suite completa (`pytest`) para validar los 5 pasos de salida.

---

## 1. Alcance y Fronteras
* **Objetivo:** Implementar la capa de persistencia y deduplicación para que el agente recuerde las vacantes previamente procesadas, definiendo el puerto `JobRepositoryPort`, implementando el adaptador `SQLiteJobRepositoryAdapter` sobre SQLite nativo sin dependencias externas, e integrándolo en `JobHunterUseCase` y `main.py` para procesar y notificar exclusivamente ofertas nuevas.
* **En Alcance (In-Scope):**
  - Definición del puerto abstracto `JobRepositoryPort` en `src/domain/ports/repository.py` con métodos asíncronos `is_seen`, `save_job` y `filter_unseen`.
  - Implementación del adaptador `SQLiteJobRepositoryAdapter` en `src/adapters/repositories/sqlite.py` utilizando la librería estándar `sqlite3` y `asyncio.to_thread`.
  - Creación automática del esquema de base de datos y la tabla `processed_jobs` con soporte para rutas en disco (ej. `data/job_hunter.db`) y bases en memoria (`:memory:`).
  - Integración en `JobHunterUseCase` mediante inyección opcional de `repository: Optional[JobRepositoryPort] = None`, filtrando vacantes no vistas antes de evaluar y persistiendo las procesadas.
  - Actualización de `main.py` para instanciar el repositorio y pasarlo al caso de uso.
  - Creación de suite unitaria exhaustiva en `tests/unit/test_sqlite_repository.py`.
* **Fuera de Alcance (Out-of-Scope / Non-Goals):**
  - Modificación de modelos de dominio canónicos en `src/domain/models/job.py`.
  - Modificación de harvesters existentes (`lever.py`, `greenhouse.py`, `composite.py`), evaluadores o loaders.
  - Instalación de ORMs externos o librerías async (SQLAlchemy, aiosqlite, tortoise-orm).
  - Modificación de suites de tests unitarias existentes en `tests/unit/**` (deben seguir pasando al 100%).
* **Archivos Afectados:**
  * **Crear:**
    - `src/domain/ports/repository.py`
    - `src/adapters/repositories/__init__.py`
    - `src/adapters/repositories/sqlite.py`
    - `tests/unit/test_sqlite_repository.py`
  * **Modificar:**
    - `src/domain/use_cases/hunt_jobs.py` (inyección opcional y lógica de deduplicación)
    - `main.py` (instanciación de `SQLiteJobRepositoryAdapter`)
    - `specs/TASK_STATUS.md` (registro tras completarse)
  * **Prohibido modificar:**
    - `src/domain/models/**`
    - `requirements.txt`
    - `src/adapters/harvesters/**`
    - `src/adapters/evaluators/**`
    - `src/adapters/loaders/**`
    - `src/adapters/notifiers/**`
    - `tests/unit/test_domain_models.py`
    - `tests/unit/test_lever_harvester.py`
    - `tests/unit/test_greenhouse_harvester.py`
    - `tests/unit/test_composite_harvester.py`
    - `tests/unit/test_hunt_jobs_usecase.py`
    - `tests/unit/test_target_loader.py`
    - `tests/integration/test_lever_live.py`

---

## 2. Entorno y Dependencias Permitidas
* **Runtime / Versión:** Python 3.11+
* **Librerías autorizadas:**
  - `sqlite3` (módulo estándar de Python para base de datos relacional liviana)
  - `asyncio` (`asyncio.to_thread` para ejecución I/O no bloqueante)
  - `pathlib`, `typing`, `abc`, `datetime` (módulos estándar)
  - `pydantic` (modelos JobRaw y JobEvaluation)
  - `pytest` y `pytest-asyncio` (suite de pruebas)
* **Regla estricta:** Prohibido instalar o importar paquetes externos no listados (ej. `aiosqlite`, `sqlalchemy`) ni alterar `requirements.txt`.

---

## 3. Contratos e Interfaces (Single Source of Truth)

### 3.1 Definición del Puerto (`src/domain/ports/repository.py`)
```python
from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.models.job import JobEvaluation, JobRaw

class JobRepositoryPort(ABC):
    """Puerto de dominio para la persistencia y deduplicación de vacantes."""

    @abstractmethod
    async def is_seen(self, job_id: str) -> bool:
        """Determina si un job_id ya ha sido procesado previamente.
        
        Args:
            job_id: Identificador canónico del empleo (e.g. 'lever_123', 'greenhouse_456').
            
        Returns:
            True si el job_id ya está registrado en el repositorio; False en caso contrario.
        """
        raise NotImplementedError

    @abstractmethod
    async def save_job(self, job: JobRaw, evaluation: Optional[JobEvaluation] = None) -> None:
        """Registra o actualiza una vacante y su evaluación en el repositorio.
        
        Args:
            job: Instancia canónica de JobRaw.
            evaluation: Instancia opcional de JobEvaluation generada para la vacante.
        """
        raise NotImplementedError

    @abstractmethod
    async def filter_unseen(self, jobs: List[JobRaw]) -> List[JobRaw]:
        """Filtra una lista de vacantes, retornando únicamente aquellas que no existan en el repositorio.
        
        Args:
            jobs: Lista de instancias JobRaw a verificar.
            
        Returns:
            Lista de instancias JobRaw no vistas previamente, preservando el orden de entrada.
        """
        raise NotImplementedError
```

### 3.2 Esquema Relacional de la Tabla SQLite
```sql
CREATE TABLE IF NOT EXISTS processed_jobs (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    is_actionable INTEGER NOT NULL,
    fit_score REAL,
    first_seen_at TEXT NOT NULL
);
```

### 3.3 Firma del Adaptador SQLite (`src/adapters/repositories/sqlite.py`)
```python
from pathlib import Path
from typing import List, Optional, Union
from src.domain.models.job import JobEvaluation, JobRaw
from src.domain.ports.repository import JobRepositoryPort

class SQLiteJobRepositoryAdapter(JobRepositoryPort):
    """Adaptador de repositorio basado en SQLite nativo con ejecución en hilos asíncronos."""

    def __init__(self, db_path: Union[str, Path] = "data/job_hunter.db") -> None:
        """Inicializa el adaptador y asegura la existencia de la base de datos y la tabla processed_jobs.
        
        Args:
            db_path: Ruta al archivo SQLite o ':memory:' para bases en memoria.
        """
        pass

    async def is_seen(self, job_id: str) -> bool:
        pass

    async def save_job(self, job: JobRaw, evaluation: Optional[JobEvaluation] = None) -> None:
        pass

    async def filter_unseen(self, jobs: List[JobRaw]) -> List[JobRaw]:
        pass
```

### 3.4 Extensión de `JobHunterUseCase` (`src/domain/use_cases/hunt_jobs.py`)
```python
class JobHunterUseCase:
    def __init__(
        self,
        harvester: Any,
        evaluator: JobEvaluatorPort,
        pitch_generator: PitchGeneratorPort,
        repository: Optional[JobRepositoryPort] = None,
    ) -> None:
        self.harvester = harvester
        self.evaluator = evaluator
        self.pitch_generator = pitch_generator
        self.repository = repository
```

---

## 4. Reglas de Negocio y Casos Borde

### 4.1 Reglas de Negocio (RN)
- **RN-01 (Inicialización Automática e Idempotente):** Al instanciar `SQLiteJobRepositoryAdapter`, si la ruta de archivo incluye directorios no existentes (ej. `data/`), estos deben crearse (`parent.mkdir(parents=True, exist_ok=True)`). Debe ejecutarse el DDL de `CREATE TABLE IF NOT EXISTS processed_jobs` para garantizar disponibilidad inmediata.
- **RN-02 (Consulta de Existencia):** `is_seen(job_id)` debe consultar por clave primaria `id`. Retorna `True` si existe coincidencia exacta y `False` si no se encuentra.
- **RN-03 (Filtrado de Novedades):** `filter_unseen(jobs)` debe verificar qué identificadores existen en la base de datos (por ejemplo mediante una consulta `SELECT id FROM processed_jobs WHERE id IN (...)` o validaciones indexadas) y retornar únicamente aquellas instancias de `JobRaw` no registradas, respetando el orden original.
- **RN-04 (Persistencia Atómica e Idempotente):** `save_job` debe persistir el registro con `INSERT OR REPLACE INTO processed_jobs`. Si `evaluation` se proporciona:
  * `is_actionable` = 1 si `evaluation.is_actionable` es `True`, sino 0.
  * `fit_score` = `evaluation.fit_score`.
  Si `evaluation` es `None`:
  * `is_actionable` = 0.
  * `fit_score` = `None`.
  `first_seen_at` se almacena como string ISO 8601 en UTC (`datetime.now(timezone.utc).isoformat()`).
- **RN-05 (Integración y Deduplicación en el Caso de Uso):**
  * Si `self.repository` está presente en `JobHunterUseCase`:
    1. Las ofertas recolectadas pasan por `collected_jobs = await self.repository.filter_unseen(collected_jobs)`.
    2. Las ofertas que superen el filtro son evaluadas.
    3. Cada oferta evaluada es registrada en el repositorio mediante `await self.repository.save_job(job, evaluation)`.
  * Si `self.repository is None`: el caso de uso procesa todas las ofertas sin filtrado, preservando retrocompatibilidad total con tests existentes.

### 4.2 Casos Borde (CB)
- **CB-01 (Bases de Datos en Memoria):** Cuando `db_path == ":memory:"`, la conexión debe gestionarse de modo que persista durante la vida del adaptador en el mismo proceso (o compartir la conexión bajo hilo seguro) para permitir pruebas unitarias sin residuos en disco.
- **CB-02 (Lista Vacía en filter_unseen):** Si `jobs` es `[]`, `filter_unseen` debe retornar inmediatamente `[]` sin emitir sentencias SQL.
- **CB-03 (Ejecución No Bloqueante con asyncio.to_thread):** Dado que `sqlite3` es una librería sincrónica de C, los métodos asíncronos del adaptador deben ejecutar las operaciones de base de datos a través de `asyncio.to_thread` para no bloquear el bucle de eventos principal.

---

## 5. Plan de Ejecución Secuencial (Atomic Tasks)
- [x] **Paso 1: Contrato de Puerto:** Crear `src/domain/ports/repository.py` con `JobRepositoryPort`.
- [x] **Paso 2: Suite de Pruebas Unitarias del Repositorio (TDD Red):**
  - Crear `tests/unit/test_sqlite_repository.py` utilizando `SQLiteJobRepositoryAdapter(":memory:")` para probar:
    * Creación de esquema y tabla `processed_jobs`.
    * `is_seen()` retorna `False` para vacantes nuevas y `True` para vacantes guardadas.
    * `save_job()` con y sin `evaluation` persistiendo tipos correctos.
    * `filter_unseen()` filtrando correctamente duplicados y manteniendo novedades.
    * Comportamiento con lista vacía en `filter_unseen()`.
- [x] **Paso 3: Implementación del Adaptador SQLite:**
  - Crear `src/adapters/repositories/__init__.py`.
  - Crear `src/adapters/repositories/sqlite.py` implementando `SQLiteJobRepositoryAdapter` según RN-01 a RN-04 y CB-01 a CB-03.
- [x] **Paso 4: Integración en JobHunterUseCase:**
  - Modificar `src/domain/use_cases/hunt_jobs.py` aceptando `repository: Optional[JobRepositoryPort] = None`.
  - Implementar el filtrado con `filter_unseen` y guardado con `save_job` según RN-05.
- [x] **Paso 5: Integración en main.py:**
  - Actualizar `main.py` instanciando `SQLiteJobRepositoryAdapter("data/job_hunter.db")` e inyectándolo en `JobHunterUseCase`.
- [x] **Paso 6: Validación Completa y Trazabilidad:**
  - Ejecutar `pytest tests/unit/test_sqlite_repository.py` (debe pasar al 100% en verde).
  - Ejecutar la suite completa `pytest` asegurando que todos los tests pasen.
  - Actualizar `specs/TASK_STATUS.md` registrando `SPEC-011` como `Implemented`.

---

## 6. Verificación y Checklist de Salida (Pipeline de 5 Pasos)
- [x] **1. Validación Arquitectónica:**
  - `JobRepositoryPort` definido como abstracción pura en el dominio.
  - Cero dependencias externas agregadas a `requirements.txt` (uso exclusivo de `sqlite3`).
  - Modelos en `src/domain/models/**` intactos.
- [x] **2. Generación de Tests:**
  - Suite unitaria implementada en `tests/unit/test_sqlite_repository.py` con DB en memoria.
- [x] **3. Validación de Cobertura y Ejecución:**
  - 100% de los tests pasando en verde con `pytest`.
- [x] **4. Documentación As-Built:**
  - Docstrings completos en métodos y clases creadas/modificadas.
- [x] **5. Trazabilidad y Estado:**
  - Checklist de esta spec completado y tabla de `specs/TASK_STATUS.md` actualizada.
