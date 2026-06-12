# REGISTRO_DECISIONES_TRABAJO

Este documento registra decisiones operativas tomadas durante el cierre del MVP. Complementa `docs/documentacion/DECISIONES_TESIS.md`, que queda reservado para decisiones metodologicas mas formales.

## Criterio de uso

- Registrar decisiones que afecten alcance, defensa, demo, HU, contratos API o criterios de cierre.
- Mantener frases breves y accionables.
- Cuando una decision sea metodologicamente relevante para tesis, replicarla o resumirla tambien en `docs/documentacion/DECISIONES_TESIS.md`.

---

## RD-01 - Presentar BuildWise como DSS MVP

- Fecha: mayo de 2026
- Decision: presentar el sistema actual como `DSS de compra trazable en estado MVP`.
- Motivo: el sistema ya transforma datos historicos y forecast en recomendacion economica accionable.
- Alcance: no se presenta como asistente conversacional completo ni como sistema proactivo.
- Evidencia: `HU21`, `HU22`, `HU23`, `HU28` y `HU28b`.

## RD-02 - Congelar alcance funcional antes de Epica 6/7

- Fecha: mayo de 2026
- Decision: no agregar chat, alertas proactivas, sustitutos, mas materiales ni nuevos modelos para el cierre MVP.
- Motivo: el riesgo principal ya no es funcionalidad faltante, sino evidencia, consistencia y defensa.
- Impacto: el trabajo restante se concentra en demo reproducible, documentacion, tests y salida DSS clara.

## RD-03 - Renumerar HU agregadas con sufijo `b`

- Fecha: mayo de 2026
- Decision: evitar `HU34` y `HU35` como numeros nuevos independientes.
- Renumeracion:
  - `HU34` -> `HU27b`
  - `HU35` -> `HU28b`
- Motivo: mantener agrupacion conceptual sin mezclar numeracion de epicas.
- Impacto: `HU27b` queda en asistencia conversacional futura; `HU28b` queda como cierre DSS de recomendacion operativa trazable.

## RD-04 - Definir `HU28b` como salida estrella del DSS

- Fecha: mayo de 2026
- Decision: usar `/compras/recomendacion-operativa` como endpoint principal de demostracion DSS.
- Motivo: consolida accion, cantidades, presupuesto, impacto economico, confianza, supuestos y advertencias en una unica salida.
- Campos clave:
  - `fecha_calculo`
  - `decision_resumen`
  - `accion_recomendada`
  - `cantidad_comprar_ahora`
  - `cantidad_postergar`
  - `presupuesto_utilizado`
  - `presupuesto_restante`
  - `impacto_economico_estimado`
  - `impacto_economico_pct`
  - `confianza`
  - `supuestos`
  - `advertencias`

## RD-05 - Preparar demo reproducible del DSS

- Fecha: mayo de 2026
- Decision: documentar una demo con tres casos individuales y un caso multi-material restrictivo.
- Casos:
  - `Cemento Portland`
  - `Pastina`
  - `Membrana Megaflex`
  - optimizacion multi-material con presupuesto limitado
- Evidencia documental: `docs/documentacion/DEMO_DSS.md`.
- Motivo: demostrar que el sistema responde que comprar, que postergar, cuanto impacta y bajo que supuestos.

## RD-06 - Verificacion tecnica enfocada

- Fecha: mayo de 2026
- Decision: usar el siguiente comando como verificacion critica del DSS:

```bash
.venv/bin/python -m pytest --no-cov tests/test_purchase_recommendations.py tests/test_purchase_strategies.py tests/test_purchase_optimization.py
```

- Motivo: el ejecutable `pytest` del entorno local puede apuntar a una ruta historica invalida; usar el interprete del venv evita ese problema.
- Ultimo resultado registrado: `33 passed`.

## RD-07 - Mensaje unico de defensa

- Fecha: mayo de 2026
- Decision: alinear README, HU, demo y tesis con la siguiente idea:

```text
BuildWise no se limita a visualizar indicadores. Integra forecast, criticidad y restricciones presupuestarias para emitir una recomendacion operativa trazable.
```

- Frase oral corta:

```text
La visualizacion es la interfaz; el nucleo metodologico es la decision trazable de compra.
```

- Motivo: separar claramente el sistema de un dashboard descriptivo.

## RD-08 - Priorizar una pantalla de decision final

- Fecha: mayo de 2026
- Decision: agregar una vista principal `Decisión final` como primera pantalla operativa del frontend.
- Motivo: reducir el tiempo hasta la primera decision y evitar que el usuario tenga que navegar por graficos o modulos tecnicos para entender que comprar ahora y que postergar.
- Alcance: no agrega nuevas reglas de negocio; consume la salida DSS ya implementada en `/compras/recomendacion-operativa`.
- Criterio UX:
  - decision visible antes que analisis;
  - lenguaje simple por defecto;
  - tarjetas por accion (`COMPRAR_AHORA`, `COMPRA_PARCIAL`, `POSTERGAR`);
  - confianza y supuestos visibles sin obligar a interpretar metricas tecnicas.
- Evidencia tecnica:
  - componente `frontend/src/features/pricing/FinalDecisionCard.jsx`;
  - nueva pestaña inicial `Decisión final`;
  - build frontend verificado con `npm run build`.

## RD-09 - Quitar referencias HU del frontend visible

- Fecha: mayo de 2026
- Decision: remover etiquetas como `HU21`, `HU22`, `HU24` y `HU28b` de los textos visibles del frontend.
- Motivo: las HU son utiles para documentacion y trazabilidad interna, pero no aportan claridad al usuario final durante la demo.
- Alcance: mantener las referencias en documentacion tecnica y de tesis, pero usar nombres funcionales en pantalla.
- Evidencia tecnica:
  - `frontend/src/features/pricing/FinalDecisionCard.jsx`;
  - busqueda `rg "HU" frontend/src` sin apariciones visibles luego del cambio.

