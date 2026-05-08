# DISENO_EPICA_1

## Propósito del documento

Este documento resume el diseno funcional de la Epica 1 de `BuildWise`, orientada a la gestion y preparacion de datos. Su objetivo es dejar claro que informacion entra al sistema, como se organiza y que condiciones minimas debe cumplir para ser util en analisis y forecasting.

## Marco general

- la calidad del sistema depende primero de la calidad del dato;
- la unidad comparable sigue siendo `precio_promedio_normalizado`;
- la trazabilidad de fuente y fecha es obligatoria;
- esta epica sostiene al resto del producto.

---

## HU1 - Registrar precios historicos de materiales

### Objetivo

Permitir registrar precios historicos con fecha, fuente, material y presentacion para construir una base confiable de analisis.

### Datos minimos

- material
- presentacion
- fecha
- precio original
- precio normalizado
- fuente
- observaciones

### Salida esperada

- registro persistido;
- validaciones basicas de consistencia;
- trazabilidad de origen.

---

## HU2 - Consultar historial de precios de un material

### Objetivo

Permitir consultar la serie historica de un material para revisar su evolucion temporal.

### Salida esperada

- listado ordenado por fecha;
- posibilidad de ver precio original y normalizado;
- soporte para filtros posteriores.

---

## HU3 - Normalizar precios segun una unidad comparable

### Objetivo

Expresar precios en una unidad base comun para comparar materiales aun cuando cambie la presentacion comercial.

### Regla general

```text
precio_normalizado = precio_original / cantidad_base
```

### Salida esperada

- valor comparable entre presentaciones;
- soporte correcto para forecast y comparaciones.

---

## HU4 - Seleccionar distintos materiales para su analisis

### Objetivo

Permitir trabajar con un material puntual o comparar varios segun el flujo funcional.

### Salida esperada

- seleccion por material;
- soporte para analisis individual y comparativo.

---

## HU5 - Filtrar datos por periodo

### Objetivo

Permitir limitar el analisis a un rango temporal para observar tendencias o cambios en una ventana concreta.

### Salida esperada

- filtros `desde` y `hasta`;
- consistencia entre tabla, grafico y serie usada.

---

## HU6 - Consultar la fuente de los datos registrados

### Objetivo

Permitir saber de donde proviene cada precio para sostener la confianza metodologica del sistema.

### Salida esperada

- fuente visible por registro;
- posibilidad de distinguir datos `REAL` y `ESTIMADO` cuando corresponda.

---

## Ubicación sugerida en la arquitectura

### domain

- reglas de normalizacion;
- validaciones de consistencia de dato.

### application

- casos de uso para alta, consulta y filtrado;
- orquestacion de trazabilidad y conversion.

### infrastructure

- persistencia de materiales, presentaciones, fuentes y precios;
- importadores y bootstrap.

### interfaces

- endpoints de carga y consulta;
- schemas de entrada y salida.
