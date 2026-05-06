# Mediciones Forecasting

## Alcance

Este documento resume las métricas obtenidas hasta el momento para el pronóstico del precio del cemento en `BuildWise`.

Tambien incorpora una lectura comparativa de confiabilidad relativa para los materiales adicionales ya integrados al sistema, con el fin de dejar explicitadas sus diferencias metodologicas.

Supuestos principales usados en esta etapa:

- material: `Cemento Portland`
- variable objetivo: `precio_promedio_normalizado`
- ventana de trabajo: desde `2022-01-01`
- backtesting temporal sobre serie mensual
- las comparaciones principales de regresores se midieron con horizonte de `3 meses`

## Precondicion de reproducibilidad

Las metricas registradas en este documento suponen un dataset minimo reproducible de tesis que todavia debe cerrarse operativamente en el bootstrap oficial.

Ese dataset minimo debe reconstruir:

- `Cemento Portland` con serie historica real, densa y continua;
- `Pastina` con serie mensual hibrida, diferenciando `REAL` y `ESTIMADO`;
- `Membrana Megaflex` con serie mensual hibrida, diferenciando `REAL` y `ESTIMADO`;
- regresores `ipc`, `dolar_oficial`, `dolar_mayorista`, `dolar_blue` e `ipim_nivel_general`.

La fuente canonica correcta para la serie robusta de `Cemento Portland` ya es el extracto versionado y auditable `db/bootstrap/cemento_portland_historico.csv`, cargado por `app/operations/bootstrap/import_cemento_canonico.py`. En consecuencia, `import_cemento_facturas` debe leerse como import incremental u operativo y no como base suficiente para reproducir estas mediciones. `import_sicons_excel` queda como mecanismo legacy o transitorio de conversion desde Excel.

El contrato tecnico previsto para esa fuente canonica es:

- formato `CSV` versionado dentro del repo;
- columnas minimas `fecha`, `empresa`, `numero_comprobante`, `articulo`, `precio_original`, `precio_normalizado`, `moneda`, `origen_dato`, `metodo_estimacion` y `observaciones_origen`;
- `origen_dato = REAL` en todos los registros de `Cemento Portland`;
- `metodo_estimacion` vacio o `null`;
- posibilidad de anonimizar `numero_comprobante` si hubiera sensibilidad, siempre que se preserve un identificador estable para trazabilidad e idempotencia.

Mientras la reconstruccion automatica de ese dataset minimo no quede cerrada en `Docker + bootstrap`, estas metricas deben interpretarse como evidencia metodologica ya medida, pero todavia no como resultado automaticamente regenerable en cualquier base limpia sin pasos adicionales gobernados.

## Datos utilizados

- registros crudos de cemento: `1624`
- puntos mensuales: `51`
- puntos diarios: `759`
- rango observado: `2022-01-03` a `2026-03-25`

## Baselines y Prophet sin regresores

### Mejor baseline mensual

- modelo: `promedio_movil_3m`
- `MAPE`: `7.28%`

### Mejor Prophet mensual sin regresores

Configuración:

- `yearly_seasonality=False`
- `changepoint_prior_scale=0.01`
- `seasonality_prior_scale=1.0`
- `seasonality_mode=additive`

Métricas:

- `MAPE`: `13.90%`

## Prophet sin regresores por horizonte

### Horizonte 3 meses

- `MAPE`: `13.90%`
- efectividad informal: `86.10%`

### Horizonte 6 meses

- `MAPE`: `18.30%`
- efectividad informal: `81.70%`

### Horizonte 12 meses

- `MAPE`: `19.31%`
- efectividad informal: `80.69%`

## Regresores externos probados

Resultados con serie mensual desde `2022-01-01`, `9` folds y horizonte de test de `3 meses` por fold:

| Modelo | MAE | MAPE | Efectividad informal |
|---|---:|---:|---:|
| `prophet_base` | 18.33 | 13.90% | 86.10% |
| `prophet_blue` | 16.51 | 12.35% | 87.65% |
| `prophet_ipc` | 13.91 | 9.60% | 90.40% |
| `prophet_blue_ipc` | 11.35 | 8.16% | 91.84% |
| `prophet_oficial` | 11.47 | 7.78% | 92.22% |
| `prophet_oficial_ipc` | 13.75 | 9.48% | 90.52% |
| `prophet_mayorista` | 13.42 | 9.54% | 90.46% |
| `prophet_mayorista_ipc` | 12.28 | 8.20% | 91.80% |
| `prophet_oficial_blue` | 12.31 | 8.55% | 91.45% |
| `prophet_oficial_mayorista` | 11.32 | 7.74% | 92.26% |
| `prophet_oficial_ipc_blue` | 12.76 | 9.04% | 90.96% |
| `prophet_oficial_ipc_mayorista` | 12.78 | 8.58% | 91.42% |

