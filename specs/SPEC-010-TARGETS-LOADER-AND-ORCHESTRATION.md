# SPEC: SPEC-010 - Targets Loader & End-to-End Orchestration

> **Instrucciones para el Agente Codificador:**
> 1. No instales dependencias externas, librerías ni paquetes que no estén explícitamente autorizados en la sección 2.
> 2. No agregues campos adicionales, métodos auxiliares públicos ni endpoints fuera de los contratos descritos en la sección 3.
> 3. Implementa únicamente las tareas listadas en la sección 5 en orden secuencial. Si encuentras un bloqueo, detén la ejecución y solicita aclaración.
> 4. Al finalizar, ejecuta el arnés de pruebas unitarias (`pytest tests/unit/test_target_loader.py`) y la suite completa (`pytest`) para validar los 5 pasos de salida.

---

## 1. Alcance y Fronteras
* **Objetivo:** Externalizar la configuración de empresas objetivo desacoplándolas de `main.py` mediante un archivo JSON estructurado (`companies.json`), un cargador tipado (`JsonTargetLoaderAdapter`), la extensión de `JobHunterUseCase` para soportar `List[CompanyTarget]` mediante `CompositeHarvesterAdapter`, y la actualización del entrypoint `main.py` para ejecutar el pipeline integral de prospección multiplataforma (Lever + Greenhouse).
* **En Alcance (In-Scope):**
  - Creación del archivo de configuración `companies.json` en la raíz con empresas reales de prueba (ej. Kavak en Lever, Nubank en Greenhouse).
  - Extensión del DTO `CompanyTarget` en `src/domain/ports/harvester.py` para soportar el campo opcional `name: Optional[str] = None`.
  - Definición del puerto `TargetLoaderPort` y la excepción `TargetLoaderError` en `src/domain/ports/target_loader.py`.
  - Implementación del adaptador `JsonTargetLoaderAdapter` en `src/adapters/loaders/json_targets.py`.
  - Extensión de `JobHunterUseCase.execute()` en `src/domain/use_cases/hunt_jobs.py` para aceptar tanto `List[CompanyTarget]` como `List[str]` manteniendo retrocompatibilidad total con tests existentes.
  - Actualización de `main.py` para ensamblar el pipeline completo con `CompositeHarvesterAdapter` (Lever + Greenhouse), cargar objetivos desde `companies.json` y notificar resultados.
  - Creación de suite de pruebas unitarias en `tests/unit/test_target_loader.py`.
* **Fuera de Alcance (Out-of-Scope / Non-Goals):**
  - Modificación de modelos canónicos inmutables en `src/domain/models/job.py`.
  - Modificación de los adaptadores individuales `LeverHarvesterAdapter` y `GreenhouseHarvesterAdapter`.
  - Modificación del adaptador compuesto `CompositeHarvesterAdapter`.
  - Modificación de los evaluadores (`rule_based.py`, `pitch_generator.py`) ni notificador (`console.py`).
  - Adición de librerías de parsing de configuración pesadas (PyYAML, TOML externo); se usará la librería estándar `json` y `pydantic`.
* **Archivos Afectados:**
  * **Crear:**
    - `companies.json`
    - `src/domain/ports/target_loader.py`
    - `src/adapters/loaders/__init__.py`
    - `src/adapters/loaders/json_targets.py`
    - `tests/unit/test_target_loader.py`
  * **Modificar:**
    - `src/domain/ports/harvester.py` (campo `name: Optional[str] = None` en `CompanyTarget`)
    - `src/domain/use_cases/hunt_jobs.py` (soporte de `List[CompanyTarget]`)
    - `main.py` (pipeline con composite y target loader)
    - `specs/TASK_STATUS.md` (registro de la spec y métricas)
  * **Prohibido modificar:**
    - `src/domain/models/**`
    - `requirements.txt`
    - `src/adapters/harvesters/lever.py`
    - `src/adapters/harvesters/greenhouse.py`
    - `src/adapters/harvesters/composite.py`
    - `tests/unit/test_domain_models.py`
    - `tests/unit/test_lever_harvester.py`
    - `tests/unit/test_greenhouse_harvester.py`
    - `tests/unit/test_composite_harvester.py`
    - `tests/unit/test_hunt_jobs_usecase.py`
    - `tests/integration/test_lever_live.py`

