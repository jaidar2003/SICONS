# DISENO_EPICA_3

## Propósito del documento

Este documento resume el diseno funcional de la Epica 3 de `BuildWise`, orientada a la prediccion de precios. Es la capa que transforma series historicas en estimaciones futuras defendibles.

## Marco general

- la variable principal es `precio_promedio_normalizado`;
- la metrica principal de comparacion es `MAPE`;
- `MAE`, cantidad de folds y estabilidad entre folds se usan como soporte;
- no corresponde elegir modelo solo por inspeccion visual.

---

## HU11 - Ingresar precio actual y horizonte para estimar precio futuro

### Objetivo

Permitir que el usuario ingrese un precio actual de referencia y un horizonte temporal para estimar el precio futuro y comparar ese valor contra la proyeccion del sistema.

Esta entrada no registra un precio historico, no requiere rol admin, no debe contaminar la serie historica ni reemplazar el precio vigente registrado. Funciona como simulacion puntual para responder la historia literal sin abrir permisos de carga de precios a usuarios no admin.

### Datos de entrada

- material
- horizonte
- precio actual de referencia ingresado por el usuario
- serie historica mensual comparable

### Salida esperada

- precio proyectado;
- diferencia absoluta entre precio de referencia y precio proyectado;
- diferencia porcentual entre precio de referencia y precio proyectado;
- serie de soporte utilizada;
- referencia al modelo aplicado;
- aclaracion de que el precio de referencia fue usado solo para la comparacion de la simulacion.

### Criterio de aceptacion literal

La historia se considera completa al pie de la letra cuando existe un formulario o endpoint que acepte `material`, `horizonte_meses` y `precio_referencia`, y devuelva la estimacion futura con impacto ARS/% para los tres productos MVP sin persistir ese precio como dato historico.

---

## HU12 - Visualizar la proyeccion futura junto al historico

### Objetivo

Mostrar en un mismo flujo la serie historica y la proyeccion para facilitar la interpretacion.

### Salida esperada

- historico observado;
- tramo proyectado;
- distincion visual entre ambos.

---

## HU13 - Obtener la variacion esperada entre precio actual y precio proyectado

### Objetivo

Permitir leer el impacto economico esperado entre el presente y el horizonte proyectado.

### Salida esperada

- diferencia absoluta;
- diferencia porcentual;
- horizonte al que corresponde.

---

## HU14 - Estimar precios a distintos horizontes temporales

### Objetivo

Permitir trabajar con escenarios de `3`, `6` y `12` meses sin tratarlos como equivalentes.

### Salida esperada

- proyeccion por horizonte;
- comparacion separada por cada horizonte.

---

## HU15 - Consultar el nivel de confianza o error del modelo

### Objetivo

Permitir interpretar la calidad de la prediccion.

### Medidas actuales

- `MAPE`
- `MAE`
- cantidad de `folds`
- efectividad informal `100 - MAPE`

---

## Ubicación sugerida en la arquitectura

### domain

- definiciones de metricas y criterios de comparacion.

### application

- construccion de dataset;
- entrenamiento y backtesting;
- seleccion y exposicion del forecast.

### infrastructure

- carga de regresores externos;
- snapshots y cache de forecast.

### interfaces

- endpoints de forecast;
- respuestas por material y horizonte.
