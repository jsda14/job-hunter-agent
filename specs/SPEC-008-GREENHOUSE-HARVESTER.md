# SPEC: SPEC-008 - Greenhouse Harvester Adapter

> **Instrucciones para el Agente Codificador:**
> 1. No instales dependencias externas, librerías ni paquetes que no estén explícitamente autorizados en la sección 2.
> 2. No agregues campos adicionales, métodos auxiliares públicos ni endpoints fuera de los contratos descritos en la sección 3.
> 3. Implementa únicamente las tareas listadas en la sección 5 en orden secuencial. Si encuentras un bloqueo, detén la ejecución y solicita aclaración.
> 4. Al finalizar, ejecuta el arnés de pruebas unitarias (`pytest tests/unit/test_greenhouse_harvester.py`) para validar los 5 pasos.

---

## 1. Alcance y Fronteras
* **Objetivo:** Implementar el adaptador concreto `GreenhouseHarvesterAdapter` que consuma la API pública de Greenhouse (`https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs?content=true`), normalice las vacantes al modelo canónico `JobRaw` con `SourcePlatform.GREENHOUSE`, maneje fallos de red encapsulándolos en `HarvesterConnectionError` y aplique valores por defecto si `location` o `posted_at` vienen nulos.
* **En Alcance (In-Scope):**
  - Implementación de `GreenhouseHarvesterAdapter` en `src/adapters/harvesters/greenhouse.py` satisfaciendo el puerto `JobHarvesterPort`.
  - Consumo asíncrono con `httpx.AsyncClient` del endpoint `https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs?content=true`.
  - Normalización de campos del JSON de Greenhouse a `JobRaw`:
    * `id`: `f"greenhouse_{job['id']}"`
    * `platform`: `SourcePlatform.GREENHOUSE`
    * `external_id`: `str(job['id'])`
    * `title`: `job['title']`
    * `company`: `company_slug`
    * `url`: `job['absolute_url']`
    * `location`: `job.get('location', {}).get('name')` con fallback a `"Remote"` si viene ausente o vacío.
    * `raw_description`: Limpieza básica de etiquetas HTML de `job.get('content', '')` o fallback a `job['title']` si viene vacío.
    * `posted_at`: Parseo de fecha ISO 8601 desde `job.get('updated_at')` en UTC o `None` como fallback si es nulo o inválido.
  - Manejo de excepciones de red y códigos de estado HTTP (404, 5xx) capturando `httpx.HTTPError` y relanzando `HarvesterConnectionError`.
  - Creación de fixture de respuesta muestra en `tests/harness/fixtures/greenhouse_payload.py`.
  - Creación de suite unitaria en `tests/unit/test_greenhouse_harvester.py`.
* **Fuera de Alcance (Out-of-Scope / Non-Goals):**
  - Modificación de modelos canónicos en `src/domain/models/job.py`.
  - Modificación de contratos de puertos en `src/domain/ports/harvester.py`.
  - Modificación del adaptador existente `LeverHarvesterAdapter`.
  - Modificación de los tests unitarios existentes en `tests/unit/**`.
  - Instalación de librerías de parsing HTML externas como BeautifulSoup (se utilizará regex estándar o stripping nativo).
* **Archivos Afectados:**
  * **Crear:**
    - `src/adapters/harvesters/greenhouse.py`
    - `tests/harness/fixtures/greenhouse_payload.py`
    - `tests/unit/test_greenhouse_harvester.py`
  * **Modificar:**
    - `specs/TASK_STATUS.md` (registro de la spec y métricas del harness tras completarse)
  * **Prohibido modificar:**
    - `src/domain/**`
    - `requirements.txt`
    - `src/adapters/harvesters/lever.py`
    - `tests/unit/test_lever_harvester.py`

---

## 2. Entorno y Dependencias Permitidas
* **Runtime / Versión:** Python 3.11+
* **Librerías autorizadas:**
  - `httpx` (cliente HTTP asíncrono ya presente en requirements.txt)
  - `pydantic` (modelos JobRaw y HttpUrl)
  - `pytest` y `pytest-asyncio` (arnés de pruebas)
  - Librerías estándar de Python (`datetime`, `html`, `re`, `inspect`)
* **Regla estricta:** Prohibido instalar o importar paquetes externos no listados ni alterar `requirements.txt`.

---

## 3. Contratos e Interfaces (Single Source of Truth)

### 3.1 Modelos de Dominio y Puertos Involucrados
```python
# Importación desde el dominio
from src.domain.ports.harvester import JobHarvesterPort, HarvesterConnectionError
from src.domain.models.job import JobRaw, SourcePlatform
```

### 3.2 Firma del Adaptador (`src/adapters/harvesters/greenhouse.py`)
```python
from typing import List, Optional
import httpx
from src.domain.ports.harvester import JobHarvesterPort
from src.domain.models.job import JobRaw

class GreenhouseHarvesterAdapter(JobHarvesterPort):
    """Adaptador para recolectar vacantes desde la API pública de Greenhouse."""

    def __init__(self, client: Optional[httpx.AsyncClient] = None) -> None:
        self._client = client

    async def fetch_jobs(self, company_slug: str) -> List[JobRaw]:
        """Consulta y normaliza las vacantes de un tablero público de Greenhouse.
        
        Args:
            company_slug: Identificador del tablero (board token) de la empresa.
            
        Returns:
            Lista de instancias canónicas JobRaw.
            
        Raises:
            HarvesterConnectionError: Si ocurre error HTTP, 404 de tablero inexistente o fallo de red.
        """
        pass
```

