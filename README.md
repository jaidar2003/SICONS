<p align="center">
 <img src="frontend/bwlogo.jpeg" alt="BuildWise" width="260" />
</p>

# BuildWise

BuildWise es un sistema de apoyo a la toma de decisiones para la compra de materiales de construccion.

La idea no es solo guardar precios, sino ayudar a responder preguntas concretas:

- cuanto aumento un material
- como comparar precios cuando cambia la presentacion
- cuanto cuesta realmente por kg, metro o unidad
- como evoluciono el precio en el tiempo
- que impacto podria tener comprar ahora o mas adelante

El foco principal esta en el comprador de materiales. El administrador existe para mantener la base de datos limpia y confiable.

## Estado actual

El proyecto ya tiene:

- backend con FastAPI
- base PostgreSQL con Docker
- migraciones con Alembic
- frontend web
- login con roles
- carga de precios historicos solo para admin
- consulta de historial para cliente y admin
- normalizacion automatica de precios
- grafico historico
- filtros por material y periodo
- datos reales de cemento

## Demo local

Levantar todo:

```bash
cp .env.example .env
docker compose up -d --build
```

URLs principales:

```text
Frontend: http://localhost:3000
API: http://localhost:8000
Swagger: http://localhost:8000/docs
```

Ver estado de los servicios:

```bash
docker compose ps
```

Apagar:

```bash
docker compose down
```

## Usuarios de prueba

Admin:

```text
usuario: admin
clave: admin123
```

Puede:

- consultar historial
- ver graficos
- filtrar datos
- registrar precios historicos

Cliente:

```text
usuario: cliente
clave: cliente123
```

Puede:

- consultar historial
- ver graficos
- filtrar datos
- analizar variaciones

No puede cargar precios.

## Stack

Backend:

- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Pydantic

Frontend:

- Vite
- React
- Material UI
- Tailwind CSS
- Chart.js
- Nginx

Infra local:

- Docker Compose

## Arquitectura

El backend sigue un monolito modular con arquitectura hexagonal incremental.

```text
app/
 modules/
 auth/
 catalog/
 pricing/
 health/

 shared/
 config/
 database/
 security/
```

Cada modulo se organiza por capas:

```text
domain/
 Reglas puras del negocio.

application/
 Casos de uso y orquestacion.

infrastructure/
 Modelos SQLAlchemy, repositorios y dependencias tecnicas.

interfaces/
 Rutas FastAPI, dependencias HTTP y schemas Pydantic.
```

La regla de dependencias es:

```text
interfaces -> application -> domain
infrastructure -> application/domain
shared -> infraestructura comun reutilizable
```

Los paquetes historicos `app.api`, `app.models`, `app.schemas`, `app.services`, `app.core` y `app.db` quedan como compatibilidad temporal y reexportan desde la nueva estructura.

El frontend usa Vite + React, con componentes organizados por feature. Material UI aporta componentes y tema visual; Tailwind queda como capa utilitaria de layout/spacing.

```text
frontend/
 package.json
 vite.config.js
 tailwind.config.js
 index.html
 src/
 main.jsx
 app/
 App.jsx
 config.js
 theme.js
 features/
 admin/
 auth/
 catalog/
 layout/
 pricing/
 shared/
 api/
 components/
 utils/
```

Reglas del frontend:

```text
frontend/src/app/App.jsx compone la aplicacion.
features/* contiene componentes y API propias de cada dominio.
shared/* contiene cliente HTTP, componentes transversales y formatters.
features no deben depender entre si salvo por flujos explicitos de composicion.
shared no importa features.
```

## Conceptos principales

### Material

Representa el producto que se quiere analizar.

Ejemplos:

- Cemento Portland
- Pastina 

### Presentacion

Representa como se vende un material.

Ejemplos:

- Bolsa 25 kg
- Bolsa 50 kg
- Cano 3 m

### Precio historico

Registra un valor observado para un material, una presentacion comercial, una fuente y una fecha determinadas.

## Metodología de forecasting

### 1. Construcción del dataset

El forecasting de cemento se construye a partir de la serie historica de precios observados en la base de datos. La variable principal del modelo es `precio_promedio_normalizado`, que representa el precio promedio mensual normalizado del cemento expresado en `ARS/kg`.

La serie utilizada para entrenamiento y evaluacion debe preservar consistencia temporal, trazabilidad de fuente y una agregacion mensual homogenea, a fin de evitar comparaciones espurias entre observaciones con distinta granularidad o distinta presentacion comercial.

