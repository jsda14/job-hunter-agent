# SPEC: SPEC-007 - Lever Integration Harness & Live Network Test

> **Instrucciones para el Agente Codificador:**
> 1. No instales dependencias externas, librerías ni paquetes que no estén explícitamente autorizados en la sección 2.
> 2. No agregues campos adicionales, métodos auxiliares públicos ni endpoints fuera de los contratos descritos en la sección 3.
> 3. Implementa únicamente las tareas listadas en la sección 5 en orden secuencial. Si encuentras un bloqueo, detén la ejecución y solicita aclaración.
> 4. Al finalizar, ejecuta la verificación del harness (`pytest -m integration` y `pytest -m "not integration"`) para validar los 5 pasos de salida.

---

## 1. Alcance y Fronteras
* **Objetivo:** Implementar el primer arnés de pruebas de integración reales en vivo contra la red externa para verificar que `LeverHarvesterAdapter` consume y normaliza correctamente ofertas de trabajo desde la API pública de Lever (`https://api.lever.co/v0/postings/{company_slug}?mode=json`) sin mocks, y valida el manejo ante empresas inexistentes.
* **En Alcance (In-Scope):**
  - Creación del archivo de prueba de integración `tests/integration/test_lever_live.py`.
  - Prueba en vivo con tráfico HTTP real a una empresa pública activa en Lever (ej. `palta` o `kavak`).
  - Validación de que la respuesta retorne instancias canónicas de `JobRaw` con campos y URLs válidas.
  - Prueba en vivo contra una empresa inexistente (`this-company-does-not-exist-xyz-999`) verificando que lance `HarvesterConnectionError`.
  - Marcado explícito de la suite con el decorador `@pytest.mark.integration` para aislar las pruebas de red de la suite unitaria rápida offline.
* **Fuera de Alcance (Out-of-Scope / Non-Goals):**
  - Modificación de contratos de dominio o modelos en `src/domain/**`.
  - Modificación del adaptador `src/adapters/harvesters/lever.py` salvo que se detecte una discrepancia demostrada con el API real de Lever.
  - Uso de mocks HTTP (`AsyncMock`, `patch`) en esta suite de integración.
  - Integración con otras plataformas externas (Greenhouse, Ashby).
  - Instalación de librerías adicionales en `requirements.txt`.
* **Archivos Afectados:**
  * **Crear:**
    - `tests/integration/test_lever_live.py`
  * **Modificar:**
    - `pytest.ini` (registro del marker `integration` para evitar warnings de pytest)
  * **Prohibido modificar:**
    - `src/domain/**` (modelos, puertos y casos de uso inmutables)
    - `requirements.txt`
    - `tests/unit/**` (suite unitaria existente)
    - `tests/harness/**` (fixtures preexistentes)

---

## 2. Entorno y Dependencias Permitidas
* **Runtime / Versión:** Python 3.11+
* **Librerías autorizadas:**
  - `pytest` (ejecución de assertions y categorización por markers)
  - `pytest-asyncio` (ejecución asíncrona con `@pytest.mark.asyncio`)
  - `httpx` (cliente HTTP asíncrono subyacente de `LeverHarvesterAdapter`)
  - `pydantic` (validación de modelos de datos `JobRaw` y `HttpUrl`)
* **Regla estricta:** Prohibido instalar o importar paquetes externos no listados arriba ni alterar `requirements.txt`.

---

## 3. Contratos e Interfaces (Single Source of Truth)

### 3.1 Modelos de Datos e Interfaces Bajo Prueba
```python
# Componentes importados desde el dominio y adaptadores del proyecto:
from src.adapters.harvesters.lever import LeverHarvesterAdapter
from src.domain.models.job import JobRaw, SourcePlatform
from src.domain.ports.harvester import HarvesterConnectionError
```

### 3.2 Firmas de Métodos de Integración (`tests/integration/test_lever_live.py`)
```python
import pytest
from src.adapters.harvesters.lever import LeverHarvesterAdapter
from src.domain.ports.harvester import HarvesterConnectionError
from src.domain.models.job import JobRaw, SourcePlatform

@pytest.mark.integration
@pytest.mark.asyncio
async def test_lever_live_harvest_real_company():
    """Consulta la API pública real de Lever para una empresa activa (ej. 'palta').
    
    Aserciones mínimas:
    - No debe lanzar excepciones no controladas.
    - Debe retornar una lista de instancias JobRaw (puede estar vacía si la empresa no tiene vacantes activas,
      pero si hay elementos, cada uno debe ser JobRaw válido con platform == SourcePlatform.LEVER y URL válida).
    """
    pass

@pytest.mark.integration
@pytest.mark.asyncio
async def test_lever_live_nonexistent_company_raises_harvester_error():
    """Consulta un slug inexistente en Lever ('this-company-does-not-exist-xyz-999').
    
    Aserciones mínimas:
    - Debe capturar el error HTTP 404 retornado por Lever.
    - Debe lanzar HarvesterConnectionError explícitamente.
    """
    pass
```

