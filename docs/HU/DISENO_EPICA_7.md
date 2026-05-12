# DISENO_EPICA_7

## Propósito del documento

Este documento define el diseno funcional inicial de la Epica 7 de `BuildWise`, orientada a la decision asistida y la operacion proactiva. Su objetivo es transformar analisis y forecast en acciones concretas de compra, con explicaciones defendibles y foco en el MVP vigente.

## Marco general

- la Epica 7 consume resultados de las Epicas 3, 4 y 5; no reemplaza forecasting ni optimizacion;
- la salida principal debe ser accionable: recomendar que hacer, cuando hacerlo y por que;
- toda recomendacion debe exponer incertidumbre del modelo (al menos `MAPE` y umbral de decision);
- el MVP actual trabaja sobre 3 productos: `Cemento Portland`, `Pastina` y `Membrana Megaflex`;
- `HU33` queda diferida a post-MVP por falta de universo de sustitucion entre materiales.

---

## HU29 - Recomendar estrategia segun fase de obra y fecha objetivo

### Objetivo

Emitir una recomendacion de compra contextualizada por fase de obra, horizonte de uso y tolerancia al riesgo.

### Datos de entrada

- `material_id` o `material_key`;
- `fase_obra` (ejemplo: estructura, terminaciones, impermeabilizacion);
- `fecha_objetivo_uso` o `horizonte_meses`;
- `cantidad_requerida`;
- `tolerancia_riesgo` (baja, media, alta);
- precios actuales y proyectados disponibles;
- `MAPE` del horizonte evaluado.

### Regla funcional base

- si el material se usa en el corto plazo y el riesgo de aumento supera el umbral, priorizar `comprar ahora`;
- si el uso es mas lejano y no hay ventaja clara por encima del umbral, permitir `escalonar` o `postergar`;
- si la diferencia economica cae dentro del margen de error, devolver `sin ventaja clara`.

### Salida esperada

- accion recomendada (`comprar ahora`, `escalonar`, `postergar`, `sin ventaja clara`);
- horizonte de referencia;
- ahorro o sobrecosto esperado en ARS y porcentaje;
- nivel de riesgo asociado;
- justificacion resumida por fase + horizonte + error del modelo.

---

## HU30 - Explicar por que se recomienda una estrategia

### Objetivo

Hacer trazable y defendible cada recomendacion de compra con una explicacion numerica y legible.

### Datos de entrada

- recomendacion calculada en HU21/HU22/HU28/HU29;
- precio actual, precio proyectado y variacion esperada;
- impacto presupuestario estimado;
- metricas de confianza (`MAPE`, `MAE` cuando aplique);
- factores de criticidad del material.

### Contenido minimo de explicabilidad

- `que se recomienda` (accion);
- `por que` (drivers principales: variacion, impacto, criticidad, horizonte);
- `cuanto cambia` (ARS y %);
- `que tan confiable` (error del modelo y lectura cualitativa);
- `cuando revisar` (si se requiere nueva evaluacion por cambios de datos).

### Salida esperada

- bloque de explicacion estructurado y reutilizable por API y frontend;
- texto breve para usuario final;
- campos tecnicos auditables para trazabilidad.

---

## HU31 - Simular escenarios comparables (optimista/base/pesimista)

### Objetivo

Consolidar en una unica vista la comparacion de escenarios de precio y estrategia de compra para apoyar decisiones bajo incertidumbre.

### Escenarios minimos

- `optimista`;
- `base`;
- `pesimista`.

### Estrategias minimas por escenario

- `100% ahora`;
- `100% futuro`;
- `mixta 50/50`.

### Salida esperada

- tabla unificada por material y escenario;
- costo esperado por estrategia;
- mejor estrategia por escenario;
- rango de resultados (mejor caso / caso base / peor caso);
- lectura de sensibilidad para decision.

### Criterio de decision

La recomendacion final no debe depender de un unico escenario aislado. Debe considerar consistencia entre escenarios y umbral minimo para evitar decisiones por diferencias marginales.

---

## HU32 - Emitir alertas proactivas de decision

### Objetivo

Disparar alertas accionables cuando cambian condiciones relevantes para comprar o postergar.

### Disparadores minimos

- variacion de precio proyectado por encima de umbral configurable;
- deterioro de confiabilidad del forecast (suba de `MAPE`);
- cambio relevante en fuente o actualizacion brusca de precio;
- proximidad de fecha objetivo sin cobertura de compra recomendada.

### Salida esperada

- alerta con severidad (`info`, `atencion`, `critica`);
- motivo del disparo;
- accion sugerida;
- material afectado;
- timestamp y referencia de datos.

### Criterio operativo

La alerta debe invitar a una accion concreta y enlazar con la recomendacion vigente, evitando notificaciones descriptivas sin decision asociada.

---

## HU33 - Sugerir materiales sustitutos con impacto tecnico-economico

### Estado de alcance

`HU33` queda en **post-MVP**. Con el catalogo actual de 3 productos no existe universo suficiente para sustitucion tecnica entre materiales equivalentes.

### Condicion para activacion futura

Esta HU se retoma cuando exista un catalogo ampliado por familias equivalentes (por ejemplo, mas de una opcion comparable por tipo de material y uso).

### Salida objetivo (post-MVP)

- alternativas tecnicas viables;
- impacto economico esperado por alternativa;
- impacto en mantenimiento/diseno;
- justificacion de trade-offs.

### Nota opcional para MVP extendido

Si se requiere una version acotada antes de ampliar catalogo, solo podria evaluarse una variante comercial del mismo material (marca/presentacion), no una sustitucion tecnica completa.

---

## Dependencias funcionales de Epica 7

- `HU21`, `HU22` y `HU28` como base de recomendacion y comparacion;
- `HU24` para criticidad de materiales;
- datos de forecast y error de Epica 3;
- vistas de costo y planificacion de Epica 4;
- la interfaz conversacional de Epica 6 puede consumir salidas de Epica 7 para respuesta accionable (`HU34`).

---

## Ubicación sugerida en la arquitectura

### domain

- reglas de decision por fase y horizonte;
- reglas de explicabilidad y trazabilidad;
- definicion de umbrales para alertas.

### application

- casos de uso de recomendacion contextual (HU29);
- orquestacion de explicabilidad (HU30);
- simulacion multi-escenario (HU31);
- evaluacion de disparadores y emision de alertas (HU32).

### interfaces

- endpoints para recomendacion contextual, explicacion y escenarios;
- endpoint o canal de alertas;
- schemas de respuesta accionable reutilizables por frontend y chat.

### infrastructure

- adaptadores para lectura de forecast, errores y fuentes;
- scheduler/eventos para chequeo periodico de alertas;
- persistencia de historial de alertas y decisiones (si aplica en etapa siguiente).

---

## Criterios minimos de validacion documental

- cada recomendacion debe devolver accion, impacto y confianza;
- los escenarios deben verse en una sola salida comparable;
- las alertas deben incluir gatillo y accion sugerida;
- `HU33` debe permanecer marcada como post-MVP mientras el catalogo siga en 3 productos;
- la epica debe poder alimentar respuestas conversacionales sin recalcular reglas fuera de backend.