---

## 2. Entorno y Dependencias Permitidas
* **Runtime / Versión:** Python 3.11+
* **Librerías autorizadas:**
  - `pydantic` (validación de `CompanyTarget`)
  - `pytest` y `pytest-asyncio` (suite de pruebas)
  - Librerías estándar de Python (`json`, `pathlib`, `typing`, `abc`, `asyncio`)
* **Regla estricta:** Prohibido instalar o importar paquetes externos no listados ni alterar `requirements.txt`.

---

## 3. Contratos e Interfaces (Single Source of Truth)

### 3.1 Extensión de DTO en `src/domain/ports/harvester.py`
```python
from typing import Optional
from pydantic import BaseModel, Field
from src.domain.models.job import SourcePlatform

class CompanyTarget(BaseModel):
    """Objetivo estructurado de recolección que asocia una empresa con su plataforma ATS."""
    company_slug: str = Field(min_length=1, description="Slug o identificador de la empresa en el ATS")
    platform: SourcePlatform = Field(description="Plataforma ATS donde está alojada la vacante")
    name: Optional[str] = Field(default=None, description="Nombre legible comercial de la empresa")
```

### 3.2 Definición del Puerto (`src/domain/ports/target_loader.py`)
```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Union
from src.domain.ports.harvester import CompanyTarget

class TargetLoaderError(Exception):
    """Excepción de dominio lanzada ante errores de lectura o validación de empresas objetivo."""
    pass

class TargetLoaderPort(ABC):
    """Puerto para cargar objetivos de prospección desde fuentes de configuración."""

    @abstractmethod
    def load_targets(self, file_path: Union[str, Path]) -> List[CompanyTarget]:
        """Lee y valida un archivo de configuración retornando una lista de CompanyTarget.
        
        Args:
            file_path: Ruta hacia el archivo de configuración.
            
        Returns:
            Lista de instancias validadas de CompanyTarget.
            
        Raises:
            TargetLoaderError: Si el archivo no existe, no es JSON válido o falla validación de esquema.
        """
        raise NotImplementedError
```

### 3.3 Adaptador JSON (`src/adapters/loaders/json_targets.py`)
```python
from pathlib import Path
from typing import List, Union
from src.domain.ports.harvester import CompanyTarget
from src.domain.ports.target_loader import TargetLoaderPort, TargetLoaderError

class JsonTargetLoaderAdapter(TargetLoaderPort):
    """Adaptador concreto para cargar y validar empresas desde archivos JSON."""

    def load_targets(self, file_path: Union[str, Path]) -> List[CompanyTarget]:
        """Carga y deserializa el archivo JSON en instancias de CompanyTarget."""
        pass
```

### 3.4 Estructura de `companies.json`
```json
[
  {
    "company_slug": "kavak",
    "platform": "lever",
    "name": "Kavak"
  },
  {
    "company_slug": "nubank",
    "platform": "greenhouse",
    "name": "Nubank"
  }
]
```

### 3.5 Extensión de `JobHunterUseCase.execute` (`src/domain/use_cases/hunt_jobs.py`)
```python
from typing import List, Tuple, Union
from src.domain.models.job import JobRaw, JobEvaluation
from src.domain.ports.harvester import CompanyTarget

class JobHunterUseCase:
    ...
    async def execute(
        self, targets: Union[List[str], List[CompanyTarget]]
    ) -> List[Tuple[JobRaw, JobEvaluation]]:
        """Ejecuta la orquestación recibiendo una lista de slugs (str) o una lista de CompanyTarget.
        
        Si recibe CompanyTarget y el harvester posee el método fetch_jobs_from_targets,
        delega la recolección multi-plataforma a dicho método.
        Si recibe str, ejecuta la recolección tradicional por slug.
        """
        pass
```

---

## 4. Reglas de Negocio y Casos Borde

