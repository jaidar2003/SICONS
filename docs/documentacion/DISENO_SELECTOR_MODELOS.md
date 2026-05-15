# Diseno del Selector de Modelos de Forecasting

## Objetivo

Definir una politica defendible para que SICONS resuelva que modelo de forecasting usar segun una identidad estable de material y `horizonte_meses`, sin depender de un modelo global unico y sin incrustar esa decision dentro de `forecast_service.py`.

El diseno parte de una restriccion metodologica explicita: la seleccion no debe inventar resultados ni recalibrar modelos en runtime. Solo debe resolver, de manera trazable, una recomendacion ya respaldada por benchmark y documentacion.

## 1. Problema que resuelve el selector

El selector resuelve tres problemas a la vez:

- evita asumir que una mejora medida en un material vale automaticamente para todos los demas;
- evita hardcodear decisiones metodologicas dentro del flujo operativo que entrena y sirve el forecast;
- permite exponer una decision auditable sobre que modelo se eligio, con que evidencia y con que nivel de confiabilidad.

Sin esta capa, el sistema queda atado a una de estas dos alternativas debiles:

- un modelo universal, facil de operar pero metodologicamente fragil;
- una acumulacion de condicionales en el servicio de forecast, dificil de mantener, explicar y migrar.

## 2. Entrada del selector

La interfaz minima externa del flujo sigue aceptando:

- `material_id`
- `horizonte_meses`

El contrato interno real ya no depende de `material_id` como clave metodologica. El endpoint recibe `material_id`, pero el backend resuelve primero el material y deriva una identidad estable:

- `material_id -> Material.nombre -> material_key`

Luego el selector opera sobre:

- `material_key + horizonte_meses`

Esta separacion reduce tres riesgos:

- riesgo operativo, porque evita perder calibraciones validas cuando cambia un ID local;
- riesgo de portabilidad, porque desacopla la recomendacion del ambiente concreto;
- riesgo metodologico, porque asocia la calibracion al material logico y no a una clave accidental de base.

Conviene que `horizonte_meses` siga siendo obligatorio en el contrato interno, incluso si la primera version solo tiene calibraciones documentadas para horizonte de `3` meses. Eso evita ambiguedades y deja definido desde ahora el eje futuro de crecimiento.

### Claves estables iniciales

Para la etapa actual, las claves estables recomendadas son:

- `cemento-portland`
- `pastina`
- `membrana-megaflex`

## 3. Salida esperada

La salida del selector no debe ser solo el nombre de un modelo. Debe ser una decision explicable.

Campos esperados:

- `material_key`: identidad estable resuelta para el material.
- `modelo_resuelto`: identificador simbolico del modelo recomendado.
- `regresores_resueltos`: lista declarativa de regresores requeridos por ese modelo.
- `mape_referencia`: metrica principal usada para sostener la recomendacion.
- `mae_referencia`: metrica de soporte.
- `folds`: cantidad de folds usada en backtesting, cuando este dato exista.
- `confiabilidad`: calificacion metodologica de la serie asociada a esa recomendacion.
- `origen_decision`: fuente concreta de donde sale la regla aplicada.
- `justificacion`: texto breve, tecnico y auditable, apto para log, respuesta HTTP o debugging funcional.
- `no_calibrado`: indicador booleano para distinguir una recomendacion respaldada por benchmark de un fallback no calibrado.

Ejemplo conceptual de salida:

```json
{
  "material_key": "cemento-portland",
  "modelo_resuelto": "prophet_ipim_nivel_general",
  "regresores_resueltos": ["ipim_nivel_general"],
  "mape_referencia": 4.98,
  "mae_referencia": 6.76,
  "folds": 9,
  "confiabilidad": "alta",
  "origen_decision": "material_horizonte",
  "justificacion": "Configuracion recomendada para Cemento Portland a 3 meses segun benchmark documentado y MAPE minimo medido.",
  "no_calibrado": false
}
```