## Actualizacion con IPIM Nivel General

Se incorporo una nueva medicion experimental usando `IPIM Nivel General` como regresor externo adicional. La evaluacion confirma que no corresponde sostener un unico modelo global para todos los materiales.

Los resultados medidos fueron:

| Material | Modelo con `IPIM` | MAE | MAPE | Mejor modelo actual comparado | MAE comparado | MAPE comparado | Conclusion |
|---|---|---:|---:|---|---:|---:|---|
| `Cemento Portland` | `prophet_ipim_nivel_general` | 6.76 | 4.98% | `prophet_oficial_mayorista` | 11.32 | 7.74% | mejora significativa |
| `Pastina` | `prophet_ipim_nivel_general` | 140.16 | 6.47% | `prophet_blue_ipc` | 120.90 | 5.00% | no mejora |
| `Membrana Megaflex` | `prophet_ipim_nivel_general` | 823.96 | 10.06% | `prophet_ipc` | 734.37 | 8.31% | no mejora |

Interpretacion:

- `IPIM Nivel General` pasa a ser un candidato fuerte para `Cemento Portland`.
- `IPIM Nivel General` no debe adoptarse para `Pastina` ni `Membrana Megaflex`, porque empeora sus metricas frente a los mejores modelos ya medidos.
- una mejora en un material no debe generalizarse automaticamente a los demas.
- un mejor resultado visual no alcanza para cambiar la recomendacion metodologica; la metrica principal sigue siendo `MAPE`.

## Seleccion de modelo por material

Con la evidencia actual, la recomendacion metodologica deja de ser un modelo global unico y pasa a ser una seleccion diferenciada por material y horizonte.

### Horizonte 3 meses

| Material | Modelo recomendado actual | MAE | MAPE | Efectividad informal | Soporte metodologico |
|---|---|---:|---:|---:|---|
| `Cemento Portland` | `prophet_ipim_nivel_general` | 6.76 | 4.98% | 95.02% | serie real, densa y continua |
| `Pastina` | `prophet_blue_ipc` | 120.90 | 5.00% | 95.00% | serie hibrida, continuidad mensual y `9` folds |
| `Membrana Megaflex` | `prophet_ipc` | 734.37 | 8.31% | 91.69% | serie hibrida, continuidad mensual y `9` folds |

### Criterio de seleccion

- la metrica principal sigue siendo `MAPE`;
- `MAE`, cantidad de `folds` y confiabilidad relativa de la serie se usan como soporte;
- los regresores externos solo deben incorporarse si mejoran el backtesting y tienen coherencia economica;
- la seleccion automatica o parametrizada de modelos por material queda como evolucion natural del sistema;
- `CAC` queda pendiente porque todavia no hay una serie oficial usable integrada para evaluarlo en igualdad de condiciones.

## Prophet + dólar oficial por horizonte

### Horizonte 3 meses

- `MAE`: `11.47`
- `MAPE`: `7.78%`
- efectividad informal: `92.22%`

### Horizonte 6 meses

- `MAE`: `15.30`
- `MAPE`: `10.49%`
- efectividad informal: `89.51%`

### Horizonte 12 meses

- `MAE`: `23.28`
- `MAPE`: `16.09%`
- efectividad informal: `83.91%`

## Mejor combinación actual por horizonte

Modelo:

- `prophet_oficial_mayorista`

### Horizonte 3 meses

- `folds`: `9`
- `MAE`: `11.32`
- `MAPE`: `7.74%`
- efectividad informal: `92.26%`
- nota: este resultado sigue siendo una referencia valida para `Cemento Portland`, pero deja de ser la recomendacion principal una vez incorporada la medicion con `IPIM Nivel General`.

### Horizonte 6 meses

- `folds`: `4`
- `MAE`: `12.53`
- `MAPE`: `8.53%`
- efectividad informal: `91.47%`

### Horizonte 12 meses

- `folds`: `2`
- `MAE`: `14.32`
- `MAPE`: `9.56%`
- efectividad informal: `90.44%`

## Lecturas principales

