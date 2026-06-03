# RAG operativo del asistente BuildWise

## Objetivo

El asistente de `BuildWise` usa RAG operativo para responder con datos del backend antes de invocar al modelo generativo. Su objetivo es evitar respuestas inventadas sobre precios, forecast, recomendaciones, margenes o presupuesto.

No se implementa como RAG documental/vectorial sobre archivos. En este MVP, la informacion critica vive en datos estructurados y servicios de negocio; por eso la recuperacion se resuelve consultando repositorios, tablas y calculos existentes.

## Flujo

```text
pregunta del usuario
-> validacion de alcance
-> resolucion de material y horizonte
-> recuperacion de datos del backend
-> armado de contexto trazable
-> llamada al proveedor de IA
-> respuesta con chips de fuentes usadas
```

## Fuentes recuperables

El asistente puede recuperar contexto desde:

- `catalogo.materiales`;
- `catalogo.presentaciones`;
- `catalogo.fuentes`;
- `precios_historicos`;
- `external_index_values`;
- `commercial_margins`, solo para usuarios administradores;
- `purchase_recommendations`, cuando la consulta requiere forecast, decision o recomendacion;
- `presupuestacion.propuesta`, cuando se genera una propuesta comercial validada.

La UI muestra estas fuentes como chips debajo de la respuesta para que la demo pueda demostrar trazabilidad.

## Resolucion de material

El sistema intenta resolver el material por:

- `material_id` seleccionado en la interfaz;
- nombre exacto o parcial;
- tokens del nombre del material;
- alias frecuentes.

Alias cubiertos en el MVP:

- `cemento`, `portland`, `cemnto`, `bolsa cemento` -> `Cemento Portland`;
- `pastina`, `klaukol`, `pastina klaukol` -> `Pastina`;
- `membrana`, `megaflex`, `membrana asfaltica`, `impermeabilizante` -> `Membrana Megaflex`.

## Contrato visible

El endpoint `/chat/consultas` devuelve, ademas de la respuesta:

- `tipo_intencion`;
- `contexto_usado`;
- `fuentes_recuperadas`;
- `material_resuelto`;
- `horizonte_resuelto`.

El frontend traduce esos metadatos en chips:

- `RAG backend`;
- intencion clasificada;
- material resuelto;
- horizonte;
- fuentes recuperadas.

## Intenciones formales

El asistente clasifica cada consulta en una de estas categorias:

- `HISTORICO`;
- `FORECAST`;
- `RECOMENDACION`;
- `PRESUPUESTO`;
- `CATALOGO`;
- `ADMIN`;
- `FUERA_ALCANCE`.

La clasificacion sirve para trazabilidad, UI y auditoria. No reemplaza los servicios de negocio: solo orienta que recuperadores y validaciones se activan.

## Auditoria

Cada consulta del asistente se registra en `audit_logs` con:

- usuario;
- pregunta;
- respuesta;
- intencion;
- material resuelto;
- horizonte resuelto;
- fuentes recuperadas;
- proveedor IA;
- uso de fallback;
- duracion en milisegundos.

La auditoria es no bloqueante: si el registro falla, la respuesta al usuario no se interrumpe.

Los administradores pueden consultar estos registros desde `/chat/auditoria` y desde el panel `Admin > Auditoria IA`, con filtros por intencion y uso de fallback.

El panel tambien muestra metricas agregadas de auditoria:

- total de consultas;
- consultas fuera de alcance;
- tasa de fallback;
- latencia promedio y p95;
- consultas por intencion;
- usuarios unicos.

## Medicion de determinismo

El endpoint `/chat/auditoria/determinismo` calcula determinismo del RAG sobre consultas repetidas. La pregunta se normaliza y se comparan campos criticos de recuperacion:

- `tipo_intencion`;
- `material_resuelto`;
- `horizonte_resuelto`;
- `fuentes_recuperadas`;
- `contexto_usado`;
- `fallback_usado`.

El score de cada grupo es:

```text
campos_estables / campos_evaluados
```

Esto separa dos cosas:

- determinismo del RAG operativo: recuperacion, fuentes, material, horizonte e intencion;
- variabilidad aceptable del LLM: redaccion final de la respuesta.

Si la misma pregunta mantiene los campos criticos estables, el sistema puede defender que el RAG es deterministico aunque el texto natural cambie.

## Bateria canonica

El endpoint `/chat/auditoria/determinismo/canonicas` evalua una bateria fija de consultas de referencia sin mezclar preguntas historicas arbitrarias. La bateria cubre:

- historico de precios;
- forecast;
- recomendacion;
- presupuestacion;
- catalogo;
- administracion.

La idea es separar la medicion de estabilidad del RAG operativo de la variacion acumulada en la auditoria real.

## Diferencia con un chatbot generico

El modelo generativo no decide precios, forecast ni recomendaciones. El backend primero recupera o calcula contexto y luego el modelo redacta una respuesta breve sobre esos datos.

Si falta informacion en el backend, la respuesta debe indicar el dato faltante en lugar de inventarlo.

## Diferencia con un RAG documental

Un RAG documental seria util para consultar textos largos, decisiones metodologicas o documentacion de tesis. Para precios, forecast y recomendaciones, usar documentos o embeddings como fuente principal seria menos confiable que consultar servicios y tablas estructuradas.

Por eso el MVP adopta un enfoque hibrido futuro:

- RAG operativo estructurado para datos vivos y calculos de negocio;
- RAG documental opcional para documentacion metodologica si se requiere en una etapa posterior.

## Casos de prueba manual

### Historico

```text
cual fue el ultimo precio de cemento?
```

Esperado:

- material resuelto: `Cemento Portland`;
- fuentes: `catalogo.materiales`, `precios_historicos`;
- respuesta basada en el ultimo registro disponible.

### Forecast/recomendacion

```text
me conviene comprar cemento en 6 meses?
```

Esperado:

- material resuelto: `Cemento Portland`;
- horizonte: `6`;
- fuentes: `catalogo.materiales`, `purchase_recommendations`;
- respuesta con decision y confiabilidad calculadas.

### Alias

```text
cuanto sale klaukol?
```

Esperado:

- material resuelto: `Pastina`;
- fuentes historicas si hay precios disponibles.

### Presupuestacion

```text
necesito comprar 500 kg de cemento en 6 meses
```

Esperado:

- se abre el panel de validacion editable;
- el usuario confirma cantidad, material, fase, horizonte y riesgo;
- la propuesta muestra totales, decision y trazabilidad.
