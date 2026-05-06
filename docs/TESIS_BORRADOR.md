# Borrador de Tesis SICONS / BuildWise

## 1. Introducción

SICONS / BuildWise es un sistema de soporte a la decisión orientado al análisis y proyección de precios de materiales de construcción. El problema que aborda es la falta de una herramienta reproducible, trazable y metodológicamente defendible para anticipar el comportamiento de precios, comparar alternativas y reducir incertidumbre en decisiones de compra.

La propuesta no consiste únicamente en visualizar series históricas. El objetivo es convertir datos de precios en una capa de análisis y forecast con criterios explícitos de selección de modelo, trazabilidad de la decisión y una base de datos reproducible para tesis.

## 2. Problema

El dominio presenta tres dificultades principales:

1. Los precios cambian con frecuencia y no todos los materiales comparten el mismo comportamiento temporal.
2. Los datos disponibles combinan fuentes heterogéneas, series reales, series híbridas y regresores externos.
3. La reproducibilidad del entorno no puede depender de archivos personales, de IDs locales accidentales ni de imports manuales no gobernados.

En particular, una implementación defendible para tesis debe distinguir entre:
- la fuente operativa de los datos;
- el extracto canónico reproducible;
- la política de forecasting;
- y la forma en que el sistema expone sus decisiones.

## 3. Objetivos

### Objetivo general

Diseñar e implementar un sistema reproducible de forecasting y soporte a la decisión para precios de materiales de construcción, con selección controlada de modelos y trazabilidad metodológica.

### Objetivos específicos

- Construir una base mínima reproducible para la tesis.
- Reforzar la reproducibilidad del bootstrap mediante artefactos versionados.
- Diferenciar el comportamiento de forecasting por material y horizonte.
- Incorporar un selector de modelos basado en una identidad estable de material.
- Mantener el comportamiento productivo por defecto sin cambios mientras el selector permanece desactivado.
- Exponer metadatos de selección y confiabilidad del forecast cuando el selector esté activo.

## 4. Alcance

El alcance del proyecto cubre:
- la capa de datos histórica;
- el bootstrap de la base;
- el forecast por material;
- la selección de configuración de modelo;
- la exposición de metadatos de decisión en la respuesta del endpoint.

Quedan fuera de este borrador, por ahora:
- la activación productiva por defecto del selector;
- la evolución completa del frontend para mostrar la selección de modelo;
- la incorporación de funcionalidades todavía documentadas como futuras, como optimización avanzada o asistentes conversacionales.

## 5. Arquitectura general

La arquitectura del sistema puede resumirse en cuatro capas:

1. **Capa de datos**
   - materiales;
   - precios históricos;
   - presentaciones comerciales;
   - fuentes operativas y fuentes canónicas;
   - regresores externos.

2. **Capa de forecasting**
   - cálculo del forecast sobre la serie mensual del material;
   - uso de modelos basados en Prophet y regresores externos.

3. **Capa de selección**
   - resolución de una política de modelo por `material_key` y horizonte;
   - fallback controlado cuando no existe calibración exacta o faltan regresores.

4. **Capa de exposición**
   - endpoint de forecast;
   - respuesta con precio proyectado;
   - metadatos de selección y trazabilidad metodológica.

El selector no reemplaza al motor de forecasting. Define qué configuración del motor debe usarse en cada caso.

## 6. Dataset y reproducibilidad

### 6.1 Dataset mínimo reproducible

El entorno de tesis requiere una base mínima reproducible que incluya:

- `Cemento Portland` con serie histórica real, densa y continua;
- `Pastina` con serie mensual híbrida, diferenciando datos reales y estimados;
- `Membrana Megaflex` con serie mensual híbrida, diferenciando datos reales y estimados;
- regresores externos:
  - `ipc`;
  - `dolar_oficial`;
  - `dolar_mayorista`;
  - `dolar_blue`;
  - `ipim_nivel_general`.

### 6.2 Fuente canónica de Cemento Portland

La serie histórica canónica de `Cemento Portland` se resuelve mediante un extracto versionado y auditable:

- `db/bootstrap/cemento_portland_historico.csv`

Ese CSV deriva de una fuente operativa real de compra y queda congelado como artefacto reproducible para el bootstrap de tesis. En el estado actual, esa decisión ya está documentada como una separación entre:
- fuente operativa de origen;
- extracto canónico versionable;
- y carga incremental posterior.

### 6.3 Bootstrap reproducible

La prioridad actual del proyecto es cerrar la reproducibilidad del entorno antes de activar el selector por defecto o expandir nuevas features.

El bootstrap objetivo debe reconstruir la base mínima con un flujo gobernado por scripts de importación y validación. La meta metodológica es que una base limpia levantada con Docker + bootstrap reproduzca el universo asumido por las mediciones y por el selector.

