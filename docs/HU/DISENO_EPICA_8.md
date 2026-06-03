# DISENO_EPICA_8

## Propósito del documento

Este documento define el diseno funcional inicial de la Epica 8 de `BuildWise`, orientada a la presupuestacion predictiva y la asistencia de compra. Su objetivo es transformar una necesidad de obra expresada por un comprador en un presupuesto estimado y una recomendacion de compra justificable para los productos del MVP.

## Marco general

- `BuildWise` esta enfocado en quien necesita comprar materiales para una obra; el dueño o administrador del sistema puede usarlo para gestionar costos, margenes y precios finales, pero el flujo de recomendacion se orienta a la decision de compra;
- el administrador puede ver precios de costo y configurar margenes; el comprador debe ver precios finales o presupuestos estimados;
- esta epica no compara cotizaciones entre multiples proveedores;
- el alcance se limita a `Cemento Portland`, `Pastina` y `Membrana Megaflex`;
- la IA interpreta lenguaje natural, identifica faltantes y puede redactar explicaciones orientadas a la decision de compra, pero no decide ni calcula importes por su cuenta;
- los precios, calculos de presupuesto, forecast, umbrales y acciones recomendadas deben provenir de servicios auditables del backend;
- la informacion interpretada debe ser validada o corregida por el usuario antes de generar una recomendacion.
- el presupuesto del MVP se calcula con precios registrados y cantidades confirmadas; impuestos, flete, descuentos y stock minimo quedan fuera del calculo base hasta que se formalicen como reglas del dominio;
- la salida debe dejar visible el nivel de calidad o confiabilidad del dato cuando el material tenga una serie historica debil o hibrida.

## Criterio metodologico

El core de esta epica no es el proveedor generativo. El nucleo esta formado por los datos historicos de la aplicacion, el forecast entrenado/calibrado con esos datos, la deteccion de anomalias con Random Forest, el armador de presupuesto y las reglas de recomendacion. La IA generativa solo puede interpretar la necesidad escrita por el usuario o redactar la explicacion final.

Esta decision aumenta el determinismo del sistema: los importes, diferencias proyectadas y acciones recomendadas salen de servicios internos. No se aceptan valores calculados por prompt ni conocimiento general del LLM. Si se reemplaza el proveedor generativo, el presupuesto y la recomendacion deben seguir funcionando.

---

## HU33 - Ingresar una necesidad de obra en lenguaje natural

### Objetivo

Permitir que un comprador describa el trabajo previsto y solicite orientacion de compra sin completar inicialmente un formulario tecnico.

### Entrada esperada

- descripcion libre de la necesidad o etapa de obra;
- cantidad requerida, cuando el usuario la conozca;
- fecha objetivo de uso o compra, cuando este disponible;
- presupuesto maximo, cuando aplique.

### Restriccion MVP

La necesidad debe poder atenderse con al menos uno de los tres productos soportados. Si el pedido refiere a un producto fuera del catalogo MVP, el sistema debe informarlo sin generar una recomendacion.

---

## HU34 - Interpretar mediante IA la necesidad de compra

### Objetivo

Convertir el pedido en lenguaje natural en datos estructurados utilizables para presupuestar y recomendar.

### Campos a identificar

- `producto` o productos compatibles con la necesidad;
- `cantidad`;
- `etapa_obra` (por ejemplo, estructura, terminaciones o impermeabilizacion);
- `fecha_objetivo`;
- `presupuesto_maximo`, si fue informado;
- `datos_faltantes` o ambiguedades que impidan calcular.

### Uso de IA

El modelo puede inferir intencion y asociar una etapa de obra a un producto soportado, pero no puede inventar cantidades, precios, fechas ni disponibilidad. Toda inferencia debe quedar visible para validacion. Si la consulta sale del catalogo MVP, el sistema debe rechazarla en backend en lugar de pedirle al modelo que estime desde conocimiento general.

---

## HU35 - Validar los datos interpretados

### Objetivo

Evitar que un presupuesto o recomendacion se apoye en campos mal interpretados o incompletos.

### Comportamiento esperado

- mostrar los campos detectados por la IA;
- permitir editar producto, cantidad, etapa, fecha objetivo y presupuesto;
- marcar los faltantes obligatorios;
- exigir validacion previa a ejecutar calculos de presupuesto y recomendacion.

### Datos minimos validados

- producto del MVP;
- cantidad requerida;
- fecha objetivo u horizonte evaluable.

---

## HU36 - Generar un presupuesto estimado

### Objetivo

Calcular un presupuesto actual para la necesidad validada usando los precios vigentes disponibles en el sistema.