### 2. Normalización por kg

La unidad de analisis del modelo productivo es `ARS/kg`. Esta normalizacion permite comparar distintas presentaciones comerciales del mismo material sobre una unica escala economica.

Las equivalencias comerciales, por ejemplo bolsa de `25 kg` o bolsa de `50 kg`, se calculan exclusivamente para visualizacion, interpretacion por parte del usuario y comparacion comercial. No deben confundirse con la variable principal del forecast ni sustituir la serie base del modelo.

### 3. Baselines

La seleccion de modelos se evalua siempre contra baselines simples y reproducibles. El objetivo es distinguir entre una mejora real del desempeno predictivo y una mejora solo aparente en la forma de la curva proyectada.

En este proyecto, la plausibilidad visual del forecast no constituye un criterio suficiente para elegir un modelo. Una trayectoria visualmente razonable puede, aun asi, mostrar un peor desempeno cuando se la somete a backtesting temporal.

### 4. Prophet con regresores externos

El proyecto contempla variantes de Prophet con regresores externos, por ejemplo series mayoristas o indicadores macroeconomicos. Sin embargo, estos regresores introducen una exigencia metodologica adicional: sus valores futuros deben modelarse explicitamente y con supuestos verificables.

No corresponde promover variantes con `IPC` como modelo productivo salvo que demuestren una mejora objetiva del backtesting respecto del baseline productivo vigente. En todos los casos, los regresores futuros deben definirse, documentarse y validarse mediante backtesting temporal antes de incorporarse al flujo principal.

### 5. Backtesting y métricas

La validacion se realiza mediante backtesting temporal, priorizando horizontes compatibles con el uso real del sistema. En la actualidad, el horizonte principal de comparacion para cemento es el de `3 meses`.

Las metricas de referencia documentadas actualmente para el mejor modelo productivo son:

- `MAE`: `11.32`
- `MAPE`: `7.74%`
- efectividad informal: `92.26%`

Estas metricas deben interpretarse en conjunto y en el marco del horizonte evaluado. Ninguna decision metodologica debe apoyarse exclusivamente en una inspeccion grafica de la curva proyectada.

### 6. Confiabilidad relativa por material

Actualmente el sistema puede pronosticar tres materiales con series mensuales continuas:

- `Cemento Portland`
- `Pastina`
- `Membrana Megaflex`

Esa continuidad mensual vuelve pronosticables a los tres casos, pero la confiabilidad no es homogenea entre materiales.

| Material | Serie mensual continua | Datos reales | Datos estimados | Folds | MAPE | Efectividad informal | Confiabilidad relativa |
|---|---|---:|---:|---:|---:|---:|---|
| `Cemento Portland` | si | 1624 precios | 0 | 9 | 8.58% | 91.42% | alta |
| `Pastina` | si, `51` meses | 10 registros | 41 | 9 | 5.75% | 94.25% | media |
| `Membrana Megaflex` | si, `52` meses | 9 registros | 43 | 5 | 14.64% | 85.36% | media-baja |

Lectura metodologica:

- `Cemento Portland` es la referencia principal del sistema porque su serie es real, densa y continua.
- `Pastina` y `Membrana Megaflex` usan series hibridas con valores reales y estimados para mantener continuidad mensual.
- Sus metricas sirven como evidencia de utilidad operativa, pero no deben interpretarse con la misma solidez metodologica que las del cemento.
- Un `MAPE` bajo sobre una serie con muchos datos estimados puede sobrestimar la confiabilidad real del modelo.
- La efectividad informal se presenta solo como `100 - MAPE` y cumple una funcion comunicacional de apoyo. La metrica principal de comparacion sigue siendo `MAPE`.
- La continuidad mensual mejora la estabilidad del forecast, pero no equivale automaticamente a mayor confiabilidad real si la serie depende de muchos valores estimados.

### 6. Criterio de suficiencia del modelo

Se evaluaron distintas variantes de Prophet con regresores externos, comparando su desempeno mediante backtesting temporal. El modelo seleccionado actualmente es `prophet_oficial_mayorista`, no porque alcance un umbral arbitrario de efectividad, sino porque hasta el momento ofrece la mejor relacion entre desempeno predictivo, consistencia metodologica y defendibilidad para el objetivo del sistema.

Los resultados actualmente documentados son:

- horizonte `3 meses`: `MAE=11.32`, `MAPE=7.74%`, efectividad informal `=92.26%`, `folds=9`;
- horizonte `6 meses`: `MAE=12.53`, `MAPE=8.53%`, efectividad informal `=91.47%`, `folds=4`;
- horizonte `12 meses`: `MAE=14.32`, `MAPE=9.56%`, efectividad informal `=90.44%`, `folds=2`.

La efectividad informal se calcula como `100 - MAPE` y se utiliza solo como indicador de lectura rapida para usuarios no tecnicos. La metrica principal de comparacion metodologica es `MAPE`, porque expresa de manera directa el error porcentual relativo entre prediccion y observacion.

El horizonte de `3 meses` es actualmente el mas robusto, ya que dispone de `9 folds` y, por lo tanto, ofrece una base empirica mas amplia para comparar variantes. El horizonte de `12 meses` resulta prometedor como capacidad de proyeccion extendida, pero su interpretacion debe ser mas cautelosa porque cuenta solo con `2 folds`, lo que reduce la robustez estadistica de la comparacion.

En este contexto, la suficiencia del modelo no se define como perfeccion ni como version definitiva. Se considera suficiente en la medida en que cumple razonablemente el objetivo operativo del sistema, mantiene un error acotado y supera o iguala de forma consistente a las alternativas evaluadas hasta el momento.

Las iteraciones futuras seguiran el criterio de amesetamiento de mejoras: se continuaran evaluando ajustes mientras produzcan reducciones marginales de `MAPE` que sean materialmente relevantes y consistentes entre folds y horizontes. Si las mejoras pasan a ser pequenas, inestables o no reproducibles, el modelo actual puede considerarse metodologicamente suficiente para el alcance del trabajo.

### 7. Decisión actual del modelo

En funcion de la metodologia y del criterio de suficiencia expuestos, el modelo productivo preferido actualmente es `prophet_oficial_mayorista`, porque obtuvo el mejor resultado de backtesting a `3 meses` dentro de las variantes evaluadas hasta el momento.

Mientras una variante alternativa no mejore esas metricas de forma consistente, no debe presentarse como reemplazo productivo. Esto aplica especialmente a variantes con `IPC` u otros regresores externos cuya trayectoria futura dependa de supuestos adicionales.

### 8. Trabajo pendiente

Queda pendiente profundizar el modelado de escenarios futuros para regresores externos, fortalecer los experimentos comparativos por horizonte y consolidar una metodologia reproducible de seleccion de modelos.

En linea con el criterio de suficiencia adoptado, las proximas iteraciones deben concentrarse en:

- mejorar la definicion de escenarios futuros de regresores;
- validar cada variante con backtesting temporal consistente;
- comparar resultados por horizonte operativo;
- distinguir con claridad entre experimentacion metodologica y modelo productivo.

## Registro historico de precios

Cada registro historico documenta el precio observado de un material para una fecha, una presentacion comercial y una fuente determinadas.

Incluye:

- material
- presentacion
- fuente
- fecha
- precio original
- precio normalizado
- comprobante
- observaciones

### Normalizacion

La normalizacion permite comparar precios aunque cambie la presentacion comercial.

Los valores de ejemplo son ficticios y se utilizan unicamente para explicar el funcionamiento del sistema.

Ejemplo ilustrativo:

```text
Bolsa 25 kg = $ 5.000
Precio normalizado = 5.000 / 25 = $ 200 por kg
```

Asi se puede comparar contra una bolsa de 50 kg o contra cualquier otra presentacion.

## Endpoints utiles

Login:

```http
POST /auth/login
GET /auth/me
```

Catalogos:

```http
GET /materiales
GET /presentaciones
GET /fuentes
```

Precios:

```http
GET /precios-historicos
POST /precios-historicos
GET /materiales/{material_id}/precios
GET /materiales/{material_id}/serie-precios
```

Serie historica del cemento:

```bash
curl "http://localhost:8000/materiales/1/serie-precios?desde=2024-01-01&hasta=2024-12-31"
```

Entrenamiento inicial con Prophet sobre la serie mensual del cemento:

```bash
.venv/bin/python -m app.train_prophet_cemento
```

El script arma la serie mensual, la convierte al formato `ds`/`y` y hace un split cronologico `train`/`test` del 80/20.

## Migraciones

Aplicar migraciones:

```bash
.venv/bin/python -m alembic upgrade head
```

