# DECISIONES_TESIS

Este documento registra decisiones tomadas durante el desarrollo de `BuildWise`. No reemplaza al `README.md` ni a la documentacion tecnica, sino que funciona como respaldo metodologico para justificar el diseno del sistema y facilitar la redaccion posterior del informe de tesis.

## Formato de registro

Cada decision incluye:

- codigo de decision;
- fecha aproximada;
- area;
- decision tomada;
- problema que resuelve;
- alternativas consideradas;
- justificacion;
- impacto en el sistema;
- limitaciones o trabajo futuro.

---

## DT-01

- Fecha aproximada: abril de 2026
- Area: modelado de datos y forecasting
- Decision tomada: usar `precio_promedio_normalizado`, expresado en `ARS/kg`, como variable principal del forecast de cemento.
- Problema que resuelve: evita inconsistencias cuando un mismo material aparece relevado en distintas presentaciones comerciales y permite construir una serie temporal comparable.
- Alternativas consideradas:
  - trabajar con precio por bolsa u otra presentacion comercial;
  - modelar series separadas por presentacion.
- Justificacion: la normalizacion por unidad base permite comparar observaciones heterogeneas en una misma escala economica y reduce el riesgo de que cambios de presentacion distorsionen la serie principal.
- Impacto en el sistema: la capa de forecasting, el backtesting y la proyeccion economica trabajan sobre una unica unidad de analisis metodologicamente consistente.
- Limitaciones o trabajo futuro: si en el futuro se incorporan materiales cuya unidad base no sea `kg`, habra que mantener el mismo criterio de normalizacion sobre la unidad comparable correspondiente.

## DT-02

- Fecha aproximada: abril de 2026
- Area: visualizacion y experiencia de usuario
- Decision tomada: usar equivalencias de bolsas de `25 kg` y `50 kg` solo para visualizacion y comparacion comercial.
- Problema que resuelve: permite comunicar resultados de forma mas intuitiva para usuarios habituados a comprar por bolsa, sin comprometer la consistencia metodologica del modelo.
- Alternativas consideradas:
  - mostrar unicamente precios normalizados por `kg`;
  - usar el precio por bolsa como variable principal del modelo.
- Justificacion: las equivalencias comerciales mejoran la interpretabilidad para el usuario, pero no deben reemplazar a la variable metodologicamente correcta del forecast.
- Impacto en el sistema: el frontend muestra equivalencias comerciales, mientras que el backend y la evaluacion del modelo conservan `ARS/kg` como referencia principal.
- Limitaciones o trabajo futuro: si se agregan nuevas presentaciones relevantes, deberan incorporarse como equivalencias de visualizacion sin alterar la variable base del forecasting.

## DT-03

- Fecha aproximada: abril de 2026
- Area: metodologia de forecasting
- Decision tomada: usar `Prophet` como modelo principal de forecasting para la proyeccion de precios de cemento.
- Problema que resuelve: provee una base reproducible para generar proyecciones temporales y comparar variantes con y sin regresores externos.
- Alternativas consideradas:
  - baselines simples como promedio movil;
  - otros enfoques de series temporales no incorporados al MVP.
- Justificacion: `Prophet` ofrece una implementacion accesible, interpretable y adecuada para experimentacion incremental, ademas de integrarse de forma directa con el stack Python del proyecto.
- Impacto en el sistema: el flujo productivo de forecast y los experimentos metodologicos comparten una misma familia de modelos, lo que simplifica comparaciones y mantenimiento.
- Limitaciones o trabajo futuro: `Prophet` no garantiza por si solo el mejor desempeno frente a todos los baselines; su uso debe seguir validandose con backtesting temporal.

## DT-04

- Fecha aproximada: mayo de 2026
- Area: seleccion de modelo
- Decision tomada: no adoptar un unico modelo global para todos los materiales y seleccionar la variante recomendada por material y horizonte segun backtesting.
- Problema que resuelve: evita generalizar una mejora puntual a materiales con dinamicas distintas y fija un criterio cuantitativo para recomendar modelos sin cambios arbitrarios.
- Alternativas consideradas:
  - sostener un modelo global unico para todos los materiales;
  - elegir variantes solo por interpretacion economica;
  - cambiar de modelo por apreciacion visual del forecast.
- Justificacion: las mediciones mas recientes muestran que una misma variante no optimiza por igual a todos los materiales ni a todos los horizontes. En `Cemento Portland`, `IPIM` y luego combinaciones con `ICC` y `CAC` mejoran con claridad. En `Pastina`, la bateria profunda encontro mejoras con lags y con algunas combinaciones `IPIM + CAC/ICC`. En `Membrana Megaflex`, la exploracion profunda mejora `3` y `6` meses, pero no supera el mejor resultado historico de `12` meses. Por eso, la seleccion debe hacerse por material y horizonte, usando `MAPE` como criterio principal y apoyando la lectura con `MAE`, `folds` y confiabilidad de la serie.
- Impacto en el sistema: la arquitectura metodologica deja de depender de un modelo preferido universal y pasa a admitir recomendaciones diferenciadas por material, manteniendo separacion clara entre pipeline productivo y variantes experimentales.
- Limitaciones o trabajo futuro: la parametrizacion o seleccion automatica de modelos por material queda como evolucion natural del sistema. Tambien queda pendiente decidir que mejoras experimentales deben promoverse formalmente al selector productivo.

