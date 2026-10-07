# Clase Magistral: Job Hunter Agent — Arquitectura, Flujos y Razonamiento

Este documento explica **cada clase, cada función, cada método**: qué recibe, qué entrega, por qué existe, y cómo se conecta con el resto. Está pensado para leerse de arriba hacia abajo, del centro (dominio) hacia afuera (adaptadores), igual que se diseñó.

---

## Parte 0 — El mapa mental antes de entrar al código

Imagina el proyecto como una **rueda hexagonal** (de ahí el nombre "arquitectura hexagonal"):

- En el **centro** vive el dominio: las reglas de negocio puras, sin saber nada del mundo exterior (sin saber qué es HTTP, sin saber qué es Lever, sin saber qué es la consola).
- Alrededor del centro hay **puertos** (`ports/`): son enchufes, contratos, interfaces abstractas. Dicen *qué* se puede hacer, nunca *cómo*.
- Fuera del hexágono están los **adaptadores** (`adapters/`): implementaciones concretas que se conectan a esos enchufes. Son reemplazables sin tocar el centro.

Por qué importa: si mañana cambias Lever por Greenhouse, o la consola por un bot de Slack, **el dominio no se entera**. Solo escribes un adaptador nuevo que cumpla el mismo contrato.

---

## Parte 1 — El Dominio (`src/domain/`)

### 1.1 Modelos (`src/domain/models/job.py`)

Este archivo define los **sustantivos** del sistema: las cosas sobre las que se habla. Usa Pydantic, que no es solo "una clase con atributos" — es una clase que **se valida sola** en el momento de crearse. Si construyes un objeto con datos inválidos, Pydantic lanza una excepción inmediatamente, antes de que ese dato corrupto contamine el resto del sistema. Esto se llama **fail-fast** (fallar rápido, en el borde, no en el medio del proceso).

#### `class SourcePlatform(str, Enum)`

```python
class SourcePlatform(str, Enum):
    LEVER = "lever"
    GREENHOUSE = "greenhouse"
    ASHBY = "ashby"
```

- **Qué es:** un enum de texto. Al heredar de `str` además de `Enum`, sus valores se comportan como strings normales (se pueden comparar con `==` a `"lever"` directamente, se serializan limpio a JSON).
- **Qué recibe:** nada, es una constante de tipo.
- **Qué entrega:** un conjunto cerrado de valores válidos: `"lever"`, `"greenhouse"`, `"ashby"`.
- **Por qué existe:** para que `JobRaw.platform` nunca pueda ser un string arbitrario como `"leber"` (typo) o `"indeed"` (plataforma no soportada). El tipo mismo impide el error — no hace falta un `if` en ningún lado validando esto.

#### `class JobRaw(BaseModel)`

Representa **una vacante de trabajo tal como fue capturada**, ya normalizada a la forma canónica del dominio (no es el JSON crudo de Lever — eso se transforma en el adaptador, lo verás en la Parte 2).

Campos y su razón de ser:

| Campo | Tipo | Por qué esa regla |
|---|---|---|
| `id` | `str` | Identificador determinista `{platform}_{external_id}` (p. ej. `lever_abc123`). Determinista significa: si vuelves a recolectar la misma vacante, obtienes el mismo `id` — esto es lo que permitiría en el futuro deduplicar sin base de datos adicional. |
| `platform` | `SourcePlatform` | De dónde vino, usando el enum cerrado de arriba. |
| `external_id` | `str` | El ID nativo que usa Lever/Greenhouse/Ashby internamente, guardado tal cual por trazabilidad. |
| `title` | `str`, `min_length=3` | Un título de 1-2 caracteres casi seguro es basura/error de parseo, así que se rechaza en el borde. |
| `company` | `str`, `min_length=2` | Misma lógica de guardia mínima. |
| `url` | `HttpUrl` | Pydantic valida que sea una URL con esquema http/https bien formada — no un string cualquiera. |
| `location` | `str` | Texto libre (ciudad, "Remote", etc.) |
| `raw_description` | `str`, `min_length=1` | El texto completo de la vacante — es la materia prima que luego analiza el evaluador. No puede estar vacío porque sin texto no hay nada que evaluar. |
| `posted_at` | `Optional[datetime]` | Puede no venir (no todas las plataformas lo exponen), así que es opcional con default `None`. |

