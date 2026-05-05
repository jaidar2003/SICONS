# Diseno de Integracion entre Selector de Modelos y Forecast Service

## Objetivo

Definir como `forecast_service.py` deberia consumir en una etapa futura la seleccion de modelo por material y horizonte provista por `app/modules/pricing/application/model_selector.py`, sin activar todavia ese comportamiento en produccion y sin modificar la logica actual de `Prophet`.

El alcance de este documento es contractual y arquitectonico. No introduce cambios de codigo productivo ni altera el flujo actual del endpoint.

## 1. Proposito de la integracion

La integracion busca que SICONS deje de depender implicitamente de una configuracion unica de forecast y pueda resolver, de forma explicita y trazable, que modelo recomendado usar para cada combinacion de `material_id` y `horizonte_meses`.

El selector no reemplaza a `Prophet`. Su responsabilidad es definir que configuracion de `Prophet` corresponde aplicar segun la evidencia documentada.

En otras palabras:

- `Prophet` sigue siendo el motor de forecasting;
- el selector define que variante recomendada de ese motor usar;
- `forecast_service` ejecuta la variante resuelta sin absorber logica metodologica dispersa.

## 2. Punto de integracion

La llamada a `resolve_model_selection(material_id, horizonte_meses)` deberia ocurrir despues de validar que el material existe y antes de construir o entrenar el modelo concreto de forecast.

Conceptualmente, el orden futuro del flujo seria:

1. cargar material;
2. construir serie mensual y dataset base;
3. resolver seleccion de modelo con `material_id` y `horizonte_meses`;
4. traducir esa seleccion a configuracion efectiva de `Prophet`;
5. validar disponibilidad de regresores requeridos;
6. ejecutar backtesting y forecast con la configuracion resuelta;
7. devolver forecast mas metadatos de seleccion.

Esto implica que `forecast_service.py` deberia recibir desde el selector, como minimo:

- `modelo`;
- `regresores`;
- `mape`;
- `mae`;
- `folds`;
- `confiabilidad`;
- `origen_decision`;
- `justificacion`;
- `no_calibrado`.

No corresponde que `forecast_service` deduzca esas decisiones por su cuenta.

## 3. Datos que debe devolver el forecast

La respuesta futura del forecast deberia incluir, ademas de los puntos proyectados y metricas operativas del request, un bloque explicito de seleccion de modelo.

Campos recomendados:

- `modelo_usado`
- `regresores_usados`
- `mape_referencia`
- `mae_referencia`
- `folds_referencia`
- `confiabilidad_relativa`
- `origen_decision`
- `justificacion`
- `no_calibrado`

La idea no es reemplazar las metricas operativas del request actual, sino complementarlas con metadatos metodologicos de la politica de seleccion.

Ejemplo conceptual:

```json
{
  "metricas": {
    "mae": 11.32,
    "mape": 7.74
  },
  "forecast": [],
  "model_selection": {
    "modelo_usado": "prophet_ipim_nivel_general",
    "regresores_usados": ["ipim_nivel_general"],
    "mape_referencia": 4.98,
    "mae_referencia": 6.76,
    "folds_referencia": 9,
    "confiabilidad_relativa": "alta",
    "origen_decision": "material_horizonte",
    "justificacion": "Configuracion recomendada para Cemento Portland a 3 meses segun benchmark documentado.",
    "no_calibrado": false
  }
}
```

## 4. Mapeo entre modelo seleccionado y configuracion real de Prophet

Los nombres simbolicos del selector no deben ejecutarse directamente. Deben traducirse a una configuracion real y controlada del pipeline actual.

Ejemplos documentados:

- `prophet_ipim_nivel_general` -> regresores `["ipim_nivel_general"]`
- `prophet_blue_ipc` -> regresores `["dolar_blue", "ipc"]`
- `prophet_ipc` -> regresores `["ipc"]`
- `prophet_base` -> sin regresores

Ese mapeo debe vivir en una capa explicita de traduccion entre politica de seleccion y runtime de forecasting. No deberia quedar disperso en condicionales ad hoc dentro de funciones de entrenamiento.

### Regla metodologica

- no se deben inventar regresores;
- no se deben agregar regresores por similitud semantica;
- no se debe asumir que un modelo con dos regresores puede correrse con uno solo sin decision explicita.

Si falta un regresor requerido, el sistema deberia:

1. intentar un fallback controlado definido por politica;
2. o devolver una advertencia controlada si no existe fallback valido;
3. pero no romper silenciosamente ni cambiar de configuracion de manera opaca.

## 5. Fallbacks

La integracion futura debe respetar el orden de fallback ya definido por el selector, pero ademas contemplar faltantes operativos de regresores.

### Caso 1: no existe seleccion exacta para material + horizonte

Debe usarse la seleccion por material devuelta por el selector.

Consecuencias:

- el forecast sigue siendo servible;
- la salida queda marcada con `no_calibrado = true`;
- la justificacion debe dejar claro que no existe calibracion exacta para ese horizonte.

### Caso 2: existe seleccion por material, pero no para ese horizonte

