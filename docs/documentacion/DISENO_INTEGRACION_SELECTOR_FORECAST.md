# Diseno de Integracion entre Selector de Modelos y Forecast Service

## Objetivo

Documentar la integracion controlada ya implementada entre `forecast_service.py` y la seleccion de modelo por material y horizonte provista por `app/modules/pricing/application/model_selector.py`, manteniendo desactivado por defecto ese comportamiento en produccion y sin modificar la logica base de `Prophet`.

El alcance de este documento es contractual, arquitectonico y de trazabilidad de implementacion. Registra el estado actual del backend y el criterio metodologico adoptado para su activacion futura.

## Estado actual

La integracion ya fue implementada en el backend de SICONS.

Su activacion quedo protegida por el flag interno:

```python
USAR_SELECTOR_MODELO_FORECAST = False
```

Mientras ese flag permanezca en `False`:

- el endpoint de forecast conserva el comportamiento productivo vigente;
- no cambia el modelo productivo por defecto;
- no se modifica la normalizacion por `kg`;
- no se expone ninguna dependencia nueva en frontend.

Cuando el flag se activa en un ambiente controlado:

- `forecast_service.py` recibe `material_id`, resuelve el `Material` correspondiente y deriva `material_key` desde `Material.nombre`;
- el selector se invoca con `material_key` y `horizonte_meses`;
- el sistema resuelve modelo, regresores y metadatos de referencia segun material y horizonte;
- el runtime de forecast intenta ejecutar solo los regresores efectivamente soportados por el flujo actual;
- si no hay calibracion o faltan regresores operativos, se aplica fallback controlado a `prophet_base`.

Sin embargo, la validacion runtime real dejo una salvedad de diseno relevante: aunque el cableado tecnico funciona, calibrar el selector directamente contra `material_id` es fragil entre ambientes porque ese identificador es local a cada base y no representa por si mismo una identidad metodologica estable del material.

Adicionalmente, la activacion futura del selector queda condicionada a cerrar primero la reproducibilidad del entorno. Antes de cambiar el valor por defecto del flag o de exponer `seleccion_modelo` como capacidad madura del sistema, una base limpia levantada con `Docker + bootstrap` debe poder reconstruir sin intervencion manual el dataset minimo que la tesis asume.

Ese dataset minimo reproducible debe incluir:

- `Cemento Portland` con serie historica real, densa y continua;
- `Pastina` con serie mensual hibrida, diferenciando `REAL` y `ESTIMADO`;
- `Membrana Megaflex` con serie mensual hibrida, diferenciando `REAL` y `ESTIMADO`;
- regresores `ipc`, `dolar_oficial`, `dolar_mayorista`, `dolar_blue` e `ipim_nivel_general`.

La fuente canonica correcta para la serie robusta de `Cemento Portland` ya es `db/bootstrap/cemento_portland_historico.csv`, cargado por `app/operations/bootstrap/import_cemento_canonico.py`. `import_cemento_facturas` queda reclasificado como import incremental u operativo y no debe seguir considerandose base suficiente para reproducibilidad de tesis. `import_sicons_excel` queda como mecanismo legacy o transitorio de conversion desde Excel. A su vez, `ipim_nivel_general` debe cargarse desde un snapshot local versionado, dejando la sincronizacion online solo como actualizacion opcional.

## 1. Proposito de la integracion

La integracion busca que SICONS deje de depender implicitamente de una configuracion unica de forecast y pueda resolver, de forma explicita y trazable, que modelo recomendado usar para cada material logico y `horizonte_meses`.

El selector no reemplaza a `Prophet`. Su responsabilidad es definir que configuracion de `Prophet` corresponde aplicar segun la evidencia documentada.

En otras palabras:

- `Prophet` sigue siendo el motor de forecasting;
- el selector define que variante recomendada de ese motor usar;
- `forecast_service` ejecuta la variante resuelta sin absorber logica metodologica dispersa.

Para que esa politica sea realmente portable entre ambientes, la recomendacion debe quedar asociada al material logico y no a un ID accidental del ambiente.

## 2. Identidad estable previa a la seleccion

