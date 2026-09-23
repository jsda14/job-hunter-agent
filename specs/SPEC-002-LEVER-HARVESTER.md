# SPEC-002: Job Harvester Port & Lever Adapter

## 1. Propósito
Definir la interfaz del puerto de recolección de empleos (`JobHarvesterPort`) y la implementación concreta para el ATS Lever (`LeverHarvesterAdapter`), normalizando la respuesta externa en instancias canónicas de `JobRaw`.

## 2. Definición del Puerto (`src/domain/ports/harvester.py`)
Interfaz abstracta (`typing.Protocol` o `abc.ABC`):
- Método: `async def fetch_jobs(self, company_slug: str) -> list[JobRaw]`
- Lanza: `HarvesterConnectionError` si la red falla o devuelve un status code de error (e.g. 404, 500).

## 3. Adaptador Lever (`src/adapters/harvesters/lever.py`)
Consume el endpoint público: `https://api.lever.co/v0/postings/{company_slug}?mode=json`

### Reglas de Mapeo a `JobRaw`:
- `id`: f"lever_{posting['id']}"
- `platform`: `SourcePlatform.LEVER`
- `external_id`: `posting['id']`
- `title`: `posting['text']`
- `company`: `company_slug` (o nombre comercial capitalizado)
- `url`: `posting['hostedUrl']`
- `location`: `posting['categories']['location']` (o "Remote" si está vacío)
- `raw_description`: Unión de `posting['descriptionPlain']` y listas de requisitos adicionales (`posting.get('lists', [])`). No debe contener tags HTML crudos.
- `posted_at`: Convertir timestamp Unix en milisegundos (`posting['createdAt']`) a objeto `datetime` con timezone UTC.

## 4. Invariantes
1. Si la empresa no existe o devuelve 404, debe capturar la excepción y lanzar `HarvesterConnectionError`.
2. Las ofertas que no tengan título o ID válido deben ignorarse o descartarse limpiamente sin quebrar el lote completo.