### Salida esperada

- producto y cantidad presupuestados;
- precio unitario vigente;
- costo total actual;
- fecha de generacion;
- referencia al precio fuente utilizado;
- advertencias cuando la solicitud supere el alcance del MVP.

### Regla de diseño

El presupuesto se calcula en backend a partir de datos validados y precios registrados. La IA generativa no determina importes. El armador de presupuesto forma parte del core de la solucion porque convierte datos y forecast en impacto economico concreto para la compra.

---

## HU37 - Recomendar el momento de compra

### Objetivo

Contextualizar la recomendacion de compra con la necesidad validada del comprador.

### Datos de entrada

- presupuesto generado en HU36;
- fecha objetivo u horizonte;
- forecast y metricas de error disponibles;
- etapa de obra;
- presupuesto maximo, si fue informado.

### Salida esperada

- accion sugerida (`comprar ahora`, `postergar`, `escalonar` o `sin ventaja clara`);
- costo actual y costo proyectado;
- diferencia estimada en ARS y porcentaje;
- nivel de confianza o advertencia basada en error del modelo;
- supuestos usados para la recomendacion.

### Relacion con capacidades existentes

Esta HU no reemplaza las reglas de recomendacion de la Epica 5 ni la recomendacion contextual de `HU29`; agrega el flujo de compra que les provee una necesidad interpretada y validada.

---

## HU38 - Generar una propuesta de compra explicable

### Objetivo

Presentar al comprador una respuesta legible que integre el presupuesto estimado y la recomendacion calculada.

### Contenido minimo

- necesidad validada;
- presupuesto vigente;
- recomendacion de compra;
- impacto esperado de comprar ahora o postergar;
- confianza y limitaciones del forecast;
- datos que deberian revisarse ante cambios de fecha, cantidad o precio.

### Uso de IA

La IA puede redactar y adaptar el tono de la propuesta. Los importes, porcentajes, fechas de referencia, accion recomendada y metricas de confianza deben mantenerse vinculados a la salida estructurada del backend. La propuesta nunca toma precios externos ni decisiones libres del modelo generativo.

---

## Flujo del MVP

1. El comprador describe una necesidad de obra.
2. La IA estructura el pedido e identifica datos faltantes.
3. El usuario valida o corrige producto, cantidad, etapa y fecha.
4. El backend genera el presupuesto con precios vigentes.
5. El backend calcula la recomendacion con forecast y reglas de decision.
6. La IA presenta una propuesta de compra explicable, sin alterar los calculos.

---

## Conexion implementada

- vista `Costos > Asistente de compra IA` para describir y validar la necesidad antes de calcular;
- endpoint autenticado `POST /chat/presupuestacion/interpretar` para extraccion IA restringida al catalogo MVP;
- la respuesta de interpretacion expone `requiere_validacion = true` antes de calcular;
- endpoint autenticado `POST /chat/presupuestacion/propuesta` para presupuesto estimado y redaccion de propuesta;
- reutilizacion del precio vigente calculado y de la recomendacion contextual de `HU29`;
- validacion manual obligatoria entre la interpretacion IA y los calculos de recomendacion.

---

## Fuera de alcance

- comparar ofertas de multiples proveedores;
- incorporar productos fuera de los tres definidos para el MVP;
- registrar la ejecucion final de la compra;
- medir ahorro o sobrecosto real posterior a la compra;
- generar ordenes de compra, reservas o integraciones transaccionales.

---

## Ubicación sugerida en la arquitectura

### domain

- validacion de productos soportados;
- reglas de presupuesto y recomendacion de compra;
- restricciones de datos obligatorios y trazabilidad.

### application

- caso de uso para interpretar y validar necesidades;
- orquestacion de presupuesto y recomendacion;
- armado de propuesta de compra estructurada.

### infrastructure

- cliente LLM para extraccion y redaccion;
- persistencia opcional de solicitudes y propuestas para evaluacion del MVP.

### interfaces

- endpoint para interpretar la necesidad;
- endpoint para recibir datos validados y generar la propuesta;
- formulario conversacional o asistido en frontend.

---

## Criterios minimos de validacion

- procesar solicitudes de ejemplo para los tres productos del MVP;
- identificar producto, cantidad, etapa y fecha cuando esten presentes;
- pedir validacion o correccion cuando falten datos o exista ambiguedad;
- demostrar que presupuesto y recomendacion se obtienen desde servicios internos;
- exponer metricas de confianza del forecast en la propuesta;
- probar al menos un caso donde la recomendacion no sea comprar inmediatamente.