## 4. Estrategia inicial

La primera version debe ser deliberadamente simple:

- mapping declarativo en codigo;
- selector aislado;
- sin base de datos todavia.

La recomendacion concreta es mantener una configuracion versionada, legible y acotada, separada del servicio de forecast. Esa configuracion no debe contener logica; solo datos declarativos.

Importante: este documento describe la calibracion actual del selector en runtime. No debe confundirse con las mejores mediciones experimentales mas nuevas documentadas en `docs/documentacion/MEDICIONES_FORECASTING.md`, porque algunas de esas mejoras todavia no fueron promovidas formalmente al selector productivo.

### Configuracion inicial conocida

El selector runtime ya no usa una tabla hardcodeada. Lee el benchmark consolidado de los tres materiales y elige la variante ejecutable con menor `MAPE` para cada `material_key + horizonte_meses`.

| Material key | Material visible | Horizonte | Modelo recomendado | Regresores | MAPE | MAE | Folds | Confiabilidad |
|---|---|---:|---|---|---:|---:|---:|---|
| `cemento-portland` | `Cemento Portland` | `3` | `prophet_ipim_icc_var_materials` | `["ipim_nivel_general", "icc_var_materials"]` | `4.22%` | `5.82` | `9` | alta |
| `cemento-portland` | `Cemento Portland` | `6` | `prophet_ipim_icc_var_materials` | `["ipim_nivel_general", "icc_var_materials"]` | `5.52%` | `7.58` | `9` | alta |
| `cemento-portland` | `Cemento Portland` | `12` | `prophet_ipim_icc_var_materials` | `["ipim_nivel_general", "icc_var_materials"]` | `4.51%` | `6.36` | `9` | alta |
| `pastina` | `Pastina` | `3` | `prophet_ipim_cac_labour_force` | `["ipim_nivel_general", "cac_labour_force"]` | `4.27%` | `97.97` | `9` | media |
| `pastina` | `Pastina` | `6` | `prophet_ipim_cac_labour_force` | `["ipim_nivel_general", "cac_labour_force"]` | `5.26%` | `115.97` | `9` | media |
| `pastina` | `Pastina` | `12` | `prophet_ipim_cac_var_materials` | `["ipim_nivel_general", "cac_var_materials"]` | `4.94%` | `105.88` | `9` | media |
| `membrana-megaflex` | `Membrana Megaflex` | `3` | `prophet_ipim_icc_var_general` | `["ipim_nivel_general", "icc_var_general"]` | `7.53%` | `619.75` | `9` | media-baja |
| `membrana-megaflex` | `Membrana Megaflex` | `6` | `prophet_ipim_icc_var_general` | `["ipim_nivel_general", "icc_var_general"]` | `9.73%` | `759.85` | `9` | media-baja |
| `membrana-megaflex` | `Membrana Megaflex` | `12` | `prophet_ipim_icc_var_materials` | `["ipim_nivel_general", "icc_var_materials"]` | `13.57%` | `1080.42` | `9` | media-baja |

Las variantes con lags, medias moviles, variaciones y ensemble siguen siendo las mejores en varios experimentos de investigacion, pero todavia no se usan en el selector runtime porque el pipeline operativo no las ejecuta de forma nativa.

## 5. Reglas de fallback

La politica inicial debe resolver en este orden:

1. configuracion exacta por `material_key` y `horizonte_meses`;
2. configuracion generica por `material_key`;
3. `prophet_base` sin regresores;
4. marcado explicito como `no_calibrado`, si la decision no proviene de benchmark especifico para esa combinacion.

### Fallback 1: configuracion exacta por material y horizonte

Es la ruta preferida. Solo se usa cuando existe una calibracion documentada para esa combinacion exacta.

Valores esperados:

- `origen_decision = "material_horizonte"`
- `no_calibrado = false`

### Fallback 2: configuracion por material

