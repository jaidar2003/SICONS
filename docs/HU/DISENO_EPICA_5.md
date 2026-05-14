# DISENO_EPICA_5

## Propósito del documento

Este documento define el diseno funcional inicial de la Epica 5 de `BuildWise`, orientada a la decision economica y a la optimizacion de compras. No reemplaza al `README.md` ni a `DECISIONES_TESIS.md`: su objetivo es describir de forma operativa como se estructuraria esta capa antes de implementar codigo productivo.

## Marco general

- `Prophet` sigue siendo el proveedor de precios futuros normalizados por unidad base.
- La Epica 5 no reemplaza el forecasting, sino que consume sus resultados.
- La variable principal del sistema sigue siendo `precio_promedio_normalizado`, expresada en `ARS/kg` o en la unidad base comparable que corresponda.
- Las equivalencias de bolsas de `25 kg` y `50 kg` se mantienen solo para visualizacion y comparacion comercial.
- La capa de decision economica debe ser metodologicamente interpretable y defendible para tesis.

---

## HU24 - Priorizar materiales criticos

### Objetivo

Ordenar materiales segun su urgencia relativa de compra, combinando riesgo de aumento y efecto presupuestario.

### Datos de entrada

Por cada material:

- `material_id`
- `nombre`
- `cantidad_requerida`
- `precio_actual_normalizado`
- `precio_proyectado_normalizado`
- `horizonte`
- `variacion_esperada_porcentual`

### Cálculo de impacto absoluto

El impacto absoluto estimado de postergar la compra se define como:

```text
impacto_absoluto = (precio_proyectado_normalizado - precio_actual_normalizado) * cantidad_requerida
```

Esta magnitud expresa cuanto dinero adicional implicaria postergar la compra del material en el horizonte analizado.

### Cálculo de criticidad

No corresponde combinar directamente una variacion porcentual con un impacto monetario absoluto, porque ambas magnitudes se expresan en escalas distintas. Por lo tanto, antes de construir un puntaje conjunto, ambas deben normalizarse.

Formula base:

```text
criticidad = alpha * variacion_normalizada + beta * impacto_normalizado
```

Donde:

- `variacion_normalizada` representa la variacion esperada llevada a una escala comun;
- `impacto_normalizado` representa el impacto economico absoluto en una escala comparable;
- `alpha` y `beta` son pesos configurables segun el criterio de negocio o experimental.

### Salida esperada

- ranking de materiales de mayor a menor criticidad;
- puntaje de criticidad;
- nivel cualitativo, por ejemplo `alta`, `media` o `baja`;
- explicacion funcional resumida, por ejemplo:
  - "priorizado por mayor aumento esperado";
  - "priorizado por mayor impacto presupuestario";
  - "priorizado por combinacion de riesgo e impacto".

### Explicación funcional

Esta historia no requiere inicialmente un solver. Puede resolverse con reglas de negocio y un esquema de scoring transparente, util para priorizar materiales antes de pasar a una etapa de recomendacion u optimizacion formal.

---

## HU21 - Recomendar mejor momento de compra

### Objetivo

Sugerir si conviene comprar ahora, postergar la compra o indicar que no existe una ventaja clara entre alternativas.

### Datos de entrada

- `precio_actual_normalizado`
- precios proyectados para los horizontes analizados, por ejemplo `3`, `6` y `12` meses
- `cantidad_requerida`
- criticidad del material
- metricas de error del forecast para el horizonte evaluado, especialmente `MAPE`

### Regla base

La recomendacion inicial puede estructurarse en tres salidas:

- `comprar ahora`
- `postergar`
- `sin ventaja clara`

Criterio general:

- si el costo futuro esperado es consistentemente mayor que el actual, recomendar `comprar ahora`;
- si el costo futuro esperado es menor que el actual y la diferencia es metodologicamente significativa, recomendar `postergar`;
- si la diferencia es pequena o ambigua, devolver `sin ventaja clara`.

### Umbral mínimo de decisión

La recomendacion no debe basarse en diferencias marginales, porque una parte de esa diferencia puede estar dentro del error esperable del modelo.

Por eso, debe definirse un umbral minimo de decision. Ese umbral puede relacionarse con el `MAPE` historico del horizonte analizado.

Ejemplo conceptual:

- si la diferencia esperada entre comprar ahora y postergar es menor que un umbral asociado al error historico del modelo, no corresponde emitir una recomendacion fuerte;
- en ese caso, la salida adecuada es `sin ventaja clara`.

### Salida esperada

- recomendacion final;
- horizonte asociado a la recomendacion;
- diferencia economica estimada;
- diferencia porcentual estimada;
- explicacion resumida del criterio aplicado;
- indicacion de si la recomendacion supera o no el umbral minimo de decision.

### Criterio de aceptacion literal

`HU21` se considera completa cuando, para `Cemento Portland`, `Pastina` y `Membrana Megaflex`, la salida indica una accion concreta (`comprar ahora`, `postergar` o `sin ventaja clara`) junto con impacto en ARS, impacto porcentual, horizonte, `MAPE` y umbral de decision aplicado.

