# Anomalias con Random Forest

## Objetivo

Detectar meses con comportamiento atipico en la serie historica de precios sin depender de un umbral porcentual fijo comun para todos los materiales.

La deteccion se aplica sobre la serie mensual ya normalizada. El resultado se expone en la vista de historial como meses marcados por el modelo, junto con una explicacion breve del residuo detectado.

## Por que no usar un umbral fijo

Un umbral unico, por ejemplo `8%`, es facil de explicar pero puede ser rigido:

- puede ser demasiado sensible para materiales naturalmente volatiles;
- puede ser demasiado permisivo para materiales estables;
- no aprende el patron historico propio de cada serie;
- obliga a defender un porcentaje fijo aunque los materiales tengan comportamientos distintos.

Por eso se reemplaza por una deteccion basada en `RandomForestRegressor`, que aprende un precio mensual esperado a partir del comportamiento historico del material.

## Enfoque implementado

La implementacion esta en `app/modules/pricing/application/series.py`.

Para cada material:

1. Se agrupan los precios por mes.
2. Se calcula el precio promedio mensual normalizado.
3. Se calcula la variacion porcentual contra el mes anterior.
4. Se entrena un `RandomForestRegressor` sobre la propia serie mensual.
5. El modelo estima el precio esperado para cada mes evaluable.
6. Se calcula el residuo porcentual entre precio observado y precio esperado.
7. Se mide la incertidumbre interna del modelo a partir de la dispersion de predicciones entre arboles.
8. Se marca anomalia cuando el residuo queda fuera de una banda dinamica calculada con IQR sobre los residuos del modelo y supera el margen requerido por la incertidumbre del ensemble.

## Variables usadas

El modelo usa features simples y trazables:

- indice temporal del mes dentro de la serie;
- mes calendario;
- precio del mes anterior;
- variacion porcentual anterior;
- promedio movil corto de precios previos;
- rezagos de precio y variacion;
- dispersion robusta reciente;
- desvio contra tendencia local y referencia estacional;
- cantidad de registros del mes.

Estas variables permiten capturar tendencia, estacionalidad simple, inercia de precio y robustez de la muestra mensual.

## Regla de marca

El modelo no marca anomalias por superar un porcentaje fijo.

La regla es:

```text
residuo porcentual observado > limite dinamico de residuos
```

El limite dinamico se calcula con:

```text
Q3 + 1.5 * IQR
```

donde `IQR` es el rango intercuartil de los residuos porcentuales.

Ese limite se vuelve mas conservador si el Random Forest muestra alta dispersion entre sus arboles. En terminos practicos, si el modelo no tiene un precio esperado estable, el sistema exige un residuo mayor antes de marcar una alerta.

Ademas del residuo, la marca requiere evidencia complementaria: variacion mensual atipica, desvio contra tendencia local o desvio contra una referencia estacional cuando existe. Esto reduce falsos positivos por cambios esperables de mercado.

## Series cortas

Si la serie tiene menos de 6 meses, no se entrena Random Forest y no se fuerzan anomalias.

Esto evita marcar puntos atipicos sin evidencia suficiente. En esos casos, la salida conserva la serie y deja `es_anomalia = false`.

## Salida

Cada punto mensual puede incluir:

- `es_anomalia`: indica si el mes fue marcado como atipico;
- `severidad_anomalia`: clasifica la magnitud relativa de la desviacion detectada;
- `score_anomalia`: cantidad de senales que respaldan la alerta;
- `confianza_anomalia`: confianza porcentual ajustada por evidencia e incertidumbre del modelo;
- `motivo_anomalia`: describe la deteccion, incluyendo precio esperado, residuo porcentual, incertidumbre, variacion mensual y senales activadas.

Ejemplo conceptual:

```text
Anomalia detectada por Random Forest: precio esperado 120.0000, residuo 35.0000%, incertidumbre modelo 4.2000%, variacion mensual 41.6667% y score 3/4
```

## Limitaciones

Random Forest detecta atipicidad, no explica causalidad.

Una anomalia puede deberse a:

- cambio real de proveedor;
- cambio de presentacion;
- error de carga;
- shock de mercado;
- dato estimado inconsistente;
- salto normal en una serie muy volatil.

La marca debe interpretarse como una alerta para revisar el mes, no como una prueba automatica de error.

La severidad no reemplaza la revision humana. Solo ayuda a priorizar que meses merecen atencion primero: una anomalia `alta` sugiere una desviacion mucho mas fuerte respecto de la banda aprendida por el modelo, mientras que una `leve` esta apenas por encima del umbral dinamico.

## Criterio de defensa

La ventaja metodologica frente al umbral fijo es que el sistema aprende el comportamiento historico del material y evalua el residuo contra una banda propia de la serie.

Esto permite decir:

```text
La anomalia no se define por un porcentaje arbitrario, sino por la distancia entre el precio observado y el precio esperado por un modelo entrenado sobre el patron historico del material.
```