## 7. Forecasting

### 7.1 Enfoque

El forecasting se construye sobre series mensuales por material. No todos los materiales comparten el mismo modelo óptimo, por lo que la elección del modelo no debe ser global ni uniforme.

### 7.2 Materiales principales

Los materiales priorizados en el proyecto son:
- `Cemento Portland`;
- `Pastina`;
- `Membrana Megaflex`.

Cada uno tiene una serie con confiabilidad y comportamiento distintos. La evidencia de backtesting y medición mostró que una misma variante de Prophet no optimiza por igual a todos los materiales.

### 7.3 Unidad de interpretación

La serie técnica puede normalizarse en una unidad común para sostener comparabilidad metodológica. En `Cemento Portland`, la normalización por kilo fue necesaria para preservar continuidad cuando cambió el packaging comercial. En `Pastina` y `Membrana Megaflex`, la interpretación comercial se mantiene sobre presentaciones estables.

## 8. Selector de modelos

### 8.1 Motivación

El selector existe porque un único modelo no explica de forma adecuada todos los materiales ni todos los horizontes. Su función es resolver una política explícita de selección con respaldo metodológico.

### 8.2 Identidad estable de material

La calibración del selector no debe depender de `material_id`, porque ese valor es una identidad local de cada base y puede cambiar entre entornos. La solución adoptada es resolver internamente una `material_key` estable antes de aplicar la selección de modelo.

La entrada pública del endpoint puede seguir siendo `material_id`, pero internamente la decisión debe operar sobre:

- `material_id -> material_key -> modelo recomendado`

### 8.3 Estado actual

El selector está implementado y cableado en el backend, pero permanece apagado por defecto mediante un flag interno. Ese comportamiento conservador es correcto para no alterar el runtime productivo mientras se consolidan validación y reproducibilidad.

Cuando se activa, la respuesta puede exponer:
- `material_key`;
- modelo resuelto;
- regresores resueltos;
- `MAPE` de referencia;
- `MAE` de referencia;
- `folds`;
- confiabilidad;
- no calibrado;
- origen de decisión;
- justificación.

## 9. Reproducibilidad operativa

La reproducibilidad no es sólo un tema de documentación. Es una propiedad operacional del sistema.

Para que la tesis sea defendible, el entorno debe:
- reconstruirse sin intervención manual no gobernada;
- evitar depender de archivos personales externos;
- distinguir entre importadores históricos, importadores incrementales y fuentes canónicas;
- validar el dataset mínimo antes de considerar el entorno listo.

El proyecto ya avanza en esa dirección con:
- un CSV canónico de Cemento versionado;
- un importador canónico de Cemento;
- cargas separadas para Pastina y Membrana;
- un flujo de selector aislado detrás de flag;
- y una validación del dataset mínimo como objetivo del bootstrap.

## 10. Validación

La validación del sistema debe cubrir dos planos:

1. **Validación de datos**
   - existencia de los materiales principales;
   - continuidad mensual;
   - distinción entre datos reales y estimados;
   - disponibilidad de regresores.

2. **Validación funcional**
   - respuesta correcta del endpoint;
   - mantenimiento del comportamiento legacy cuando el selector está apagado;
   - uso de la selección por `material_key` cuando el selector está activo;
   - exposición de metadatos sin romper compatibilidad.

La validación runtime realizada hasta ahora confirma que el cableado técnico funciona, pero también evidencia que la documentación todavía contiene restos de narrativa previa al refactor.

## 11. Trabajo futuro

Quedan como pasos futuros o condicionados:

- cerrar completamente el bootstrap reproducible con validación automática;
- alinear toda la documentación con el contrato real del selector por `material_key`;
- decidir la activación progresiva del selector en ambiente controlado;
- extender la interfaz de usuario para mostrar la selección de modelo con criterio claro;
- revisar si futuras capas de optimización o asistentes conversacionales deben incorporarse al alcance de tesis o mantenerse fuera de ella.

## 12. Puntos a aclarar

Existen algunas inconsistencias documentales que conviene resolver antes de usar este borrador como versión final:

- algunos documentos todavía mencionan `import_sicons_excel` como fuente principal de Cemento, mientras que la decisión metodológica más reciente define el extracto canónico versionado `db/bootstrap/cemento_portland_historico.csv`;
- parte de la documentación del selector conserva nombres antiguos de claves o referencias históricas previas al refactor;
- `validate_minimum_dataset` existe como objetivo de bootstrap, pero su alcance debe seguir alineándose con todos los regresores que la tesis promete.

Este borrador asume el estado más actual del código y de las decisiones metodológicas, no los textos heredados que todavía no se han reescrito.

