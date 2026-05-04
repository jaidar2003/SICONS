# GEMINI.md

## Proposito

Este archivo funciona como contexto operativo para asistentes IA que trabajen sobre `SICONS`. No reemplaza al `README.md`: el `README` es la documentacion formal del proyecto, mientras que este archivo resume decisiones tecnicas, convenciones y puntos de cuidado para intervenir en el repo sin contradecir criterios ya adoptados.

## Contexto del proyecto

- Proyecto: `SICONS`
- Dominio: seguimiento historico, normalizacion y forecasting de precios de materiales de construccion
- Stack principal: `FastAPI`, `PostgreSQL`, `React`, `Material UI`, `Prophet`, `Docker Compose`
- Enfoque arquitectonico: monolito modular con arquitectura hexagonal incremental

## Estructura relevante

- `app/modules/pricing/`: logica de precios, series y forecasting
- `app/modules/catalog/`: materiales, presentaciones y fuentes
- `app/modules/auth/`: autenticacion y usuarios
- `app/shared/`: configuracion, base de datos y componentes reutilizables
- `frontend/src/features/pricing/`: UI de precios, series y forecast

## Convenciones para forecasting

- La variable principal del forecast de cemento es `precio_promedio_normalizado`, expresada en `ARS/kg`.
- Las equivalencias comerciales de bolsas de `25 kg` y `50 kg` se usan solo para visualizacion y comparacion comercial.
- No usar precio por bolsa como serie principal del modelo.
- El modelo productivo preferido actualmente es `prophet_oficial_mayorista`.
- La metrica principal de comparacion metodologica es `MAPE`.
- La efectividad informal se calcula como `100 - MAPE` y se usa solo como indicador complementario.
- El horizonte de `3 meses` es el mas robusto por cantidad de `folds`.
- El horizonte de `12 meses` es prometedor, pero menos robusto por la menor cantidad de `folds`.
- No presentar variantes con `IPC` como modelo productivo salvo mejora consistente en backtesting.
- La plausibilidad visual del forecast no alcanza para elegir un modelo.
- Los regresores futuros deben modelarse explicitamente y validarse con backtesting temporal.

## Criterios de trabajo para asistentes

- Antes de tocar forecasting, revisar `README.md` y los archivos del modulo `pricing`.
- Si el pedido es de documentacion, no modificar codigo productivo.
- No inventar metricas, endpoints ni resultados experimentales.
- No contradecir la decision actual de mantener `prophet_oficial_mayorista` como baseline productivo.
- Diferenciar siempre entre variantes experimentales y modelo productivo.
- Si aparecen ejemplos de precios en documentacion publica, usar valores ficticios.

## Comandos utiles

```bash
make dev
docker compose up -d --build
.venv/bin/python -m pytest -q
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m app.train_prophet_cemento
```

## Archivos a revisar antes de cambios sensibles

- `README.md`
- `app/modules/pricing/interfaces/routes.py`
- `app/modules/pricing/application/`
- `frontend/src/features/pricing/`

## Nota final

Si una tarea afecta documentacion, metodologia o criterios de evaluacion del forecast, preservar coherencia con el `README.md`. Si una tarea afecta el modelo o la logica de negocio, explicitar si el cambio corresponde a experimentacion o a flujo productivo.