- `Prophet` base no supera al mejor baseline mensual
- `dólar blue` mejora frente a Prophet base, pero no es la mejor señal
- `IPC` mejora más que `blue` cuando se usa solo
- para `Cemento Portland`, `IPIM Nivel General` pasa a ser la mejor variante individual medida hasta el momento
- para `Pastina` y `Membrana Megaflex`, `IPIM` no mejora frente a los mejores modelos ya documentados
- la mejor combinación medida previamente para cemento sigue siendo `dólar oficial + dólar mayorista`, pero deja de ser la recomendacion principal a `3 meses` una vez incorporado `IPIM`
- una mejora puntual no debe generalizarse a todos los materiales
- el mejor modelo debe definirse por material, horizonte y evidencia de backtesting

## Confiabilidad relativa por material

Los tres materiales actualmente pronosticables del sistema tienen series mensuales continuas. Esa continuidad habilita el forecast y mejora la estabilidad operativa del pipeline, pero no implica por si sola la misma confiabilidad metodologica en todos los casos.

La comparacion actual es:

| Material | Continuidad mensual | Datos reales | Datos estimados | Folds | MAPE | Efectividad informal | Confiabilidad relativa |
|---|---|---:|---:|---:|---:|---:|---|
| `Cemento Portland` | si | 1624 precios | 0 | 9 | 8.58% | 91.42% | alta |
| `Pastina` | si, `51` meses | 10 registros | 41 | 9 | 5.75% | 94.25% | media |
| `Membrana Megaflex` | si, `52` meses | 9 registros | 43 | 5 | 14.64% | 85.36% | media-baja |

### Interpretacion

- `Cemento Portland` es la referencia principal del sistema porque combina continuidad mensual, densidad de observaciones y una serie historica real.
- `Pastina` y `Membrana Megaflex` usan series hibridas, compuestas por observaciones reales y meses estimados para cerrar continuidad temporal.
- En consecuencia, sus metricas sirven como evidencia de utilidad operativa y de capacidad de pronostico, pero no deben interpretarse con la misma solidez metodologica que las del cemento.
- Un `MAPE` bajo sobre una serie con muchos datos estimados puede sobrestimar la confiabilidad real del modelo, porque parte de la estructura temporal fue reconstruida y no observada directamente.
- La efectividad informal debe leerse solo como `100 - MAPE`, con funcion comunicacional de apoyo. La metrica principal de comparacion y defensa metodologica sigue siendo `MAPE`.
- La continuidad mensual mejora la estabilidad del forecast, pero no equivale automaticamente a mayor confiabilidad real si la serie depende en gran proporcion de valores estimados.

La lectura anterior debe entenderse sobre la base de tres fuentes de datos ya diferenciadas en el repositorio:

- `Cemento Portland` se apoya en el dataset canónico versionado;
- `Pastina` y `Membrana Megaflex` conservan series hibridas con `REAL` y `ESTIMADO`;
- `IPIM Nivel General` se integra desde un snapshot local versionado y no debe asumirse como sincronizacion online obligatoria.

## Próximas mediciones a agregar

- estabilidad fold por fold de `oficial + mayorista`
- comparación diaria vs mensual una vez corregida la evaluación diaria irregular
- nuevas corridas con regresores adicionales como `ICC`
- evaluacion de `CAC` cuando exista una serie oficial usable integrada en el benchmark experimental

## Proximo cierre operativo

Antes de activar el selector o priorizar nuevas features, el proyecto debe implementar un cierre de reproducibilidad con este flujo objetivo:

1. `alembic upgrade head`
2. `python -m app.operations.bootstrap.seed`
3. `python -m app.operations.bootstrap.import_cemento_canonico`
4. `python -m app.operations.bootstrap.import_pastina`
5. `python -m app.operations.bootstrap.import_membrana_megaflex`
6. `python -m app.operations.bootstrap.import_external_indices_snapshot`
7. `python -m app.operations.bootstrap.validate_minimum_dataset`

La validacion post-bootstrap debera comprobar:

- existencia de `Cemento Portland`, `Pastina` y `Membrana Megaflex`;
- presentaciones esperadas por material;
- series mensuales sin huecos;
- suficientes datos reales en `Cemento Portland`;
- deteccion estructurada de `REAL` y `ESTIMADO` en `Pastina` y `Membrana Megaflex`;
- disponibilidad de regresores requeridos;
- respuesta `200` en endpoints basicos de pricing y forecast.
