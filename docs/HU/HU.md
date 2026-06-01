# Historias de usuario y trazabilidad funcional

Este documento resume el alcance funcional de `BuildWise` y deja visible dos niveles de lectura:

- **Estado actual**: si la funcionalidad esta implementada, parcial o pendiente.
- **Cumplimiento literal**: si la implementacion coincide al pie de la letra con la redaccion de la historia.

## Resumen

| Grupo | Cantidad |
| --- | ---: |
| Historias totales | 40 |
| Implementadas | 40 |
| Parciales | 0 |
| Pendientes | 0 |

| Cumplimiento literal | Cantidad |
| --- | ---: |
| ✅ Si | 40 |
| 🟡 Parcial | 0 |
| ❌ No | 0 |

## Alcance MVP vigente

Para esta etapa, el alcance funcional y de validacion de historias se concentra en **3 productos clave**:

- `Cemento Portland`
- `Pastina`
- `Membrana Megaflex`

Las historias nuevas o pendientes deben considerarse prioritariamente sobre estos tres productos. La extension a otros materiales queda fuera del MVP actual.

## Criterios

| Campo | Valor | Criterio |
| --- | --- | --- |
| Estado actual | Implementada | La funcionalidad aparece reflejada en el sistema o en la documentacion operativa actual. |
| Estado actual | Parcial | Existe soporte inicial, pero falta completar parte del flujo, la visualizacion o su consolidacion funcional. |
| Estado actual | Pendiente | La funcionalidad forma parte del alcance previsto, pero no esta documentada como resuelta. |
| Cumplimiento literal | ✅ Si | La implementacion coincide de forma directa con la redaccion de la historia. |
| Cumplimiento literal | 🟡 Parcial | La implementacion cubre la intencion funcional principal, pero no todos los detalles literales. |
| Cumplimiento literal | ❌ No | La historia no esta implementada o no cubre todavia la conducta pedida. |

# Sprint 1

## Epica 1. Gestion y preparacion de datos

| HU | Historia | Estado | Literal | Observacion |
| --- | --- | --- | --- | --- |
| HU1 | Registrar precios historicos de materiales junto con su fecha. | Implementada | ✅ Si | Registro disponible para construir la base historica. |
| HU2 | Consultar historial de precios de un material. | Implementada | ✅ Si | Historial visible por material. |
| HU3 | Normalizar precios segun una unidad comparable. | Implementada | ✅ Si | Normalizacion por unidad base soportada. |
| HU4 | Seleccionar distintos materiales para su analisis. | Implementada | ✅ Si | Selector de material disponible. |
| HU5 | Filtrar datos por periodo. | Implementada | ✅ Si | Filtros por rango de fechas disponibles. |
| HU6 | Consultar la fuente de los datos registrados. | Implementada | ✅ Si | La serie conserva fuentes y datos de origen. |

## Epica 2. Analisis y visualizacion

| HU | Historia | Estado | Literal | Observacion |
| --- | --- | --- | --- | --- |
| HU7 | Visualizar precios historicos en graficos. | Implementada | ✅ Si | Grafico historico disponible. |
| HU8 | Comparar materiales entre si. | Implementada | ✅ Si | Comparacion entre materiales disponible. |
| HU9 | Identificar variaciones porcentuales de precios. | Implementada | ✅ Si | Incluye comparador libre entre dos fechas arbitrarias por material mediante `variacion-entre-fechas`, con trazabilidad de fechas usadas y variacion % calculada. |
| HU10 | Detectar cambios bruscos o anomalias. | Implementada | ✅ Si | Deteccion mensual disponible con Random Forest y residuo dinamico por material, sin umbral porcentual fijo. |

## Epica 3. Prediccion de precios

| HU | Historia | Estado | Literal | Observacion |
| --- | --- | --- | --- | --- |
| HU11 | Consultar precio actual del sistema y horizonte para estimar precio futuro. | Implementada | ✅ Si | El sistema estima por material y horizonte usando precio actual derivado de la serie historica; en MVP no se requiere ingreso manual de precio por parte del usuario comun. |
| HU12 | Visualizar proyeccion futura junto al historico. | Implementada | ✅ Si | Historico y forecast conviven en el grafico. |
| HU13 | Obtener diferencia y variacion entre precio actual y proyectado. | Implementada | ✅ Si | Variacion esperada expuesta en las vistas de forecast/costo. |
| HU14 | Estimar precios a 3, 6 y 12 meses. | Implementada | ✅ Si | Horizontes soportados dentro del rango del forecast. |
| HU15 | Consultar nivel de confianza o error del modelo. | Implementada | ✅ Si | Se expone MAPE, MAE, folds y efectividad informal; MAPE sigue como metrica principal. |

## Epica 4. Proyeccion de costos de obra

| HU | Historia | Estado | Literal | Observacion |
| --- | --- | --- | --- | --- |
| HU16 | Proyectar costo futuro segun cantidad necesaria. | Implementada | ✅ Si | Calculo por cantidad disponible. |
| HU17 | Comparar comprar ahora versus comprar despues. | Implementada | ✅ Si | Comparacion actual/proyectado disponible. |
| HU18 | Simular escenarios temporales de compra. | Implementada | ✅ Si | Incluye simulador temporal multi-horizonte en una sola salida (`simulacion-escenarios-compra`) con estrategias comparables por horizonte; no equivale a los escenarios optimista/base/pesimista de HU31. |
| HU19 | Estimar costo futuro de varios materiales de una obra. | Implementada | ✅ Si | Planificador multi-material disponible. |
| HU20 | Obtener resumen del impacto presupuestario. | Implementada | ✅ Si | Resumen agregado disponible para materiales cargados. |