**Qué recibe:** sus propios campos como argumentos al construirse (`JobRaw(id=..., platform=..., ...)`).
**Qué entrega:** una instancia inmutable-por-convención (Pydantic v2 permite mutación, pero el proyecto la trata como un DTO de solo lectura) que **ya está garantizado que es válida** — cualquier código que reciba un `JobRaw` no necesita re-validar sus campos.

#### `class JobEvaluation(BaseModel)`

Representa **el veredicto** sobre una vacante: qué tan bien encaja con el perfil del candidato.

| Campo | Tipo | Rol |
|---|---|---|
| `job_id` | `str` | Enlaza esta evaluación con el `JobRaw.id` que la originó (relación 1 a 1). |
| `fit_score` | `float`, rango `[0.0, 100.0]` | Puntaje numérico de encaje, validado por rango — no puede ser -5 ni 150. |
| `salary_match` | `bool` | Si cumple el piso salarial (en esta iteración siempre `True`, ver Parte 2.2 — es un campo preparado para una regla futura). |
| `requires_spoken_english` | `bool` | Bandera excluyente: ¿la vacante exige inglés hablado fluido en tiempo real? |
| `tech_stack_detected` | `list[str]` | Qué tecnologías del perfil del candidato aparecen mencionadas en la vacante. |
| `pros` | `list[str]` | Razones a favor, en lenguaje humano. |
| `red_flags` | `list[str]` | Razones de alerta, en lenguaje humano. |
| `is_actionable` | `bool` | El veredicto final: ¿vale la pena postularse? |
| `tailored_pitch` | `Optional[str]` | El texto de postulación generado — `None` hasta que se genera (ver Parte 2.3). |

##### `model_validator` — `validate_spoken_english_actionable`

```python
@model_validator(mode="after")
def validate_spoken_english_actionable(self) -> "JobEvaluation":
    if self.requires_spoken_english and self.is_actionable:
        raise ValueError("Spoken English jobs cannot be actionable")
    return self
```

- **Qué es:** un validador de Pydantic que corre *después* (`mode="after"`) de que todos los campos individuales ya se validaron, y que puede comparar varios campos entre sí (algo que un `Field(...)` individual no puede hacer, porque un campo no sabe lo que vale otro campo).
- **Qué recibe:** `self`, la instancia ya casi construida con todos sus campos poblados.
- **Qué entrega:** `self` de vuelta si todo está bien (Pydantic exige que el validador retorne la instancia), o lanza `ValueError` si la combinación de campos es inválida.
- **Por qué existe:** esta es la **invariante de negocio más importante del dominio**: nunca, bajo ninguna circunstancia, una vacante que exige inglés hablado fluido puede marcarse como accionable. Ponerla aquí —en el modelo, no en el evaluador— significa que **es imposible construir un `JobEvaluation` inconsistente**, sin importar qué adaptador de evaluación se use en el futuro (regex hoy, LLM mañana). Es la diferencia entre "esperamos que todos los evaluadores respeten la regla" y "el sistema de tipos lo hace cumplir".

---

### 1.2 Puertos (`src/domain/ports/`)

Los puertos son **clases abstractas** (`abc.ABC` + `@abstractmethod`). No tienen lógica, solo firman contratos: "quien implemente esto, debe ofrecer este método con esta firma exacta". Ninguna de estas clases se instancia jamás directamente.

#### `JobHarvesterPort` (`harvester.py`)

```python
class JobHarvesterPort(ABC):
    @abstractmethod
    async def fetch_jobs(self, company_slug: str) -> List[JobRaw]:
        ...
```

