# Mediciones Forecasting

## Alcance

Este documento resume las métricas obtenidas hasta el momento para el pronóstico del precio del cemento en `BuildWise`.

Supuestos principales usados en esta etapa:

- material: `Cemento Portland`
- variable objetivo: `precio_promedio_normalizado`
- ventana de trabajo: desde `2022-01-01`
- backtesting temporal sobre serie mensual
- las comparaciones principales de regresores se midieron con horizonte de `3 meses`

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

## Mejor modelo actual

Hasta este punto, el mejor resultado por `MAPE` es:

- modelo: `prophet_oficial_mayorista`
- `MAE`: `11.32`
- `MAPE`: `7.74%`
- efectividad informal: `92.26%`

Interpretación:

- `Prophet` mejora mucho al incorporar regresores externos
- el mejor regresor individual probado hasta ahora es `dólar oficial`
- el error reportado en esta sección corresponde a predicción de `3 meses`
- sumar variables no garantiza mejora

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
- `dólar oficial` es el mejor regresor individual probado hasta ahora
- la mejor combinación medida hasta ahora es `dólar oficial + dólar mayorista`
- con `oficial + mayorista`, el error crece mucho menos entre `3` y `12` meses
- el mejor modelo actual queda por debajo de `10%` de `MAPE` incluso a `12 meses`

## Próximas mediciones a agregar

- estabilidad fold por fold de `oficial + mayorista`
- comparación diaria vs mensual una vez corregida la evaluación diaria irregular
- nuevas corridas con regresores adicionales como `ICC`
