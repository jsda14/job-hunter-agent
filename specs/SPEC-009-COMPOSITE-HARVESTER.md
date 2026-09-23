# SPEC: SPEC-009 - Composite Harvester Adapter & Multi-Platform Dispatcher

> **Instrucciones para el Agente Codificador:**
> 1. No instales dependencias externas, librerías ni paquetes que no estén explícitamente autorizados en la sección 2.
> 2. No agregues campos adicionales, métodos auxiliares públicos ni endpoints fuera de los contratos descritos en la sección 3.
> 3. Implementa únicamente las tareas listadas en la sección 5 en orden secuencial. Si encuentras un bloqueo, detén la ejecución y solicita aclaración.
> 4. Al finalizar, ejecuta el arnés de pruebas unitarias (`pytest tests/unit/test_composite_harvester.py`) para validar los 5 pasos de salida.

---

## 1. Alcance y Fronteras
* **Objetivo:** Implementar un adaptador compuesto (`CompositeHarvesterAdapter`) que actúe como registro y despachador de múltiples harvesters (`JobHarvesterPort`) indexados por `SourcePlatform`, permitiendo consultar objetivos estructurados heterogéneos (`CompanyTarget`), aislando fallos de red por objetivo y consolidando las ofertas capturadas en una única lista de `JobRaw`.
* **En Alcance (In-Scope):**
  - Definición del DTO `CompanyTarget` y de la excepción de dominio `UnsupportedPlatformError` en `src/domain/ports/harvester.py`.
  - Implementación de `CompositeHarvesterAdapter` en `src/adapters/harvesters/composite.py`.
  - Soporte de inyección por constructor y registro dinámico mediante método `register(platform, harvester)`.
  - Aislamiento de fallos: captura de `HarvesterConnectionError` por objetivo individual sin abortar el procesamiento de los demás.
  - Consolidación acumulativa de resultados en `list[JobRaw]`.
  - Lanzamiento de `UnsupportedPlatformError` ante solicitudes con plataformas no registradas.
  - Creación de suite unitaria en `tests/unit/test_composite_harvester.py`.
* **Fuera de Alcance (Out-of-Scope / Non-Goals):**
  - Modificación de modelos canónicos en `src/domain/models/job.py`.
  - Modificación de los adaptadores individuales existentes (`LeverHarvesterAdapter`, `GreenhouseHarvesterAdapter`).
  - Refactorización de `JobHunterUseCase` (se mantendrá compatible o se extenderá en especificaciones posteriores).
  - Instalación de nuevas dependencias en `requirements.txt`.
* **Archivos Afectados:**
  * **Crear:**
    - `src/adapters/harvesters/composite.py`
    - `tests/unit/test_composite_harvester.py`
  * **Modificar:**
    - `src/domain/ports/harvester.py` (adición de `UnsupportedPlatformError` y `CompanyTarget`)
    - `specs/TASK_STATUS.md` (registro de la spec y métricas del harness)
  * **Prohibido modificar:**
    - `src/domain/models/**`
    - `requirements.txt`
    - `src/adapters/harvesters/lever.py`
    - `src/adapters/harvesters/greenhouse.py`
    - `tests/unit/test_lever_harvester.py`
    - `tests/unit/test_greenhouse_harvester.py`

---

## 2. Entorno y Dependencias Permitidas
* **Runtime / Versión:** Python 3.11+
* **Librerías autorizadas:**
  - `pydantic` (definición y validación de `CompanyTarget`)
  - `pytest` y `pytest-asyncio` (suite de pruebas unitarias asíncronas)
  - Módulos estándar de Python (`typing`, `abc`, `asyncio`)
* **Regla estricta:** Prohibido instalar o importar paquetes externos no listados arriba ni modificar `requirements.txt`.

---

## 3. Contratos e Interfaces (Single Source of Truth)

### 3.1 Modelos de Datos y Excepciones (`src/domain/ports/harvester.py`)
```python
from pydantic import BaseModel, Field
from src.domain.models.job import SourcePlatform

class UnsupportedPlatformError(Exception):
    """Excepción lanzada cuando se solicita recolección sobre una plataforma no registrada en el despachador."""
    pass

class CompanyTarget(BaseModel):
    """Objetivo estructurado de recolección que asocia una empresa con su plataforma ATS."""
    company_slug: str = Field(min_length=1, description="Slug o identificador de la empresa en el ATS")
    platform: SourcePlatform = Field(description="Plataforma ATS donde está alojada la vacante")
```

### 3.2 Firma del Adaptador Compuesto (`src/adapters/harvesters/composite.py`)
```python
from typing import Dict, List, Optional
from src.domain.models.job import JobRaw, SourcePlatform
from src.domain.ports.harvester import JobHarvesterPort, CompanyTarget, UnsupportedPlatformError, HarvesterConnectionError

class CompositeHarvesterAdapter:
    """Adaptador compuesto que despacha recolecciones según la plataforma de cada objetivo."""

    def __init__(
        self,
        harvesters: Optional[Dict[SourcePlatform, JobHarvesterPort]] = None,
    ) -> None:
        """Inicializa el composite con un mapeo opcional de harvesters por SourcePlatform."""
        pass

    def register(self, platform: SourcePlatform, harvester: JobHarvesterPort) -> None:
        """Registra o actualiza el adaptador para una plataforma específica.
        
        Args:
            platform: Valor de SourcePlatform correspondiente.
            harvester: Instancia que implementa JobHarvesterPort.
        """
        pass

    async def fetch_jobs_from_targets(self, targets: List[CompanyTarget]) -> List[JobRaw]:
        """Despacha la recolección hacia los adaptadores correspondientes y consolida los resultados.
        
        Args:
            targets: Lista de objetivos estructurados CompanyTarget.
            
        Returns:
            Lista consolidada de JobRaw obtenidas de todas las consultas exitosas.
            
        Raises:
            UnsupportedPlatformError: Si algún objetivo especifica una plataforma no registrada.
        """
        pass
```