## DT-05

- Fecha aproximada: mayo de 2026
- Area: validacion y metricas
- Decision tomada: usar `MAPE` como metrica principal de comparacion y `MAE`, `folds` y efectividad informal como soporte.
- Problema que resuelve: establece un criterio cuantitativo central para comparar modelos y evita evaluaciones ambiguas.
- Alternativas consideradas:
  - priorizar `MAE` como metrica principal;
  - usar una unica metrica resumen;
  - basar la comparacion en apreciacion visual.
- Justificacion: `MAPE` permite interpretar el error relativo en terminos porcentuales, lo cual facilita la comparacion entre horizontes y variantes. `MAE`, cantidad de `folds` y efectividad informal complementan esa lectura.
- Impacto en el sistema: la UI, la documentacion y la evaluacion metodologica quedan alineadas alrededor de un criterio principal comun.
- Limitaciones o trabajo futuro: la efectividad informal se usa solo como apoyo comunicacional y no debe reemplazar a `MAPE` en decisiones metodologicas.

## DT-06

- Fecha aproximada: mayo de 2026
- Area: criterio metodologico
- Decision tomada: no elegir modelos unicamente por la plausibilidad visual del forecast.
- Problema que resuelve: evita seleccionar variantes que parecen razonables en el grafico, pero que no sostienen su desempeno al evaluarse temporalmente.
- Alternativas consideradas:
  - priorizar la forma visual de la curva proyectada;
  - ajustar el modelo buscando trayectorias economicamente intuitivas sin validacion suficiente.
- Justificacion: una proyeccion visualmente plausible no implica mejor capacidad predictiva. La eleccion del modelo debe apoyarse en backtesting temporal y metricas consistentes.
- Impacto en el sistema: fortalece la defendibilidad metodologica del proyecto y reduce el riesgo de sobreajuste narrativo.
- Limitaciones o trabajo futuro: la plausibilidad visual sigue siendo una verificacion cualitativa util, pero subordinada a la validacion cuantitativa.

## DT-07

- Fecha aproximada: mayo de 2026
- Area: experimentacion con regresores
- Decision tomada: incorporar regresores externos solo cuando mejoran el backtesting del material evaluado y mantienen coherencia economica con su dinamica de precios.
- Problema que resuelve: evita promover a produccion regresores atractivos en lo narrativo o sectorial que no demuestran mejora cuantitativa consistente.
- Alternativas consideradas:
  - incorporar cualquier regresor sectorial por criterio intuitivo;
  - usar un conjunto fijo de regresores para todos los materiales;
  - priorizar una mejora visual del forecast por sobre el error medido.
- Justificacion: los resultados con `IPIM Nivel General` mostraron primero que una mejora fuerte en `Cemento Portland` no implicaba mejora automatica en el resto de materiales. Sin embargo, la exploracion profunda posterior mostro algo mas fino: `Pastina` y `Membrana Megaflex` si pueden mejorar, pero con otras familias de variables, por ejemplo lags o combinaciones `IPIM + CAC/ICC`, y no necesariamente con la misma variante que gana en cemento. Esto refuerza que una mejora en un material no debe generalizarse automaticamente a los demas.
- Impacto en el sistema: los regresores externos quedan subordinados a evidencia de backtesting por material y por horizonte. `IPIM` se mantiene como baseline productivo vigente, mientras que `ICC`, `CAC` y features autoregresivas quedan como candidatas experimentales a promover si se formaliza su adopcion.
- Limitaciones o trabajo futuro: `ICC` y `CAC` ya fueron evaluados experimentalmente, pero todavia falta decidir cuales de esas mejoras pasan del espacio experimental al selector productivo.

## DT-08

- Fecha aproximada: mayo de 2026
- Area: producto y capa de negocio
- Decision tomada: resolver la epica de impacto economico como una capa deterministica construida sobre los forecasts ya generados.
- Problema que resuelve: permite estimar costos futuros, comparar compra actual versus compra futura y agregar escenarios economicos sin introducir un segundo modelo predictivo.
- Alternativas consideradas:
  - entrenar un modelo especifico para costo de obra;
  - incorporar optimizacion antes de resolver calculos basicos de impacto.
- Justificacion: en esta etapa, el problema principal consiste en trasladar precios proyectados a decisiones economicas simples. Eso puede resolverse con reglas y calculos deterministas sobre la salida del forecast.
- Impacto en el sistema: las epicas de proyeccion de costos reutilizan `Prophet` como proveedor de precio futuro unitario y agregan una capa separada de calculo economico.
- Limitaciones o trabajo futuro: esta capa no optimiza decisiones bajo restricciones complejas; solo cuantifica escenarios e impacto presupuestario.

## DT-09

- Fecha aproximada: mayo de 2026
- Area: optimizacion de compras
- Decision tomada: evaluar `PuLP` como primera herramienta de optimizacion para la epica 5.
- Problema que resuelve: brinda una forma clara y defendible de modelar decisiones de compra bajo restricciones de presupuesto, cantidades requeridas y criticidad de materiales.
- Alternativas consideradas:
  - implementar reglas fijas sin solver;
  - incorporar directamente `OR-Tools`;
  - postergar totalmente la capa de optimizacion.
