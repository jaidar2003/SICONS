# Glosario funcional

## Horizonte

Cantidad de meses hacia adelante que se usa para proyectar precios o evaluar una decision.

Ejemplo:

```text
Horizonte 3 meses = usar el precio proyectado al tercer mes futuro.
```

## Escenario de costos

Horizonte elegido dentro del planificador de costos multi-material. Permite evaluar el costo proyectado de varios materiales a un mes futuro comun.

No necesariamente coincide con el horizonte global del forecast.

## Precio actual

Ultimo precio observado valido en la serie historica usada por el sistema. Para forecast se excluyen fechas futuras respecto del dia de calculo.

## Precio proyectado

Precio estimado por el modelo de forecast para un horizonte futuro.

## MAPE

Error porcentual absoluto medio.

Indica, en promedio, cuanto se equivoco el modelo en terminos porcentuales durante el backtesting.

```text
MAPE = promedio(|real - predicho| / real * 100)
```

Un `MAPE 5%` significa que el error promedio fue aproximadamente 5%.

## MAE

Error absoluto medio.

Indica, en promedio, cuanto se equivoco el modelo en unidades monetarias o de precio normalizado.

```text
MAE = promedio(|real - predicho|)
```

## Folds

Cortes temporales usados para evaluar el modelo.

Cada fold entrena con una parte de la historia y prueba contra meses posteriores. Varios folds hacen que la metrica sea mas defendible que una sola prueba.

## Confiabilidad

Lectura metodologica de la calidad relativa del forecast para un material y horizonte.

Valores usados:

- `alta`
- `media`
- `media-baja`
- `baja`
- `no_calibrada`
- `no_disponible`

No es una probabilidad. Es una clasificacion operativa basada en metricas, calibracion y evidencia disponible.

## Criticidad

Importancia operativa del material para la decision de compra.

Valores usados:

- `alta`
- `media`
- `baja`

La criticidad afecta recomendaciones y priorizacion. Un material critico puede justificar una decision mas conservadora.

## Umbral de decision

Variacion minima necesaria para emitir una accion fuerte.

En la implementacion actual, el umbral base es `5%` cuando la confiabilidad no obliga a ser mas conservador.

Ejemplo:

```text
Variacion esperada 4.8291% < umbral 5% -> monitorear
Variacion esperada 8% >= umbral 5% -> comprar ahora si corresponde
```

El umbral evita decisiones tajantes por diferencias marginales o ruido del forecast.

## Comprar ahora

Accion recomendada cuando el precio futuro esperado sube de forma significativa y la criticidad/confianza habilitan anticipar la compra.

## Postergar

Accion recomendada cuando el precio futuro esperado baja de forma significativa y la criticidad permite esperar.

## Monitorear

Accion conservadora cuando:

- la variacion no supera el umbral;
- la confiabilidad es baja;
- el modelo no esta suficientemente calibrado;
- no hay ventaja clara entre comprar ahora y esperar.

## Compra parcial

Resultado posible en optimizacion presupuestaria. Indica comprar una parte ahora y postergar el resto, respetando presupuesto, cantidades y restricciones.

## Optimizar presupuesto

Resolver cuanto comprar ahora y cuanto postergar para varios materiales bajo un presupuesto disponible.

La implementacion usa `PuLP` para formular y resolver el problema de optimizacion.

## Anomalia

Mes cuyo precio observado se aleja del precio esperado por el detector basado en Random Forest.

Una anomalia no prueba error de carga: indica un mes que merece revision.
