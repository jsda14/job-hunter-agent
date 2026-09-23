# SPEC: [ID-Corto] - [Nombre del Módulo o Feature]

> **Instrucciones para el Agente Codificador:**
> 1. No instales dependencias externas, librerías ni paquetes que no estén explícitamente autorizados en la sección 2.
> 2. No agregues campos adicionales, métodos auxiliares públicos ni endpoints fuera de los contratos descritos en la sección 3.
> 3. Implementa únicamente las tareas listadas en la sección 5 en orden secuencial. Si encuentras un bloqueo, detén la ejecución y solicita aclaración.
> 4. Al finalizar, ejecuta el script de verificación `python scripts/verify_sdd_pipeline.py specs/[SPEC_FILE].md` para validar los 5 pasos.

---

## 1. Alcance y Fronteras
* **Objetivo:** [Descripción precisa de 1 a 2 oraciones del cambio o funcionalidad]
* **En Alcance (In-Scope):**
  - [Elemento 1]
  - [Elemento 2]
* **Fuera de Alcance (Out-of-Scope / Non-Goals):**
  - [Exclusión explícita 1]
  - [Exclusión explícita 2]
* **Archivos Afectados:**
  * **Crear:**
    - `ruta/al/nuevo_archivo.py`
    - `tests/ruta/al/test_nuevo_archivo.py`
  * **Modificar:**
    - `ruta/al/archivo_existente.py`
  * **Prohibido modificar:**
    - `app/config.py`
    - `requirements.txt`
    - [Otras rutas críticas sensibles]

---

## 2. Entorno y Dependencias Permitidas
* **Runtime / Versión:** Python 3.11+
* **Librerías autorizadas:**
  - `pydantic` (modelado y validación de datos)
  - `pytest` (pruebas unitarias y de integración)
  - [Otras librerías explícitas ya presentes en requirements.txt]
* **Regla estricta:** Prohibido instalar o importar paquetes externos no listados arriba ni modificar `requirements.txt` sin autorización de Arquitectura.

---

## 3. Contratos e Interfaces (Single Source of Truth)

### 3.1 Modelos de Datos / DTOs
```python
# Ejemplo de contrato de datos Pydantic / dataclass
from pydantic import BaseModel, Field

class FeatureInputDTO(BaseModel):
    id: str = Field(..., description="Identificador único")
    payload: str = Field(..., description="Contenido a procesar")

class FeatureOutputDTO(BaseModel):
    success: bool
    processed_value: str
```

### 3.2 Firmas de Métodos / Interfaces Públicas
```python
def process_feature(data: FeatureInputDTO) -> FeatureOutputDTO:
    """Procesa la entrada siguiendo las reglas RN-01 a RN-03.
    
    Args:
        data: DTO de entrada validado.
        
    Returns:
        FeatureOutputDTO con el resultado de la transformación.
        
    Raises:
        ValueError: Si los datos de entrada violan las precondiciones.
    """
    pass
```

---

## 4. Reglas de Negocio y Casos Borde

### 4.1 Reglas de Negocio (RN)
- **RN-01:** [Descripción de la regla principal de transformación o validación].
- **RN-02:** [Comportamiento esperado ante condiciones específicas de negocio].
- **RN-03:** [Políticas de normalización, saneamiento o precedencia].

### 4.2 Casos Borde (CB)
- **CB-01 (Entrada vacía o nula):** Debe retornar un error controlado o fallback sin provocar excepción no capturada.
- **CB-02 (Caracteres especiales / Encoding):** Soporte de caracteres UTF-8, saltos de línea y strings multilínea.
- **CB-03 (Timeouts / Límites de tamaño):** Comportamiento definido si se excede el límite de memoria o longitud de tokens.

---

## 5. Plan de Ejecución Secuencial (Atomic Tasks)
- [ ] **Paso 1: Contratos y DTOs Base:** Crear o actualizar modelos e interfaces en los archivos autorizados.
- [ ] **Paso 2: Lógica de Negocio / Implementación:** Desarrollar los casos de uso implementando estrictamente RN-01 a RN-03.
- [ ] **Paso 3: Pruebas Unitarias:** Implementar tests en `tests/` cubriendo cada RN y caso borde de la Sección 4.
- [ ] **Paso 4: Validación y Cobertura:** Ejecutar tests locales y asegurar que pasen en verde.
- [ ] **Paso 5: Documentación y Trazabilidad:** Documentar métodos públicos y actualizar `specs/TASK_STATUS.md`.

---

## 6. Verificación y Checklist de Salida (Pipeline de 5 Pasos)
- [ ] **1. Validación Arquitectónica:**
  - Sin dependencias ni imports no autorizados en capas de parsers/dominio.
  - `git diff` coincide únicamente con los archivos autorizados en la Sección 1.
- [ ] **2. Generación de Tests:**
  - Tests unitarios derivados directamente de la Sección 4 (RN y CB) implementados en `tests/`.
- [ ] **3. Validación de Cobertura:**
  - Suite de `pytest` ejecutada exitosamente (0 errores, cobertura >= 85% en código nuevo).
- [ ] **4. Documentación As-Built:**
  - Docstrings completos en funciones, clases y métodos públicos creados/modificados.
- [ ] **5. Trazabilidad y Estado:**
  - Checklist de esta spec completado y entrada registrada en `specs/TASK_STATUS.md`.
