# DISENO_EPICA_4

## Propósito del documento

Este documento resume el diseno funcional de la Epica 4 de `BuildWise`, orientada a la proyeccion de costos de obra. Su objetivo es traducir precios proyectados en impacto presupuestario concreto.

## Marco general

- esta epica consume forecasting, no lo reemplaza;
- la unidad base sigue siendo el precio normalizado;
- las salidas deben ser economicamente legibles para el comprador.

---

## HU16 - Proyectar el costo futuro segun la cantidad necesaria

### Objetivo

Permitir calcular cuanto costaria una cantidad requerida si se compra en un horizonte futuro.

### Formula base

```text
costo_futuro = precio_proyectado_normalizado * cantidad_requerida
```

---

## HU17 - Comparar el costo de comprar ahora versus comprar despues

### Objetivo

Permitir contrastar costo actual y costo futuro para decidir el mejor momento de compra.

### Salida esperada

- costo actual;
- costo futuro;
- diferencia absoluta;
- diferencia porcentual.

---

## HU18 - Simular escenarios de compra

### Objetivo

Permitir evaluar distintos horizontes o momentos de compra para dimensionar impacto presupuestario.

### Salida esperada

- escenarios por horizonte;
- comparacion simple entre escenarios;
- lectura de sensibilidad temporal.

---

## HU19 - Estimar el costo futuro de varios materiales de una obra

### Objetivo

Permitir proyectar el costo total de varios materiales al mismo tiempo.

### Salida esperada

- detalle por material;
- total agregado;
- soporte para decision global.

---

## HU20 - Obtener un resumen del impacto presupuestario

### Objetivo

Devolver una lectura sintetica del aumento o ahorro esperado sobre el presupuesto.

### Salida esperada

- resumen global;
- materiales de mayor impacto;
- diferencia estimada total.

---

## Ubicación sugerida en la arquitectura

### domain

- formulas de costo e impacto.

### application

- orquestacion entre forecast y cantidades;
- agregacion de escenarios y totales.

### interfaces

- endpoints de proyeccion y simulacion;
- respuestas resumidas para frontend.
