# Diseno del Selector de Modelos de Forecasting

## Objetivo

Definir una politica defendible para que SICONS resuelva que modelo de forecasting usar segun `material_id` y `horizonte_meses`, sin depender de un modelo global unico y sin incrustar esa decision dentro de `forecast_service.py`.

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

La interfaz minima del selector debe aceptar:

- `material_id`
- `horizonte_meses`

Conviene que ambos parametros sean obligatorios en el contrato interno, incluso si la primera version solo tiene calibraciones documentadas para horizonte de `3` meses. Eso evita ambiguedades y deja definido desde ahora el eje futuro de crecimiento.

## 3. Salida esperada

La salida del selector no debe ser solo el nombre de un modelo. Debe ser una decision explicable.

Campos esperados:

- `modelo`: identificador simbolico del modelo recomendado.
- `regresores`: lista declarativa de regresores requeridos por ese modelo.
- `mape`: metrica principal usada para sostener la recomendacion.
- `mae`: metrica de soporte.
- `folds`: cantidad de folds usada en backtesting, cuando este dato exista.
- `confiabilidad`: calificacion metodologica de la serie asociada a esa recomendacion.
- `origen_decision`: fuente concreta de donde sale la regla aplicada.
- `justificacion`: texto breve, tecnico y auditable, apto para log, respuesta HTTP o debugging funcional.
- `calibrado`: indicador booleano para distinguir una recomendacion respaldada por benchmark de un fallback no calibrado.

Ejemplo conceptual de salida:

```json
{
  "modelo": "prophet_ipim_nivel_general",
  "regresores": ["ipim_nivel_general"],
  "mape": 4.98,
  "mae": 6.76,
  "folds": 9,
  "confiabilidad": "alta",
  "origen_decision": "material_horizonte",
  "justificacion": "Configuracion recomendada para Cemento Portland a 3 meses segun benchmark documentado y MAPE minimo medido.",
  "calibrado": true
}
```

## 4. Estrategia inicial

La primera version debe ser deliberadamente simple:

- mapping declarativo en codigo;
- selector aislado;
- sin base de datos todavia.

La recomendacion concreta es mantener una configuracion versionada, legible y acotada, separada del servicio de forecast. Esa configuracion no debe contener logica; solo datos declarativos.

### Configuracion inicial conocida

Con la evidencia actualmente documentada, solo corresponde fijar de manera explicita estas recomendaciones:

| Material | Horizonte | Modelo recomendado | Regresores | MAPE | MAE | Folds | Confiabilidad |
|---|---:|---|---|---:|---:|---:|---|
| `Cemento Portland` | `3` | `prophet_ipim_nivel_general` | `["ipim_nivel_general"]` | `4.98%` | `6.76` | `9` | alta |
| `Pastina` | `3` | `prophet_blue_ipc` | `["dolar_blue", "ipc"]` | `5.00%` | `120.90` | `9` | media |
| `Membrana Megaflex` | `3` | `prophet_ipc` | `["ipc"]` | `8.31%` | `734.37` | `9` | media-baja |

No corresponde completar artificialmente otros horizontes con resultados no medidos. Para horizontes no calibrados, el selector debe caer en reglas de fallback y dejar esa condicion explicitada.

## 5. Reglas de fallback

La politica inicial debe resolver en este orden:

1. configuracion exacta por `material_id` y `horizonte_meses`;
2. configuracion generica por `material_id`;
3. `prophet_base` sin regresores;
4. marcado explicito como `no calibrado`, si la decision no proviene de benchmark especifico para esa combinacion.

### Fallback 1: configuracion exacta por material y horizonte

Es la ruta preferida. Solo se usa cuando existe una calibracion documentada para esa combinacion exacta.

Valores esperados:

- `origen_decision = "material_horizonte"`
- `calibrado = true`

### Fallback 2: configuracion por material

Aplica cuando existe evidencia suficiente para el material, pero no para el horizonte pedido. Su funcion es operativa, no epistemica: permite seguir sirviendo forecast sin fingir una calibracion exacta inexistente.

Valores esperados:

- `origen_decision = "material_default"`
- `calibrado = false`
- la `justificacion` debe indicar que se reutiliza la mejor configuracion conocida del material por ausencia de evidencia especifica para ese horizonte.