- Justificacion: `PuLP` se adapta bien a problemas iniciales de programacion lineal o entera mixta, mantiene baja la complejidad de implementacion y facilita la explicacion metodologica en tesis.
- Impacto en el sistema: permite proyectar una capa de decision por encima del forecast sin reemplazar el modelo de precios ni alterar la logica actual de `Prophet`.
- Limitaciones o trabajo futuro: antes de implementar optimizacion completa, deben definirse con precision las reglas de negocio, variables de decision y restricciones del problema.

## DT-10

- Fecha aproximada: mayo de 2026
- Area: evolucion futura de optimizacion
- Decision tomada: reservar `OR-Tools` como alternativa futura para problemas combinatorios mas complejos.
- Problema que resuelve: evita sobredimensionar la solucion actual y deja abierta una ruta de evolucion si el problema de compra crece en complejidad.
- Alternativas consideradas:
  - adoptar `OR-Tools` desde el inicio;
  - limitar permanentemente la optimizacion a modelos lineales simples.
- Justificacion: `OR-Tools` resulta mas adecuado cuando aparecen restricciones logisticas, multiples proveedores, calendarizacion, asignacion o decisiones combinatorias de mayor escala. Ese no es todavia el problema principal del MVP.
- Impacto en el sistema: la arquitectura puede evolucionar por etapas, manteniendo primero una solucion simple y defendible, y escalando solo cuando el alcance lo exija.
- Limitaciones o trabajo futuro: si la epica 5 incorpora restricciones logisticas o de calendarizacion, sera necesario reevaluar si `PuLP` sigue siendo suficiente o si corresponde migrar a herramientas mas amplias.

## DT-11

- Fecha aproximada: mayo de 2026
- Area: producto y toma de decisiones
- Decision tomada: incorporar una capa de decision economica sobre el forecast como base de la Epica 5.
- Problema que resuelve: permite pasar de la simple proyeccion de precios a recomendaciones de accion concretas sobre cuando comprar, que priorizar y como asignar presupuesto.
- Alternativas consideradas:
  - limitar el sistema a mostrar solo precios actuales y proyectados;
  - incorporar directamente un solver sin reglas intermedias;
  - usar desde el inicio herramientas mas amplias de optimizacion combinatoria.
- Justificacion: `Prophet` ya cumple el rol de proveedor de precios futuros. Sobre esa base, resulta metodologicamente mas ordenado incorporar primero reglas simples para `HU24`, `HU21` y `HU22`, y reservar `PuLP` para `HU23`, donde aparece de forma explicita la restriccion presupuestaria.
- Impacto en el sistema: la arquitectura evoluciona en dos capas complementarias, una de forecasting y otra de decision economica, lo que facilita explicar, validar e implementar cada responsabilidad por separado.
- Limitaciones o trabajo futuro: si el problema incorpora restricciones logisticas, multiples proveedores o decisiones combinatorias mas complejas, debera reevaluarse el uso de `OR-Tools` como alternativa futura.

## DT-12

- Fecha aproximada: mayo de 2026
- Area: implementacion de decision economica
- Decision tomada: implementar `HU24` como primera capa de priorizacion de materiales criticos.
- Problema que resuelve: permite rankear materiales segun urgencia de compra antes de incorporar recomendaciones de compra o optimizacion con restriccion presupuestaria.
- Alternativas consideradas:
  - avanzar directamente a `HU21` sin una capa previa de criticidad;
  - incorporar un solver desde el inicio;
  - resolver la priorizacion solo de forma cualitativa y no cuantificada.
- Justificacion: `HU24` consume precios actuales y proyectados ya provistos por el modulo de pricing/forecasting, no modifica la logica de `Prophet` y permite validar una capa inicial de decision economica sin introducir aun complejidad de optimizacion. La criticidad se definio combinando variacion esperada normalizada e impacto absoluto normalizado, evitando sumar directamente porcentajes con montos monetarios.
- Impacto en el sistema: se incorpora una capacidad nueva de ranking de materiales criticos, con reglas testeables, explicacion funcional y base metodologica reutilizable para `HU21`, `HU22` y `HU23`.

## DT-17

- Fecha aproximada: mayo de 2026
- Area: optimizacion presupuestaria
- Decision tomada: implementar `HU23` mediante una formulacion de programacion lineal en `PuLP`, manteniendo `OR-Tools` y otros solvers fuera del alcance actual.
- Problema que resuelve: permite asignar presupuesto entre materiales de forma optima y trazable, usando precios actuales, precios proyectados y criticidad sin introducir una capa de optimizacion mas compleja que la requerida por el problema actual.
- Alternativas consideradas:
  - resolver `HU23` solo con reglas heuristicas y ordenamiento manual;
  - incorporar `OR-Tools` desde la primera version;
  - modelar el problema con implementaciones ad hoc sin una formulacion explicita de optimizacion.
