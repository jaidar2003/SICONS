# DISENO_EPICA_2

## Propósito del documento

Este documento resume el diseno funcional de la Epica 2 de `BuildWise`, orientada al analisis y la visualizacion. Su foco es transformar series historicas en informacion interpretable para el comprador.

## Marco general

- esta epica consume la base historica ya preparada;
- no modifica el dato base, sino que lo presenta e interpreta;
- debe priorizar claridad visual y lectura economica simple.

---

## HU7 - Visualizar precios historicos en graficos

### Objetivo

Mostrar la evolucion temporal de un material en una visualizacion simple y legible.

### Salida esperada

- grafico por fecha;
- soporte de filtros temporales;
- lectura clara de tendencia.

---

## HU8 - Comparar materiales entre si

### Objetivo

Permitir comparar materiales para identificar diferencias de comportamiento y riesgo de aumento.

### Salida esperada

- comparacion sobre unidad normalizada;
- lectura paralela de tendencias;
- soporte para analisis por material.

---

## HU9 - Identificar variaciones porcentuales de precios

### Objetivo

Mostrar cuanto vario un material entre dos puntos del tiempo en terminos porcentuales.

### Formula base

```text
variacion_pct = ((precio_final - precio_inicial) / precio_inicial) * 100
```

### Salida esperada

- variacion absoluta;
- variacion porcentual;
- periodo sobre el que se calcula.

---

## HU10 - Detectar cambios bruscos o anomalias

### Objetivo

Identificar meses o puntos con cambios atipicos que merezcan revision.

### Salida esperada

- marcas de anomalia;
- explicacion breve del cambio;
- soporte para interpretacion del grafico y la serie.

---

## Ubicación sugerida en la arquitectura

### domain

- reglas de variacion;
- criterios de anomalia.

### application

- armado de series;
- calculo de comparaciones y variaciones.

### interfaces

- endpoints de series y comparacion;
- respuestas listas para frontend.