## RD-10 - Mostrar selector de vista en Resumen y Forecast

- Fecha: mayo de 2026
- Decision: exponer `Vista actual` y `Serie historica` tambien en `Resumen` y `Forecast`, no solo en `Historial`.
- Motivo: el usuario necesita cambiar material y contexto historico sin abandonar la pantalla donde esta interpretando el resultado.
- Alcance: se reutiliza el selector existente y se mantiene el comportamiento de cada vista.
- Evidencia tecnica:
  - `frontend/src/app/App.jsx`;
  - `FiltersBar` compartido entre resumen, forecast e historial.

## RD-11 - Separar escenario de costos e horizonte individual

- Fecha: mayo de 2026
- Decision: permitir seleccionar el escenario de costos en la vista de Costos y el horizonte de recomendacion en `Analizar material`.
- Motivo: el escenario economico agregado y la decision individual responden preguntas distintas, aunque ambos usen forecast como insumo.
- Alcance:
  - Costos usa un escenario de `1` a `12` meses para resumen, optimizacion y criticidad;
  - Analizar material usa un horizonte propio de `1` a `12` meses para recomendacion y estrategia.
- Evidencia tecnica:
  - `frontend/src/features/pricing/CostPlannerCard.jsx`;
  - `frontend/src/features/pricing/PurchaseDecisionCard.jsx`.

## RD-12 - Eliminar advertencia de registros futuros en pantalla

- Fecha: mayo de 2026
- Decision: quitar del frontend el mensaje `Hay registros posteriores a hoy...` y corregir el calculo para que ignore registros futuros.
- Motivo: mostrar una advertencia sin resolver la causa confundia la demo; la solucion correcta es que el forecast use solo informacion disponible hasta la fecha de calculo.
- Alcance: el mensaje visible se elimina y la serie mensual filtra precios posteriores a `date.today()`.
- Evidencia tecnica:
  - `frontend/src/app/appData.js`;
  - `app/modules/pricing/application/forecast_service.py`;
  - prueba de cobertura actualizada en `tests/test_coverage_gaps.py`.

## RD-13 - Reemplazar umbral fijo de anomalias por Random Forest

- Fecha: mayo de 2026
- Decision: implementar deteccion de anomalias con `RandomForestRegressor` y residuo dinamico, reemplazando el umbral fijo del `8%`.
- Motivo: el criterio fijo era dificil de defender metodologicamente y fue observado por el docente.
- Alcance:
  - backend calcula precio esperado, residuo y motivo de anomalia;
  - frontend muestra un grafico con serie mensual y puntos anomalos;
  - documentacion especifica explica features, criterio IQR y limitaciones.
- Evidencia tecnica:
  - `app/modules/pricing/application/series.py`;
  - `frontend/src/features/pricing/AnomaliesCard.jsx`;
  - `frontend/src/styles.css`;
  - `docs/documentacion/ANOMALIAS_RANDOM_FOREST.md`;
  - `tests/test_series.py`.

## RD-14 - Ajustar mensajes conservadores de recomendacion

- Fecha: mayo de 2026
- Decision: separar los motivos de monitoreo cuando el modelo no esta calibrado, cuando la confiabilidad es baja y cuando la variacion no supera el umbral de decision.
- Motivo: algunas justificaciones mezclaban condiciones incompatibles y podian leerse como contradictorias.
- Alcance: no cambia el criterio economico de fondo; mejora la trazabilidad textual de la recomendacion.
- Evidencia tecnica:
  - `app/modules/pricing/application/purchase_recommendations.py`;
  - `tests/test_purchase_recommendations.py`;
  - `docs/documentacion/GLOSARIO_FUNCIONAL.md`.

## RD-15 - Consolidar documentacion funcional del proyecto

- Fecha: mayo de 2026
- Decision: agregar documentacion transversal para explicar conceptos, flujos de UI y anomalias.
- Motivo: el proyecto ya tenia documentacion por HU y decisiones, pero faltaba material de lectura directa para entender como usar y defender el sistema.
- Documentos agregados:
  - `docs/documentacion/GLOSARIO_FUNCIONAL.md`;
  - `docs/documentacion/GUIA_FLUJOS_UI.md`;
  - `docs/documentacion/ANOMALIAS_RANDOM_FOREST.md`.
- Impacto: el `README.md` queda como entrada principal y enlaza esos documentos junto con las decisiones metodologicas y operativas.

## RD-16 - Alineación de documentación con lineamientos TIF 3

- Fecha: 29 de mayo de 2026
- Decision: reestructurar el borrador de tesis y crear guías de referencia basadas en los lineamientos de la cátedra de Trabajo Final (Facultad de Ingeniería - UM).
- Motivo: asegurar que el Marco Metodológico y el Análisis de Resultados cumplan con el rigor académico exigido por los docentes (Mag. Ing. Diego Navarro / Prof. Dra. Ruth Leiton).
- Cambios realizados:
  - Creación de `docs/documentacion/GUIA_MARCO_METODOLOGICO_Y_RESULTADOS.md` como referencia permanente.
  - Consolidación de la redacción principal en `docs/documentacion/ENTREGABLE_METODOLOGIA_TIF3.md`.
  - Eliminación de borradores parciales reemplazados para evitar contradicciones metodológicas.
  - Incorporación de justificaciones técnicas explícitas (elección de FastAPI, Prophet, PostgreSQL) y separación de análisis de métricas vs. conclusiones generales.
- Evidencia: `docs/documentacion/ENTREGABLE_METODOLOGIA_TIF3.md` como documento base actualizado.