- Justificacion: el problema vigente de `HU23` puede expresarse de forma natural como un modelo lineal con funcion objetivo y restricciones transparentes: presupuesto disponible, cantidades objetivo y no negatividad. En este contexto, `PuLP` ofrece una forma simple de declarar el modelo y resolverlo con un solver estandar, manteniendo una explicacion metodologica clara para tesis. La decision evita adelantar complejidad combinatoria que hoy no agrega valor real. En la formulacion continua actual, el problema es esencialmente lineal y puede interpretarse como resoluble por tecnicas tipo simplex; si en una evolucion futura aparecen variables enteras o decisiones discretas por presentacion, la resolucion pasara a requerir mecanismos de ramificacion sobre esa base.
- Impacto en el sistema: `HU23` queda respaldada por una optimizacion formal, auditable y alineada con la arquitectura Python existente. La capa de decision economica conserva trazabilidad entre inputs, restricciones, resultado y justificacion funcional.
- Limitaciones o trabajo futuro: si el problema incorpora lotes enteros obligatorios, multiples proveedores, ventanas temporales multiples o restricciones logisticas complejas, debera reevaluarse la conveniencia de migrar a `OR-Tools` u otro solver con mejor soporte para optimizacion combinatoria mas rica.

## DT-13

- Fecha aproximada: mayo de 2026
- Area: arquitectura de forecasting
- Decision tomada: separar el serving productivo de forecasting de los scripts de experimentacion offline.
- Problema que resuelve: evita que la logica experimental, los accesos auxiliares a datos y la configuracion tecnica de Prophet queden mezclados con el flujo HTTP productivo.
- Alternativas consideradas:
  - mantener scripts y serving compartiendo helpers dispersos dentro de `routes.py`;
  - duplicar logica entre experimentos y serving;
  - mover toda la experimentacion fuera del repositorio principal.
- Justificacion: el forecasting es un componente central de `BuildWise` y requiere distinguir claramente entre pipeline productivo y pipeline experimental. La separacion permite que los experimentos sigan evolucionando sin contaminar la interfaz publica ni aumentar el acoplamiento del modulo de pricing.
- Impacto en el sistema: el serving productivo queda concentrado en `application` e `infrastructure`, mientras que la experimentacion se apoya en un espacio propio bajo `app/experiments`, con responsabilidades mas claras y reutilizacion controlada.
- Limitaciones o trabajo futuro: la separacion actual ordena el codigo, pero no elimina todavia el costo computacional del forecast request-time ni incorpora mecanismos de cache, precomputacion o ejecucion asincrona.

## DT-14

- Fecha aproximada: mayo de 2026
- Area: seleccion parametrizada de modelos
- Decision tomada: resolver el modelo de forecasting mediante un selector parametrizado por `material_key` y `horizonte_meses`, aislado del `forecast_service` y respaldado inicialmente por una configuracion declarativa en codigo. El endpoint puede seguir recibiendo `material_id`, pero su uso es solo de entrada externa para derivar la clave estable.
- Problema que resuelve: evita sostener un modelo global unico para todos los materiales y tambien evita dispersar logica hardcodeada de seleccion dentro del flujo principal del serving.
- Alternativas consideradas:
  - mantener un unico modelo universal para todos los materiales;
  - resolver la seleccion con condicionales dentro de `forecast_service.py`;
  - llevar la parametrizacion directamente a base de datos en una primera etapa.
- Justificacion: la evidencia de backtesting ya muestra que `Cemento Portland`, `Pastina` y `Membrana Megaflex` no comparten la misma mejor variante. Por eso, la recomendacion metodologica debe resolverse como una politica explicita de seleccion por material y horizonte, usando `MAPE` como criterio principal y dejando `MAE`, `folds`, confiabilidad y coherencia economica como soporte. Un selector dedicado preserva trazabilidad, reduce acoplamiento y deja preparado el camino para una futura parametrizacion persistida sin cambiar el contrato del serving.
- Impacto en el sistema: la arquitectura de forecasting incorpora una capa de resolucion de modelo separada del entrenamiento y serving de `Prophet`, con capacidad para exponer que configuracion fue elegida, por que fue elegida y con que evidencia fue calibrada.
- Limitaciones o trabajo futuro: la primera version no implica automatizacion estadistica en runtime ni almacenamiento en base. La politica se apoya en recomendaciones versionadas en codigo y debera migrar luego a una fuente parametrizable si aumenta la cantidad de materiales, horizontes o experimentos activos.

## DT-15

- Fecha aproximada: mayo de 2026
- Area: despliegue y operacion
- Decision tomada: separar el runtime web del bootstrap operativo de base de datos y carga inicial de datos.
- Problema que resuelve: evita que el contenedor de la API ejecute migraciones, seed e imports cada vez que arranca el servicio web.
- Alternativas consideradas:
  - mantener un unico comando de arranque con migraciones, seed, imports y `uvicorn`;
  - delegar toda la preparacion de datos a instrucciones manuales no versionadas;
  - posponer la separacion operativa hasta una etapa posterior.
- Justificacion: mezclar bootstrap destructivo con el proceso web principal genera arranques lentos, dificulta releases controlados y consolida una practica valida solo para prototipos. Separar ambos flujos mejora la previsibilidad operativa y acerca el proyecto a un estandar mas serio de despliegue.
- Impacto en el sistema: `docker-compose` distingue ahora el servicio `api` del servicio `bootstrap`, y `Makefile` expone un comando operativo explicito para correr migraciones y cargas iniciales cuando corresponda.
- Limitaciones o trabajo futuro: esta separacion mejora el control operativo, pero aun falta definir mejor la estrategia de entornos, la idempotencia completa de imports y el endurecimiento del despliegue productivo.