Aplica cuando existe evidencia suficiente para el material, pero no para el horizonte pedido. Su funcion es operativa, no epistemica: permite seguir sirviendo forecast sin fingir una calibracion exacta inexistente.

Valores esperados:

- `origen_decision = "material_default"`
- `no_calibrado = true`
- la `justificacion` debe indicar que se reutiliza la mejor configuracion conocida del material por ausencia de evidencia especifica para ese horizonte.

### Fallback 3: `prophet_base` sin regresores

Aplica cuando no existe ninguna recomendacion documentada para el material.

Valores esperados:

- `origen_decision = "global_fallback"`
- `modelo_resuelto = "prophet_base"`
- `regresores_resueltos = []`
- `no_calibrado = true`

Esta salida no debe presentarse como recomendacion metodologica fuerte. Debe presentarse como fallback operativo conservador.

### Marcado de no calibrado

El selector debe poder marcar como `no_calibrado` cualquier resolucion que no tenga respaldo exacto de benchmark para esa combinacion de material y horizonte.

Ese marcado es importante por dos razones:

- evita sobreinterpretar la precision del sistema;
- deja lista la semantica que luego podra usarse en UI, logs, auditoria o decisiones de producto.

## 6. Resolucion de identidad estable

La validacion runtime real ya mostro que dos ambientes pueden tener series utiles del mismo material con IDs distintos. Por eso, la seleccion no deberia consumir directamente `material_id` como clave metodologica.

La recomendacion para el MVP es resolver `material_key` a partir del catalogo actual mediante una normalizacion controlada del nombre o un slug derivado, sin migracion de base todavia.

Alternativas consideradas:

- `material_id`
  - simple, pero fragil entre ambientes;
- nombre normalizado
  - no requiere migracion, pero depende de consistencia nominal;
- slug o codigo interno derivado del nombre
  - mas controlado que el nombre raw y adecuado como solucion intermedia;
- campo persistido futuro como `codigo_material` o `clave_modelo`
  - solucion estructural mas robusta, pero requiere migracion y gobernanza;
- tabla futura de calibraciones por `material_key`
  - evolucion natural cuando se quiera desacoplar por completo catalogo, calibracion y runtime.

### Recomendacion para el MVP

La opcion mas razonable en esta etapa es:

- mantener `material_id` como parametro externo del endpoint;
- resolver internamente `material_key` desde el catalogo actual;
- operar el selector sobre `material_key + horizonte_meses`;
- no introducir todavia una migracion de base;
- dejar como evolucion futura un campo persistido explicito, por ejemplo `codigo_material` o `clave_modelo`.

Si no se puede resolver una `material_key` con confianza suficiente, el sistema deberia caer a:

- `prophet_base`
- `no_calibrado = true`
- `origen_decision = "global_fallback"` o `origen_decision = "material_key_unresolved"`

Eso preserva operatividad sin fingir una calibracion segura.

## 7. Ubicacion sugerida en la arquitectura

La politica no debe vivir en `forecast_service.py`. La ubicacion sugerida es:

- capa: `application`
- responsabilidad: resolucion de politica de modelo
- dependencia de entrada: identidad estable de material y horizonte
- dependencia de salida: especificacion declarativa del modelo a correr

Una organizacion coherente con la arquitectura actual seria separar:

- un archivo de configuracion declarativa, por ejemplo `app/modules/pricing/application/model_selection_config.py`;
- un selector, por ejemplo `app/modules/pricing/application/model_selector.py`;
- el `forecast_service`, que solo consume la decision resuelta.

El servicio de forecast no deberia conocer tablas de benchmark ni condicionales de seleccion. Deberia recibir una especificacion resuelta y ejecutar el pipeline ya existente de `Prophet` con esos parametros.

## 8. Migracion futura a tabla parametrizable

La migracion a persistencia no debe cambiar el contrato del selector. Ese es el punto clave para no romper el sistema.

La estrategia recomendada es:

1. definir ahora un contrato estable de salida;
2. implementar primero una fuente declarativa en codigo que satisfaga ese contrato;
3. reemplazar despues la fuente por una tabla parametrizable, manteniendo la misma interfaz del selector.

### Forma de migracion

En una etapa posterior, el selector puede dejar de leer un mapping en codigo y pasar a leer una tabla con columnas como:

- `material_key`
- `horizonte_meses`
- `modelo`
- `regresores`
- `mape`
- `mae`
- `folds`
- `confiabilidad`
- `origen_benchmark`
- `justificacion`
- `activo`
- `vigente_desde`

La clave es que `forecast_service` no deberia enterarse de ese cambio. Solo seguiria pidiendo una decision al selector.

### Beneficios de esta migracion gradual

- no rompe la API interna;
- permite auditar cambios de politica sin tocar codigo productivo;
- facilita incorporar nuevos materiales, nuevos horizontes o recalibraciones futuras;
- habilita gobernanza posterior sobre vigencia, activacion y versionado de recomendaciones.

## 9. Tests minimos

Sin implementar serving nuevo, ya puede definirse que pruebas deberia cubrir el selector:

- resuelve la configuracion exacta cuando existe `material_key + horizonte_meses`;
- cae a configuracion por material cuando falta la exacta;
- cae a `prophet_base` cuando no existe configuracion del material;
- marca `no_calibrado = false` solo para reglas exactas respaldadas por benchmark;
- marca `no_calibrado = true` en todos los fallbacks;
- conserva `MAPE`, `MAE`, `folds`, `confiabilidad` y `justificacion` sin alterarlos;
- expone `regresores` coherentes con el modelo recomendado;
- no inventa horizontes ni metricas ausentes.

Tambien conviene cubrir especificamente la capa de identidad estable:

- el mismo material logico con distinto `material_id` resuelve la misma `material_key`;
- `Membrana Megaflex` resuelve `membrana-megaflex`;
- `Pastina` resuelve `pastina`;
- un material desconocido cae a `prophet_base/no_calibrado`;
- el selector deja de depender de IDs locales para devolver modelos calibrados.

Tambien conviene un test de contrato:

- toda salida del selector debe incluir los campos requeridos, incluso cuando la decision sea fallback.

## 10. Exposicion en la respuesta del endpoint de forecast

La decision del selector no debe quedar oculta. El endpoint de forecast deberia exponerla para trazabilidad.

La forma recomendada es agregar un bloque de metadatos de seleccion, por ejemplo:

```json
{
  "forecast": { "...": "..." },
  "seleccion_modelo": {
    "material_key": "cemento-portland",
    "modelo_resuelto": "prophet_ipim_nivel_general",
    "regresores_resueltos": ["ipim_nivel_general"],
    "mape_referencia": 4.98,
    "mae_referencia": 6.76,
    "folds": 9,
    "confiabilidad": "alta",
    "origen_decision": "material_horizonte",
    "justificacion": "Configuracion recomendada para Cemento Portland a 3 meses segun benchmark documentado y MAPE minimo medido.",
    "no_calibrado": false
  }
}
```

Esto mejora tres cosas:

- trazabilidad metodologica;
- capacidad de debugging funcional;
- defensa academica y tecnica del comportamiento del sistema.

## Criterio metodologico consolidado

La politica propuesta deja fijado este criterio:

- SICONS no adopta un modelo universal unico;
- SICONS selecciona modelo por identidad estable de material y horizonte;
- `MAPE` sigue siendo la metrica principal;
- `MAE`, `folds` y confiabilidad de la serie funcionan como soporte;
- los regresores externos solo se sostienen si mejoran backtesting y conservan coherencia economica;
- cuando no hay calibracion suficiente, el sistema debe decirlo de forma explicita.

Ese ultimo punto es importante: el selector no solo elige modelo; tambien comunica el nivel de sustento metodologico de esa eleccion.