### 3.3 Estructura Esperada del Fixture (`tests/harness/fixtures/greenhouse_payload.py`)
```python
SAMPLE_GREENHOUSE_RESPONSE = {
    "jobs": [
        {
            "id": 4829102,
            "title": "Staff Backend Engineer - Python",
            "absolute_url": "https://boards.greenhouse.io/nubank/jobs/4829102",
            "location": {
                "name": "Bogota, Colombia"
            },
            "updated_at": "2024-05-10T14:30:00-04:00",
            "content": "&lt;p&gt;We are looking for a Staff Engineer with Python and FastAPI experience.&lt;/p&gt;"
        }
    ],
    "meta": {
        "total": 1
    }
}
```

---

## 4. Reglas de Negocio y Casos Borde

### 4.1 Reglas de Negocio (RN)
- **RN-01 (Endpoint y Query Parameter):** Debe consultar obligatoriamente la URL `https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs?content=true` para obtener la descripción completa de las vacantes.
- **RN-02 (Mapeo Canónico Estricto):**
  * `id`: `f"greenhouse_{job['id']}"` en minúsculas.
  * `platform`: `SourcePlatform.GREENHOUSE`.
  * `external_id`: `str(job['id'])`.
  * `title`: `job['title']`.
  * `company`: `company_slug`.
  * `url`: `job['absolute_url']`.
- **RN-03 (Fallback de Ubicación):** Si `location` es nulo, vacío o no contiene `name`, asignar por defecto `"Remote"`.
- **RN-04 (Saneamiento de Descripción):** El campo `content` de Greenhouse viene escapado con entidades HTML (`&lt;p&gt;`). Debe desescaparse (`html.unescape`) y limpiarse de tags HTML crudos (`<[^<]+?>`). Si el texto resultante está vacío, usar `title` como fallback.
- **RN-05 (Parseo y Fallback de Fecha):** Si `updated_at` está presente, parsear la fecha ISO 8601 y convertirla a UTC (`timezone.utc`). Si es nulo o inválido, asignar `None`.
- **RN-06 (Manejo de Errores de Conexión):** Cualquier error de red o código de error HTTP (404 Not Found, 500, etc.) debe ser capturado y relanzado como `HarvesterConnectionError`.

### 4.2 Casos Borde (CB)
- **CB-01 (Tablero sin vacantes):** Si `jobs` es una lista vacía `[]`, retornar `[]` sin errores.
- **CB-02 (Formato de Respuesta Inesperado):** Si el JSON retornado no contiene la clave `"jobs"` o no es un diccionario, lanzar `HarvesterConnectionError`.
- **CB-03 (Vacante con campos incompletos):** Ofertas que carezcan de `id`, `title` o `absolute_url` deben descartarse silenciosamente sin abortar el procesamiento de las demás vacantes.

---

## 5. Plan de Ejecución Secuencial (Atomic Tasks)
- [x] **Paso 1: Fixture de Pruebas:** Crear `tests/harness/fixtures/greenhouse_payload.py` con `SAMPLE_GREENHOUSE_RESPONSE`.
- [x] **Paso 2: Suite de Pruebas Unitarias (TDD Red):** Crear `tests/unit/test_greenhouse_harvester.py` cubriendo:
  * Caso exitoso: mapeo a `JobRaw`, `platform == SourcePlatform.GREENHOUSE`, saneamiento de HTML y conversión de fecha.
  * Fallbacks: `location` nulo -> `"Remote"`, `updated_at` nulo -> `None`.
  * Manejo de error HTTP: captura de 404 o fallo de red levantando `HarvesterConnectionError`.
- [x] **Paso 3: Implementación del Adaptador:** Crear `src/adapters/harvesters/greenhouse.py` implementando `GreenhouseHarvesterAdapter` según RN-01 a RN-06.
- [x] **Paso 4: Validación y Cobertura (TDD Green):**
  * Ejecutar `pytest tests/unit/test_greenhouse_harvester.py`.
  * Ejecutar la suite completa `pytest` asegurando que todos los tests (unitarios + integración) pasen al 100%.
- [x] **Paso 5: Trazabilidad y Estado:** Actualizar `specs/TASK_STATUS.md` registrando `SPEC-008` como implementada.

---

## 6. Verificación y Checklist de Salida (Pipeline de 5 Pasos)
- [x] **1. Validación Arquitectónica:**
  - `GreenhouseHarvesterAdapter` implementa fielmente `JobHarvesterPort`.
  - Sin dependencias externas añadidas en `requirements.txt`.
  - Modelos de dominio inalterados.
- [x] **2. Generación de Tests:**
  - Suite unitaria implementada en `tests/unit/test_greenhouse_harvester.py` usando mocks de `httpx.AsyncClient`.
- [x] **3. Validación de Cobertura y Ejecución:**
  - 100% de los tests pasando en verde con `pytest`.
- [x] **4. Documentación As-Built:**
  - Docstrings completos en métodos y clases de `GreenhouseHarvesterAdapter`.
- [x] **5. Trazabilidad y Estado:**
  - Checklist de esta spec completado y tabla de `specs/TASK_STATUS.md` actualizada.
