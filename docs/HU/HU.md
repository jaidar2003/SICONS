Historias de usuario y trazabilidad funcional

Esta seccion organiza el alcance funcional del sistema en epicas e historias de usuario. Su objetivo es servir como referencia de avance del proyecto y como guia para identificar funcionalidades implementadas, parciales o pendientes.

Convencion de estado:

Implementada: la funcionalidad ya aparece reflejada en el sistema o en la documentacion operativa actual.
Parcial: existe soporte inicial, pero falta completar parte del flujo, la visualizacion o su consolidacion funcional.
Pendiente: la funcionalidad forma parte del alcance previsto, pero no esta documentada como resuelta en el estado actual del proyecto.
Epica 1. Gestión y preparación de datos

HU1 Registrar precios historicos de materiales. Como usuario del sistema, quiero registrar precios historicos de materiales junto con su fecha para disponer de una base de datos que permita analizar su evolucion. Estado actual: Implementada.

HU2 Consultar historial de precios de un material. Como comprador de materiales, quiero visualizar el historial de precios de un material para entender como vario su costo en el tiempo. Estado actual: Implementada.

HU3 Normalizar precios segun una unidad comparable. Como usuario del sistema, quiero que los precios se expresen en una unidad comparable para poder analizar correctamente materiales cuya presentacion haya cambiado. Estado actual: Implementada.

HU4 Seleccionar distintos materiales para su analisis. Como comprador de materiales, quiero seleccionar distintos materiales para poder analizar y proyectar el comportamiento de cada uno por separado. Estado actual: Implementada.

HU5 Filtrar datos por periodo. Como comprador de materiales, quiero filtrar los datos por rango de fechas para analizar la evolucion de un material en un periodo determinado. Estado actual: Implementada.

HU6 Consultar la fuente de los datos registrados. Como usuario del sistema, quiero conocer la fuente de cada precio registrado para confiar en la validez de la informacion utilizada. Estado actual: Implementada.

Epica 2. Análisis y visualización

HU7 Visualizar precios historicos en graficos. Como comprador de materiales, quiero ver un grafico con la evolucion historica de precios para interpretar facilmente la tendencia del material. Estado actual: Implementada.

HU8 Comparar materiales entre si. Como comprador de materiales, quiero comparar la evolucion de precios de distintos materiales para identificar cuales presentan mayor variacion o riesgo de aumento. Estado actual: Implementada.

HU9 Identificar variaciones porcentuales de precios. Como comprador de materiales, quiero ver el porcentaje de variacion de un material entre dos fechas para dimensionar cuanto aumento o disminuyo. Estado actual: Implementada.

HU10 Detectar cambios bruscos o anomalias. Como usuario del sistema, quiero identificar meses con aumentos o cambios atipicos para detectar comportamientos relevantes en la serie historica. Estado actual: Implementada.

Epica 3. Predicción de precios

HU11 Estimar el precio futuro de un material. Como comprador de materiales, quiero ingresar un precio actual y un horizonte temporal para estimar cuanto podria costar el material en el futuro. Estado actual: Parcial.

HU12 Visualizar la proyeccion futura junto al historico. Como comprador de materiales, quiero ver en un mismo grafico los precios historicos y la proyeccion futura para comprender la evolucion esperada del material. Estado actual: Implementada.

HU13 Obtener la variacion esperada entre precio actual y precio proyectado. Como comprador de materiales, quiero conocer la diferencia y el porcentaje de variacion entre el precio actual y el estimado para evaluar el impacto economico futuro. Estado actual: Implementada.

HU14 Estimar precios a distintos horizontes temporales. Como comprador de materiales, quiero obtener estimaciones a 3, 6 y 12 meses para planificar la compra segun distintas etapas de la obra. Estado actual: Implementada.

HU15 Consultar el nivel de confianza o error del modelo. Como usuario del sistema, quiero conocer una medida de error o fiabilidad de la prediccion para interpretar los resultados con mayor criterio. Estado actual: Implementada. Nota metodologica: la fiabilidad del modelo se documenta actualmente mediante MAPE, MAE, cantidad de folds y efectividad informal. La metrica principal de comparacion sigue siendo MAPE.

Epica 4. Proyección de costos de obra

HU16 Proyectar el costo futuro segun la cantidad necesaria. Como comprador de materiales, quiero indicar la cantidad de material que necesito para calcular cuanto podria gastar si lo compro mas adelante. Estado actual: Implementada.

HU17 Comparar el costo de comprar ahora versus comprar despues. Como comprador de materiales, quiero comparar el costo actual con el costo futuro estimado para decidir si me conviene comprar ahora o esperar. Estado actual: Implementada.

HU18 Simular escenarios de compra. Como comprador de materiales, quiero simular distintos escenarios temporales de compra para evaluar como impacta el momento de adquisicion en mi presupuesto. Estado actual: Implementada.

HU19 Estimar el costo futuro de varios materiales de una obra. Como comprador de materiales, quiero ingresar varios materiales y sus cantidades para proyectar el costo total estimado de una parte de la obra. Estado actual: Implementada.

HU20 Obtener un resumen del impacto presupuestario. Como comprador de materiales, quiero recibir un resumen del aumento estimado de costos para tomar decisiones con una vision global del presupuesto. Estado actual: Implementada.

Epica 5. Optimización de compras

HU21 Recomendar el mejor momento de compra. Como comprador de materiales, quiero recibir una recomendacion sobre cuando comprar para minimizar el costo estimado de mi obra. Estado actual: Parcial.

HU22 Comparar estrategias de compra. Como comprador de materiales, quiero comparar distintas estrategias de compra para decidir entre comprar todo hoy, comprar por etapas o esperar. Estado actual: Parcial.

HU23 Optimizar la compra bajo una restriccion presupuestaria. Como comprador de materiales, quiero que el sistema considere un presupuesto disponible para sugerirme una estrategia de compra viable. Estado actual: Parcial.

HU24 Priorizar materiales criticos. Como comprador de materiales, quiero identificar cuales materiales tienen mayor riesgo de aumento para priorizar su compra antes que otros. Estado actual: Implementada.

HU28 Optimizar presupuesto de compra con criticidad y forecast. Como comprador de materiales, quiero ingresar un presupuesto total y una lista de materiales con cantidades y criticidad para obtener una recomendacion operativa de compra que priorice el mejor uso del presupuesto disponible. Estado actual: Parcial.

Epica 6. Asistencia conversacional

HU25 Consultar precios y proyecciones en lenguaje natural. Como comprador de materiales, quiero hacer preguntas al sistema en lenguaje natural para obtener informacion sin navegar manualmente por graficos y tablas. Estado actual: Pendiente.

HU26 Preguntar por un material especifico. Como comprador de materiales, quiero consultar cuanto podria costar un material en el futuro mediante una pregunta para obtener una respuesta rapida y directa. Estado actual: Pendiente.

HU27 Solicitar explicaciones sobre la proyeccion. Como comprador de materiales, quiero pedirle al sistema una explicacion del resultado estimado para entender en que datos se basa la proyeccion. Estado actual: Pendiente.