- **Qué recibe (contractualmente):** un `company_slug: str` — el identificador de la empresa en el ATS (p. ej. `"rappi"`).
- **Qué entrega (contractualmente):** una `List[JobRaw]` — ya en formato canónico del dominio, sin importar de qué ATS haya venido.
- **Por qué es `async`:** porque recolectar implica una llamada de red, que es una operación de I/O que puede tardar; `async/await` permite que el programa no se quede bloqueado esperando mientras podría estar haciendo otra cosa (aunque en este proyecto el uso es secuencial, ver Parte 1.3 — la asincronía está preparada para paralelizarse fácilmente después).

##### `class HarvesterConnectionError(Exception)`

- **Qué es:** una excepción de dominio propia, no una excepción genérica de Python ni de `httpx`.
- **Por qué existe:** el dominio no puede depender de `httpx.HTTPError` (eso sería el dominio conociendo detalles del adaptador — rompería la regla de dependencia hexagonal). En cambio, el puerto define su **propio vocabulario de errores**, y es responsabilidad del adaptador **traducir** cualquier error técnico (timeout, 404, JSON malformado) a esta excepción de dominio. Así el `use_case` (Parte 1.3) puede capturar `HarvesterConnectionError` sin saber ni que `httpx` existe.

#### `JobEvaluatorPort` (`evaluator.py`)

```python
class JobEvaluatorPort(ABC):
    @abstractmethod
    async def evaluate(self, job: JobRaw) -> JobEvaluation:
        ...
```

- **Qué recibe:** un `JobRaw` (una vacante ya normalizada).
- **Qué entrega:** un `JobEvaluation` (el veredicto).
- **Por qué existe como interfaz separada del harvester:** *Single Responsibility* — recolectar y evaluar son dos preocupaciones distintas que cambian por razones distintas (cambias de ATS sin tocar las reglas de evaluación, y cambias las reglas de evaluación —o las reemplazas por un LLM— sin tocar cómo se recolecta).

#### `PitchGeneratorPort` (`pitch_generator.py`)

```python
class PitchGeneratorPort(ABC):
    @abstractmethod
    async def generate_pitch(self, job: JobRaw, evaluation: JobEvaluation) -> str:
        ...
```

- **Qué recibe:** el `JobRaw` original **y** el `JobEvaluation` ya calculado (necesita ambos: el título/empresa vienen del job, el stack detectado viene de la evaluación).
- **Qué entrega:** un `str` — el texto del pitch, listo para copiar y pegar.
- **Por qué es un puerto separado del evaluador:** de nuevo SRP. Evaluar (¿es buena esta vacante?) y redactar (¿cómo me vendo para esta vacante?) son decisiones independientes — de hecho una podría delegarse a un LLM generativo mientras la otra sigue siendo reglas determinísticas, sin que se estorben.

#### `JobNotifierPort` (`notifier.py`)

```python
class JobNotifierPort(ABC):
    @abstractmethod
    async def notify(self, jobs: List[Tuple[JobRaw, JobEvaluation]]) -> int:
        ...
```

- **Qué recibe:** la lista final de pares `(JobRaw, JobEvaluation)` — solo los accionables, ya con pitch incluido.
- **Qué entrega:** un `int` — cuántos se notificaron exitosamente (permite que un futuro adaptador de email, por ejemplo, reporte si algunos fallaron al enviarse).
- **Por qué existe:** aísla el *cómo se entera el humano* (consola hoy, email/Slack mañana) del resto del flujo.

---

### 1.3 El Caso de Uso — `JobHunterUseCase` (`src/domain/use_cases/hunt_jobs.py`)

Esta es **la clase más importante del proyecto**: el orquestador. No sabe hacer nada por sí mismo (no sabe hablar HTTP, no sabe evaluar con regex, no sabe imprimir) — su única responsabilidad es **coordinar la secuencia correcta de llamadas** a sus tres colaboradores, respetando las reglas de negocio del flujo.

#### `__init__`