### Fallback 3: `prophet_base` sin regresores

Aplica cuando no existe ninguna recomendacion documentada para el material.

Valores esperados:

- `origen_decision = "global_fallback"`
- `modelo = "prophet_base"`
- `regresores = []`
- `calibrado = false`

Esta salida no debe presentarse como recomendacion metodologica fuerte. Debe presentarse como fallback operativo conservador.

### Marcado de no calibrado

El selector debe poder marcar como `no calibrado` cualquier resolucion que no tenga respaldo exacto de benchmark para esa combinacion de material y horizonte.

Ese marcado es importante por dos razones:

- evita sobreinterpretar la precision del sistema;
- deja lista la semantica que luego podra usarse en UI, logs, auditoria o decisiones de producto.

## 6. Ubicacion sugerida en la arquitectura

La politica no debe vivir en `forecast_service.py`. La ubicacion sugerida es:

- capa: `application`
- responsabilidad: resolucion de politica de modelo
- dependencia de entrada: identificador de material y horizonte
- dependencia de salida: especificacion declarativa del modelo a correr

Una organizacion coherente con la arquitectura actual seria separar:

- un archivo de configuracion declarativa, por ejemplo `app/modules/pricing/application/model_selection_config.py`;
- un selector, por ejemplo `app/modules/pricing/application/model_selector.py`;
- el `forecast_service`, que solo consume la decision resuelta.

El servicio de forecast no deberia conocer tablas de benchmark ni condicionales de seleccion. Deberia recibir una especificacion resuelta y ejecutar el pipeline ya existente de `Prophet` con esos parametros.

## 7. Migracion futura a tabla parametrizable

La migracion a persistencia no debe cambiar el contrato del selector. Ese es el punto clave para no romper el sistema.

La estrategia recomendada es:

1. definir ahora un contrato estable de salida;
2. implementar primero una fuente declarativa en codigo que satisfaga ese contrato;
3. reemplazar despues la fuente por una tabla parametrizable, manteniendo la misma interfaz del selector.

### Forma de migracion

En una etapa posterior, el selector puede dejar de leer un mapping en codigo y pasar a leer una tabla con columnas como:

- `material_id`
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

## 8. Tests minimos

Sin implementar serving nuevo, ya puede definirse que pruebas deberia cubrir el selector:

- resuelve la configuracion exacta cuando existe `material_id + horizonte_meses`;
- cae a configuracion por material cuando falta la exacta;
- cae a `prophet_base` cuando no existe configuracion del material;
- marca `calibrado = true` solo para reglas exactas respaldadas por benchmark;
- marca `calibrado = false` en todos los fallbacks;
- conserva `MAPE`, `MAE`, `folds`, `confiabilidad` y `justificacion` sin alterarlos;
- expone `regresores` coherentes con el modelo recomendado;
- no inventa horizontes ni metricas ausentes.

Tambien conviene un test de contrato:

- toda salida del selector debe incluir los campos requeridos, incluso cuando la decision sea fallback.

## 9. Exposicion en la respuesta del endpoint de forecast

La decision del selector no debe quedar oculta. El endpoint de forecast deberia exponerla para trazabilidad.

La forma recomendada es agregar un bloque de metadatos de seleccion, por ejemplo:

```json
{
  "forecast": { "...": "..." },
  "model_selection": {
    "modelo": "prophet_ipim_nivel_general",
    "regresores": ["ipim_nivel_general"],
    "mape": 4.98,
    "mae": 6.76,
    "folds": 9,
    "confiabilidad": "alta",
    "origen_decision": "material_horizonte",
    "justificacion": "Configuracion recomendada para Cemento Portland a 3 meses segun benchmark documentado y MAPE minimo medido.",
    "calibrado": true
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
- SICONS selecciona modelo por material y horizonte;
- `MAPE` sigue siendo la metrica principal;
- `MAE`, `folds` y confiabilidad de la serie funcionan como soporte;
- los regresores externos solo se sostienen si mejoran backtesting y conservan coherencia economica;
- cuando no hay calibracion suficiente, el sistema debe decirlo de forma explicita.

Ese ultimo punto es importante: el selector no solo elige modelo; tambien comunica el nivel de sustento metodologico de esa eleccion.
