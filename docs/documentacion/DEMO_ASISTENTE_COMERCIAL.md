# Demo asistente de compra

## Objetivo

Mostrar que `BuildWise` no se limita a graficos o forecast: toma una necesidad de compra de una persona o empresa que debe adquirir materiales para una obra, la valida y la convierte en presupuesto, comparacion contra precio proyectado y recomendacion accionable.

## Alcance defendible

- Productos soportados: `Cemento Portland`, `Pastina` y `Membrana Megaflex`.
- El dueño o administrador puede ver costos y configurar margenes; el comprador valida su necesidad y recibe precio final o presupuesto estimado.
- La IA interpreta lenguaje natural y redacta la propuesta final, pero solo sobre datos y calculos ya resueltos por backend.
- Los precios, forecast, umbrales, totales y decision salen de servicios del backend.
- La validacion humana ocurre antes de calcular la propuesta: el usuario puede corregir producto, cantidad, fase, fecha/horizonte, presupuesto y tolerancia al riesgo.
- El selector de producto de la vista de compra queda limitado al catalogo MVP para evitar propuestas fuera de alcance.
- Random Forest se usa para detectar anomalias historicas; no se presenta como modelo de forecasting.
- La integracion generativa puede usar la API de la facultad o Claude como fallback; cambiar de proveedor no cambia los calculos de negocio.

## Flujo recomendado

1. Entrar a `Costos > Asistente de compra IA`.
2. Escribir una necesidad de compra.
3. Ejecutar `Interpretar con IA`.
4. Revisar los datos detectados y corregirlos si hace falta.
5. Ejecutar `Validar y generar propuesta`.
6. Explicar la salida: total actual, total proyectado, diferencia estimada, decision, confianza/MAPE, nivel de calidad del dato y advertencias.

## Casos de demo

### Caso feliz

Entrada:

```text
En septiembre voy a impermeabilizar un techo y necesito 30 unidades de Membrana Megaflex. Me conviene comprar ahora?
```

Validar:

- producto: `Membrana Megaflex`;
- cantidad: `30`;
- fase: `impermeabilizacion`;
- fecha objetivo u horizonte equivalente;
- tolerancia al riesgo: `baja` o `media`.

Resultado esperado:

- el sistema calcula presupuesto actual;
- compara contra forecast;
- devuelve una decision explicada.

### Dato faltante

Entrada:

```text
Voy a hacer terminaciones con pastina mas adelante. Me conviene comprar ahora?
```

Resultado esperado:

- la interpretacion debe marcar faltantes, especialmente cantidad y fecha/horizonte;
- el usuario completa los campos antes de generar la propuesta.

### Presupuesto insuficiente

Entrada:

```text
Necesito 30 unidades de Membrana Megaflex para impermeabilizacion dentro de 3 meses, pero tengo un presupuesto maximo bajo.
```

Validar un presupuesto inferior al total actual.

Resultado esperado:

- si la senal economica favorece comprar ahora pero el presupuesto no alcanza, la decision pasa a `ESCALONAR`;
- la justificacion indica cuantas unidades puede comprar inicialmente con el presupuesto informado.

### Sin ventaja clara

Usar un caso donde la diferencia proyectada no supere el umbral de decision o la confiabilidad del forecast no habilite una accion fuerte.

Resultado esperado:

- decision `SIN_VENTAJA_CLARA`;
- explicacion asociada a umbral, MAPE/confiabilidad o diferencia marginal.

### Misma necesidad, distinta decisión

Repetir una consulta ya resuelta cambiando solo el presupuesto maximo o el horizonte.

Ejemplo:

```text
Necesito 30 unidades de Membrana Megaflex para impermeabilizacion dentro de 3 meses.
```

Probar dos variantes:

- presupuesto maximo suficiente: el sistema puede recomendar `COMPRAR_AHORA` o `ESCALONAR` segun la proyeccion;
- presupuesto maximo insuficiente o horizonte mas lejano: el sistema puede pasar a `POSTERGAR` o `SIN_VENTAJA_CLARA`.

Objetivo:

- mostrar que la decision no es decorativa y cambia con los datos de entrada;
- demostrar que el valor del MVP no esta en el texto del chat, sino en el calculo deterministico que responde a cambios reales de contexto.

## Frase corta para presentar

El asistente de compra usa IA para transformar lenguaje natural en datos validados, pero no delega la decision economica al modelo generativo. La recomendacion se calcula con precios actuales, forecast, umbrales de decision, confiabilidad y presupuesto disponible. El foco del flujo es ayudar a quien compra materiales a decidir si conviene adquirirlos ahora, postergar o escalonar la compra. Si el material no pertenece al catalogo MVP, la consulta se rechaza y no se pide al modelo que invente una respuesta.