```python
def __init__(
    self,
    harvester: JobHarvesterPort,
    evaluator: JobEvaluatorPort,
    pitch_generator: PitchGeneratorPort,
) -> None:
    self.harvester = harvester
    self.evaluator = evaluator
    self.pitch_generator = pitch_generator
```

- **Qué recibe:** tres objetos, cada uno tipado por su **interfaz abstracta**, nunca por su clase concreta. Esto es **Inyección de Dependencias**: la clase no crea sus propias dependencias (`self.harvester = LeverHarvesterAdapter()` estaría *mal* aquí), las recibe ya construidas desde afuera.
- **Qué entrega:** nada, es un constructor — deja la instancia lista con sus tres colaboradores guardados.
- **Por qué importa tipar por interfaz y no por clase concreta:** esto es lo que hace posible, por ejemplo, en los tests (Parte 4) pasar un `harvester` falso que no hace ninguna llamada de red real, sin que `JobHunterUseCase` note la diferencia — cumple el mismo contrato (`JobHarvesterPort`), eso es todo lo que le importa.

#### `async def execute(self, company_slugs: List[str]) -> List[Tuple[JobRaw, JobEvaluation]]`

Este es el corazón del negocio. Vamos línea por línea:

```python
actionable_results: List[Tuple[JobRaw, JobEvaluation]] = []

for company_slug in company_slugs:
    try:
        jobs = await self.harvester.fetch_jobs(company_slug)
    except HarvesterConnectionError:
        continue
```

- **Qué recibe:** `company_slugs: List[str]` — la lista de empresas a prospectar (p. ej. `["mercadolibre", "rappi", "nubank"]`).
- Itera empresa por empresa, y por cada una llama al harvester inyectado.
- **Manejo de errores clave:** si una empresa específica falla (API caída, 404, timeout — cualquier cosa que el adaptador tradujo a `HarvesterConnectionError`), el `except` la salta con `continue` y sigue con la siguiente empresa. **Esto es una decisión de negocio deliberada, no un accidente**: la spec (`SPEC-005`) exige explícitamente que un fallo aislado no tumbe todo el proceso. Si Nubank cambia su API y empieza a devolver 500, el usuario igual quiere ver los resultados de Rappi y MercadoLibre.

```python
    for job in jobs:
        evaluation = await self.evaluator.evaluate(job)
        if evaluation.is_actionable:
            pitch = await self.pitch_generator.generate_pitch(job, evaluation)
            evaluation.tailored_pitch = pitch
            actionable_results.append((job, evaluation))

return actionable_results
```

- Por cada `JobRaw` recolectado, pide una evaluación.
- **Punto de decisión central:** solo si `evaluation.is_actionable` es `True` se invierte el costo (computacional y, si fuera un LLM, económico) de generar un pitch. Las vacantes descartadas ni siquiera pasan por el generador de pitch — **optimización natural que surge de ordenar bien el flujo**, no de una optimización prematura escrita a mano.
- `evaluation.tailored_pitch = pitch` — aquí se **muta** el objeto `JobEvaluation` recién creado (es válido porque Pydantic v2 permite asignación después de construir, a menos que se congele explícitamente; este dominio no lo congela).
- Solo los pares `(job, evaluation)` que sobrevivieron el filtro entran al resultado final.

- **Qué entrega el método completo:** la lista de vacantes **que vale la pena mostrarle al humano**, ya enriquecidas con su pitch — cero trabajo adicional de filtrado le queda al llamador (`main.py`).

**Por qué esta clase no usa ningún import de `adapters/`:** si lo hiciera, dejaría de poder testearse sin red real, y dejaría de ser reemplazable. Repásalo: `hunt_jobs.py` solo importa desde `src.domain.*`. Nunca desde `src.adapters.*`. Esa única línea de disciplina es la que sostiene toda la arquitectura hexagonal.

---

## Parte 2 — Los Adaptadores (`src/adapters/`)