## DT-16

- Fecha aproximada: mayo de 2026
- Area: serving de forecasting
- Decision tomada: incorporar una cache en memoria, con TTL y firma del dataset, para reutilizar resultados de forecast repetidos sobre la misma serie.
- Problema que resuelve: reduce el costo de recalcular en request-time el mismo forecast cuando no hubo cambios en la serie mensual del material ni en el horizonte consultado.
- Alternativas consideradas:
  - mantener siempre el recalculo completo por request;
  - incorporar desde el inicio una capa de persistencia o precomputacion mas compleja;
  - posponer cualquier mitigacion hasta redisenar por completo el serving.
- Justificacion: el costo principal del endpoint de forecast proviene del entrenamiento y backtesting repetidos de `Prophet`. Una cache en memoria permite bajar ese costo de forma inmediata sin alterar el modelo productivo, manteniendo ademas una invalidacion simple basada en cambios reales de la serie.
- Impacto en el sistema: el modulo de pricing reutiliza resultados recientes cuando la firma del dataset y el horizonte coinciden, lo que mejora la eficiencia del serving y reduce trabajo redundante dentro del proceso de la API.
- Limitaciones o trabajo futuro: la cache actual es local al proceso y no reemplaza una estrategia mas robusta de precomputacion, persistencia compartida o ejecucion asincrona. Sigue siendo una mitigacion intermedia mientras el forecast continúe sirviendose request-time.

## DT-17

- Fecha aproximada: mayo de 2026
- Area: precomputacion de forecasting
- Decision tomada: incorporar snapshots persistidos de forecast y un comando explicito de precomputacion para materiales activos.
- Problema que resuelve: permite reutilizar resultados de forecast entre reinicios del proceso web y evita depender exclusivamente de una cache en memoria calentada por trafico HTTP.
- Alternativas consideradas:
  - mantener solo cache local por proceso;
  - crear de inmediato una tabla nueva en base de datos para snapshots;
  - dejar toda la precomputacion para una etapa posterior.
- Justificacion: una persistencia simple en archivo, con firma del dataset y horizonte como clave, permite avanzar hacia un serving mas estable sin introducir todavia una migracion adicional ni complejizar prematuramente la infraestructura. El comando de precomputacion hace explicito el paso operativo y separa mejor serving de calculo batch.
- Impacto en el sistema: `forecast_service` puede reutilizar snapshots persistidos, y el proyecto cuenta con un entrypoint operativo para precomputar forecasts de materiales activos en horizontes definidos.
- Limitaciones o trabajo futuro: la persistencia actual en archivo sigue siendo una solucion transicional. Si el sistema evoluciona a multiinstancia, colas o mayor concurrencia, convendra migrar estos snapshots a una persistencia compartida o a un pipeline batch mas robusto.

## DT-18

- Fecha aproximada: mayo de 2026
- Area: organizacion operativa y compatibilidad legacy
- Decision tomada: mover los entrypoints operativos de bootstrap a un namespace explicito `app.operations.bootstrap`, dejando `app.db` como capa de compatibilidad minima.
- Problema que resuelve: reduce la ambiguedad del paquete `app.db`, que mezclaba compatibilidad historica con scripts operativos reales, y deja mas clara la frontera entre infraestructura compartida y tareas de inicializacion/importacion.
- Alternativas consideradas:
  - mantener todos los scripts en `app.db`;

## DT-19

- Fecha aproximada: mayo de 2026
- Area: integracion controlada de forecasting
- Decision tomada: integrar el selector de modelos con `forecast_service.py` detras del flag interno `USAR_SELECTOR_MODELO_FORECAST = False`, manteniendo inalterado el comportamiento productivo por defecto.
- Problema que resuelve: permite incorporar resolucion explicita de modelo por `material_key` y `horizonte_meses` sin introducir un cambio abrupto en el serving productivo ni mezclar la politica metodologica con la activacion operativa.
- Alternativas consideradas:
  - activar inmediatamente el selector en todos los requests de forecast;
  - mantener la integracion solo documentada, sin implementacion en el servicio;
  - absorber la logica de seleccion con condicionales ad hoc dentro del flujo productivo.
- Justificacion: la evidencia de backtesting ya justifica seleccionar configuraciones distintas por material y horizonte, pero esa capacidad debia incorporarse de forma reversible y defendible. El flag interno permite validar la integracion sin alterar la salida vigente del endpoint. Cuando se activa, el sistema resuelve el modelo recomendado, sus regresores y los metadatos metodologicos asociados; si no existe calibracion o faltan regresores operativos, degrada de forma controlada a `prophet_base`, marcado como `no_calibrado`, sin romper el endpoint ni inventar metricas nuevas.
- Impacto en el sistema: `forecast_service` ya puede resolver `material_key` a partir de `Material.nombre`, consumir `resolve_model_selection(material_key, horizonte_meses)`, traducir la seleccion a una configuracion efectiva de `Prophet`, preservar la normalizacion por `kg`, y exponer `seleccion_modelo` con `material_key`, `modelo_resuelto`, `regresores_resueltos`, metricas de referencia, confiabilidad, `origen_decision`, `justificacion` y `no_calibrado` cuando el flag se encuentra activo. El frontend no fue modificado en esta etapa.
- Limitaciones o trabajo futuro: la integracion permanece desactivada por defecto aun despues de una validacion controlada del cableado tecnico y del contrato de respuesta, ejecutada con el flag activado solo en memoria. Esa validacion no constituye una nueva medicion de backtesting ni de precision predictiva y no modifica las metricas documentadas. La activacion futura en prueba o produccion debe responder a un criterio explicito de activacion progresiva y rollback, documentado en `docs/DISENO_INTEGRACION_SELECTOR_FORECAST.md`, antes de considerar cualquier cambio del valor por defecto del flag.
  - eliminar de inmediato los paths legacy sin transicion;
  - mezclar bootstrap con comandos informales fuera del repositorio.