La validacion runtime real mostro dos sintomas claros de fragilidad por identidad local:

- `Pastina` no valido con `material_id = 4` por insuficiencia de serie mensual, aunque el flujo si funciono con la serie real disponible en `material_id = 5` mediante repo controlado;
- `Membrana Megaflex` figura en la base local como `material_id = 6`, mientras que el selector estaba calibrado para `material_id = 10`.

Esto confirma que `material_id` no debe tratarse como clave metodologica de calibracion.

La solucion propuesta es mantener `material_id` como parametro externo del endpoint, pero resolver internamente:

- `material_id -> Material.nombre -> material_key -> modelo recomendado`

La seleccion deberia operar sobre:

- `material_key + horizonte_meses`

y no directamente sobre:

- `material_id + horizonte_meses`

Claves iniciales recomendadas:

- `cemento-portland`
- `pastina`
- `membrana-megaflex`

Para el MVP, la recomendacion es resolver `material_key` desde el catalogo actual mediante normalizacion controlada del nombre o slug derivado, sin migracion de base todavia. Como evolucion futura, conviene incorporar un campo persistido explicito como `codigo_material` o `clave_modelo`.

Si no se puede resolver `material_key` con suficiente confianza, el sistema deberia degradar de forma controlada a:

- `prophet_base`
- `no_calibrado = true`
- `origen_decision = "global_fallback"` o `origen_decision = "material_key_unresolved"`

## 3. Punto de integracion

La llamada a `resolve_model_selection(material_key, horizonte_meses)` ya ocurre dentro de `forecast_service.py` cuando el flag interno de selector esta activo. El service recibe `material_id` desde el endpoint, resuelve el material, deriva `material_key` y luego realiza la seleccion antes de ejecutar backtesting y forecast con la configuracion efectiva.

El flujo implementado queda, conceptualmente, en este orden:

1. cargar material;
2. construir serie mensual y dataset base;
3. resolver `material_key` estable a partir del material solicitado;
4. resolver seleccion de modelo con `material_key` y `horizonte_meses`;
5. traducir esa seleccion a configuracion efectiva de `Prophet`;
6. validar disponibilidad de regresores requeridos;
7. ejecutar backtesting y forecast con la configuracion resuelta;
8. devolver forecast mas metadatos de seleccion cuando corresponde.

En la implementacion actual, `forecast_service.py` recibe desde el selector, como minimo:

- `material_key`;
- `modelo_resuelto`;
- `regresores_resueltos`;
- `mape_referencia`;
- `mae_referencia`;
- `folds`;
- `confiabilidad`;
- `origen_decision`;
- `justificacion`;
- `no_calibrado`.

No corresponde que `forecast_service` deduzca esas decisiones por su cuenta.

## 4. Datos que devuelve el forecast cuando el selector esta activo

La respuesta del forecast puede incluir, ademas de los puntos proyectados y metricas operativas del request, un bloque explicito `seleccion_modelo`.

Campos expuestos:

- `modelo_resuelto`
- `regresores_resueltos`
- `mape_referencia`
- `mae_referencia`
- `folds`
- `confiabilidad`
- `origen_decision`
- `justificacion`
- `no_calibrado`
- `advertencia`, cuando existe degradacion operativa

La idea no es reemplazar las metricas operativas del request actual, sino complementarlas con metadatos metodologicos de la politica de seleccion.

Ejemplo conceptual:

```json
{
  "metricas": {
    "mae": 11.32,
    "mape": 7.74
  },
  "forecast": [],
  "seleccion_modelo": {
    "material_key": "cemento-portland",
    "modelo_resuelto": "prophet_ipim_nivel_general",
    "regresores_resueltos": ["ipim_nivel_general"],
    "mape_referencia": 4.98,
    "mae_referencia": 6.76,
    "folds": 9,
    "confiabilidad": "alta",
    "origen_decision": "material_horizonte",
    "justificacion": "Configuracion recomendada para Cemento Portland a 3 meses segun benchmark documentado.",
    "no_calibrado": false
  }
}
```

## 5. Mapeo entre modelo seleccionado y configuracion real de Prophet

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

## 6. Fallbacks

