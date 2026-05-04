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
- Decision tomada: seleccionar `prophet_oficial_mayorista` como modelo preferido actual por su desempeno en backtesting.
- Problema que resuelve: fija un modelo productivo vigente sobre una base cuantitativa y evita cambios arbitrarios entre variantes experimentales.
- Alternativas consideradas:
  - `prophet_oficial`;
  - variantes con `IPC`;
  - variantes con otros regresores externos.
- Justificacion: en el estado actual del proyecto, `prophet_oficial_mayorista` obtuvo el mejor resultado de backtesting documentado para los horizontes analizados, con especial robustez a `3 meses`.
- Impacto en el sistema: el sistema expone una decision metodologica concreta y mantiene una separacion clara entre modelo productivo y variantes experimentales.
- Limitaciones o trabajo futuro: la seleccion no se considera definitiva; si nuevas variantes superan consistentemente al modelo actual, la decision debera revisarse.

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
- Decision tomada: mantener las variantes con `IPC` como experimentales mientras no superen en backtesting al modelo principal.
- Problema que resuelve: evita promover a produccion variantes que agregan complejidad metodologica sin demostrar una mejora consistente.
- Alternativas consideradas:
  - incorporar `IPC` al flujo productivo por su atractivo interpretativo;
  - usar `IPC` como regresor fijo por criterio economico.
- Justificacion: las pruebas realizadas muestran que sumar `IPC` no garantiza una mejora respecto del modelo preferido actual y, en algunos casos, empeora el resultado.
- Impacto en el sistema: el pipeline productivo se mantiene estable y las variantes con `IPC` quedan acotadas al espacio de experimentacion.
- Limitaciones o trabajo futuro: si en futuras pruebas `IPC` aporta mejoras consistentes y reproducibles, podra reevaluarse su incorporacion.

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
- Limitaciones o trabajo futuro: `PuLP` se mantiene reservado para `HU23`, cuando aparezca formalmente la restriccion presupuestaria. La capa actual prioriza materiales, pero todavia no recomienda estrategias completas de compra.

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

## DT-15

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

## DT-16

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

## DT-17

- Fecha aproximada: mayo de 2026
- Area: organizacion operativa y compatibilidad legacy
- Decision tomada: mover los entrypoints operativos de bootstrap a un namespace explicito `app.operations.bootstrap`, dejando `app.db` como capa de compatibilidad minima.
- Problema que resuelve: reduce la ambiguedad del paquete `app.db`, que mezclaba compatibilidad historica con scripts operativos reales, y deja mas clara la frontera entre infraestructura compartida y tareas de inicializacion/importacion.
- Alternativas consideradas:
  - mantener todos los scripts en `app.db`;
  - eliminar de inmediato los paths legacy sin transicion;
  - mezclar bootstrap con comandos informales fuera del repositorio.
- Justificacion: un namespace operativo explicito mejora la legibilidad del proyecto, facilita explicar la arquitectura y permite migrar de manera incremental sin romper de golpe referencias existentes. La compatibilidad minima en `app.db` evita una ruptura innecesaria mientras se termina de limpiar el remanente legacy.
- Impacto en el sistema: los comandos operativos principales pasan a vivir en `app.operations.bootstrap`, mientras `docker-compose` y los tests dejan de depender directamente de `app.db` como contrato primario.
- Limitaciones o trabajo futuro: todavia queda compatibilidad legacy en algunos wrappers de `app.db`. El cierre definitivo requerira remover esos puentes cuando no existan referencias activas que los necesiten.