## Epica 5. Optimizacion de compras

| HU | Historia | Estado | Literal | Observacion |
| --- | --- | --- | --- | --- |
| HU21 | Recomendar el mejor momento de compra. | Implementada | ✅ Si | Devuelve accion, variacion, impacto economico, MAPE, umbral de decision, confianza y advertencias. |
| HU22 | Comparar estrategias de compra. | Implementada | ✅ Si | Compara compra ahora, espera y compra parcial, con costo, diferencia ARS/%, estrategia ganadora y significancia. |
| HU23 | Optimizar compra bajo restriccion presupuestaria. | Implementada | ✅ Si | Usa variables explicitas de compra inmediata y postergada, minimiza costo total esperado, respeta presupuesto, cantidades, no negatividad y minimos por criticidad cuando se informan. |
| HU24 | Priorizar materiales criticos. | Implementada | ✅ Si | Ranking de criticidad disponible. |
| HU28 | Optimizar presupuesto con criticidad y forecast. | Implementada | ✅ Si | Devuelve asignacion recomendada, presupuesto usado/restante, impacto economico, criticidad, confianza y advertencias. |
| HU28b | Generar recomendacion operativa trazable. | Implementada | ✅ Si | Consolida accion, cantidades, impacto economico, confianza, supuestos y advertencias en una salida final, incorporando recomendacion simple y mejor estrategia comparativa por material. |

# Sprint 2

## Epica 6. Asistencia conversacional

| HU | Historia | Estado | Literal | Observacion |
| --- | --- | --- | --- | --- |
| HU25 | Consultar precios y proyecciones en lenguaje natural. | Implementada | ✅ Si | Capa conversacional integrada con el motor de pricing y forecast. |
| HU26 | Preguntar por un material especifico en lenguaje natural. | Implementada | ✅ Si | El chat hereda el material_id seleccionado y responde sobre su contexto. |
| HU27 | Solicitar explicaciones sobre la proyeccion. | Implementada | ✅ Si | El LLM interpreta y explica los drivers del modelo y la confianza. |
| HU27b | Conversar con el asistente y recibir una recomendacion accionable de compra. | Implementada | ✅ Si | Integra la funcion de recomendacion de compra en la salida conversacional. |

## Epica 7. Decision asistida y operacion proactiva

| HU | Historia | Estado | Literal | Observacion |
| --- | --- | --- | --- | --- |
| HU29 | Recomendar estrategia segun fase de obra y fecha objetivo. | Implementada | ✅ Si | Endpoint `recomendacion-contextual` y vista de decision incorporan fase, fecha u horizonte, cantidad y tolerancia al riesgo para devolver una accion justificada. |
| HU30 | Explicar por que se recomienda una estrategia. | Implementada | ✅ Si | El asistente conversacional y las vistas de estrategia (HU22/HU28b) ya ofrecen explicaciones sobre drivers e impacto. |
| HU31 | Simular escenarios comparables (optimista/base/pesimista) en una vista unica. | Implementada | ✅ Si | El motor de forecast genera intervalos de confianza y la UI los visualiza como una franja de incertidumbre (fan chart). |
| HU32 | Emitir alertas proactivas de decision ante cambios relevantes. | Implementada | ✅ Si | Motor de alertas en backend que detecta oportunidades de compra, desvios de precio y perdida de confianza. Interfaz de notificaciones en el AppHeader. |

## Epica 8. Asistente inteligente de presupuestacion y decision de compra

| HU | Historia | Estado | Literal | Observacion |
| --- | --- | --- | --- | --- |
| HU33 | Ingresar una necesidad de obra en lenguaje natural para solicitar orientacion de compra. | Implementada | ✅ Si | La vista `Asistente de compra IA` admite el pedido libre para productos del MVP. |
| HU34 | Interpretar mediante IA la necesidad e identificar producto, cantidad, etapa de obra, fecha objetivo, presupuesto disponible y datos faltantes. | Implementada | ✅ Si | Endpoint `chat/presupuestacion/interpretar` restringe el catalogo a los tres productos y devuelve datos estructurados y faltantes. |
| HU35 | Validar o corregir los datos interpretados antes de generar un presupuesto o recomendacion. | Implementada | ✅ Si | El frontend presenta un formulario editable y requiere validar los datos antes de generar la propuesta. |
| HU36 | Generar un presupuesto estimado con precios vigentes y cantidades confirmadas para los productos del MVP. | Implementada | ✅ Si | La propuesta utiliza el precio vigente calculado por backend y totales por cantidad. |
| HU37 | Recomendar el momento de compra considerando presupuesto, precio actual, forecast, fecha de uso y confianza del modelo. | Implementada | ✅ Si | El flujo de compra reutiliza `recomendacion-contextual` para combinar fase, fecha/horizonte, tolerancia y forecast. |
| HU38 | Generar una propuesta de compra explicable que integre presupuesto, recomendacion, supuestos y riesgos. | Implementada | ✅ Si | Endpoint `chat/presupuestacion/propuesta` entrega importes calculados y texto redactado por IA bajo contexto controlado. |