La integracion implementada respeta el orden de fallback ya definido por el selector y ademas contempla faltantes operativos de regresores.

### Caso 1: no existe seleccion exacta para material_key + horizonte

Debe usarse la seleccion por material devuelta por el selector.

Consecuencias:

- el forecast sigue siendo servible;
- la salida queda marcada con `no_calibrado = true`;
- la justificacion debe dejar claro que no existe calibracion exacta para ese horizonte.

### Caso 2: existe seleccion por material_key, pero no para ese horizonte

Operativamente es el mismo caso anterior, pero conviene explicitarlo porque es uno de los riesgos metodologicos principales: no mezclar evidencia exacta de `3` meses con una afirmacion fuerte sobre `6` o `12` meses.

La respuesta debe exponer que se reutiliza la mejor configuracion conocida del material sin afirmar calibracion puntual para ese horizonte.

### Caso 3: no existe ninguna seleccion para el material

Debe aplicarse `prophet_base` sin regresores, marcado como `no_calibrado`.

Consecuencias:

- se preserva operatividad;
- no se fuerza una seleccion artificial;
- se evita presentar el resultado como recomendacion metodologica consolidada.

### Caso 4: no se puede resolver material_key estable

Si el sistema no puede traducir con confianza `material_id` a una identidad estable de material, no deberia inventar una calibracion.

Politica recomendada:

1. detectar explicitamente que no se pudo resolver `material_key`;
2. degradar de forma controlada a `prophet_base`;
3. marcar `no_calibrado = true`;
4. registrar `origen_decision = "material_key_unresolved"` o usar `global_fallback` si se mantiene una semantica unica de fallback.

### Caso 5: faltan datos de regresores

Este caso debe separarse de la falta de calibracion. Puede existir una seleccion valida, pero no disponibilidad operativa de datos para ejecutarla.

Politica implementada:

1. detectar de forma explicita que faltan regresores requeridos;
2. degradar de forma controlada a `prophet_base`;
3. devolver `seleccion_modelo` con `origen_decision = fallback_regresores`, `no_calibrado = true` y una advertencia explicita.

La decision no debe quedar implicita ni silenciosa.

### Caso 6: el selector devuelve `prophet_base` `no_calibrado`

`forecast_service` debe aceptar esa salida como un caso legitimo de fallback operativo. No corresponde tratarlo como error.

La respuesta actual puede exponerlo claramente para que quien consuma el endpoint sepa que el sistema no conto con una calibracion metodologica especifica para ese material u horizonte.

## 7. Compatibilidad hacia atras

La integracion fue implementada sin activarse de golpe.

El mecanismo adoptado es un `feature flag` interno:

```python
USAR_SELECTOR_MODELO_FORECAST = False
```

Mientras ese flag este desactivado:

- `forecast_service.py` mantiene su comportamiento actual;
- no cambia la configuracion productiva vigente;
- el endpoint sigue devolviendo la misma semantica actual.

Cuando el flag se active en ambientes de prueba:

- el selector resuelve la politica de modelo;
- el service traduce esa politica a runtime;
- la respuesta expone trazabilidad adicional.

Esto mantiene una migracion por etapas:

1. contrato definido;
2. integracion interna implementada pero desactivada por defecto;
3. validacion en tests y ambiente controlado;
4. activacion gradual.

## 8. Tests verificados en la implementacion

La integracion quedo respaldada por pruebas que validan, como minimo, estos escenarios:

- forecast con selector desactivado mantiene exactamente el comportamiento actual;
- forecast con selector activado usa el modelo recomendado para `Cemento Portland`, `Pastina` y `Membrana Megaflex`;
- fallback por material cuando no existe calibracion exacta para el horizonte;
- material sin calibracion cae a `prophet_base` y queda marcado como `no_calibrado`;
- faltante de regresor requerido no rompe el endpoint y produce fallback o advertencia controlada;
- la respuesta expone `material_key`, `modelo_resuelto`, `regresores_resueltos`, metricas de referencia, confiabilidad, `origen_decision`, `justificacion` y `no_calibrado` cuando corresponde;
- no se modifica la logica actual de normalizacion por `kg` ni las equivalencias comerciales ya existentes.