Los adaptadores son donde vive **todo el código "sucio"**: llamadas HTTP, parsing de JSON ajeno, regex, formato de texto para consola. El dominio no debe ensuciarse con esto — por eso vive aquí, aislado.

### 2.1 `LeverHarvesterAdapter` (`src/adapters/harvesters/lever.py`)

Implementa `JobHarvesterPort` para la API pública de Lever.

#### `__init__(self, client: Optional[httpx.AsyncClient] = None)`

- **Qué recibe:** opcionalmente, un cliente HTTP ya construido.
- **Por qué es opcional e inyectable:** esto es el mismo patrón de Inyección de Dependencias aplicado un nivel más abajo. En producción (`main.py`), se instancia sin argumento y el adaptador crea su propio `httpx.AsyncClient` de usar y tirar por cada llamada. En **tests**, se le inyecta un cliente falso/mockeado que nunca toca la red real — así los tests corren en milisegundos y no dependen de que Lever esté disponible ni de tener internet.

#### `async def fetch_jobs(self, company_slug: str) -> List[JobRaw]`

Paso a paso:

1. **Construye la URL:** `https://api.lever.co/v0/postings/{company_slug}?mode=json` — el endpoint público documentado de Lever.
2. **Hace la petición HTTP**, usando el cliente inyectado si existe, o uno temporal (`async with httpx.AsyncClient()`) si no. El bloque `try/except` envuelve la llamada y **traduce cualquier error técnico a `HarvesterConnectionError`** — esta es la frontera de traducción de la que hablamos en 1.2: `httpx.HTTPError` (errores de red/HTTP) nunca escapa de este archivo hacia el dominio.
   - Nota sobre `inspect.isawaitable(...)`: es una defensa extra para que el código funcione igual tanto si `response.json()`/`raise_for_status()` son síncronos (comportamiento real de `httpx`) como si en un test se inyecta un mock cuyos métodos son *coroutines* (`AsyncMock`). No es parte de la lógica de negocio — es una adaptación pragmática para que el mismo código sirva en producción y en test sin ramas duplicadas.
3. **Valida la forma de la respuesta:** si `data` no es una lista, lanza `HarvesterConnectionError` — Lever siempre responde con un array de postings; cualquier otra forma es una señal de que algo cambió o falló silenciosamente.
4. **Por cada `posting` (diccionario crudo de Lever), lo transforma en un `JobRaw`:**
   - Descarta el posting entero si no es un `dict`, o si le faltan `id`, `text` (título) o `hostedUrl` — campos sin los cuales un `JobRaw` no podría siquiera construirse válidamente (recordemos las validaciones de Pydantic de la Parte 1.1).
   - `location`: intenta leer `categories.location`; si no existe, usa el literal `"Remote"` como default sensato (spec `SPEC-002`, regla explícita).
   - `raw_description`: concatena `descriptionPlain` con el texto de cada item en `lists` (los bloques de "Requisitos", "Responsabilidades", etc. que Lever separa en secciones). Si tras concatenar todo sigue vacío, usa el título como último recurso — garantiza que `raw_description` nunca viole la regla `min_length=1` del modelo.
   - `posted_at`: convierte el timestamp Unix en milisegundos (`createdAt`) a un `datetime` con zona horaria UTC explícita — nunca "naive datetime" (sin timezone), porque comparar fechas sin timezone es una fuente clásica de bugs.
   - Envuelve la construcción del `JobRaw` en un `try/except` silencioso: si por algún motivo los datos no pasan la validación de Pydantic (un título de 2 caracteres, una URL rota), **descarta ese posting individual y sigue con los demás**, en vez de que un solo registro corrupto tumbe la recolección completa de la empresa (misma filosofía de resiliencia que ya vimos en el use case).
5. **Retorna** la lista de `JobRaw` válidos y normalizados.

**Qué recibe la función en resumen:** un slug de texto.
**Qué entrega:** una lista de objetos de dominio ya limpios, validados y en el formato canónico — el resto del sistema jamás ve un JSON crudo de Lever.