Ver revision actual:

```bash
.venv/bin/python -m alembic current
```

Validar modelos contra migraciones:

```bash
.venv/bin/python -m alembic check
```

## Tests

Ejecutar tests:

```bash
.venv/bin/python -m pytest -q
```

## Estructura

```text
app/
├── api/ Endpoints y dependencias HTTP
├── core/ Configuracion y seguridad
├── db/ Sesion, seed e importadores
├── models/ Modelos SQLAlchemy
├── schemas/ Schemas Pydantic
├── services/ Logica de negocio
└── main.py App FastAPI

data/
└── raw/ Archivos crudos de IPC y dolares

docs/
├── DECISIONES_TESIS.md
├── MEDICIONES_FORECASTING.md
└── DISENO_EPICA_5.md

resources/
└── branding/ Logos y assets de marca

scripts/
└── local_server.py Wrapper de uvicorn para desarrollo local

frontend/
├── index.html
├── src/
├── bwlogo.jpeg
├── favicon.jpeg
├── Dockerfile
└── nginx.conf
```

```text
db/
├── migrations/
└── seed/
```

## Vision del producto

BuildWise apunta a convertirse en una herramienta de inteligencia de compras para obras chicas y medianas.

La evolucion natural del proyecto es:

1. ordenar datos historicos
2. normalizar precios
3. analizar variaciones
4. predecir precios futuros
5. estimar impacto economico
6. comparar comprar ahora contra comprar despues

En una frase:

```text
BuildWise ayuda a anticipar aumentos de materiales y decidir mejor cuando comprar.
```

## Historias de usuario y trazabilidad funcional

Esta seccion organiza el alcance funcional del sistema en epicas e historias de usuario. Su objetivo es servir como referencia de avance del proyecto y como guia para identificar funcionalidades implementadas, parciales o pendientes.

Convencion de estado:

- `Implementada`: la funcionalidad ya aparece reflejada en el sistema o en la documentacion operativa actual.
- `Parcial`: existe soporte inicial, pero falta completar parte del flujo, la visualizacion o su consolidacion funcional.
- `Pendiente`: la funcionalidad forma parte del alcance previsto, pero no esta documentada como resuelta en el estado actual del proyecto.

### Epica 1. Gestión y preparación de datos

- `HU1` Registrar precios historicos de materiales.
Como usuario del sistema, quiero registrar precios historicos de materiales junto con su fecha para disponer de una base de datos que permita analizar su evolucion.
Estado actual: `Implementada`.

- `HU2` Consultar historial de precios de un material.
Como comprador de materiales, quiero visualizar el historial de precios de un material para entender como vario su costo en el tiempo.
Estado actual: `Implementada`.

- `HU3` Normalizar precios segun una unidad comparable.
Como usuario del sistema, quiero que los precios se expresen en una unidad comparable para poder analizar correctamente materiales cuya presentacion haya cambiado.
Estado actual: `Implementada`.

- `HU4` Seleccionar distintos materiales para su analisis.
Como comprador de materiales, quiero seleccionar distintos materiales para poder analizar y proyectar el comportamiento de cada uno por separado.
Estado actual: `Implementada`.

- `HU5` Filtrar datos por periodo.
Como comprador de materiales, quiero filtrar los datos por rango de fechas para analizar la evolucion de un material en un periodo determinado.
Estado actual: `Implementada`.

- `HU6` Consultar la fuente de los datos registrados.
Como usuario del sistema, quiero conocer la fuente de cada precio registrado para confiar en la validez de la informacion utilizada.
Estado actual: `Parcial`.

### Epica 2. Análisis y visualización

- `HU7` Visualizar precios historicos en graficos.
Como comprador de materiales, quiero ver un grafico con la evolucion historica de precios para interpretar facilmente la tendencia del material.
Estado actual: `Implementada`.

- `HU8` Comparar materiales entre si.
Como comprador de materiales, quiero comparar la evolucion de precios de distintos materiales para identificar cuales presentan mayor variacion o riesgo de aumento.
Estado actual: `Implementada`.

- `HU9` Identificar variaciones porcentuales de precios.
Como comprador de materiales, quiero ver el porcentaje de variacion de un material entre dos fechas para dimensionar cuanto aumento o disminuyo.
Estado actual: `Parcial`.

- `HU10` Detectar cambios bruscos o anomalias.
Como usuario del sistema, quiero identificar meses con aumentos o cambios atipicos para detectar comportamientos relevantes en la serie historica.
Estado actual: `Implementada`.

