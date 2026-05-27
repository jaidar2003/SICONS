# DISENO_EPICA_8

## Propósito del documento

Este documento define el diseno funcional inicial de la Epica 8 de `BuildWise`, orientada a la presupuestacion predictiva y la asistencia comercial. Su objetivo es transformar una necesidad de obra expresada por un cliente en un presupuesto y una recomendacion de compra justificable para los productos comercializados en el MVP.

## Marco general

- `BuildWise` opera desde el rol de un unico proveedor, por lo que esta epica no compara cotizaciones entre proveedores;
- el alcance se limita a `Cemento Portland`, `Pastina` y `Membrana Megaflex`;
- la IA interpreta lenguaje natural, identifica faltantes y puede redactar explicaciones comerciales;
- los precios, calculos de presupuesto, forecast, umbrales y acciones recomendadas deben provenir de servicios auditables del backend;
- la informacion interpretada debe ser confirmada o corregida por el usuario antes de generar una recomendacion.

---

## HU33 - Ingresar una necesidad de obra en lenguaje natural

### Objetivo

Permitir que un cliente o vendedor describa el trabajo previsto y solicite orientacion comercial sin completar inicialmente un formulario tecnico.

### Entrada esperada

- descripcion libre de la necesidad o etapa de obra;
- cantidad requerida, cuando el usuario la conozca;
- fecha objetivo de uso o compra, cuando este disponible;
- presupuesto maximo, cuando aplique.

### Restriccion MVP

La necesidad debe poder atenderse con al menos uno de los tres productos soportados. Si el pedido refiere a un producto fuera del catalogo MVP, el sistema debe informarlo sin generar una recomendacion.

---

## HU34 - Interpretar mediante IA la necesidad comercial

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

El modelo puede inferir intencion y asociar una etapa de obra a un producto soportado, pero no puede inventar cantidades, precios, fechas ni disponibilidad. Toda inferencia debe quedar visible para validacion.

---

## HU35 - Validar los datos interpretados

### Objetivo

Evitar que un presupuesto o recomendacion se apoye en campos mal interpretados o incompletos.

### Comportamiento esperado

- mostrar los campos detectados por la IA;
- permitir editar producto, cantidad, etapa, fecha objetivo y presupuesto;
- marcar los faltantes obligatorios;
- exigir confirmacion previa a ejecutar calculos comerciales.

### Datos minimos confirmados

- producto del MVP;
- cantidad requerida;
- fecha objetivo u horizonte evaluable.

---

## HU36 - Generar un presupuesto comercial

### Objetivo

Calcular un presupuesto actual para la necesidad confirmada usando los precios vigentes del proveedor.

### Salida esperada

- producto y cantidad presupuestados;
- precio unitario vigente;
- costo total actual;
- fecha de generacion;
- referencia al precio fuente utilizado;
- advertencias cuando la solicitud supere el alcance del MVP.

### Regla de diseño

El presupuesto se calcula en backend a partir de datos confirmados y precios registrados. La IA no determina importes.

---

## HU37 - Recomendar el momento de compra

### Objetivo

Contextualizar la recomendacion de compra con la necesidad comercial confirmada del cliente.

### Datos de entrada

- presupuesto generado en HU36;
- fecha objetivo u horizonte;
- forecast y metricas de error disponibles;
- etapa de obra;
- presupuesto maximo, si fue informado.

### Salida esperada

- accion sugerida (`comprar ahora`, `postergar`, `compra parcial` o `sin ventaja clara`);
- costo actual y costo proyectado;
- diferencia estimada en ARS y porcentaje;
- nivel de confianza o advertencia basada en error del modelo;
- supuestos usados para la recomendacion.

### Relacion con capacidades existentes

Esta HU no reemplaza las reglas de recomendacion de la Epica 5 ni la recomendacion contextual de `HU29`; agrega el flujo comercial que les provee una necesidad interpretada y validada.

---

## HU38 - Generar una propuesta comercial explicable

### Objetivo

Presentar al cliente o vendedor una respuesta legible que integre el presupuesto y la recomendacion calculada.

### Contenido minimo

- necesidad confirmada;
- presupuesto vigente;
- recomendacion de compra;
- impacto esperado de comprar ahora o postergar;
- confianza y limitaciones del forecast;
- datos que deberian revisarse ante cambios de fecha, cantidad o precio.

### Uso de IA

La IA puede redactar y adaptar el tono de la propuesta. Los importes, porcentajes, fechas de referencia, accion recomendada y metricas de confianza deben mantenerse vinculados a la salida estructurada del backend.

---

## Flujo del MVP

1. El cliente o vendedor describe una necesidad de obra.
2. La IA estructura el pedido e identifica datos faltantes.
3. El usuario confirma o corrige producto, cantidad, etapa y fecha.
4. El backend genera el presupuesto con precios vigentes.
5. El backend calcula la recomendacion con forecast y reglas de decision.
6. La IA presenta una propuesta comercial explicable, sin alterar los calculos.

---

## Conexion implementada

- vista `Costos > Asistente comercial IA` para describir, validar y confirmar la necesidad;
- endpoint autenticado `POST /chat/presupuestacion/interpretar` para extraccion IA restringida al catalogo MVP;
- endpoint autenticado `POST /chat/presupuestacion/propuesta` para presupuesto comercial y redaccion de propuesta;
- reutilizacion del precio comercial con margen configurado y de la recomendacion contextual de `HU29`;
- confirmacion manual obligatoria entre la interpretacion IA y los calculos comerciales.

---

## Fuera de alcance

- comparar ofertas de multiples proveedores;
- incorporar productos fuera de los tres definidos para el MVP;
- registrar la ejecucion final de la venta;
- medir ahorro o sobrecosto real posterior a la compra;
- generar ordenes de compra, reservas o integraciones transaccionales.

---

## Ubicación sugerida en la arquitectura

### domain

- validacion de productos soportados;
- reglas de presupuesto y recomendacion comercial;
- restricciones de datos obligatorios y trazabilidad.

### application

- caso de uso para interpretar y confirmar necesidades;
- orquestacion de presupuesto y recomendacion;
- armado de propuesta comercial estructurada.

### infrastructure

- cliente LLM para extraccion y redaccion;
- persistencia opcional de solicitudes y propuestas para evaluacion del MVP.

### interfaces

- endpoint para interpretar la necesidad;
- endpoint para confirmar datos y generar la propuesta;
- formulario conversacional o asistido en frontend.

---

## Criterios minimos de validacion

- procesar solicitudes de ejemplo para los tres productos del MVP;
- identificar producto, cantidad, etapa y fecha cuando esten presentes;
- pedir confirmacion cuando falten datos o exista ambiguedad;
- demostrar que presupuesto y recomendacion se obtienen desde servicios internos;
- exponer metricas de confianza del forecast en la propuesta;
- probar al menos un caso donde la recomendacion no sea comprar inmediatamente.