---

## 4. Reglas de Negocio y Casos Borde

### 4.1 Reglas de Negocio (RN)
- **RN-01 (Despacho por Plataforma):** Por cada `CompanyTarget` recibido, el composite debe consultar su registro interno de adaptadores utilizando `target.platform` y delegar la llamada a `await harvester.fetch_jobs(target.company_slug)`.
- **RN-02 (Registro e Inyección):** Los adaptadores pueden suministrarse en el constructor mediante un diccionario `{SourcePlatform: JobHarvesterPort}` o registrarse en tiempo de ejecución mediante `register(platform, harvester)`. Si se vuelve a registrar una plataforma existente, el nuevo adaptador sobrescribe al anterior.
- **RN-03 (Aislamiento de Fallas de Red):** Si la consulta de un objetivo falla lanzando `HarvesterConnectionError`, el adaptador debe capturar la excepción y continuar con el siguiente objetivo sin detener la recolección global.
- **RN-04 (Consolidación de Resultados):** Las listas de vacantes devueltas por cada objetivo exitoso deben agregarse en una lista única de `JobRaw`, preservando el orden de ejecución de los objetivos.
- **RN-05 (Validación Estricta de Plataformas Soportadas):** Si se solicita un objetivo con una `SourcePlatform` que no esté presente en el registro del composite, debe lanzarse de manera inmediata `UnsupportedPlatformError` especificando la plataforma no soportada.

### 4.2 Casos Borde (CB)
- **CB-01 (Lista de objetivos vacía):** Si `targets` es una lista vacía `[]`, retornar inmediatamente una lista vacía `[]` sin realizar operaciones.
- **CB-02 (Fallo total de red):** Si todos los objetivos lanzan `HarvesterConnectionError`, el método debe retornar `[]` de forma resiliente sin propagar excepciones no controladas.
- **CB-03 (Objetivos repetidos o múltiples plataformas):** Permite procesar múltiples empresas que compartan la misma plataforma (ej. dos empresas Lever) o empresas en plataformas distintas en una sola llamada.

---

## 5. Plan de Ejecución Secuencial (Atomic Tasks)
- [x] **Paso 1: Contratos de Dominio:** Actualizar `src/domain/ports/harvester.py` agregando `UnsupportedPlatformError` y `CompanyTarget`.
- [x] **Paso 2: Suite de Pruebas Unitarias (TDD Red):** Crear `tests/unit/test_composite_harvester.py` verificando:
  * Despacho exitoso multiplataforma consolidando vacantes de Lever y Greenhouse.
  * Registro dinámico con `register()` y vía constructor.
  * Aislamiento de fallos cuando un objetivo lanza `HarvesterConnectionError` y el otro responde exitosamente.
  * Lanzamiento de `UnsupportedPlatformError` cuando la plataforma no está registrada.
  * Comportamiento con lista vacía de objetivos y fallo total de red.
- [x] **Paso 3: Implementación del Adaptador:** Crear `src/adapters/harvesters/composite.py` implementando `CompositeHarvesterAdapter` según RN-01 a RN-05 y CB-01 a CB-03.
- [x] **Paso 4: Validación y Cobertura (TDD Green):**
  * Ejecutar `pytest tests/unit/test_composite_harvester.py`.
  * Ejecutar la suite completa `pytest` asegurando que todos los tests pasen al 100%.
- [x] **Paso 5: Trazabilidad y Estado:** Actualizar `specs/TASK_STATUS.md` registrando `SPEC-009` como implementada.

---

## 6. Verificación y Checklist de Salida (Pipeline de 5 Pasos)
- [x] **1. Validación Arquitectónica:**
  - `CompositeHarvesterAdapter` no acopla directamente implementaciones concretas, sino el puerto abstracto `JobHarvesterPort`.
  - Sin dependencias externas añadidas en `requirements.txt`.
  - Modelos de `src/domain/models/**` inalterados.
- [x] **2. Generación de Tests:**
  - Suite unitaria implementada en `tests/unit/test_composite_harvester.py` utilizando mocks de `JobHarvesterPort`.
- [x] **3. Validación de Cobertura y Ejecución:**
  - 100% de los tests pasando en verde con `pytest`.
- [x] **4. Documentación As-Built:**
  - Docstrings completos en métodos y clases de `CompositeHarvesterAdapter` y nuevos contratos en `src/domain/ports/harvester.py`.
- [x] **5. Trazabilidad y Estado:**
  - Checklist de esta spec completado y tabla de `specs/TASK_STATUS.md` actualizada.
