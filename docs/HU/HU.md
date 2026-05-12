# Historias de usuario y trazabilidad funcional

Este documento resume el alcance funcional de `BuildWise` y deja visible dos niveles de lectura:

- **Estado actual**: si la funcionalidad esta implementada, parcial o pendiente.
- **Cumplimiento literal**: si la implementacion coincide al pie de la letra con la redaccion de la historia.

## Resumen

| Grupo | Cantidad |
| --- | ---: |
| Historias totales | 28 |
| Implementadas | 21 |
| Parciales | 4 |
| Pendientes | 3 |

| Cumplimiento literal | Cantidad |
| --- | ---: |
| Si | 18 |
| Parcial | 7 |
| No | 3 |

## Criterios

| Campo | Valor | Criterio |
| --- | --- | --- |
| Estado actual | Implementada | La funcionalidad aparece reflejada en el sistema o en la documentacion operativa actual. |
| Estado actual | Parcial | Existe soporte inicial, pero falta completar parte del flujo, la visualizacion o su consolidacion funcional. |
| Estado actual | Pendiente | La funcionalidad forma parte del alcance previsto, pero no esta documentada como resuelta. |
| Cumplimiento literal | Si | La implementacion coincide de forma directa con la redaccion de la historia. |
| Cumplimiento literal | Parcial | La implementacion cubre la intencion funcional principal, pero no todos los detalles literales. |
| Cumplimiento literal | No | La historia no esta implementada o no cubre todavia la conducta pedida. |

## Epica 1. Gestion y preparacion de datos

| HU | Historia | Estado | Literal | Observacion |
| --- | --- | --- | --- | --- |
| HU1 | Registrar precios historicos de materiales junto con su fecha. | Implementada | Si | Registro disponible para construir la base historica. |
| HU2 | Consultar historial de precios de un material. | Implementada | Si | Historial visible por material. |
| HU3 | Normalizar precios segun una unidad comparable. | Implementada | Si | Normalizacion por unidad base soportada. |
| HU4 | Seleccionar distintos materiales para su analisis. | Implementada | Si | Selector de material disponible. |
| HU5 | Filtrar datos por periodo. | Implementada | Si | Filtros por rango de fechas disponibles. |
| HU6 | Consultar la fuente de los datos registrados. | Implementada | Si | La serie conserva fuentes y datos de origen. |

## Epica 2. Analisis y visualizacion

| HU | Historia | Estado | Literal | Observacion |
| --- | --- | --- | --- | --- |
| HU7 | Visualizar precios historicos en graficos. | Implementada | Si | Grafico historico disponible. |
| HU8 | Comparar materiales entre si. | Implementada | Si | Comparacion entre materiales disponible. |
| HU9 | Identificar variaciones porcentuales de precios. | Implementada | Parcial | La variacion se calcula sobre el periodo filtrado o puntos de la serie, no como comparador libre entre dos fechas arbitrarias. |
| HU10 | Detectar cambios bruscos o anomalias. | Implementada | Si | Deteccion de anomalias mensual disponible. |

## Epica 3. Prediccion de precios

| HU | Historia | Estado | Literal | Observacion |
| --- | --- | --- | --- | --- |
| HU11 | Ingresar precio actual y horizonte para estimar precio futuro. | Parcial | Parcial | El sistema estima por material y horizonte, pero no toma un precio actual manual como entrada principal. |
| HU12 | Visualizar proyeccion futura junto al historico. | Implementada | Si | Historico y forecast conviven en el grafico. |
| HU13 | Obtener diferencia y variacion entre precio actual y proyectado. | Implementada | Si | Variacion esperada expuesta en las vistas de forecast/costo. |
| HU14 | Estimar precios a 3, 6 y 12 meses. | Implementada | Si | Horizontes soportados dentro del rango del forecast. |
| HU15 | Consultar nivel de confianza o error del modelo. | Implementada | Si | Se expone MAPE, MAE, folds y efectividad informal; MAPE sigue como metrica principal. |

## Epica 4. Proyeccion de costos de obra

| HU | Historia | Estado | Literal | Observacion |
| --- | --- | --- | --- | --- |
| HU16 | Proyectar costo futuro segun cantidad necesaria. | Implementada | Si | Calculo por cantidad disponible. |
| HU17 | Comparar comprar ahora versus comprar despues. | Implementada | Si | Comparacion actual/proyectado disponible. |
| HU18 | Simular escenarios temporales de compra. | Implementada | Parcial | Se evalua por horizonte y estrategia, pero no hay un simulador libre de multiples escenarios temporales en una sola vista. |
| HU19 | Estimar costo futuro de varios materiales de una obra. | Implementada | Si | Planificador multi-material disponible. |
| HU20 | Obtener resumen del impacto presupuestario. | Implementada | Si | Resumen agregado disponible para materiales cargados. |

## Epica 5. Optimizacion de compras

| HU | Historia | Estado | Literal | Observacion |
| --- | --- | --- | --- | --- |
| HU21 | Recomendar el mejor momento de compra. | Parcial | Parcial | Existe recomendacion por material y horizonte, pero no cubre de forma completa todos los escenarios de obra. |
| HU22 | Comparar estrategias de compra. | Parcial | Parcial | Existe comparacion de estrategias base, pero sigue acotada a un conjunto simple. |
| HU23 | Optimizar compra bajo restriccion presupuestaria. | Parcial | Parcial | Hay optimizacion con presupuesto como primera version operativa. |
| HU24 | Priorizar materiales criticos. | Implementada | Si | Ranking de criticidad disponible. |
| HU28 | Optimizar presupuesto con criticidad y forecast. | Parcial | Parcial | La base tecnica existe, pero falta cerrar experiencia y criterios de aceptacion como funcionalidad final. |

## Epica 6. Asistencia conversacional

| HU | Historia | Estado | Literal | Observacion |
| --- | --- | --- | --- | --- |
| HU25 | Consultar precios y proyecciones en lenguaje natural. | Pendiente | No | La capa conversacional esta disenada, pero no implementada. |
| HU26 | Preguntar por un material especifico en lenguaje natural. | Pendiente | No | No existe endpoint ni vista conversacional activa. |
| HU27 | Solicitar explicaciones sobre la proyeccion. | Pendiente | No | Las explicaciones existen en vistas tecnicas, no mediante asistente conversacional. |