---

## 4. Reglas de Negocio y Casos Borde

### 4.1 Reglas de Negocio (RN)
- **RN-01 (Conexión Real sin Mocks):** La suite de integración debe instanciar `LeverHarvesterAdapter()` y llamar a `fetch_jobs()` realizando tráfico HTTP real contra `https://api.lever.co/v0/postings/{company_slug}?mode=json`.
- **RN-02 (Aislamiento mediante Marker):** Todas las funciones de test deben estar marcadas con `@pytest.mark.integration` y `@pytest.mark.asyncio` para permitir ejecución selectiva (`pytest -m integration` para red vs `pytest -m "not integration"` para desarrollo local sin conexión).
- **RN-03 (Validación de Esquema Real):** Si la empresa real retorna vacantes, cada objeto normalizado debe satisfacer:
  * `isinstance(job, JobRaw)`
  * `job.platform == SourcePlatform.LEVER`
  * `job.id.startswith("lever_")`
  * `len(job.title) >= 3`
  * `str(job.url).startswith("http")`
- **RN-04 (Mapeo de Errores de Red):** Las respuestas HTTP de error (404 Not Found, 5xx Server Error) emitidas por Lever deben transformarse invariablemente en `HarvesterConnectionError`.

### 4.2 Casos Borde (CB)
- **CB-01 (Empresa con 0 vacantes abiertas):** Si la empresa pública no tiene ofertas activas en el momento de la ejecución, la API devuelve `[]`. El adaptador debe retornar una lista vacía `[]` sin romper ni fallar.
- **CB-02 (Degradación de Red / Timeout):** Si hay latencia o corte de red hacia `api.lever.co`, `httpx` lanzará `RequestError`/`TimeoutException`, el cual el adaptador debe capturar y encapsular en `HarvesterConnectionError`.
- **CB-03 (Estructura de Vacante Heterogénea):** Respuestas de Lever sin campos opcionales (`categories.location`, listas vacías de requisitos) deben resolverse con los fallbacks implementados (`"Remote"`, concatenación segura).

---

## 5. Plan de Ejecución Secuencial (Atomic Tasks)
- [x] **Paso 1: Configuración de Pytest:** Registrar el marker `integration` en `pytest.ini` (`markers = integration: pruebas de integración con llamadas de red en vivo`).
- [x] **Paso 2: Creación del Módulo de Integración:** Crear el archivo `tests/integration/test_lever_live.py`.
- [x] **Paso 3: Implementación del Caso Positivo Real:** Implementar `test_lever_live_harvest_real_company` consultando `palta` (o `kavak`), comprobando integridad de tipos y propiedades en cada `JobRaw`.
- [x] **Paso 4: Implementación del Caso Negativo Real:** Implementar `test_lever_live_nonexistent_company_raises_harvester_error` verificando `pytest.raises(HarvesterConnectionError)` al consultar `this-company-does-not-exist-xyz-999`.
- [x] **Paso 5: Verificación Dual del Harness:**
  * Ejecutar `pytest -m integration` para asegurar paso en verde del arnés en vivo.
  * Ejecutar `pytest -m "not integration"` para asegurar que los 13 tests unitarios rápidos corran aislados sin tocar red.
- [x] **Paso 6: Registro de Estado:** Actualizar `specs/TASK_STATUS.md` reflejando el nuevo estado y métricas del harness.

---

## 6. Verificación y Checklist de Salida (Pipeline de 5 Pasos)
- [x] **1. Validación Arquitectónica:**
  - Sin librerías nuevas en `requirements.txt`.
  - Sin modificaciones en la capa de dominio (`src/domain/**`).
  - Único archivo nuevo en código de pruebas: `tests/integration/test_lever_live.py`.
- [x] **2. Generación de Tests:**
  - Tests en vivo creados con decoradores `@pytest.mark.integration` y `@pytest.mark.asyncio`.
- [x] **3. Validación de Cobertura y Ejecución:**
  - `pytest -m integration` ejecuta 2 tests en verde contra internet.
  - `pytest -m "not integration"` ejecuta 13 tests unitarios en verde.
  - Suite completa `pytest` ejecuta los 15 tests al 100% en verde.
- [x] **4. Documentación As-Built:**
  - Docstrings detallados en `tests/integration/test_lever_live.py` documentando los slugs consultados y el comportamiento esperado.
- [x] **5. Trazabilidad y Estado:**
  - `SPEC-007` con checklist completado y registrada como `Implemented` en `specs/TASK_STATUS.md`.