Operativamente es el mismo caso anterior, pero conviene explicitarlo porque es uno de los riesgos metodologicos principales: no mezclar evidencia exacta de `3` meses con una afirmacion fuerte sobre `6` o `12` meses.

La respuesta debe exponer que se reutiliza la mejor configuracion conocida del material sin afirmar calibracion puntual para ese horizonte.

### Caso 3: no existe ninguna seleccion para el material

Debe aplicarse `prophet_base` sin regresores, marcado como `no_calibrado`.

Consecuencias:

- se preserva operatividad;
- no se fuerza una seleccion artificial;
- se evita presentar el resultado como recomendacion metodologica consolidada.

### Caso 4: faltan datos de regresores

Este caso debe separarse de la falta de calibracion. Puede existir una seleccion valida, pero no disponibilidad operativa de datos para ejecutarla.

Politica recomendada:

1. detectar de forma explicita que faltan regresores requeridos;
2. intentar fallback a una configuracion alternativa permitida por politica;
3. si no existe fallback seguro, responder con advertencia controlada o degradar a `prophet_base` marcado como `no_calibrado`.

La decision no debe quedar implicita ni silenciosa.

### Caso 5: el selector devuelve `prophet_base` `no_calibrado`

`forecast_service` debe aceptar esa salida como un caso legitimo de fallback operativo. No corresponde tratarlo como error.

La respuesta futura deberia exponerlo claramente para que quien consuma el endpoint sepa que el sistema no conto con una calibracion metodologica especifica para ese material u horizonte.

## 6. Compatibilidad hacia atras

La integracion no debe activarse de golpe.

La recomendacion es introducir un `feature flag` o parametro interno equivalente, por ejemplo:

```python
usar_selector_modelo = False
```

Mientras ese flag este desactivado:

- `forecast_service.py` mantiene su comportamiento actual;
- no cambia la configuracion productiva vigente;
- el endpoint sigue devolviendo la misma semantica actual.

Cuando el flag se active en ambientes de prueba:

- el selector resuelve la politica de modelo;
- el service traduce esa politica a runtime;
- la respuesta expone trazabilidad adicional.

Esto permite una migracion por etapas:

1. contrato definido;
2. integracion interna implementada pero desactivada;
3. validacion en tests y ambiente controlado;
4. activacion gradual.

## 7. Tests necesarios antes de activar

Antes de encender el selector en produccion, deberian existir pruebas para estos escenarios:

- forecast con selector desactivado mantiene exactamente el comportamiento actual;
- forecast con selector activado usa el modelo recomendado para `material_id + horizonte_meses`;
- material sin calibracion cae a `prophet_base` y queda marcado como `no_calibrado`;
- faltante de regresor requerido no rompe el endpoint y produce fallback o advertencia controlada;
- la respuesta expone `modelo`, `regresores`, metricas de referencia y `justificacion`;
- no se modifica la logica actual de normalizacion por `kg` ni las equivalencias comerciales ya existentes.

Tambien conviene cubrir:

- que no se mezclen metricas de referencia de un horizonte con otro distinto;
- que la ausencia de `folds` se exprese de forma valida cuando corresponda;
- que los fallbacks no borren trazabilidad sobre el origen de la decision.

## 8. Riesgos y mitigaciones

### Riesgo de hardcodear decisiones experimentales

Si `forecast_service.py` absorbe condicionales sobre materiales, modelos y regresores, la politica metodologica vuelve a quedar acoplada al runtime.

Mitigacion:

- mantener selector aislado;
- mantener mapping declarativo;
- documentar el contrato de integracion antes de activarlo.

### Riesgo de cambiar comportamiento productivo sin validacion

Activar el selector directamente podria alterar resultados actuales sin una etapa controlada de pruebas.

Mitigacion:

- `feature flag`;
- tests de backward compatibility;
- activacion gradual.

### Riesgo de mezclar metricas de distintos horizontes

Una configuracion buena a `3` meses no debe presentarse automaticamente como calibrada a `6` o `12`.

Mitigacion:

- uso explicito de `horizonte_meses` en el selector;
- marcado `no_calibrado` en fallbacks por material;
- justificacion visible en la respuesta.

### Riesgo de usar regresores no disponibles

El modelo recomendado puede depender de un regressor que aun no este disponible o alineado en tiempo.

Mitigacion:

- validacion previa de regresores requeridos;
- fallback controlado;
- advertencia explicita cuando haya degradacion.

## 9. Trabajo futuro

- migrar el mapping declarativo a una tabla parametrizable;
- versionar decisiones de modelo;
- registrar fecha de evaluacion de cada recomendacion;
- automatizar benchmark periodico por material y horizonte;
- mostrar confiabilidad del modelo y estado de calibracion en frontend.

## Cierre metodologico

La integracion propuesta no cambia la naturaleza del forecast: sigue siendo un sistema basado en `Prophet`.

Lo que cambia es la forma de decidir y exponer la configuracion aplicada:

- la politica de seleccion deja de estar implicita;
- el runtime deja de hardcodear decisiones experimentales;
- la respuesta del forecast gana trazabilidad metodologica;
- la activacion puede hacerse de manera controlada y reversible.