### 2.2 `RuleBasedEvaluatorAdapter` (`src/adapters/evaluators/rule_based.py`)

Implementa `JobEvaluatorPort` con un motor de reglas basado en expresiones regulares — determinista, explicable, sin IA.

Constantes de configuración al tope del archivo (el "perfil del candidato" codificado):

- `SPOKEN_ENGLISH_TRIGGERS`: frases que, si aparecen en la descripción, delatan que el rol exige inglés hablado sincrónico.
- `AUDITED_TECH_STACK`: las tecnologías del perfil del candidato que se buscan activamente en el texto.

#### `async def evaluate(self, job: JobRaw) -> JobEvaluation`

1. **Detección de inglés excluyente:** recorre `SPOKEN_ENGLISH_TRIGGERS`, construye un patrón regex con `\b` (límites de palabra, para no matchear subcadenas dentro de otras palabras) y `re.escape` (para que caracteres especiales de regex en la frase no rompan el patrón), y busca con `re.IGNORECASE`. Al primer match: `requires_spoken_english = True`, agrega el red flag correspondiente, y corta el loop (`break` — con una sola coincidencia basta, no hace falta seguir buscando).
2. **Detección de stack técnico:** recorre `AUDITED_TECH_STACK` con la misma técnica de regex, y por cada match agrega la tecnología a `tech_stack_detected` y una frase a `pros`.
3. **Cálculo del `fit_score`:**
   - Arranca en 50.0 (punto base neutral).
   - Suma 10.0 por cada tecnología detectada, con techo en 100.0 (`min(100.0, ...)`).
   - Si `requires_spoken_english` es `True`: **penaliza restando 40.0** — nótese que la penalización se aplica *después* del cálculo del stack, no antes; y además fuerza `is_actionable = False` explícitamente, sin importar qué tan alto haya quedado el score. Esto es la regla de negocio más estricta del proyecto ("inglés hablado fluido es excluyente, punto") reflejada en código, y es exactamente la misma regla que el `model_validator` de `JobEvaluation` (Parte 1.1) hace **imposible violar** desde el modelo — doble candado: una vez en la regla de negocio del adaptador, otra vez en la invariante del dominio.
   - Si no requiere inglés hablado: `is_actionable = fit_score >= 70.0` — el umbral de corte que define "vale la pena postularse".
4. **Genera un pitch corto embebido** (`tailored_pitch`) si es accionable — nota: este es un pitch *simple*, mencionando solo el stack. El pitch *elaborado* y persuasivo lo produce el `RuleBasedPitchGeneratorAdapter` (2.3) y **sobreescribe** este valor en el use case (`evaluation.tailored_pitch = pitch`, línea de `hunt_jobs.py`). Este campo aquí es más bien un valor provisional / señal de que "sí, hay pitch"; el pitch real y elaborado se calcula aparte, respetando SRP: el evaluador evalúa, no redacta pitches complejos.
5. **`salary_match: bool`** siempre se retorna `True` en esta iteración — es un campo del modelo que ya existe (preparado en la spec para una regla futura de rango salarial), pero todavía no hay lógica que lo calcule; es honesto dejarlo así en vez de simular una validación que no existe.

**Qué recibe:** un `JobRaw`.
**Qué entrega:** un `JobEvaluation` completo y válido (pasa automáticamente por la validación de Pydantic al construirse — si alguna combinación violara la invariante de inglés/accionable, fallaría aquí mismo, en el momento de construcción, no más adelante en el flujo).

### 2.3 `RuleBasedPitchGeneratorAdapter` (`src/adapters/evaluators/pitch_generator.py`)

Implementa `PitchGeneratorPort`. Su trabajo es elegir, entre tres pitches pre-redactados (plantillas con textos reales de experiencia profesional), cuál encaja mejor con el stack detectado.

#### `async def generate_pitch(self, job: JobRaw, evaluation: JobEvaluation) -> str`

