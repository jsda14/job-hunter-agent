# SPEC: SPEC-012 - Telegram Notifier Adapter

> **Instrucciones para el Agente Codificador:**
> 1. No instales dependencias externas, librerías ni paquetes que no estén explícitamente autorizados en la sección 2.
> 2. No agregues campos adicionales, métodos auxiliares públicos ni endpoints fuera de los contratos descritos en la sección 3.
> 3. Implementa únicamente las tareas listadas en la sección 5 en orden secuencial. Si encuentras un bloqueo, detén la ejecución y solicita aclaración.
> 4. Al finalizar, ejecuta el arnés de pruebas unitarias (`pytest tests/unit/test_telegram_notifier.py`) y la suite completa (`pytest`) para validar los 5 pasos de salida.

---

## 1. Alcance y Fronteras
* **Objetivo:** Implementar un adaptador de notificación push móvil para Telegram (`TelegramNotifierAdapter`) en `src/adapters/notifiers/telegram.py` que satisfaga el puerto `JobNotifierPort`, permitiendo despachar alertas formateadas en HTML con métricas de fit y pitch accionable vía la Bot API oficial de Telegram sin dependencias externas pesadas.
* **En Alcance (In-Scope):**
  - Definición de la jerarquía de excepciones de notificación en `src/domain/ports/notifier.py`: `NotifierError`, `NotifierConfigurationError` y `NotifierDeliveryError`.
  - Implementación de `TelegramNotifierAdapter` en `src/adapters/notifiers/telegram.py` heredando de `JobNotifierPort`.
  - Soporte de inyección explícita de credenciales (`bot_token`, `chat_id`, `client`) con fallback a variables de entorno (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`).
  - Envío asíncrono vía `httpx` hacia `https://api.telegram.org/bot{bot_token}/sendMessage`.
  - Formateo de mensajes en HTML (`parse_mode="HTML"`) con escape de caracteres (`html.escape`), incluyendo enlace web, título, empresa, score de fit, stack detectado y bloque de pitch preformateado (`<pre>` o `<blockquote>`) para copia rápida en dispositivos móviles.
  - Manejo robusto de errores HTTP de Telegram (400, 401, 500) y de red/timeout traduciéndolos en `NotifierDeliveryError`.
  - Arnés de pruebas unitarias exhaustivas en `tests/unit/test_telegram_notifier.py` con simulación y mocks de `httpx.AsyncClient`.
* **Fuera de Alcance (Out-of-Scope / Non-Goals):**
  - Instalación de librerías como `python-telegram-bot`, `telethon` o `aiogram`.
  - Modificación de modelos de dominio canónicos en `src/domain/models/**`.
  - Implementación de comandos interactivos de Telegram o webhooks de recepción (el agente es un notificador unidireccional).
  - Modificación de suites de tests unitarias previas (`test_domain_models.py`, `test_lever_harvester.py`, `test_greenhouse_harvester.py`, `test_composite_harvester.py`, `test_sqlite_repository.py`, etc.).
* **Archivos Afectados:**
  * **Crear:**
    - `src/adapters/notifiers/telegram.py`
    - `tests/unit/test_telegram_notifier.py`
  * **Modificar:**
    - `src/domain/ports/notifier.py` (adición de jerarquía de excepciones `NotifierError`, `NotifierConfigurationError`, `NotifierDeliveryError`)
  * **Prohibido modificar:**
    - `src/domain/models/**`
    - `requirements.txt`
    - `src/adapters/harvesters/**`
    - `src/adapters/evaluators/**`
    - `src/adapters/loaders/**`
    - `src/adapters/repositories/**`
    - `tests/unit/test_domain_models.py`
    - `tests/unit/test_composite_harvester.py`
    - `tests/unit/test_sqlite_repository.py`
    - `tests/unit/test_target_loader.py`

---

## 2. Entorno y Dependencias Permitidas
* **Runtime / Versión:** Python 3.11+
* **Librerías autorizadas:**
  - `httpx` (cliente HTTP asíncrono ya presente en `requirements.txt`)
  - `os`, `html`, `typing`, `abc` (librería estándar de Python)
  - `pydantic` (modelos canónicos `JobRaw` y `JobEvaluation`)
  - `pytest`, `pytest-asyncio`, `unittest.mock` (suite de pruebas del harness)
* **Regla estricta:** Prohibido instalar paquetes externos adicionales (ej. `python-telegram-bot`, `respx`, `requests`) ni alterar `requirements.txt`.

---

## 3. Contratos e Interfaces (Single Source of Truth)

### 3.1 Excepciones y Puerto de Notificación (`src/domain/ports/notifier.py`)
```python
from abc import ABC, abstractmethod
from typing import List, Tuple

from src.domain.models.job import JobEvaluation, JobRaw


class NotifierError(Exception):
    """Excepción base del dominio para fallos en el subsistema de notificación."""
    pass


class NotifierConfigurationError(NotifierError):
    """Lanzada cuando faltan credenciales o configuraciones requeridas para notificar."""
    pass


class NotifierDeliveryError(NotifierError):
    """Lanzada cuando falla la entrega de una notificación al canal externo (HTTP error, timeout, red)."""
    pass


class JobNotifierPort(ABC):
    """Port defining the interface for notifying or displaying evaluated jobs."""

    @abstractmethod
    async def notify(self, jobs: List[Tuple[JobRaw, JobEvaluation]]) -> int:
        """Notify or display actionable jobs.

        Args:
            jobs: List of (JobRaw, JobEvaluation) pairs.

        Returns:
            Count of successfully notified items.

        Raises:
            NotifierConfigurationError: Si las credenciales requeridas no están configuradas.
            NotifierDeliveryError: Si la entrega al canal de notificación falla.
        """
        raise NotImplementedError
```

### 3.2 Adaptador Concreto de Telegram (`src/adapters/notifiers/telegram.py`)
```python
import html
import os
from typing import List, Optional, Tuple
import httpx

from src.domain.models.job import JobEvaluation, JobRaw
from src.domain.ports.notifier import (
    JobNotifierPort,
    NotifierConfigurationError,
    NotifierDeliveryError,
)


class TelegramNotifierAdapter(JobNotifierPort):
    """Adaptador de notificación vía Telegram Bot API utilizando httpx asíncrono."""

    TELEGRAM_API_BASE_URL: str = "https://api.telegram.org"

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """Inicializa el adaptador resolviendo credenciales vía argumentos o entorno.

        Args:
            bot_token: Token del bot de Telegram. Si es None, lee TELEGRAM_BOT_TOKEN de entorno.
            chat_id: ID del chat o canal receptor. Si es None, lee TELEGRAM_CHAT_ID de entorno.
            client: Instancia opcional inyectada de httpx.AsyncClient para pruebas o reuso de conexiones.
        """
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.client = client

    def _format_message(self, job: JobRaw, evaluation: JobEvaluation) -> str:
        """Genera el cuerpo del mensaje en formato HTML seguro para Telegram."""
        pass

    async def notify(self, jobs: List[Tuple[JobRaw, JobEvaluation]]) -> int:
        """Envía cada vacante accionable como mensaje individual a Telegram.

        Args:
            jobs: Lista de tuplas (JobRaw, JobEvaluation).

        Returns:
            Número total de mensajes entregados exitosamente.

        Raises:
            NotifierConfigurationError: Si bot_token o chat_id no están definidos al procesar vacantes.
            NotifierDeliveryError: Si ocurre un error de red, timeout o respuesta HTTP >= 400 de Telegram.
        """
        pass
```

---

## 4. Reglas de Negocio y Casos Borde

### 4.1 Reglas de Negocio (RN)
- **RN-01 (Endpoint Canónico y Método):** Las notificaciones deben despacharse mediante `POST` asíncrono al endpoint `https://api.telegram.org/bot{bot_token}/sendMessage`.
- **RN-02 (Resolución de Credenciales y Fallback):**
  - Si `bot_token` o `chat_id` no se pasan en el constructor, se leen desde las variables de entorno `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`.
  - Si la lista de `jobs` tiene al menos un elemento y `bot_token` o `chat_id` están ausentes o son strings vacíos/espacios en blanco, debe lanzarse inmediatamente `NotifierConfigurationError`.
- **RN-03 (Estructura y Formato del Mensaje HTML):**
  - El payload enviado debe incluir `chat_id`, `text`, `parse_mode="HTML"` y deshabilitar vista previa de enlaces (`disable_web_page_preview=True` o equivalente).
  - Cada mensaje debe estructurarse con:
    1. Encabezado con título del puesto y enlace HTML `<a href="{job.url}">{escaped_title}</a>`.
    2. Nombre de la empresa (`{escaped_company}`).
    3. Métrica de compatibilidad: `Fit Score: {fit_score:.1f}%`.
    4. Stack detectado formateado: `Stack: {', '.join(stack)}` (o `N/A` si está vacío).
    5. Propuesta de pitch dentro de un bloque preformateado `<pre>{escaped_pitch}</pre>` para que el usuario pueda copiarlo con un toque desde su teléfono.
- **RN-04 (Sanitización HTML contra Inyección / Sintaxis Rota):**
  - Todos los textos dinámicos (`job.title`, `job.company`, stack y `evaluation.tailored_pitch`) deben ser sanitizados con `html.escape(..., quote=False)` para evitar que caracteres como `<`, `>`, `&` rompan el parser de Telegram y causen error 400 Bad Request.
- **RN-05 (Manejo Robusto de Respuestas y Fallas de Red):**
  - Si Telegram responde con código de estado HTTP >= 400 (ej. 400 Bad Request por parseo, 401 Unauthorized por token inválido, 403 Forbidden por bot bloqueado, 429 Too Many Requests o 5xx), debe capturarse la excepción y relanzar `NotifierDeliveryError` con mensaje contextual descriptivo.
  - Si ocurre un timeout o error de conexión (`httpx.RequestError`), debe capturarse y relanzarse como `NotifierDeliveryError`.
- **RN-06 (Gestión del Ciclo de Vida del Cliente HTTP):**
  - Si se inyecta un `client: httpx.AsyncClient` en el constructor, el adaptador debe utilizarlo sin cerrarlo tras la petición.
  - Si `client` es `None`, debe gestionar un cliente propio de forma contextual (`async with httpx.AsyncClient(timeout=10.0) as client:`) asegurando la liberación de recursos.

### 4.2 Casos Borde (CB)
- **CB-01 (Lista de Vacantes Vacía):**
  - Si `jobs` es una lista vacía `[]`, el método `notify()` debe retornar `0` de inmediato sin validar credenciales ni realizar ninguna petición HTTP.
- **CB-02 (Pitch Nulo o Vacío):**
  - Si `evaluation.tailored_pitch` es `None` o string vacío, el bloque de pitch debe mostrar `"Sin pitch generado"` en lugar de fallar o dejar campos vacíos.
- **CB-03 (Caracteres Especiales en Contenido):**
  - Ofertas con títulos como `"Tech Lead (C++ & C# <Cloud>)"` deben ser enviadas sin provocar fallo de entidad en Telegram gracias a `html.escape`.
- **CB-04 (Múltiples Vacantes en una Ejecución):**
  - Si se reciben N vacantes, se envían N peticiones secuenciales y se retorna el total `N` si todas fueron entregadas. Si alguna falla con HTTP o error de conexión, se levanta `NotifierDeliveryError`.

---

## 5. Plan de Ejecución Secuencial (Atomic Tasks)

- [x] **Paso 1: Contratos de Dominio y Excepciones:**
  - Actualizar `src/domain/ports/notifier.py` agregando `NotifierError`, `NotifierConfigurationError` y `NotifierDeliveryError` heredando de `Exception`.
  - Mantener la firma intacta de `JobNotifierPort.notify`.
- [x] **Paso 2: Suite de Pruebas Unitarias del Adaptador (Harness First):**
  - Crear `tests/unit/test_telegram_notifier.py` cubriendo:
    * Envío exitoso con payload validado (`chat_id`, `text` con formato HTML, `parse_mode="HTML"`, `disable_web_page_preview=True`).
    * Retorno de conteo correcto al entregar vacantes.
    * Lanzamiento de `NotifierConfigurationError` cuando faltan `bot_token` o `chat_id`.
    * Retorno inmediato de `0` ante lista vacía sin invocar HTTP ni lanzar error de configuración.
    * Fallo con 401 Unauthorized relanzado como `NotifierDeliveryError`.
    * Fallo con 400 Bad Request relanzado como `NotifierDeliveryError`.
    * Fallo de conexión o timeout (`httpx.ConnectTimeout`) relanzado como `NotifierDeliveryError`.
    * Sanitización de entidades HTML (`<`, `>`, `&`) en título y pitch.
    * Inyección de `client: httpx.AsyncClient` externo y gestión de cliente propio cuando es `None`.
- [x] **Paso 3: Implementación de TelegramNotifierAdapter:**
  - Crear `src/adapters/notifiers/telegram.py` implementando `TelegramNotifierAdapter` conforme a la Sección 3.2, cumpliendo rigurosamente RN-01 a RN-06 y CB-01 a CB-04.
- [x] **Paso 4: Validación y Cobertura del Harness:**
  - Ejecutar `pytest tests/unit/test_telegram_notifier.py` (100% verde).
  - Ejecutar suite completa `pytest` (mínimo 43 tests en verde, 0 fallos).
- [x] **Paso 5: Documentación y Trazabilidad:**
  - Actualizar `specs/TASK_STATUS.md` registrando `SPEC-012` como `Implemented`.

---

## 6. Verificación y Checklist de Salida (Pipeline de 5 Pasos)
- [x] **1. Validación Arquitectónica:**
  - Sin librerías externas de Telegram (`python-telegram-bot`, `telethon`).
  - Uso exclusivo de `httpx` estándar ya listado en `requirements.txt`.
  - Sin modificaciones a `src/domain/models/**` ni al comportamiento de notifiers previos.
- [x] **2. Generación de Tests:**
  - Pruebas unitarias en `tests/unit/test_telegram_notifier.py` cubriendo todas las RN y CB de la Sección 4 mediante mocks limpios de `httpx`.
- [x] **3. Validación de Cobertura:**
  - Suite de `pytest` ejecutada con éxito (0 fallos, 100% verde).
- [x] **4. Documentación As-Built:**
  - Docstrings completos en `TelegramNotifierAdapter`, métodos y excepciones.
- [x] **5. Trazabilidad y Estado:**
  - Checklist de esta spec completado y entrada registrada en `specs/TASK_STATUS.md`.
