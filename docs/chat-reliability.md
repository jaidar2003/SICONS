# Confiabilidad conversacional

## Limite de responsabilidad

El asistente interpreta lenguaje natural y redacta explicaciones. Precios, normalizacion, forecasts, metricas, presupuestos y decisiones provienen de casos de uso deterministas del backend. El proveedor LLM no tiene acceso a SQL ni a herramientas arbitrarias.

La presentacion comercial vigente de Cemento Portland es una bolsa de 25 kg. Los registros historicos conservan bolsas de 50 kg cuando esa fue la presentacion adquirida y toda comparacion economica usa ARS/kg.

## Flujo

1. La API carga la conversacion y su estado persistido.
2. La consulta se normaliza y se clasifica mediante reglas de alta precision.
3. Material, cantidad, unidad, presupuesto y horizonte se interpretan con origen explicito, inferido, heredado, ambiguo o faltante.
4. La recuperacion obtiene catalogo, historicos, snapshots y resultados deterministas segun la intencion.
5. El contexto recuperado se envia al proveedor como datos no ejecutables, separado del mensaje del usuario.
6. La respuesta se valida contra numeros, materiales y decisiones presentes en el contexto.
7. Una respuesta no respaldada se descarta completa y se reemplaza por una explicacion deterministica.
8. Auditoria registra intencion, fuentes, material, horizonte, proveedor, fallback, validacion y duracion.

## Contexto

Material, intencion y horizonte pueden heredarse en seguimientos breves. Un valor explicito siempre reemplaza al heredado. Cantidad y presupuesto solo se heredan dentro de la misma necesidad comercial y el mismo material; no se trasladan a una compra nueva. Un material nuevo invalida cantidades y presupuestos anteriores. Permisos, decisiones, fuentes y fechas calculadas nunca se heredan desde texto del asistente.

## Aclaraciones

Forecast y recomendacion requieren material y horizonte. Presupuesto requiere material, pero cantidad y presupuesto pueden llegar en turnos separados. Un valor ambiguo, un horizonte fuera de 1 a 12 meses o varios materiales candidatos requiere confirmacion. No se solicita informacion que el catalogo o el estado conversacional ya resuelven.

## Evaluacion

`tests/fixtures/chat_evaluation_cases.json` contiene 24 escenarios con cinco variantes cada uno. Se expanden a 120 casos deterministas. La evaluacion mide intencion, material, cantidad, unidad, normalizacion, presupuesto, horizonte, contexto y seguridad; tambien produce una matriz de confusion y la lista de fallos.

```bash
PYTHONPATH=. .venv/bin/python scripts/evaluate_chat.py
pytest -m chat_evaluation -o addopts=''
```

La evaluacion externa con proveedores reales queda fuera de CI y debe ejecutarse solo con variables explicitas del proveedor. Nunca se registran claves ni prompts con datos sensibles.

## Limitaciones

La fecha objetivo comercial continua usando el parser existente de propuestas. La interpretacion estructurada general no expone metadatos nuevos en HTTP para preservar OpenAPI. La validacion numerica es conservadora: ante duda descarta la redaccion generativa completa. No se modificaron modelos, selector, regresores, MAPE ni reglas economicas.