- **Qué recibe:** el `job` (para tomar `job.company` y `job.title` y personalizar el saludo) y la `evaluation` (para leer `tech_stack_detected`).
- Normaliza el stack detectado a minúsculas en un `set` (`detected_stack`) para comparaciones case-insensitive rápidas (`in` sobre un set es O(1)).
- **Regla 1 — Eje IA & Backend:** si el stack incluye `fastapi`, `rag` o `ai agents`, retorna el pitch que destaca el proyecto de observabilidad bancaria con RAG y colas Redis.
- **Regla 2 — Eje Frontend & Telemetría:** si incluye `react`, `telemetry` o `charts`, retorna el pitch centrado en el dashboard petrolero con React.
- **Regla 3 — Fallback (Resiliencia & Escala):** si ninguna de las anteriores aplica, retorna el pitch genérico sobre sistemas transaccionales de alta concurrencia (caso Avianca) — **siempre hay un pitch**, nunca retorna vacío ni `None`, porque toda vacante accionable merece un texto de postulación, incluso si su stack no calzó con ninguna categoría específica.
- **Qué entrega:** un `str` ya formateado con saludo personalizado (`f"Hola equipo de {job.company}..."`), evidencia de impacto concreta, y un llamado a la acción — listo para copiar y enviar sin edición manual.

Nota de diseño: las reglas son **mutuamente excluyentes por orden de evaluación** (`if` / `if` / fallback final, no `elif` encadenado con más ramas) — si una vacante matchea tanto Regla 1 como Regla 2, gana la primera que se evalúa (IA & Backend tiene prioridad sobre Frontend). Esto está definido explícitamente en `SPEC-004` como el orden de los "ejes".

### 2.4 `ConsoleNotifierAdapter` (`src/adapters/notifiers/console.py`)

Implementa `JobNotifierPort`. El adaptador más simple del proyecto.

#### `async def notify(self, jobs: List[Tuple[JobRaw, JobEvaluation]]) -> int`

- **Caso vacío:** si no hay vacantes accionables, imprime un mensaje neutro ("No se encontraron vacantes accionables.") y retorna `0` — nunca deja al usuario sin feedback, ni siquiera cuando no hay resultados.
- **Caso con resultados:** por cada par `(job, evaluation)`, arma una "tarjeta" de texto con separadores visuales (`===...===`), mostrando título, empresa, URL, fit score formateado a un decimal (`{:.1f}%`), stack detectado (o `"N/A"` si la lista está vacía), y el pitch completo.
- **Qué entrega:** `len(jobs)` — el conteo de tarjetas impresas, que cumple el contrato del puerto ("retorna cuántas se notificaron con éxito"). En este adaptador simple, imprimir nunca "falla" a medias, así que el conteo siempre es el total; un futuro adaptador de email sí podría retornar un número menor al total si algunos envíos fallan.

---

## Parte 3 — El Entrypoint (`main.py`)

Esta es la **capa de composición** — el único archivo del proyecto donde dominio y adaptadores se mencionan en la misma función. Aquí, y solo aquí, se decide *qué implementación concreta* usa cada puerto.

```python
async def main() -> None:
    harvester = LeverHarvesterAdapter()
    evaluator = RuleBasedEvaluatorAdapter()
    pitch_generator = RuleBasedPitchGeneratorAdapter()
    notifier = ConsoleNotifierAdapter()

    use_case = JobHunterUseCase(
        harvester=harvester,
        evaluator=evaluator,
        pitch_generator=pitch_generator,
    )

    target_companies: List[str] = ["mercadolibre", "rappi", "nubank"]

    actionable_jobs = await use_case.execute(target_companies)
    total_notified = await notifier.notify(actionable_jobs)
```