- Justificacion: un namespace operativo explicito mejora la legibilidad del proyecto, facilita explicar la arquitectura y permite migrar de manera incremental sin romper de golpe referencias existentes. La compatibilidad minima en `app.db` evita una ruptura innecesaria mientras se termina de limpiar el remanente legacy.
- Impacto en el sistema: los comandos operativos principales pasan a vivir en `app.operations.bootstrap`, mientras `docker-compose` y los tests dejan de depender directamente de `app.db` como contrato primario.
- Limitaciones o trabajo futuro: todavia queda compatibilidad legacy en algunos wrappers de `app.db`. El cierre definitivo requerira remover esos puentes cuando no existan referencias activas que los necesiten.

## DT-19

- Fecha aproximada: mayo de 2026
- Area: interpretacion metodologica del forecast
- Decision tomada: documentar la confiabilidad del sistema por material y no asumir homogeneidad metodologica entre series continuas.
- Problema que resuelve: evita presentar como equivalentes materiales cuyas series tienen distinta proporcion de datos reales y estimados, aunque todos sean pronosticables en terminos operativos.
- Alternativas consideradas:
  - comunicar una unica confiabilidad global del sistema;
  - inferir confiabilidad solo a partir de la continuidad mensual de la serie;
  - presentar `MAPE` sin contexto sobre calidad del dato historico.
- Justificacion: la continuidad mensual mejora la estabilidad del forecast y habilita el backtesting temporal, pero no garantiza por si sola la misma confiabilidad real. Las series hibridas con muchos valores estimados pueden arrojar metricas utiles para operacion, aunque metodologicamente menos solidas que una serie real, densa y continua como la de cemento.
- Impacto en el sistema: la documentacion y la defensa metodologica del proyecto distinguen ahora entre `Cemento Portland` como referencia principal, `Pastina` como serie de confiabilidad media y `Membrana Megaflex` como serie de confiabilidad media-baja.
- Limitaciones o trabajo futuro: a futuro conviene separar explicitamente evaluaciones sobre puntos reales frente a evaluaciones sobre series hibridas, para reducir el riesgo de sobreinterpretar `MAPE` sobre datos estimados.

## DT-20

- Fecha aproximada: mayo de 2026
- Area: integracion de seleccion de modelo con serving de forecast
- Decision tomada: integrar el selector interno de modelos al flujo de forecast de forma gradual, sin activarlo por defecto en la primera etapa y resguardando el comportamiento actual mediante un `feature flag` o mecanismo equivalente.
- Problema que resuelve: permite incorporar seleccion de modelo por material y horizonte sin mezclar logica experimental dentro de `forecast_service.py` ni alterar de golpe el serving productivo ya operativo.
- Alternativas consideradas:
  - activar el selector inmediatamente para todos los forecasts;
  - mantener la logica de seleccion embebida dentro de `forecast_service.py`;
  - postergar indefinidamente la integracion y sostener un modelo productivo unico.
- Justificacion: el selector ya concentra una politica metodologica versionada y testeable, pero su integracion al flujo productivo requiere validacion adicional sobre regressors disponibles, respuesta HTTP, compatibilidad de backward y pruebas de no regresion. Por eso, la integracion debe hacerse de manera controlada, con activacion explicita y capacidad de exponer el modelo usado junto con su justificacion, sin romper la arquitectura actual de `Prophet`.
- Impacto en el sistema: `forecast_service` podra evolucionar hacia una interfaz donde la resolucion del modelo quede desacoplada del entrenamiento, y la respuesta del forecast exponga trazabilidad metodologica sobre la configuracion aplicada.
- Limitaciones o trabajo futuro: hasta que el selector no se active, el comportamiento productivo sigue igual. La etapa siguiente requerira definir el contrato exacto de integracion, validar fallbacks por falta de regresores y asegurar que la salida del endpoint mantenga compatibilidad razonable con clientes actuales.

## DT-21

- Fecha aproximada: mayo de 2026
- Area: identidad metodologica de materiales
- Decision tomada: usar una identidad estable de material para la seleccion de modelos, separada del `material_id` local de cada base.
- Problema que resuelve: evita que la calibracion metodologica del selector dependa de IDs tecnicos accidentales del ambiente, que pueden cambiar entre desarrollo, testing, produccion, seeds recreados o cargas manuales.
- Alternativas consideradas:
  - seguir calibrando por `material_id`;
  - resolver la identidad por nombre raw sin normalizacion;
  - incorporar inmediatamente un campo persistido nuevo en base;
  - postergar el problema y asumir consistencia de IDs entre ambientes.
