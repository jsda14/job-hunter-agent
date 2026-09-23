# SPEC-001: Core Domain Contracts & Job Model

## 1. Propósito
Definir los modelos canónicos inmutables del dominio para representar ofertas de trabajo ingeridas desde plataformas externas (Lever, Greenhouse, Ashby) y los resultados de evaluación técnica.

## 2. Modelos de Dominio

### 2.1 Enumeraciones
- `SourcePlatform`: Valores permitidos: `lever`, `greenhouse`, `ashby`.

### 2.2 Entidad Canónica: `JobRaw`
Representa una vacante capturada sin procesar.
Campos obligatorios:
- `id`: str (identificador determinista generado: `{platform}_{external_id}`)
- `platform`: SourcePlatform
- `external_id`: str (ID nativo en la plataforma origen)
- `title`: str (mínimo 3 caracteres)
- `company`: str (mínimo 2 caracteres)
- `url`: HttpUrl (URL válida hacia la vacante)
- `location`: str (descripción geográfica textual)
- `raw_description`: str (texto completo o HTML crudo de la vacante, no vacío)
- `posted_at`: Optional[datetime] (fecha de publicación en UTC, default None)

### 2.3 Objeto de Valor: `JobEvaluation`
Representa el resultado del análisis semántico frente al perfil del candidato.
Campos obligatorios:
- `job_id`: str (debe coincidir con `JobRaw.id`)
- `fit_score`: float (rango estricto [0.0, 100.0])
- `salary_match`: bool (True si cumple con el piso salarial o no lo excluye)
- `requires_spoken_english`: bool (True si detecta necesidad de inglés conversacional síncrono)
- `tech_stack_detected`: List[str] (lista de tecnologías detectadas en el texto)
- `pros`: List[str] (aspectos alineados con el perfil)
- `red_flags`: List[str] (aspectos de fricción detectados)
- `is_actionable`: bool (True si fit_score >= 70.0 y no tiene red_flags bloqueantes)
- `tailored_pitch`: Optional[str] (pitch adaptado si es accionable)

## 3. Invariantes y Reglas de Negocio
1. `JobRaw.id` debe seguir estrictamente la convención `{platform}_{external_id}` en minúsculas.
2. Si `is_actionable` es `True`, `fit_score` no puede ser menor a 70.0.
3. Si `requires_spoken_english` es `True`, `is_actionable` debe ser `False` de manera predeterminada.