- **Paso 1:** instancia las cuatro clases concretas (los "enchufes conectados a sus adaptadores reales").
- **Paso 2:** construye `JobHunterUseCase` inyectándole tres de los cuatro adaptadores (el `notifier` se usa después, fuera del use case, porque notificar no es parte del *cómputo* de qué es accionable — es un paso posterior de *entrega* del resultado. Esta separación entre "calcular resultado" y "comunicar resultado" es otra aplicación de SRP a nivel de flujo completo).
- **Paso 3:** define la lista de empresas objetivo — el único "input" real de esta corrida.
- **Paso 4:** ejecuta el caso de uso y luego notifica — dos llamadas `await` secuenciales, reflejando el flujo real: primero se sabe todo el resultado, después se comunica.
- `if __name__ == "__main__": asyncio.run(main())` — el patrón estándar de Python para arrancar un programa asíncrono desde la línea de comandos.

---

## Parte 4 — Testing como parte del contrato (Harness)

Cada pieza tiene su archivo de test correspondiente en `tests/unit/`, y todos siguen el mismo patrón: **inyectar dobles de prueba (fakes) en lugar de dependencias reales**, gracias a que todo está tipado por interfaz abstracta.

- **`test_domain_models.py`:** construye `JobEvaluation` con combinaciones inválidas de `requires_spoken_english=True, is_actionable=True` y verifica que Pydantic lance `ValueError` — prueba directa de la invariante de la Parte 1.1.
- **`test_lever_harvester.py`:** inyecta un `httpx.AsyncClient` simulado (usando los payloads de `tests/harness/fixtures/lever_payload.py`) para verificar el mapeo JSON→`JobRaw` sin tocar la red real.
- **`test_rule_based_evaluator.py`:** alimenta descripciones de texto controladas y verifica el `fit_score` resultante y las banderas.
- **`test_pitch_generator.py`:** verifica que cada combinación de stack dispare la plantilla de pitch correcta.
- **`test_console_notifier.py`:** captura la salida impresa y verifica el conteo retornado.
- **`test_hunt_jobs_usecase.py`:** el más importante para validar la orquestación — inyecta harvesters/evaluators/pitch generators falsos (algunos que lanzan `HarvesterConnectionError` a propósito) para comprobar que el use case tolera fallos parciales y solo retorna lo accionable.

Esto no es un detalle secundario: es la **prueba viviente** de que la arquitectura hexagonal cumple su promesa. Si no se pudiera testear el dominio sin llamadas de red reales, la separación de capas habría fallado en la práctica, sin importar cómo se vieran las carpetas.

---

## Parte 5 — Por qué cada principio de diseño aparece, y dónde

| Principio | Dónde se ve en este proyecto |
|---|---|
| **SRP** (Single Responsibility) | Cuatro puertos separados (harvest / evaluate / pitch / notify), cada uno una sola razón para cambiar |
| **OCP** (Open/Closed) | Se puede añadir un adaptador Greenhouse sin modificar `JobHunterUseCase` ni ningún puerto existente |
| **LSP** (Liskov Substitution) | Cualquier implementación de `JobHarvesterPort` es intercambiable sin romper al use case — es literalmente lo que permite los tests con fakes |
| **ISP** (Interface Segregation) | Los puertos son mínimos: un solo método cada uno, nada de interfaces "gigantes" que fuercen implementar métodos innecesarios |
| **DIP** (Dependency Inversion) | `JobHunterUseCase` depende de abstracciones (`*Port`), nunca de clases concretas; quien decide la implementación es `main.py` |
| **DRY** | Las constantes de reglas (`SPOKEN_ENGLISH_TRIGGERS`, `AUDITED_TECH_STACK`) están centralizadas una sola vez; los fixtures de test están en `tests/harness/fixtures/` para no duplicarse entre archivos |
| **SoC** (Separation of Concerns) | domain/ vs adapters/; y dentro del dominio, modelo vs puerto vs caso de uso, cada capa con una preocupación distinta |
| **Fail-fast** | Validación de Pydantic en el borde (al construir el objeto), no dispersada en checks manuales por todo el código |

La arquitectura hexagonal, en este proyecto, no es una decoración — es la razón concreta por la que se puede testear todo sin red, reemplazar Lever sin tocar el dominio, y añadir un evaluador basado en IA el día de mañana sin rediseñar nada.
