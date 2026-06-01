# DISENO_EPICA_6

## Propósito del documento

Este documento resume el diseno funcional inicial de la Epica 6 de `BuildWise`, orientada a la asistencia conversacional acotada. Su objetivo es exponer capacidades del sistema en lenguaje natural sin reemplazar la logica de negocio ya existente.

## Marco general

- la capa conversacional no calcula desde cero;
- consume datos, forecast y reglas ya resueltas en backend;
- el LLM actua como interfaz y sintetizador, no como fuente unica de verdad;
- si el material o la consulta quedan fuera del catalogo soportado, el backend corta la respuesta y no delega al modelo una estimacion inventada.

---

## HU25 - Consultar precios y proyecciones en lenguaje natural

### Objetivo

Permitir preguntas abiertas sobre precios y proyecciones sin navegar manualmente por tablas y graficos, siempre dentro del universo de datos propios cargados en BuildWise.

### Salida esperada

- respuesta textual clara;
- uso de datos reales del sistema;
- referencia al material y horizonte consultado.

---

## HU26 - Preguntar por un material especifico

### Objetivo

Permitir consultas directas del tipo “cuanto podria costar X en 6 meses”.

### Salida esperada

- respuesta puntual por material;
- precio actual y proyectado;
- variacion esperada.

---

## HU27 - Solicitar explicaciones sobre la proyeccion

### Objetivo

Permitir que el sistema explique de manera comprensible en que se basa una estimacion.

### Salida esperada

- explicacion resumida;
- horizonte usado;
- referencia a metricas de error o confiabilidad cuando corresponda.

---

## HU27b - Conversar con el asistente y recibir una recomendacion accionable de compra

### Objetivo

Permitir que el usuario consulte en lenguaje natural una decision de compra y reciba una respuesta accionable basada en servicios internos de forecast, comparacion economica, recomendacion y optimizacion.

### Salida esperada

- accion sugerida segun el flujo ejecutado: comprar ahora, esperar/monitorear, postergar, compra parcial, escalonar o sin ventaja clara;
- ahorro o sobrecosto estimado;
- nivel de confianza o advertencia;
- referencia a los supuestos usados.

---

## Criterio de integracion

La implementacion minima de esta epica deberia:

- consultar servicios internos ya existentes;
- armar contexto estructurado;
- llamar al modelo de chat;
- devolver una respuesta explicada sin inventar datos no presentes.

No corresponde usar esta capa para sustituir:

- calculos de forecast;
- reglas de compra;
- optimizacion presupuestaria.

---

## Ubicación sugerida en la arquitectura

### application

- orquestador conversacional;
- armado de contexto y prompts.

### infrastructure

- cliente del proveedor LLM;
- integracion con `OPENAI_BASE_URL`, `OPENAI_API_KEY` y `OPENAI_MODEL`.

### interfaces

- endpoint de chat o consulta conversacional;
- schema de pregunta y respuesta.

## Conexion base implementada

Se incorpora una primera integracion OpenAI-compatible para habilitar la conversacion sin delegar calculos de negocio al modelo:

- endpoint autenticado `POST /chat/consultas`;
- proveedor configurado mediante `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL` y `OPENAI_TIMEOUT_SECONDS`;
- llamada HTTP a `{OPENAI_BASE_URL}/chat/completions`;
- alternativa nativa Claude mediante `CHAT_PROVIDER=anthropic`, con llamada a `{ANTHROPIC_BASE_URL}/messages`;
- rechazo local de consultas evidentemente ajenas al dominio, sin consumir el proveedor;
- vista de conversacion IA disponible en el frontend.

Ejemplo de request:

```json
{
  "pregunta": "Que significa la confiabilidad del forecast de cemento?"
}
```

Una consulta fuera de alcance devuelve `aceptada: false` y `proveedor_utilizado: false`.

### Operaciones conversacionales implementadas

La capa conversacional arma contexto con los servicios internos y permite:

- consultar y explicar forecast y recomendacion del material seleccionado;
- resumir historial de precios;
- comparar estrategias de compra y simular horizontes;
- priorizar materiales y optimizar un presupuesto;
- generar la decision final multi-material;
- listar usuarios y margenes unicamente cuando el usuario autenticado es administrador;
- preparar cargas de precios y cambios administrativos unicamente para administradores, ejecutandolos solo luego de una confirmacion explicita (`CONFIRMAR`);
- rechazar localmente pedidos administrativos de usuarios cliente, sin enviarlos al proveedor LLM.

El LLM interpreta la solicitud y explica el resultado; los valores, decisiones y transacciones se resuelven en servicios de BuildWise. Si el pedido refiere a un material fuera del MVP, la consulta se rechaza localmente sin intentar inferir un precio externo.

### Configuracion con Claude

Para usar una API key de Anthropic, configurar localmente:

```env
CHAT_PROVIDER=anthropic
ANTHROPIC_API_KEY=replace-with-your-anthropic-key
ANTHROPIC_BASE_URL=https://api.anthropic.com/v1
ANTHROPIC_MODEL=replace-with-an-enabled-claude-model
ANTHROPIC_VERSION=2023-06-01
ANTHROPIC_MAX_TOKENS=1024
```

La clave debe quedar solamente en `.env`, no en archivos versionados.