### 4.1 Reglas de Negocio (RN)
- **RN-01 (Validación Estricta de Esquema):** Cada entrada en el JSON debe ser convertible a `CompanyTarget`. Si un registro tiene una plataforma desconocida o carece de `company_slug`, debe lanzarse `TargetLoaderError`.
- **RN-02 (Aislamiento de Error en Carga):** Si el archivo especificado en `load_targets` no existe o no tiene sintaxis JSON válida, debe lanzarse `TargetLoaderError` indicando la causa raíz.
- **RN-03 (Retrocompatibilidad en Caso de Uso):** `JobHunterUseCase.execute` debe continuar admitiendo `List[str]` (para no romper tests existentes de `test_hunt_jobs_usecase.py`) y admitir `List[CompanyTarget]`, delegando en `fetch_jobs_from_targets` cuando el harvester inyectado sea compatible.
- **RN-04 (Composición de Pipeline en main.py):** `main.py` debe instanciar `CompositeHarvesterAdapter` registrando `SourcePlatform.LEVER` y `SourcePlatform.GREENHOUSE`, cargar los objetivos desde `companies.json` mediante `JsonTargetLoaderAdapter`, y ejecutar el flujo completo informando en consola.

### 4.2 Casos Borde (CB)
- **CB-01 (Archivo companies.json vacío o lista vacía):** Si el JSON contiene `[]`, `load_targets` retorna `[]` y el caso de uso retorna `[]` de inmediato.
- **CB-02 (JSON que no es lista raíz):** Si el JSON contiene un diccionario u otro tipo que no sea una lista en la raíz (ej. `{"targets": []}`), debe lanzar `TargetLoaderError`.
- **CB-03 (Archivos corruptos o inaccesibles):** Archivos sin permisos o con sintaxis inválida deben capturarse y encapsularse en `TargetLoaderError`.

---

## 5. Plan de Ejecución Secuencial (Atomic Tasks)
- [x] **Paso 1: Contratos y DTOs:**
  - Actualizar `CompanyTarget` en `src/domain/ports/harvester.py` agregando `name: Optional[str] = None`.
  - Crear `src/domain/ports/target_loader.py` con `TargetLoaderError` y `TargetLoaderPort`.
- [x] **Paso 2: Suite de Pruebas Unitarias del Loader (TDD Red):**
  - Crear `tests/unit/test_target_loader.py` cubriendo carga exitosa, archivo inexistente, JSON inválido, formato raíz inválido y validación de `CompanyTarget`.
- [x] **Paso 3: Implementación del Adaptador Loader:**
  - Crear `src/adapters/loaders/__init__.py`.
  - Crear `src/adapters/loaders/json_targets.py` implementando `JsonTargetLoaderAdapter`.
- [x] **Paso 4: Archivo de Configuración:**
  - Crear `companies.json` en la raíz con empresas reales de prueba en Lever y Greenhouse.
- [x] **Paso 5: Extensión de Caso de Uso y Actualización de main.py:**
  - Actualizar `src/domain/use_cases/hunt_jobs.py` para soportar `Union[List[str], List[CompanyTarget]]`.
  - Actualizar `main.py` integrando `CompositeHarvesterAdapter`, `JsonTargetLoaderAdapter` y lectura de `companies.json`.
- [x] **Paso 6: Validación Completa y Trazabilidad:**
  - Ejecutar `pytest tests/unit/test_target_loader.py` (debe pasar en verde).
  - Ejecutar `pytest` asegurando que todos los tests (27 preexistentes + nuevos unitarios) pasen al 100%.
  - Actualizar `specs/TASK_STATUS.md` registrando `SPEC-010` como `Implemented`.

---

## 6. Verificación y Checklist de Salida (Pipeline de 5 Pasos)
- [x] **1. Validación Arquitectónica:**
  - Capa de dominio desacoplada del formato físico JSON.
  - Sin dependencias externas añadidas en `requirements.txt`.
  - Modelos canónicos inmutables en `src/domain/models/**` intactos.
- [x] **2. Generación de Tests:**
  - Suite unitaria implementada en `tests/unit/test_target_loader.py`.
- [x] **3. Validación de Cobertura y Ejecución:**
  - 100% de los tests pasando en verde con `pytest`.
- [x] **4. Documentación As-Built:**
  - Docstrings completos en métodos y clases creadas/modificadas.
- [x] **5. Trazabilidad y Estado:**
  - Checklist de esta spec completado y tabla de `specs/TASK_STATUS.md` actualizada.
