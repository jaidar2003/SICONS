# CONTEXT

## Propósito del archivo

Este archivo funciona como bitacora tecnica de experimentacion para forecasting. No reemplaza al `README.md`, que contiene la documentacion formal del proyecto, ni a `GEMINI.md`, que resume reglas operativas para asistentes IA.

Su funcion es conservar contexto de trabajo, resultados intermedios, comparaciones entre variantes y proximos pasos metodologicos, de modo que futuras iteraciones no repitan analisis ya realizados.

Referencia de uso:

- `README.md`: estado metodologico vigente, decisiones formales y alcance funcional del proyecto.
- `GEMINI.md`: contexto operativo breve para asistentes IA.
- `MEDICIONES_FORECASTING.md`: mediciones y resultados puntuales cuando corresponda.

## Alcance y criterio de lectura

- Los resultados documentados aqui pueden incluir hallazgos exploratorios o comparaciones intermedias.
- La decision productiva vigente debe interpretarse siempre segun lo documentado en `README.md`.
- Este archivo no debe leerse como especificacion final del sistema, sino como registro tecnico de trabajo sobre forecasting.

## Objetivo actual

Evaluar y mejorar pronósticos del precio del cemento usando `Prophet`, con foco en:

- serie base: `precio_promedio_normalizado`
- rango de trabajo: desde `2022-01-01`
- comparación por backtesting temporal
- uso de regresores externos para bajar el error

## Datos disponibles

### Cemento

- registros crudos: `1624`
- rango observado: `2022-01-03` a `2026-03-25`
- puntos mensuales para modelado: `51`
- puntos diarios para modelado: `759`

### Dólar

Fuente descargada:

- `dolares_historico.json`

Exportadores y salidas:

- script: `scripts/exportar_dolares.py`
- carpeta filtrada desde 2022: `tmp/dolares_2022/`

Series usadas:

- `tmp/dolares_2022/dolar_blue_historico.csv`
- `tmp/dolares_2022/dolar_oficial_historico.csv`
- `tmp/dolares_2022/dolar_mayorista_historico.csv`

### IPC

Fuente actual preferida:

- `ipc.xls`

Exportador:

- `scripts/exportar_ipc.py`

Salida normalizada:

- `tmp/ipc_2022/ipc_nacional.csv`

Rango actual:

- desde `2022-01-01`
- hasta `2026-03-01`

## Scripts relevantes

- `app/train_prophet_cemento.py`
  - entrenamiento puntual de Prophet sobre cemento
- `app/experiment_prophet_cemento.py`
  - comparación de Prophet por frecuencia y horizonte
- `app/experiment_prophet_cemento_regresores.py`
  - comparación de Prophet con regresores externos

## Hallazgos confirmados

### Baselines y Prophet mensual sin regresores

En backtesting mensual previo:

- mejor baseline/sistema simple: `promedio_movil_3m`
- `MAPE`: `7.28%`

Mejor Prophet mensual sin regresores:

- configuración:
  - `yearly_seasonality=False`
  - `changepoint_prior_scale=0.01`
  - `seasonality_prior_scale=1.0`
  - `seasonality_mode=additive`
- `MAPE`: `13.90%`

Conclusión:

- `Prophet` base no supera a los modelos simples en la serie mensual actual

### Prophet por horizonte sin regresores

Mejor Prophet mensual:

- `3 meses`: `MAPE=13.90%`
- `6 meses`: `MAPE=18.30%`
- `12 meses`: `MAPE=19.31%`

Conclusión:

- el error crece con el horizonte
- `Prophet` es más defendible a corto plazo que a 12 meses

### Regresores externos ya probados

Resultados usando datos desde `2022-01-01`, `9` folds mensuales y horizonte de test de `3 meses`:

- `prophet_base`: `MAE=18.33` | `MAPE=13.90%`
- `prophet_blue`: `MAE=16.51` | `MAPE=12.35%`
- `prophet_ipc`: `MAE=13.91` | `MAPE=9.60%`
- `prophet_blue_ipc`: `MAE=11.35` | `MAPE=8.16%`
- `prophet_oficial`: `MAE=11.47` | `MAPE=7.78%`
- `prophet_oficial_ipc`: `MAE=13.75` | `MAPE=9.48%`
- `prophet_mayorista`: `MAE=13.42` | `MAPE=9.54%`
- `prophet_mayorista_ipc`: `MAE=12.28` | `MAPE=8.20%`
- `prophet_oficial_blue`: `MAE=12.31` | `MAPE=8.55%`
- `prophet_oficial_mayorista`: `MAE=11.32` | `MAPE=7.74%`
- `prophet_oficial_ipc_blue`: `MAE=12.76` | `MAPE=9.04%`
- `prophet_oficial_ipc_mayorista`: `MAE=12.78` | `MAPE=8.58%`

Conclusión vigente:

- el mejor Prophet actual es `Prophet + dólar oficial + dólar mayorista`
- `MAPE=7.74%`
- efectividad informal a `3 meses`: `~92.26%`

Nota:

- esta conclusion resume el mejor resultado experimental observado;
- la formulacion metodologica y el criterio de suficiencia del modelo vigente deben tomarse del `README.md`.

### Prophet + dólar oficial por horizonte

- `3 meses`: `MAE=11.47` | `MAPE=7.78%` | efectividad `~92.22%`
- `6 meses`: `MAE=15.30` | `MAPE=10.49%` | efectividad `~89.51%`
- `12 meses`: `MAE=23.28` | `MAPE=16.09%` | efectividad `~83.91%`

Conclusión:

- mejora fuerte frente a Prophet base
- sigue degradándose bastante a 12 meses

### Mejor combinación actual por horizonte

Modelo:

- `prophet_oficial_mayorista`

Resultados:

- `3 meses`: `MAE=11.32` | `MAPE=7.74%` | efectividad `~92.26%` | `folds=9`
- `6 meses`: `MAE=12.53` | `MAPE=8.53%` | efectividad `~91.47%` | `folds=4`
- `12 meses`: `MAE=14.32` | `MAPE=9.56%` | efectividad `~90.44%` | `folds=2`

Conclusión:

- `oficial + mayorista` supera levemente a `oficial` solo a `3 meses`
- la mejora se sostiene mejor de lo esperado a `6` y `12 meses`
- con esta combinación, el `MAPE` queda por debajo de `10%` incluso a `12 meses`

## Estado metodológico actual

- `Prophet` ya está implementado y evaluado con backtesting temporal
- el mejor resultado actual de `Prophet` requiere regresores externos
- `dólar oficial` es el mejor regresor individual probado
- la mejor combinación probada hasta ahora es `oficial + mayorista`
- sumar más regresores no garantiza mejora
- hay evidencia concreta de redundancia:
  - `oficial` solo: `MAPE=7.78%`
  - `oficial + ipc`: `MAPE=9.48%`

Lectura recomendada:

- usar esta seccion como resumen tecnico de experimentacion;
- validar cualquier decision final contra las definiciones vigentes del `README.md`.

## Próximo paso

Comparar combinaciones chicas centradas en `dólar oficial`:

1. comparar `oficial + mayorista` contra el mejor baseline a `6` y `12 meses`
2. medir estabilidad fold por fold de `oficial + mayorista`
3. probar `ICC` encima de `oficial + mayorista`
4. cerrar la comparación diaria vs mensual una vez corregida la evaluación diaria irregular

Regla de decisión:

- priorizar `MAPE`
- usar backtesting temporal
- no asumir que más regresores implica mejor forecast

## Nota de mantenimiento

Si este archivo deja de aportar contexto distinto del `README.md` o de `MEDICIONES_FORECASTING.md`, conviene consolidarlo para evitar multiples fuentes de verdad. Mientras conserve resultados exploratorios, comparaciones historicas y lineas de trabajo abiertas, sigue siendo util como bitacora tecnica.
