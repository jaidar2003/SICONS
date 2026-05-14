# DISENO_EPICA_6

## Propósito del documento

Este documento resume el diseno funcional inicial de la Epica 6 de `BuildWise`, orientada a la asistencia conversacional. Su objetivo es exponer capacidades del sistema en lenguaje natural sin reemplazar la logica de negocio ya existente.

## Marco general

- la capa conversacional no calcula desde cero;
- consume datos, forecast y reglas ya resueltas en backend;
- el LLM debe actuar como interfaz y sintetizador, no como fuente unica de verdad.

---

## HU25 - Consultar precios y proyecciones en lenguaje natural

### Objetivo

Permitir preguntas abiertas sobre precios y proyecciones sin navegar manualmente por tablas y graficos.

### Salida esperada

- respuesta textual clara;
- uso de datos reales del sistema;
- referencia al material y horizonte consultado.

---

## HU26 - Preguntar por un material especifico

### Objetivo

Permitir consultas directas del tipo “cuanto podria costar X en 6 meses”.

### Salida esperada

- respuesta puntual por material;
- precio actual y proyectado;
- variacion esperada.

---

## HU27 - Solicitar explicaciones sobre la proyeccion

### Objetivo

Permitir que el sistema explique de manera comprensible en que se basa una estimacion.

### Salida esperada

- explicacion resumida;
- horizonte usado;
- referencia a metricas de error o confiabilidad cuando corresponda.

---

## HU27b - Conversar con el asistente y recibir una recomendacion accionable de compra

### Objetivo

Permitir que el usuario consulte en lenguaje natural una decision de compra y reciba una respuesta accionable basada en servicios internos de forecast, comparacion economica, recomendacion y optimizacion.

### Salida esperada

- accion sugerida: comprar ahora, postergar o compra parcial;
- ahorro o sobrecosto estimado;
- nivel de confianza o advertencia;
- referencia a los supuestos usados.

---

## Criterio de integracion

La implementacion minima de esta epica deberia:

- consultar servicios internos ya existentes;
- armar contexto estructurado;
- llamar al modelo de chat;
- devolver una respuesta explicada sin inventar datos no presentes.

No corresponde usar esta capa para sustituir:

- calculos de forecast;
- reglas de compra;
- optimizacion presupuestaria.

---

## Ubicación sugerida en la arquitectura

### application

- orquestador conversacional;
- armado de contexto y prompts.

### infrastructure

- cliente del proveedor LLM;
- integracion con `OPENAI_BASE_URL`, `OPENAI_API_KEY` y `OPENAI_MODEL`.

### interfaces

- endpoint de chat o consulta conversacional;
- schema de pregunta y respuesta.