- Justificacion: la validacion runtime real mostro que el cableado tecnico del selector funciona, pero tambien evidencio que un mismo material logico puede quedar representado con IDs distintos o con series utiles en otro registro del catalogo. Por eso, la recomendacion del modelo debe asociarse al material logico y no a una clave accidental del ambiente. Para el MVP, conviene resolver una `material_key` estable desde el catalogo actual mediante normalizacion controlada del nombre o slug derivado, sin migracion de base todavia. Como evolucion futura, esa clave deberia persistirse explicitamente.
- Impacto en el sistema: el selector podra migrar de un mapping basado en `material_id + horizonte_meses` a uno basado en `material_key + horizonte_meses`, mejorando portabilidad, trazabilidad y reproducibilidad entre ambientes sin cambiar la logica de `Prophet` ni el contrato externo del endpoint.
- Limitaciones o trabajo futuro: la resolucion derivada desde nombres sigue siendo una solucion intermedia y requiere criterios claros de normalizacion. A futuro convendra incorporar un campo persistido como `codigo_material` o `clave_modelo`, y eventualmente una tabla de calibraciones gobernada por `material_key`.

## DT-22

- Fecha aproximada: mayo de 2026
- Area: reproducibilidad del entorno y dataset de tesis
- Decision tomada: priorizar el cierre de un dataset minimo reproducible antes de activar el selector, avanzar frontend o incorporar nuevas features de forecasting.
- Problema que resuelve: evita que la tesis y la demo dependan de intervenciones manuales, archivos personales no versionados o diferencias accidentales entre bases al reconstruir el entorno desde cero.
- Alternativas consideradas:
  - continuar con frontend y nuevas features antes de cerrar reproducibilidad;
  - depender de `import_cemento_facturas` como base suficiente para `Cemento Portland`;
  - mantener `IPIM` sujeto a sincronizacion online posterior;
  - reconstruir el entorno con archivos locales fuera del repositorio.
- Justificacion: la validacion runtime real confirmo que el cableado tecnico del sistema funciona, pero tambien expuso una brecha entre documentacion, bootstrap y dataset realmente disponible en una base limpia. Para que la tesis sea defendible, una instalacion nueva debe poder reconstruir el universo minimo asumido por las mediciones: `Cemento Portland` con serie real, densa y continua; `Pastina` y `Membrana Megaflex` con series mensuales hibridas distinguiendo `REAL` y `ESTIMADO`; y los regresores `ipc`, `dolar_oficial`, `dolar_mayorista`, `dolar_blue` e `ipim_nivel_general`. La fuente operativa de cemento quedo gobernada despues por `Factura compra` como origen de los comprobantes reales, mientras que la fuente canonica versionada paso a ser `db/bootstrap/cemento_portland_historico.csv`, cargada por `import_cemento_canonico.py`. `import_cemento_facturas` queda reclasificado como import incremental u operativo. `IPIM` debe incorporarse desde un snapshot local versionado, no desde una sincronizacion externa obligatoria.
- Impacto en el sistema: el bootstrap oficial objetivo pasa a ser `alembic upgrade head`, `seed`, `import_cemento_canonico`, `import_pastina`, `import_membrana_megaflex`, `import_external_indices_snapshot` y `validate_minimum_dataset`. Ademas, `Pastina` y `Membrana Megaflex` deberan persistir `origen_dato` y `metodo_estimacion`, mientras que `Cemento Portland` debera persistir `origen_dato = REAL` cuando provenga de la fuente historica canonica.
- Limitaciones o trabajo futuro: la reproducibilidad del entorno sigue condicionada por la cobertura real de validacion post-bootstrap. Como transicion puede admitirse la referencia historica a `import_sicons_excel` o `SICONS_XLSX_PATH`, pero no debe presentarse como fuente operativa final ni como requisito del bootstrap minimo una vez consolidado el canon versionado.

## DT-23

- Fecha aproximada: mayo de 2026
- Area: fuente canonica reproducible de `Cemento Portland`
- Decision tomada: definir `db/bootstrap/cemento_portland_historico.csv` como fuente canonica reproducible, versionada, reducida y auditable para reconstruir la serie historica de `Cemento Portland`.
- Problema que resuelve: evita que la serie robusta de cemento dependa de `db/sicons.xlsx` o de archivos personales externos, y separa con claridad la base historica metodologica del import incremental de facturas recientes.
- Alternativas consideradas:
  - mantener `XLSX` como artefacto operativo principal;
  - usar `JSON` versionado como fuente canonica;
  - sostener `SICONS_XLSX_PATH` como solucion final;
  - seguir usando `import_cemento_facturas` como base suficiente.
