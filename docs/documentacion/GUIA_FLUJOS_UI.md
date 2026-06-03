# Guia de flujos UI

## Objetivo

Explicar como recorrer la aplicacion desde la interfaz y que decision soporta cada vista.

Esta guia complementa la documentacion de endpoints y sirve para demo, defensa y pruebas manuales.

## Resumen

La vista `Resumen` da una lectura ejecutiva del material seleccionado.

Permite:

- cambiar material;
- cambiar rango historico;
- ver metricas principales;
- leer una recomendacion rapida;
- comparar materiales.

Uso recomendado en demo:

1. Entrar a `Resumen`.
2. Seleccionar `Cemento Portland`.
3. Mostrar variacion, precio reciente y recomendacion.
4. Cambiar a `Pastina` o `Membrana Megaflex` para demostrar que la lectura depende del material.

## Forecast

La vista `Forecast` muestra la capa predictiva.

Permite:

- cambiar material y rango historico;
- ver proyeccion mensual;
- elegir horizonte de forecast;
- revisar grafico historico + proyectado;
- consultar detalles del modelo, MAPE, MAE, folds, confiabilidad y seleccion tecnica.

Uso recomendado en demo:

1. Entrar a `Forecast`.
2. Cambiar el material desde `Vista actual / Serie historica`.
3. Usar `Proyeccion` para mostrar el precio proyectado.
4. Cambiar horizonte.
5. Ir a `Modelo` para explicar MAPE, MAE, folds y confiabilidad.

## Costos

La vista `Costos` convierte forecast en decision economica.

### Armar presupuesto

Sirve para cargar varios materiales, cantidades, criticidad y presupuesto.

Incluye:

- escenario de costos de 1 a 12 meses;
- costo actual total;
- costo proyectado total;
- impacto presupuestario;
- optimizacion presupuestaria con `PuLP`;
- ranking de criticidad.

Uso recomendado:

1. Elegir `Armar presupuesto`.
2. Cargar varios materiales.
3. Definir cantidades.
4. Elegir escenario de costos.
5. Revisar `Resumen`.
6. Pasar a `Optimizacion` para asignar presupuesto.
7. Pasar a `Criticidad` para ver prioridades.

### Que comprar

Genera una recomendacion operativa consolidada.

Responde:

```text
que comprar ahora
que postergar
cuanto presupuesto usa
que ahorro o sobrecosto estima
con que confianza
```

### Analizar material

Evalua un solo material.

Permite:

- elegir material;
- elegir horizonte;
- definir cantidad objetivo;
- definir criticidad;
- calcular recomendacion;
- comparar estrategias.

Uso recomendado:

1. Elegir `Analizar material`.
2. Seleccionar material y horizonte.
3. Calcular recomendacion.
4. Comparar estrategias.

### Comparar meses

Compara escenarios temporales de compra en varios horizontes.

Sirve para mostrar como cambia la decision al mirar diferentes meses futuros.

### Calcular cantidad

Estima costo futuro para una cantidad puntual de un material.

Es util para preguntas simples:

```text
Si necesito X unidades, cuanto cambia comprar hoy versus comprar despues?
```

## Historial

La vista `Historial` audita la serie historica.

Permite:

- comparar dos fechas;
- ver grafico historico;
- revisar anomalias;
- ver tabla de datos;
- cargar precios si el usuario es admin.

### Anomalias

La seccion `Variaciones bruscas` muestra:

- grafico de la serie mensual;
- puntos rojos detectados por Random Forest;
- detalle textual de los meses anomalos.

Uso recomendado:

1. Entrar a `Historial`.
2. Elegir `Variaciones bruscas`.
3. Mostrar que la deteccion no usa umbral fijo.
4. Explicar que Random Forest estima el precio esperado y marca meses con residuo atipico.

## Admin

La vista `Admin` concentra configuracion interna.

Permite:

- administrar usuarios;
- configurar margenes comerciales;
- gestionar parametros que no forman parte del flujo operativo comun.

Solo aparece para usuarios con rol admin.

## Asistente IA

La vista `Asistente IA` concentra la experiencia conversacional. No existe un asistente separado para compras: las consultas generales, el RAG operativo y el flujo de presupuestacion conviven en una unica entrada.

Incluye:

- consultas sobre catalogo, precios historicos, forecast, confiabilidad, recomendaciones y margenes segun rol;
- RAG operativo sobre datos del backend, con chips de fuentes recuperadas;
- resolucion de material por nombre, alias y algunos errores frecuentes;
- interpretacion de necesidades de compra;
- validacion editable de producto, cantidad, fase, fecha/horizonte, presupuesto y tolerancia al riesgo;
- generacion de propuesta comercial sin delegar calculos al modelo generativo.

Uso recomendado:

1. Entrar a `Asistente IA`.
2. Consultar un dato operativo, por ejemplo `cual fue el ultimo precio de cemento?`.
3. Ver chips de trazabilidad: `RAG backend`, material, horizonte y fuentes usadas.
4. Escribir una necesidad de compra, por ejemplo `Necesito comprar 500 kg de cemento en 6 meses`.
5. Revisar el panel de validacion editable.
6. Generar la propuesta.
7. Explicar que la IA interpreta y redacta, pero que los precios, forecast, recomendaciones y totales salen del backend.

## Ruta sugerida de demo completa

1. `Resumen`: mostrar lectura general del material.
2. `Forecast`: mostrar proyeccion, MAPE, MAE, folds y confiabilidad.
3. `Asistente IA`: mostrar RAG operativo y transformar una necesidad de compra en propuesta.
4. `Costos -> Analizar material`: explicar comprar ahora, postergar o sin ventaja clara.
5. `Costos -> Armar presupuesto`: mostrar presupuesto multi-material y optimizacion.
6. `Costos -> Que comprar`: mostrar recomendacion operativa consolidada.
7. `Historial -> Variaciones bruscas`: mostrar anomalias con Random Forest.

## Diferencias importantes

`Horizonte` no siempre significa lo mismo visualmente:

- en `Forecast`, define cuantos meses proyecta el modelo;
- en `Analizar material`, define el horizonte de la recomendacion individual;
- en `Armar presupuesto`, el `escenario de costos` define el mes futuro comun para comparar materiales.

La separacion evita que una decision de costos quede atada accidentalmente a una configuracion global de forecast.
