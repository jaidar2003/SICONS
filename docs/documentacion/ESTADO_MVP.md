# Estado del MVP

## Resumen ejecutivo

`BuildWise` se encuentra en estado de MVP defendible como sistema de soporte a decisiones de compra de materiales de construccion.

El sistema ya permite:

- cargar y consultar materiales, presentaciones, fuentes y precios historicos;
- normalizar precios para series comparables;
- generar forecast por material y horizonte;
- exponer metricas de modelo, seleccion y confiabilidad;
- detectar anomalias historicas;
- convertir forecast en recomendaciones de compra;
- comparar estrategias temporales;
- optimizar compras bajo restriccion presupuestaria;
- usar un asistente IA unificado con RAG operativo y presupuestacion guiada.

## Alcance implementado

### Backend

- API FastAPI modular.
- PostgreSQL con migraciones Alembic.
- Autenticacion y roles.
- Catalogo de materiales, presentaciones y fuentes.
- Precios historicos con origen de dato y normalizacion.
- Indices externos para regresores.
- Forecast con Prophet y seleccion de modelo.
- Recomendaciones de compra.
- Comparacion de estrategias.
- Optimizacion con `PuLP`.
- Deteccion de anomalias con Random Forest.
- Asistente conversacional con proveedores intercambiables y fallback.
- RAG operativo sobre datos del backend.
- Clasificacion formal de intenciones: `HISTORICO`, `FORECAST`, `RECOMENDACION`, `PRESUPUESTO`, `CATALOGO`, `ADMIN` y `FUERA_ALCANCE`.
- Auditoria persistente de consultas del asistente en `audit_logs`.
- Endpoint admin `/chat/auditoria` para consultar trazabilidad del asistente.
- Endpoint admin `/chat/auditoria/determinismo` para medir estabilidad del RAG sobre consultas repetidas.

### Frontend

- Vistas `Resumen`, `Forecast`, `Costos`, `Asistente IA`, `Historial` y `Admin`.
- Chips de trazabilidad RAG en el asistente.
- Panel integrado de validacion de necesidad de compra.
- Visualizacion de historicos, forecast, anomalias y escenarios de costo.
- Administracion de usuarios, margenes y configuracion de IA para admin.
- Panel admin de auditoria del asistente IA con filtros por intencion y fallback.
- Score de determinismo RAG visible en el panel de auditoria IA.

### Datos del MVP

Materiales principales:

- `Cemento Portland`;
- `Pastina`;
- `Membrana Megaflex`.

El material metodologicamente mas fuerte es `Cemento Portland`, por densidad y continuidad de serie. `Pastina` y `Membrana Megaflex` demuestran extensibilidad, pero deben explicarse con cautela por mayor proporcion de datos hibridos.

## Fuera de alcance

No forman parte del MVP:

- multiples proveedores por material;
- stock real;
- flete, impuestos o descuentos comerciales complejos;
- restricciones logisticas o calendario de obra completo;
- sustitucion automatica de materiales;
- decision autonoma sin validacion humana;
- RAG documental/vectorial como fuente principal;
- metricas analiticas avanzadas de auditoria del asistente.

## Evidencia tecnica

Verificaciones recientes:

```bash
.venv/bin/python -m pytest -q --no-cov
```

Resultado:

```text
374 passed
```

Verificaciones de runtime:

- API health: `GET http://localhost:8000/health` devuelve `{"status":"ok"}`;
- frontend: `http://localhost:3000` responde `200 OK`;
- servicios Docker activos: `postgres`, `api`, `frontend`.

## Checklist end-to-end de demo

### 1. Preparacion

- [ ] Levantar servicios con `docker compose up -d --build`.
- [ ] Confirmar API en `http://localhost:8000/health`.
- [ ] Abrir frontend en `http://localhost:3000`.
- [ ] Iniciar sesion con usuario de prueba.

Usuarios:

```text
admin / admin123
cliente / cliente123
```

### 2. Resumen

- [ ] Entrar a `Resumen`.
- [ ] Seleccionar `Cemento Portland`.
- [ ] Mostrar lectura ejecutiva, metricas y recomendacion rapida.
- [ ] Cambiar a `Pastina` o `Membrana Megaflex` para mostrar que la lectura depende del material.

### 3. Forecast

- [ ] Entrar a `Forecast`.
- [ ] Revisar `Proyeccion`.
- [ ] Cambiar horizonte.
- [ ] Revisar `Modelo`.
- [ ] Explicar `MAPE`, `MAE`, folds, confiabilidad y seleccion.

### 4. Asistente IA con RAG operativo

Consulta sugerida:

```text
cual fue el ultimo precio de cemento?
```

Validar:

- [ ] aparece respuesta del asistente;
- [ ] aparece chip `RAG backend`;
- [ ] aparece intencion clasificada;
- [ ] aparece material resuelto;
- [ ] aparecen fuentes, por ejemplo `catalogo.materiales` y `precios_historicos`.

### 5. Asistente IA con presupuestacion guiada

Consulta sugerida:

```text
necesito comprar 500 kg de cemento en 6 meses
```

Validar:

- [ ] se abre panel de validacion editable;
- [ ] se detecta material;
- [ ] se detecta cantidad;
- [ ] se puede corregir fase, horizonte, presupuesto y riesgo;
- [ ] `Validar y generar propuesta` devuelve total actual, total proyectado, diferencia y decision.

### 6. Costos

- [ ] Entrar a `Costos`.
- [ ] Usar `Analizar material` para calcular recomendacion individual.
- [ ] Usar `Comparar meses` para ver sensibilidad temporal.
- [ ] Usar `Armar presupuesto` para cargar multiples materiales.
- [ ] Ejecutar optimizacion presupuestaria.
- [ ] Usar `Que comprar` para mostrar recomendacion operativa consolidada.

### 7. Historial y anomalias

- [ ] Entrar a `Historial`.
- [ ] Revisar variacion entre fechas.
- [ ] Ver grafico historico.
- [ ] Abrir `Anomalias`.
- [ ] Explicar que Random Forest marca residuo atipico, no un umbral fijo.

### 8. Admin

Con usuario admin:

- [ ] Revisar configuracion de IA.
- [ ] Revisar auditoria del asistente IA.
- [ ] Revisar usuarios.
- [ ] Revisar margenes comerciales.

### 9. Logout

- [ ] Cerrar sesion.
- [ ] Confirmar que el sistema vuelve a la pantalla de login.

## Criterio de cierre

El MVP queda defendible si la demo permite observar:

- que dato se consulta;
- que fuente interna lo respalda;
- que material y horizonte se resolvieron;
- que forecast y confianza aplican;
- que decision economica recomienda el sistema;
- que restricciones presupuestarias respeta;
- que advertencias o limites deben considerarse;
- que la IA redacta e interpreta, pero no inventa calculos criticos.

## Prioridades posteriores al MVP

1. Persistencia o reconstruccion del estado conversacional luego de recargar la pagina.
2. Manejo asincronico de forecasts pesados.
3. Metricas agregadas sobre auditoria: volumen por intencion, latencia p95, tasa de fallback y consultas fuera de alcance.
4. RAG documental complementario para documentacion metodologica.
5. Ampliacion de intenciones con clasificador entrenable si el volumen de consultas lo justifica.