- Justificacion: para una serie tabular historica, `CSV` ofrece mejor auditabilidad, menor friccion de versionado, diffs mas claros y menor riesgo de arrastrar columnas irrelevantes o sensibles que un `XLSX` completo. `JSON` no aporta una ventaja real para este caso y agrega verbosidad innecesaria. `SICONS_XLSX_PATH` puede admitirse como transicion operativa, pero no cierra reproducibilidad de tesis mientras el artefacto no quede dentro del repositorio. Por eso, la fuente canonica se redujo a un extracto controlado con columnas minimas: `fecha`, `empresa`, `numero_comprobante`, `articulo`, `precio_original`, `precio_normalizado`, `moneda`, `origen_dato`, `metodo_estimacion` y `observaciones_origen`. En esta fuente, `origen_dato` debe ser `REAL` y `metodo_estimacion` debe quedar vacio o `null`.
- Impacto en el sistema: el bootstrap minimo se implemento con `import_cemento_canonico`, encargado de leer `db/bootstrap/cemento_portland_historico.csv`, crear o actualizar `Cemento Portland`, sus presentaciones `Bolsa 25 kg` y `Bolsa 50 kg`, registrar una fuente separada como `Dataset canonico Cemento Portland`, persistir `origen_dato = REAL` y conservar idempotencia. `import_sicons_excel` queda como herramienta legacy o transitoria desde Excel, mientras `import_cemento_facturas` sigue como import incremental u operativo.
- Limitaciones o trabajo futuro: si `numero_comprobante` resultara sensible al volver a exportar o regenerar el canon, debera anonimizarse de forma deterministica que preserve trazabilidad e idempotencia. Tambien debe mantenerse la convivencia posterior con `import_cemento_facturas` sin mezclar la fuente canonica con la carga incremental.

## DT-24

- Fecha aproximada: mayo de 2026
- Area: fuente operativa y extracto canónico de `Cemento Portland`
- Decision tomada: construir la serie canónica de `Cemento Portland` a partir de comprobantes reales de compra registrados en la fuente operativa `Factura compra`, y congelar ese subconjunto en `db/bootstrap/cemento_portland_historico.csv` como extracto canónico versionable.
- Problema que resuelve: distingue la fuente operativa de origen del artefacto canónico reproducible, evita ambigüedad sobre la procedencia de la serie de tesis y habilita un bootstrap mínimo auditable sin depender de archivos personales ni de imports incrementales recientes.
- Alternativas consideradas:
  - versionar directamente el `XLSX` original como fuente canónica;
  - seguir usando `import_cemento_facturas` como base suficiente;
  - incorporar una migracion de modelo solo para renombrar la fuente operativa.
- Justificacion: la auditoria del CSV de trabajo verifico que el tramo exportado desde `Factura compra` contiene `1626` registros reales, cubre el rango continuo `2022-01-03` a `2026-03-25`, tiene `51` meses observados, `0` meses faltantes en el tramo canónico, `0` duplicados en `numero_comprobante`, `origen_dato = REAL` en todas las filas, `metodo_estimacion` vacio, `moneda = ARS` y precios positivos en todo el archivo. La fuente operativa `Factura compra` es defendible como origen porque aporta comprobantes reales y trazabilidad, mientras que el CSV versionado congela un extracto controlado, reproducible y apto para tesis.
- Impacto en el sistema: `db/bootstrap/cemento_portland_historico.csv` es el artefacto versionable que alimenta el bootstrap minimo reproducible de Cemento Portland. El CSV no reemplaza a la fuente original de datos, sino que la congela de manera auditable. `import_cemento_facturas` permanece como carga incremental u operativa y no debe confundirse con la base metodologica canónica.
- Limitaciones o trabajo futuro: el extracto canónico se limita al tramo continuo efectivamente validado. Valores posteriores aislados o colas incompletas no forman parte del canon hasta que puedan integrarse sin romper continuidad mensual. Si `numero_comprobante` llegara a considerarse sensible al momento de versionar el archivo, debera anonimizarse de forma deterministica sin perder unicidad ni trazabilidad.

## DT-25

- Fecha aproximada: mayo de 2026
- Area: alcance DSS y defensa del MVP
- Decision tomada: presentar el estado actual de `BuildWise` como un DSS de compra trazable en alcance MVP, sin reclamar todavia capacidades conversacionales o proactivas.
- Problema que resuelve: evita que el sistema sea evaluado como un dashboard descriptivo y, al mismo tiempo, evita sobredimensionar el alcance vendiendolo como asistente autonomo completo.
- Alternativas consideradas:
  - presentar el sistema solo como dashboard analitico;
  - esperar a implementar chat conversacional para denominarlo asistente;
  - agregar nuevas historias funcionales antes de cerrar evidencia del DSS.
- Justificacion: la Epica 5 ya integra forecast, criticidad, comparacion economica, restriccion presupuestaria y recomendacion operativa trazable. La salida `/compras/recomendacion-operativa` permite responder que comprar ahora, que postergar, cuanto presupuesto consume, que impacto economico estima, con que confianza y bajo que supuestos. Eso satisface el nucleo de un sistema de soporte a la decision, aunque la interfaz conversacional y las alertas queden fuera del MVP actual.
- Impacto en el sistema: la documentacion, las HU y la demo deben alinear el mensaje alrededor de `DSS de compra trazable`. La visualizacion queda explicada como interfaz de consulta, mientras que el nucleo metodologico se ubica en la decision economica generada por reglas, forecast y optimizacion.
- Limitaciones o trabajo futuro: la denominacion DSS no implica automatizacion completa. Quedan fuera del alcance actual la conversacion en lenguaje natural, la operacion proactiva, sustitutos, multiples proveedores, restricciones logisticas y decisiones discretas por lote o calendario.