---

## HU22 - Comparar estrategias de compra

### Objetivo

Comparar alternativas simples de compra para identificar cual minimiza el costo esperado bajo un conjunto acotado de escenarios.

### Estrategias mínimas

- `100% ahora`
- `100% a futuro`
- `50% ahora + 50% a futuro`

### Fórmulas de costo esperado

Sea:

- `Q` la cantidad requerida;
- `P_actual` el precio actual normalizado;
- `P_futuro` el precio proyectado normalizado para el horizonte elegido.

Entonces:

```text
Costo_100_ahora = Q * P_actual
Costo_100_futuro = Q * P_futuro
Costo_mixto = 0.5 * Q * P_actual + 0.5 * Q * P_futuro
```

Si mas adelante se agregan proporciones distintas, la expresion puede generalizarse sin modificar el criterio base.

### Salida esperada

- tabla comparativa por estrategia;
- costo total esperado por estrategia;
- diferencia absoluta contra la estrategia base;
- diferencia porcentual;
- estrategia de menor costo.

### Criterio para seleccionar la estrategia más barata

La estrategia recomendada sera inicialmente aquella con menor costo esperado, siempre que la diferencia frente a las restantes supere el umbral minimo de decision definido para evitar recomendaciones basadas en ruido o diferencias metodologicamente irrelevantes.

### Criterio de aceptacion literal

`HU22` se considera completa cuando, para cada producto MVP y un horizonte elegido, se expone una tabla o payload con las tres estrategias minimas, costo esperado, diferencia ARS/%, estrategia ganadora y lectura de si la ventaja es significativa o marginal.

---

## HU23 - Optimización con presupuesto usando PuLP

### Alcance

Esta historia debe implementarse despues de `HU24`, `HU21` y `HU22`, una vez consolidadas las reglas base de criticidad, recomendacion y comparacion de estrategias.

### Rol de Prophet

`Prophet` sigue siendo el proveedor de precios futuros normalizados. La optimizacion no reemplaza el forecasting: utiliza sus resultados como insumo para la toma de decisiones.

### Herramienta adoptada

`PuLP` queda adoptado como primera implementacion de optimizacion para esta historia por su adecuacion al problema actual, que puede formularse de manera lineal con restricciones explicitas de presupuesto, cantidades requeridas y no negatividad.

En la formulacion continua vigente, el problema se apoya en una estructura de programacion lineal interpretable y defendible metodologicamente. Dicho de forma simple, esta capa equivale a resolver un problema tipo simplex sobre una funcion objetivo y restricciones transparentes, sin introducir todavia complejidad combinatoria innecesaria.

`OR-Tools` queda reservado como alternativa futura para escenarios con mayor complejidad combinatoria, por ejemplo lotes enteros obligatorios, multiples proveedores, varias ventanas temporales o restricciones logisticas mas ricas.

### Variables de decisión

Para cada material `i`:

- `x_ahora_i`: cantidad a comprar ahora
- `x_futuro_i`: cantidad a postergar

Con la relacion:

```text
x_ahora_i + x_futuro_i = cantidad_requerida_i
```

### Función objetivo

Minimizar el costo total esperado:

```text
minimizar Σ(precio_actual_i * x_ahora_i + precio_proyectado_i * x_futuro_i)
```

### Restricciones mínimas

- presupuesto disponible:

```text
Σ(precio_actual_i * x_ahora_i) <= presupuesto_disponible
```

- cantidades requeridas:

```text
x_ahora_i + x_futuro_i = cantidad_requerida_i
```

- no negatividad:

```text
x_ahora_i >= 0
x_futuro_i >= 0
```

- minimos por criticidad, si corresponde:

```text
x_ahora_i >= porcentaje_minimo_i * cantidad_requerida_i
```

Esta ultima restriccion aplica solo cuando se quiera forzar una compra minima inmediata para materiales considerados criticos.

### Salida esperada

- presupuesto utilizado y presupuesto restante;
- cantidad a comprar ahora y cantidad postergada por material;
- costo inmediato por material;
- costo futuro estimado por material;
- estado de factibilidad de la solucion;
- explicacion breve de la asignacion.

### Criterio de aceptacion literal

`HU23` se considera completa cuando la optimizacion respeta presupuesto, cantidades requeridas, no negatividad y, si aplica, minimos por criticidad. La evidencia minima debe incluir al menos un caso donde el presupuesto sea restrictivo y el resultado no exceda el limite disponible.

---

## HU28 - Optimizar presupuesto de compra con criticidad y forecast

### Objetivo

Ingresar un presupuesto total, un horizonte de compra y una lista de materiales con cantidades y criticidad para obtener una recomendacion operativa que asigne mejor el gasto disponible.

### Datos de entrada

Por cada material:

- `material_id`
- `cantidad_objetivo`
- `criticidad`

Ademas:

- `presupuesto_total`
- `horizonte_meses`

### Resultado esperado