### Epica 3. Predicción de precios

- `HU11` Estimar el precio futuro de un material.
Como comprador de materiales, quiero ingresar un precio actual y un horizonte temporal para estimar cuanto podria costar el material en el futuro.
Estado actual: `Parcial`.

- `HU12` Visualizar la proyeccion futura junto al historico.
Como comprador de materiales, quiero ver en un mismo grafico los precios historicos y la proyeccion futura para comprender la evolucion esperada del material.
Estado actual: `Implementada`.

- `HU13` Obtener la variacion esperada entre precio actual y precio proyectado.
Como comprador de materiales, quiero conocer la diferencia y el porcentaje de variacion entre el precio actual y el estimado para evaluar el impacto economico futuro.
Estado actual: `Implementada`.

- `HU14` Estimar precios a distintos horizontes temporales.
Como comprador de materiales, quiero obtener estimaciones a `3`, `6` y `12` meses para planificar la compra segun distintas etapas de la obra.
Estado actual: `Implementada`.

- `HU15` Consultar el nivel de confianza o error del modelo.
Como usuario del sistema, quiero conocer una medida de error o fiabilidad de la prediccion para interpretar los resultados con mayor criterio.
Estado actual: `Implementada`.
Nota metodologica: la fiabilidad del modelo se documenta actualmente mediante `MAPE`, `MAE`, cantidad de `folds` y efectividad informal. La metrica principal de comparacion sigue siendo `MAPE`.

### Epica 4. Proyección de costos de obra

- `HU16` Proyectar el costo futuro segun la cantidad necesaria.
Como comprador de materiales, quiero indicar la cantidad de material que necesito para calcular cuanto podria gastar si lo compro mas adelante.
Estado actual: `Implementada`.

- `HU17` Comparar el costo de comprar ahora versus comprar despues.
Como comprador de materiales, quiero comparar el costo actual con el costo futuro estimado para decidir si me conviene comprar ahora o esperar.
Estado actual: `Implementada`.

- `HU18` Simular escenarios de compra.
Como comprador de materiales, quiero simular distintos escenarios temporales de compra para evaluar como impacta el momento de adquisicion en mi presupuesto.
Estado actual: `Implementada`.

- `HU19` Estimar el costo futuro de varios materiales de una obra.
Como comprador de materiales, quiero ingresar varios materiales y sus cantidades para proyectar el costo total estimado de una parte de la obra.
Estado actual: `Implementada`.

- `HU20` Obtener un resumen del impacto presupuestario.
Como comprador de materiales, quiero recibir un resumen del aumento estimado de costos para tomar decisiones con una vision global del presupuesto.
Estado actual: `Implementada`.

### Epica 5. Optimización de compras

- `HU21` Recomendar el mejor momento de compra.
Como comprador de materiales, quiero recibir una recomendacion sobre cuando comprar para minimizar el costo estimado de mi obra.
Estado actual: `Pendiente`.

- `HU22` Comparar estrategias de compra.
Como comprador de materiales, quiero comparar distintas estrategias de compra para decidir entre comprar todo hoy, comprar por etapas o esperar.
Estado actual: `Pendiente`.

- `HU23` Optimizar la compra bajo una restriccion presupuestaria.
Como comprador de materiales, quiero que el sistema considere un presupuesto disponible para sugerirme una estrategia de compra viable.
Estado actual: `Pendiente`.

- `HU24` Priorizar materiales criticos.
Como comprador de materiales, quiero identificar cuales materiales tienen mayor riesgo de aumento para priorizar su compra antes que otros.
Estado actual: `Implementada`.

### Epica 6. Asistencia conversacional

- `HU25` Consultar precios y proyecciones en lenguaje natural.
Como comprador de materiales, quiero hacer preguntas al sistema en lenguaje natural para obtener informacion sin navegar manualmente por graficos y tablas.
Estado actual: `Pendiente`.

- `HU26` Preguntar por un material especifico.
Como comprador de materiales, quiero consultar cuanto podria costar un material en el futuro mediante una pregunta para obtener una respuesta rapida y directa.
Estado actual: `Pendiente`.

- `HU27` Solicitar explicaciones sobre la proyeccion.
Como comprador de materiales, quiero pedirle al sistema una explicacion del resultado estimado para entender en que datos se basa la proyeccion.
Estado actual: `Pendiente`.