Adicionalmente, se mantuvieron validaciones sobre:

- que la ausencia de `folds` se exprese de forma valida cuando corresponda;
- que los fallbacks no borren trazabilidad sobre el origen de la decision.

La bateria relevante paso correctamente al momento de registrar esta integracion.

## 9. Validacion controlada registrada

Ademas de la cobertura automatizada, se ejecuto una validacion controlada del cableado tecnico `route -> forecast_service -> resolve_model_selection -> metadata/fallback`, activando `USAR_SELECTOR_MODELO_FORECAST = True` solo en memoria durante la ejecucion.

Puntos metodologicos a dejar explicitados:

- esta validacion prueba el cableado tecnico y el contrato de respuesta del endpoint;
- no constituye una nueva medicion de backtesting ni una nueva evaluacion de precision predictiva;
- el valor persistido en `routes.py` permanecio en `False` antes y despues de la corrida;
- el `precio_proyectado` usado en esta validacion fue sintetico y no debe interpretarse como una proyeccion economica nueva;
- la normalizacion por `kg` y las equivalencias comerciales siguieron resguardadas por tests;
- no se introdujeron cambios en frontend.

Resultados observados en la validacion controlada del selector runtime:

- `Cemento Portland` resolvio `prophet_ipim_nivel_general` con regresor `ipim_nivel_general`, `MAPE 4.98`, `MAE 6.76`, `folds 9`, confiabilidad `alta` y `no_calibrado = false`.
- `Pastina` resolvio `prophet_blue_ipc` con regresores `dolar_blue` e `ipc`, `MAPE 5.00`, `MAE 120.90`, `folds 9`, confiabilidad `media` y `no_calibrado = false`.
- `Membrana Megaflex` resolvio `prophet_ipc` con regresor `ipc`, `MAPE 8.31`, `MAE 734.37`, `folds 9`, confiabilidad `media-baja` y `no_calibrado = false`.
- un material no calibrado resolvio `prophet_base`, con escenario base sin regresores externos, `no_calibrado = true` y `origen_decision = global_fallback`.
- el endpoint no se rompio y pudo exponer `seleccion_modelo` con `material_key`, `modelo_resuelto`, `regresores_resueltos`, `mape_referencia`, `mae_referencia`, `folds`, `confiabilidad`, `origen_decision`, `justificacion` y `no_calibrado`.

La misma validacion tambien evidencio dos limites de diseno. Primero, el selector basado unicamente en `material_id` puede ser fragil entre ambientes, por lo que corresponde resolver una identidad estable de material. Segundo, la calibracion runtime quedo congelada en una fotografia previa a la exploracion profunda posterior de `Pastina` y `Membrana Megaflex`. Por eso, este documento debe leerse como validacion del cableado tecnico del selector, no como foto final de las mejores mediciones experimentales actuales.

Como verificacion complementaria, tambien se ejecuto la bateria:

```bash
.venv/bin/python -m pytest tests/test_model_selector.py tests/test_forecast_service.py tests/test_forecast_snapshots.py tests/test_forecasting.py -q
```

Resultado registrado: `24 passed`.

## 10. Criterio de activacion progresiva

La activacion del selector no debe tratarse como una consecuencia automatica de su implementacion. Debe responder a una decision explicita, versionada y reversible.

### 9.1 Estado actual

- el selector ya esta implementado e integrado con `forecast_service.py`;
- el flag `USAR_SELECTOR_MODELO_FORECAST` permanece en `False` por defecto;
- la validacion realizada hasta el momento fue de integracion tecnica y contrato de respuesta, no de precision predictiva.

### 9.2 Condiciones minimas para activar en ambiente de prueba

Antes de habilitar `USAR_SELECTOR_MODELO_FORECAST = True` en un ambiente de prueba, deberian cumplirse como minimo estas condiciones:

- cierre del dataset minimo reproducible mediante `Docker + bootstrap`, sin archivos personales fuera del repositorio;
- bateria completa de tests en verde;
- validacion manual o automatizada de `Cemento Portland`, `Pastina` y `Membrana Megaflex`;
- confirmacion de que cada material resuelve el modelo esperado para el horizonte evaluado;
- confirmacion de que `seleccion_modelo` se expone correctamente en la respuesta;
- confirmacion de que los materiales no calibrados caen a `prophet_base` con `no_calibrado = true`;
- confirmacion de que no cambia la normalizacion por `kg`;
- confirmacion de que no se rompen los snapshots persistidos ni los contratos existentes del endpoint.

### 9.3 Criterios para considerar activacion productiva

La activacion en produccion no deberia evaluarse solo porque el cableado tecnico ya funciona. Antes de considerarla, deberian cumplirse simultaneamente estas condiciones:

- bootstrap oficial capaz de reconstruir el dataset minimo reproducible y validarlo automaticamente;
- backtesting actualizado por material y horizonte;
- comparacion explicita contra el comportamiento productivo vigente;
- mejora o, como minimo, mantenimiento de `MAPE` respecto del modelo actual;
- coherencia economica defendible de los regresores utilizados;
- disponibilidad estable de los regresores externos requeridos;
- ausencia de regresiones en endpoints y frontend que consumen el forecast;
- decision documentada de manera explicita en `DECISIONES_TESIS.md`.

### 9.4 Criterios de rollback

Si el selector llegara a activarse en un ambiente de prueba o en produccion, deberia revertirse a `False` si se verifica alguna de estas condiciones:

- faltan regresores externos necesarios para ejecutar modelos calibrados;
- aumenta el error respecto del modelo vigente en comparaciones controladas;
- aparecen respuestas inconsistentes entre `modelo`, `supuesto_regresores` y `seleccion_modelo`;
- se rompe la compatibilidad del endpoint con consumidores existentes;
- se detecta confusion relevante en la UI respecto de la confiabilidad o del modelo usado.

### 9.5 Alcance metodologico

- activar el selector no implica por si mismo que el sistema pase a ser automaticamente mas preciso;
- cualquier mejora debe demostrarse con backtesting actualizado y pruebas funcionales;
- la activacion debe ser gradual, explicita y reversible.

## 11. Riesgos y mitigaciones

### Riesgo de hardcodear decisiones experimentales

Si `forecast_service.py` absorbe condicionales sobre materiales, modelos y regresores, la politica metodologica vuelve a quedar acoplada al runtime.

Mitigacion:

- mantener selector aislado;
- mantener mapping declarativo;
- documentar el contrato de integracion antes de activarlo.

### Riesgo de calibrar por IDs locales inestables

Si la politica de seleccion queda anclada a `material_id`, la calibracion puede dejar de ser portable entre desarrollo, testing y produccion.

Mitigacion:

- resolver `material_key` estable antes de seleccionar el modelo;
- desacoplar calibracion metodologica de IDs locales de base;
- documentar la identidad estable como parte del contrato del selector.

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

## 12. Trabajo futuro

- cerrar el dataset minimo reproducible de tesis en `Docker + bootstrap`;
- gobernar una fuente canonica versionada para la serie historica de `Cemento Portland`;
- incorporar un snapshot local versionado de `ipim_nivel_general`;
- persistir `origen_dato` y `metodo_estimacion` de forma estructurada en series hibridas;
- agregar `validate_minimum_dataset` como verificacion post-bootstrap;
- introducir resolucion explicita `material_id -> material_key`;
- migrar el mapping declarativo a una tabla parametrizable;
- incorporar eventualmente un campo persistido como `codigo_material` o `clave_modelo`;
- versionar decisiones de modelo;
- registrar fecha de evaluacion de cada recomendacion;
- automatizar benchmark periodico por material y horizonte;
- mostrar confiabilidad del modelo y estado de calibracion en frontend.

## Cierre metodologico

La integracion implementada no cambia la naturaleza del forecast: sigue siendo un sistema basado en `Prophet`.

Lo que cambia es la forma de decidir y exponer la configuracion aplicada:

- la politica de seleccion deja de estar implicita;
- el runtime deja de hardcodear decisiones experimentales;
- la respuesta del forecast gana trazabilidad metodologica;
- la activacion puede hacerse de manera controlada y reversible;
- el frontend no fue modificado en esta etapa.