- presupuesto utilizado;
- presupuesto restante;
- cantidad recomendada a comprar ahora por material;
- costo estimado por material;
- ahorro estimado por criticidad;
- advertencias si la confiabilidad del forecast es baja.

### Criterio funcional

La optimizacion no reemplaza la recomendacion simple ni la comparacion de estrategias. Se apoya en ellas y las eleva a una decision mas operativa: no solo indica si conviene comprar, sino como asignar el presupuesto entre materiales segun criticidad y ahorro esperado.

### Estado de implementacion

La capa de backend expone la ruta `/compras/optimizar-presupuesto`. La salida incluye asignacion por material, cantidad recomendada a comprar ahora, cantidad a postergar, presupuesto utilizado/restante, impacto economico estimado, criticidad, confianza y advertencias.

### Criterio de aceptacion literal

`HU28` se considera completa cuando la decision presupuestaria integra criticidad, forecast y restriccion de presupuesto en una unica salida accionable. Para los tres productos MVP, debe indicar que comprar ahora, que postergar, cuanto presupuesto consume, que impacto economico espera y que advertencias de confianza aplican.

---

## HU28b - Generar recomendacion operativa trazable

### Objetivo

Consolidar en una unica salida la decision de compra recomendada para una obra o seleccion de materiales, integrando forecast, comparacion economica, criticidad, presupuesto disponible, confianza del modelo y supuestos usados.

Esta HU funciona como cierre del DSS. No reemplaza `HU21`, `HU22`, `HU23` ni `HU28`: las consume y ordena en una respuesta final orientada a decision.

### Historia de usuario

Como responsable de compras, quiero recibir una recomendacion operativa trazable basada en forecast, impacto economico, criticidad y presupuesto, para saber que materiales comprar ahora, cuales postergar y por que.

### Datos de entrada

- materiales seleccionados;
- cantidades requeridas por material;
- presupuesto disponible;
- horizonte de decision;
- criticidad o prioridad operativa por material;
- tolerancia minima para emitir recomendacion, si aplica.

### Resultado esperado

- accion recomendada por material: `COMPRAR_AHORA`, `POSTERGAR` o `COMPRA_PARCIAL`;
- cantidad recomendada a comprar ahora;
- cantidad recomendada a postergar;
- presupuesto utilizado y presupuesto restante;
- impacto economico estimado en ARS y porcentaje;
- fecha de calculo;
- nivel de confianza o advertencia asociada al forecast;
- supuestos usados para la decision;
- explicacion breve de por que se recomienda esa accion.

### Criterio funcional

La salida debe permitir tomar una decision sin obligar al usuario a reconstruir manualmente el razonamiento desde multiples graficos o tablas. El sistema puede seguir mostrando analisis historico, forecast y comparaciones, pero esta HU exige una conclusion operativa consolidada.

### Criterio de aceptacion literal

`HU28b` se considera completa cuando, para `Cemento Portland`, `Pastina` y `Membrana Megaflex`, el sistema entrega una recomendacion unica y trazable que indique que comprar ahora, que postergar, cuanto presupuesto consume, que ahorro o sobrecosto estima, que confianza tiene la recomendacion y que supuestos se aplicaron.

### Evidencia de implementacion

- Endpoint: `/compras/recomendacion-operativa`.
- Test: `test_endpoint_recomendacion_operativa_consolida_decision_trazable`.
- Salida: `fecha_calculo`, `decision_resumen`, detalle por material, `supuestos` y `advertencias`.

---

## Ubicación sugerida en la arquitectura

### domain

- reglas de criticidad;
- reglas de recomendacion;
- formulas de comparacion de estrategias;
- definicion conceptual de restricciones de negocio.

### application

- casos de uso para priorizar materiales;
- recomendar momento de compra;
- comparar estrategias;
- orquestar la optimizacion presupuestaria con `PuLP`.

### interfaces

- endpoints o handlers para exponer ranking, recomendaciones, comparaciones y resultados de optimizacion;
- schemas de entrada y salida para frontend.

### infrastructure

- integracion con el solver cuando se implemente `PuLP`;
- adaptadores necesarios para cargar datos agregados de forecast y materiales.

---

## Tests mínimos

- la criticidad ordena correctamente materiales segun el puntaje calculado;
- recomienda comprar ahora cuando el futuro es mas caro y la diferencia es significativa;
- recomienda postergar cuando el futuro es mas barato y supera el umbral;
- devuelve `sin ventaja clara` cuando la diferencia es marginal;
- la estrategia escalonada calcula correctamente su costo esperado;
- el sistema maneja empates sin producir recomendaciones arbitrarias;
- en la etapa de optimizacion, las cantidades respetan presupuesto, no negatividad y demanda total.

---

## Nota de implementación

Este documento define una secuencia metodologica recomendable:

1. implementar `HU24`, `HU21` y `HU22` con reglas simples y criterios interpretables;
2. validar esas reglas en el producto y en la documentacion metodologica;
3. incorporar `HU23` con `PuLP` una vez que el problema de optimizacion este claramente definido.
