# TRABAJO INTEGRADOR FINAL 3 (TIF 3)

# PARTE 2: MARCO METODOLÓGICO Y ANÁLISIS DE RESULTADOS

---

# CARÁTULA

**[LOGO DE LA FACULTAD DE INGENIERÍA - UNIVERSIDAD DE MENDOZA]**

<br>

# BuildWise (SICONS): Sistema de Soporte a la Decisión para el Análisis y Proyección de Precios de Materiales de Construcción

## Estudiante: Aidar, Juan Manuel

## DNI: [INSERTAR DNI]

## Docente a cargo: Mag. Ing. Diego Navarro

## Cátedra: Trabajo Integrador Final 3 (TIF 3)

## Carrera: Ingeniería en Informática

## Año de cursado: 2026

## Sede: Central / Mendoza

## Fecha de entrega: 29 de mayo de 2026

---

# PAUTAS FORMALES

**Tipografía sugerida:** Calibri  
**Tamaño de cuerpo:** 14  
**Interlineado:** 1,15  
**Márgenes:** 3 cm izquierdo y superior; 2 cm derecho e inferior  
**Alineación:** texto justificado  
**Estilo de redacción:** voz impersonal técnica

---

# ÍNDICE GENERAL

1. **CAPÍTULO 1: DESARROLLO DE INGENIERÍA**
   - 1.1 Metodología de desarrollo adoptada
   - 1.2 Criterio de éxito del MVP
   - 1.3 Arquitectura general del sistema
   - 1.4 Tecnologías, herramientas y justificación técnica
   - 1.5 Diseño de datos, normalización y reproducibilidad
   - 1.6 Desarrollo del módulo de forecasting
   - 1.7 Selector de modelos y política de fallback
   - 1.8 Detección de anomalías con Random Forest
   - 1.9 Capa de decisión económica y DSS
   - 1.10 Núcleo de IA no generativa, determinismo y armador de presupuesto
   - 1.11 Asistente de compra e integración con LLM
   - 1.12 Seguridad, roles y despliegue
   - 1.13 Iteraciones, aprendizajes y decisiones metodológicas
   - 1.14 Trazabilidad entre objetivos, componentes y evidencia
   - 1.15 Estrategia de verificación y aseguramiento de calidad
2. **CAPÍTULO 2: ANÁLISIS DE RESULTADOS**
   - 2.1 Presentación de resultados en bruto
   - 2.2 Descripción de los datos observados
   - 2.3 Interpretación de resultados en relación con los objetivos
   - 2.4 Discrepancias y comportamientos inesperados
   - 2.5 Limitaciones del análisis
3. **FUENTES BIBLIOGRÁFICAS**

---

# CAPÍTULO 1: DESARROLLO DE INGENIERÍA

El presente capítulo constituye el núcleo procedimental del Trabajo Final de Integración. Su objetivo no es enumerar tareas ni reproducir historias de usuario, sino demostrar que el desarrollo de BuildWise se apoyó en decisiones metodológicas y técnicas justificadas. Se explica qué se construyó, por qué se eligió una determinada estrategia de desarrollo, cómo se organizaron los componentes del sistema, qué alternativas fueron consideradas y de qué manera se validó cada decisión relevante.

BuildWise es un sistema de soporte a la decisión orientado a personas, profesionales o empresas que necesitan comprar materiales de construcción en un contexto de alta volatilidad económica. El sistema integra datos históricos, normalización de precios, modelos de forecasting, detección de anomalías, recomendaciones de compra, optimización presupuestaria y una capa complementaria de asistencia conversacional. El alcance del MVP se limita a tres materiales: `Cemento Portland`, `Pastina` y `Membrana Megaflex`. Esta delimitación fue intencional: permitió concentrar el esfuerzo metodológico en construir un flujo completo y verificable, en lugar de ampliar el catálogo sin poder defender la calidad de los datos y de los modelos.

El núcleo de inteligencia artificial del proyecto no está basado en un modelo generativo externo como Gemini, Claude o GPT. El core se apoya en modelos y reglas ejecutadas sobre datos propios de la aplicación: forecasting entrenado y validado con series históricas, detección de anomalías con Random Forest, selección de modelos por material y horizonte, y optimización presupuestaria. La IA generativa, cuando se utiliza, cumple un rol periférico: interpreta lenguaje natural o redacta explicaciones, pero no inventa precios, no calcula el presupuesto y no decide la acción recomendada.

Para evitar ambigüedad metodológica, el sistema se separa en dos capas bien definidas:

| Capa | Responsabilidad | Puede calcular precios | Puede decidir |
|---|---|---|---|
| Core determinístico | Forecast, anomalías, presupuesto, recomendación, optimización | Si | Si |
| Capa conversacional LLM | Interpretar pedidos y redactar explicaciones | No | No |

Esta separación es el rasgo más defendible del proyecto: la IA generativa no consulta conocimiento general para completar precios faltantes ni para inferir decisiones económicas. Solo actúa sobre un contexto estructurado generado por BuildWise. Si un material no existe en el catálogo del MVP, el sistema no le pide al LLM que lo invente; responde que no hay datos suficientes.

El sistema contempla dos vistas sobre el mismo problema económico. El administrador o dueño del sistema puede consultar precios de costo, configurar márgenes y mantener datos base. El comprador consulta precios finales o presupuestos estimados y recibe recomendaciones de compra. De esta manera, la lógica de decisión es compartida, pero la información visible se adapta al rol: el costo queda reservado para administración y el precio final se expone al usuario comprador.

La pregunta de ingeniería que guía este desarrollo puede formularse de la siguiente manera: ¿cómo convertir series históricas de precios de materiales en decisiones de compra trazables, explicables y metodológicamente defendibles? La solución no se limita a mostrar gráficos ni a una interfaz conversacional. El sistema fue diseñado para transformar datos históricos propios en una recomendación accionable: comprar ahora, postergar, escalonar o asignar presupuesto entre varios materiales según forecast, criticidad y restricción económica.

## 1.1 Metodología de desarrollo adoptada

Se adoptó una metodología ágil basada en prototipado evolutivo. Esta elección se justifica por la naturaleza experimental del proyecto. En un sistema que incorpora forecasting, backtesting, selección de modelos y recomendación económica, no era razonable definir toda la solución por adelantado mediante una metodología rígida en cascada. La calidad del sistema dependía de resultados empíricos que debían observarse durante el desarrollo: errores de predicción, comportamiento de regresores, estabilidad por horizonte, confiabilidad relativa de cada material y utilidad de las recomendaciones generadas.

El prototipado evolutivo permitió partir de un núcleo funcional mínimo y ampliarlo progresivamente. La primera base del sistema fue la persistencia de materiales, fuentes, presentaciones y precios históricos. Luego se incorporó la normalización de precios, el armado de series mensuales, el primer forecast, la comparación de variantes con regresores, la selección de modelos, la detección de anomalías, la recomendación de compra y, finalmente, el asistente de compra. Cada capa nueva se apoyó sobre la anterior, evitando introducir complejidad antes de haber validado la necesidad metodológica.

La metodología adoptada combinó tres principios. El primero fue la entrega incremental: cada sprint debía dejar una capacidad ejecutable, testeable o demostrable. El segundo fue la validación empírica: las decisiones de forecasting no se tomaron por apariencia visual de la curva, sino por métricas de backtesting temporal. El tercero fue la trazabilidad: cada decisión técnica relevante debía poder explicarse a partir de una necesidad funcional, una alternativa descartada y una justificación.

Esta elección metodológica fue especialmente importante en el tratamiento de anomalías. Originalmente, el sistema podía haber marcado variaciones bruscas mediante un porcentaje fijo, por ejemplo un aumento mensual superior al 8%. Sin embargo, ese criterio resultaba débil para una economía inflacionaria, porque un mismo porcentaje puede ser normal para un material y atípico para otro. La observación de esa limitación durante el desarrollo llevó a reemplazar el umbral fijo por un detector basado en Random Forest y residuos dinámicos. Este cambio ilustra el valor del prototipado: una primera solución simple permitió descubrir un problema metodológico y evolucionar hacia una alternativa más defendible.

El proyecto también incorporó prácticas de aseguramiento de calidad desde las primeras etapas. Las reglas de negocio, los cálculos de recomendación, la optimización, los endpoints, el procesamiento de series y la asistencia de compra cuentan con pruebas automatizadas. Esto fue necesario porque el sistema combina múltiples responsabilidades: persistencia, cálculo económico, inferencia estadística, interfaz web e integración con proveedores LLM. Sin pruebas, cada ajuste en un componente podía romper silenciosamente otro flujo.

## 1.2 Criterio de éxito del MVP

El criterio de éxito del MVP no se definió como “tener un asistente conversacional” ni como “mostrar gráficos de precios”. El objetivo operativo fue que el sistema pudiera tomar una necesidad o escenario de compra y devolver una recomendación trazable, basada en datos históricos, forecast, confianza del modelo y restricciones económicas.

Para considerar exitoso el MVP se definieron las siguientes condiciones:

- el sistema debe cargar y consultar precios históricos para los materiales definidos;
- los precios deben normalizarse a una unidad comparable;
- el sistema debe generar forecast para los materiales soportados;
- la salida de forecast debe exponer métricas de error o confiabilidad;
- debe existir una capa de recomendación que traduzca forecast en decisión;
- debe poder evaluarse un presupuesto limitado;
- la interfaz debe permitir recorrer datos, forecast, costos, recomendaciones y anomalías;
- debe diferenciar la visibilidad de precios según rol, separando precio de costo administrativo y precio final para compra;
- la capa de IA generativa no debe formar parte del núcleo decisorio: solo puede interpretar o redactar sobre resultados calculados por backend.

La restricción a tres productos fue una decisión de alcance. `Cemento Portland` se tomó como referencia metodológica principal porque cuenta con la serie real más fuerte, densa y continua. `Pastina` y `Membrana Megaflex` se incluyeron para demostrar que la arquitectura puede extenderse a otros materiales, pero se documentó que sus series son híbridas y, por lo tanto, sus métricas deben interpretarse con mayor cautela. Esta distinción evita sobregeneralizar el desempeño del sistema.

## 1.3 Arquitectura general del sistema

La arquitectura de BuildWise se organizó como un monolito modular con separación por capas. Esta decisión buscó equilibrar dos necesidades: mantener bajo control la complejidad del MVP y, al mismo tiempo, evitar que las reglas de negocio quedaran mezcladas con rutas HTTP, modelos de base de datos o componentes visuales.

La estructura conceptual se divide en las siguientes capas:

1. **Interfaces:** expone rutas HTTP, esquemas de entrada/salida y dependencias de autenticación.
2. **Application:** contiene casos de uso, orquestación de reglas, forecast, recomendaciones y asistencia de compra.
3. **Domain:** define contratos, excepciones y reglas de negocio independientes de infraestructura.
4. **Infrastructure:** implementa persistencia, modelos SQLAlchemy, clientes externos y adaptadores.
5. **Frontend:** consume la API y presenta flujos funcionales para usuarios administradores y compradores, con distinta visibilidad de precios según rol.

Esta organización permitió que el motor de forecasting no dependiera directamente de la interfaz web, y que la interfaz no conociera detalles de entrenamiento o backtesting. Por ejemplo, el endpoint de forecast recibe un `material_id` y un horizonte, pero la resolución interna puede derivar una `material_key`, aplicar un selector de modelo, reutilizar snapshots o calcular el forecast sin alterar el contrato público.

[INSERTAR DIAGRAMA DE ARQUITECTURA POR CAPAS]

El flujo general de datos puede resumirse así: los precios históricos se cargan y normalizan; luego se agrupan en series mensuales; estas series alimentan el motor de forecast; la salida del forecast es utilizada por reglas de recomendación y por modelos de optimización; finalmente, la interfaz y el asistente de compra presentan el resultado al usuario con explicaciones y advertencias.

La decisión de utilizar un monolito modular en lugar de microservicios se justifica por el tamaño y etapa del proyecto. Separar forecasting, catálogo, autenticación, chat y recomendaciones en servicios independientes habría aumentado la complejidad operativa sin aportar un beneficio proporcional al MVP. En cambio, la modularización interna conserva límites claros y deja abierta la posibilidad de extraer servicios en una etapa futura, si el volumen o las necesidades de despliegue lo justifican.

## 1.4 Tecnologías, herramientas y justificación técnica

La elección del stack tecnológico respondió a criterios de compatibilidad con ciencia de datos, velocidad de desarrollo, trazabilidad y facilidad de despliegue local.

**Python 3.11 y FastAPI.** Se eligió Python por su ecosistema maduro para análisis de datos, machine learning y modelado estadístico. FastAPI fue seleccionado sobre alternativas como Flask o Django por su integración nativa con tipado, validación mediante Pydantic y generación automática de documentación OpenAPI. En un sistema donde los contratos de forecast, recomendación y optimización transportan valores numéricos, fechas, métricas y advertencias, la validación explícita reduce errores de integración.

**PostgreSQL.** Se eligió PostgreSQL como motor relacional por su robustez transaccional, soporte para relaciones complejas y adecuación a un catálogo de materiales con precios, fuentes, presentaciones, usuarios y metadatos. Frente a una base documental, PostgreSQL ofrece mayor control referencial. Frente a una base de series temporales especializada, reduce complejidad operativa para un MVP que todavía requiere fuerte consistencia entre entidades de negocio.

**SQLAlchemy y Alembic.** SQLAlchemy permite desacoplar la lógica de negocio del esquema físico y facilita la implementación de repositorios. Alembic aporta migraciones versionadas, requisito relevante para reproducibilidad: el esquema de base de datos puede reconstruirse en otro entorno de forma controlada.

**Prophet.** Prophet fue elegido como familia principal para forecasting por su capacidad de trabajar con series temporales relativamente cortas, manejar cambios de tendencia e incorporar regresores externos. No se eligió ARIMA/SARIMA como base principal porque exige supuestos más estrictos de estacionariedad y puede resultar menos flexible ante saltos o cambios de nivel frecuentes en contextos inflacionarios. Tampoco se eligieron redes neuronales profundas como LSTM o Transformers para el MVP, porque la cantidad de datos mensuales disponibles no justifica el aumento de complejidad ni el riesgo de sobreajuste.

**Scikit-learn y Random Forest.** Scikit-learn se utilizó para la detección de anomalías. Random Forest Regressor fue seleccionado para estimar un precio mensual esperado a partir de variables simples y trazables: índice temporal, mes calendario, precio previo, variación previa, promedio móvil corto y cantidad de registros del mes. La salida se analiza mediante residuos e IQR. Esta elección permite reemplazar un umbral fijo por una banda dinámica aprendida sobre la propia serie.

**PuLP.** PuLP se adoptó para resolver la optimización presupuestaria inicial. El problema actual puede expresarse como un modelo lineal: decidir cuánto comprar ahora y cuánto postergar por material, respetando presupuesto disponible, cantidades objetivo y no negatividad. OR-Tools fue considerado como alternativa, pero se reservó para problemas combinatorios más complejos, por ejemplo múltiples cotizaciones, lotes enteros obligatorios o ventanas temporales de compra.

**React, Material UI y Chart.js.** El frontend se implementó con React por su madurez y su ecosistema para construir interfaces interactivas. Material UI se utilizó para componentes consistentes y Chart.js para visualización de series. La interfaz no se diseñó como una landing page, sino como una herramienta operativa: resumen, forecast, costos, historial, anomalías, asistente de compra y administración.

**Docker Compose y Makefile.** Docker Compose se utilizó para orquestar backend, frontend y PostgreSQL. El Makefile concentra comandos frecuentes como `make dev`, `make bootstrap-all`, `make down` y `make precompute-forecasts`. Esta decisión reduce pasos manuales y mejora la reproducibilidad de la demo.

## 1.5 Diseño de datos, normalización y reproducibilidad

El diseño de datos fue una parte central del proyecto. El problema no consiste solo en almacenar precios, sino en construir una serie temporal comparable. Un mismo material puede comprarse en diferentes presentaciones, fuentes y fechas. Si el sistema modelara precios sin normalización, una diferencia de presentación podría confundirse con una variación real de mercado.

Para resolverlo, se definió una unidad base por material. En el caso de `Cemento Portland`, la variable principal del forecast es `precio_promedio_normalizado` expresado en `ARS/kg`. Las equivalencias de compra, como bolsa de 25 kg o 50 kg, se utilizan para mejorar la interpretación del usuario, pero no reemplazan la variable metodológica usada por el modelo. Esta decisión separa dos necesidades: una unidad rigurosa para cálculo y una presentación comprensible para la decisión de compra.

El sistema distingue materiales, presentaciones, fuentes y precios históricos. Los precios se registran con fecha, moneda, valor original, valor normalizado y metadatos de origen. Para evitar que registros con fechas futuras contaminen el forecast, la serie mensual utilizada por el modelo excluye información posterior a la fecha de cálculo. Esta decisión es metodológicamente importante: un forecast defendible debe simular la información disponible al momento de tomar la decisión.

La reproducibilidad se resolvió mediante un flujo de bootstrap. El repositorio incluye fuentes canónicas para reconstruir el universo mínimo de la tesis: `Cemento Portland`, `Pastina`, `Membrana Megaflex` y regresores base como IPC, dólar e IPIM. El flujo objetivo incluye migraciones, seed de usuarios y materiales, importadores de series históricas y validación del dataset mínimo. Esto permite que una base limpia pueda reconstruir los datos esperados para demo y pruebas.

La identidad estable de materiales se resolvió mediante `material_key`, derivada del nombre del material, por ejemplo `cemento-portland`. Esto evita depender de IDs autoincrementales que pueden cambiar entre ambientes. El endpoint puede recibir `material_id`, pero las decisiones de selección de modelo pueden resolverse internamente con una clave estable.

**Fragmento representativo de derivación conceptual de clave estable:**

```python
def derive_material_key(nombre: str) -> str:
    normalized = remove_accents(nombre)
    normalized = normalized.lower().strip()
    return slugify(normalized)
```

Este fragmento ilustra la decisión de separar identidad operacional de identidad metodológica. El ID local identifica una fila de base de datos; la `material_key` permite asociar políticas de modelo a un material de forma estable.

La preparación de datos siguió un procedimiento repetible. Primero se identifica la fuente del precio y se conserva el valor original. Luego se transforma el precio a la unidad base del material. Después se agrupa por período mensual para reducir ruido de carga diaria y obtener una frecuencia compatible con los regresores económicos disponibles. Finalmente se valida que la serie resultante tenga fechas ordenadas, valores positivos y suficiente continuidad para entrenar o comparar modelos.

Este procedimiento fue necesario porque los precios de materiales de construcción no llegan al sistema como una serie limpia. Pueden existir diferencias por presentación, fechas con múltiples observaciones, meses con pocos datos, registros provenientes de distintas fuentes y cambios bruscos de mercado. Si esos elementos no se tratan antes del forecast, el modelo puede terminar explicando errores de preparación en lugar de comportamiento económico real.

El agrupamiento mensual también fue una decisión metodológica. Una frecuencia diaria ofrece más puntos aparentes, pero puede introducir ruido que no necesariamente representa una señal útil para decisiones de compra de obra. Además, varios regresores macroeconómicos se publican o se interpretan naturalmente en escala mensual. Al llevar la serie de materiales a la misma escala temporal, se facilita la comparación entre precio observado y contexto económico.

La reproducibilidad de datos no se limita a poder ejecutar el sistema. También implica que otro evaluador pueda reconstruir la misma base mínima, obtener las mismas series y comparar las mismas métricas. Por eso, el proyecto separa datos de arranque, importadores, migraciones y comandos operativos. Esta organización evita que la demo dependa de pasos manuales invisibles o de una base local irrepetible.

**Tabla 1.1. Controles aplicados durante la preparación de datos**

| Control | Propósito | Riesgo que reduce |
|---|---|---|
| Valor positivo | Evitar precios nulos o negativos | Entrenar modelos con datos inválidos |
| Fecha válida | Ordenar correctamente la serie | Fugas temporales o cortes mal definidos |
| Unidad base | Comparar valores homogéneos | Mezclar bolsas, kilogramos o unidades de compra |
| Agrupamiento mensual | Alinear frecuencia de análisis | Ruido diario o incompatibilidad con regresores |
| Clave estable de material | Repetir selección entre entornos | Depender de IDs locales variables |
| Exclusión de datos futuros | Simular información disponible | Sobreestimar desempeño por fuga de información |

## 1.6 Desarrollo del módulo de forecasting

El módulo de forecasting transforma una serie mensual en una proyección de precios futuros. La decisión metodológica principal fue usar `MAPE` como métrica central, complementada por `MAE`, cantidad de folds y confiabilidad relativa. El `MAPE` permite expresar el error en términos porcentuales, lo cual resulta más interpretable para comparar modelos y explicar resultados. El `MAE` agrega lectura en unidades de precio, mientras que los folds indican cuántos cortes temporales respaldan la medición.

El backtesting se diseñó como validación temporal, no aleatoria. En series temporales no corresponde mezclar observaciones pasadas y futuras mediante un shuffle, porque eso destruiría la causalidad temporal. En cambio, el sistema evalúa cortes cronológicos: entrena con una parte de la historia y valida contra meses posteriores. Este enfoque se alinea con la pregunta real del sistema: si en una fecha dada se hubiera entrenado con los datos disponibles, ¿qué tan bien habría predicho los meses siguientes?

En `Cemento Portland`, los datos base documentados son:

- registros crudos: 1624;
- puntos mensuales: 51;
- puntos diarios: 759;
- rango observado: desde 2022-01-03 hasta 2026-03-25.

La evolución de modelos muestra una mejora progresiva:

- `Prophet` base: MAPE 13.90%;
- mejor familia previa con regresores monetarios: `prophet_oficial_mayorista`, MAPE 7.74%;
- baseline productivo vigente con IPIM: `prophet_ipim_nivel_general`, MAPE 4.93%;
- mejor candidata experimental por regresores: `prophet_ipim_icc_var_materials`, MAPE 4.22%;
- mejor resultado puntual a 3 meses: `ensemble_simple_top2`, MAPE 4.08%.

Estos resultados justifican dos decisiones. Primero, incorporar regresores externos puede mejorar significativamente el error, pero solo si la mejora se valida con backtesting. Segundo, no conviene adoptar automáticamente el modelo con menor número puntual si su explicación metodológica es menos clara. Por ejemplo, un ensemble puede tener menor MAPE a 3 meses, pero un modelo con regresores sectoriales claros puede ser más defendible para una tesis si mantiene buen desempeño en varios horizontes.

Para `Pastina` y `Membrana Megaflex` se aplicó la misma batería experimental, pero con una lectura más conservadora. Ambos materiales tienen series híbridas con pocos registros reales y varios datos estimados. Por eso, un MAPE bajo no tiene el mismo peso metodológico que en `Cemento Portland`.

El procedimiento experimental se estructuró en etapas. En primer lugar se estableció una variante base, sin regresores externos, para contar con una referencia mínima. En segundo lugar se probaron regresores económicos o sectoriales. En tercer lugar se compararon resultados por horizonte. En cuarto lugar se evaluó si la mejora numérica justificaba incorporar complejidad adicional. Esta secuencia permitió evitar una práctica débil: agregar variables solo porque parecen relacionadas con el precio.

La comparación de modelos se realizó con una lógica de competencia controlada. Cada variante debía entrenarse y evaluarse bajo reglas equivalentes. Si un modelo usaba más información que otro, la comparación podía ser injusta. Por eso, la evaluación temporal se diseñó para que cada fold respete el orden cronológico y para que el cálculo del error represente una situación realista de decisión.

El uso de regresores externos exige una precaución adicional. Un regresor puede estar correlacionado con el precio observado, pero no necesariamente mejorar la capacidad predictiva fuera de muestra. Por esa razón, la metodología no acepta un regresor solo por plausibilidad económica. El regresor se conserva si mejora o sostiene el desempeño medido y si su significado puede explicarse en el dominio del problema.

**Tabla 1.2. Criterios de comparación de variantes de forecasting**

| Criterio | Pregunta metodológica | Uso en la decisión |
|---|---|---|
| MAPE | ¿Cuál es el error porcentual promedio? | Comparación principal entre variantes |
| MAE | ¿Cuál es el error en unidad de precio? | Lectura complementaria para impacto económico |
| Folds | ¿Cuántos cortes respaldan la medición? | Confianza relativa del resultado |
| Horizonte | ¿Funciona igual a 3, 6 y 12 meses? | Selección diferenciada por ventana |
| Explicabilidad | ¿Puede justificarse la variable usada? | Defensa técnica y económica del modelo |
| Simplicidad | ¿La mejora compensa la complejidad? | Evitar modelos innecesariamente complejos |

Esta forma de evaluación ayuda a defender por qué el mejor número puntual no siempre se convierte automáticamente en la mejor decisión de ingeniería. Si una variante mejora unas décimas de MAPE pero agrega opacidad, dependencia de datos frágiles o dificultad de reproducción, puede ser menos conveniente para el MVP. El proyecto prioriza un equilibrio entre desempeño, trazabilidad y mantenibilidad.

En consecuencia, el módulo de forecasting no se presenta como una búsqueda ciega del mínimo error posible. Se presenta como un proceso de selección responsable: se prueban alternativas, se miden resultados, se analiza estabilidad y se documenta el criterio de adopción. Esta distinción es importante para el marco metodológico porque muestra que el desarrollo no fue solo implementación, sino evaluación técnica de alternativas.

## 1.7 Selector de modelos y política de fallback

El selector de modelos surge de una limitación detectada durante la experimentación: no existe un único modelo óptimo para todos los materiales y horizontes. La evidencia muestra que `Cemento Portland`, `Pastina` y `Membrana Megaflex` no comparten necesariamente la misma mejor variante. Además, un modelo puede funcionar bien a 3 meses y no sostener el mismo desempeño a 12 meses.

La solución adoptada fue incorporar una capa de selección parametrizada por `material_key` y `horizonte_meses`. Esta capa permite separar la decisión metodológica del motor de forecasting. El servicio de forecast no queda contaminado por condicionales dispersos, sino que consulta una política de selección que indica qué configuración resolver o qué fallback aplicar.

**Fragmento representativo simplificado de la idea de selección:**

```python
def resolve_model_selection(material_key: str, horizonte_meses: int):
    selection = MODEL_SELECTIONS.get((material_key, horizonte_meses))
    if selection is None:
        return fallback_prophet_base(material_key, horizonte_meses)
    return selection
```

El fragmento no pretende reproducir todo el selector, sino mostrar la decisión de diseño: la selección se resuelve por clave estable y horizonte, con fallback explícito. La ventaja de esta arquitectura es que permite evolucionar la política de modelos sin cambiar el contrato HTTP ni duplicar lógica dentro del endpoint.

El fallback cumple una función metodológica importante. Si un material no tiene una calibración suficiente, el sistema no debe inventar una métrica ni forzar un modelo complejo. En ese caso puede degradar a una variante base y marcar la confiabilidad como no calibrada o baja. Este comportamiento es preferible a devolver una recomendación fuerte basada en evidencia insuficiente.

La selección de modelos se apoya en tres criterios:

1. `MAPE` como métrica principal;
2. estabilidad entre folds y cantidad de cortes disponibles;
3. coherencia económica de los regresores.

No se elige modelo por apariencia visual de la curva. La plausibilidad visual puede servir como control cualitativo, pero no reemplaza la validación temporal.

## 1.8 Detección de anomalías con Random Forest

La detección de anomalías se incorporó para identificar meses que merecen revisión dentro de la serie histórica. El objetivo no es demostrar automáticamente que un dato es erróneo, sino marcar comportamientos atípicos frente al patrón esperado de la propia serie.

La primera alternativa considerada fue un umbral porcentual fijo. Esta alternativa es simple de implementar y explicar, pero débil metodológicamente. En una economía inflacionaria, una suba mensual elevada puede ser normal. A la inversa, una variación menor puede ser atípica si el material venía mostrando estabilidad. Por eso, un porcentaje único aplicado a todos los materiales puede ser demasiado rígido o demasiado permisivo.

La solución implementada usa `RandomForestRegressor` sobre la serie mensual normalizada. El modelo aprende un precio esperado a partir de variables simples:

- índice temporal del mes;
- mes calendario;
- precio del mes anterior;
- variación porcentual anterior;
- promedio móvil corto;
- cantidad de registros del mes.

Luego se calcula el residuo porcentual entre el precio observado y el precio esperado. El límite dinámico se obtiene mediante `Q3 + 1.5 * IQR` sobre los residuos. Si el residuo de un mes supera ese límite, el mes se marca como anomalía.

**Fragmento representativo del criterio de decisión:**

```python
residual_limit = q3 + (1.5 * iqr)

for index, residual_pct, predicted in predictions:
    if residual_pct <= residual_limit:
        continue
    anomalies[puntos[index].fecha] = build_anomaly_reason(predicted, residual_pct)
```

La justificación técnica es que el criterio deja de preguntar “¿subió más que X%?” y pasa a preguntar “¿se alejó más de lo esperable para esta serie?”. Esto mejora la defensa frente al docente porque elimina el porcentaje fijo en código y lo reemplaza por una regla dinámica basada en el comportamiento histórico del material.

La principal limitación es que Random Forest detecta atipicidad, no causalidad. Una anomalía puede deberse a un error de carga, un cambio real de precio, un cambio de presentación, un shock de mercado o una particularidad de la muestra. Por eso, la interfaz debe presentar la marca como una alerta de revisión, no como una sentencia automática.

## 1.9 Capa de decisión económica y DSS

El núcleo metodológico de BuildWise no termina en el forecast. Un modelo predictivo que solo muestra una curva obliga al usuario a interpretar manualmente si debe comprar, esperar o asignar presupuesto. Para resolverlo, se incorporó una capa de decisión económica construida sobre los precios actuales y proyectados.

El sistema contiene tres familias de decisiones:

1. **Recomendación simple:** evalúa timing de un material y devuelve `COMPRAR_AHORA`, `ESPERAR` o `MONITOREAR`.
2. **Recomendación contextual:** incorpora fase de obra, fecha de uso, tolerancia al riesgo y presupuesto, y devuelve `COMPRAR_AHORA`, `POSTERGAR`, `ESCALONAR` o `SIN_VENTAJA_CLARA`.
3. **Optimización presupuestaria:** asigna cantidades entre materiales y devuelve `COMPRAR_AHORA`, `POSTERGAR` o `COMPRA_PARCIAL`.

Esta separación evita una inconsistencia aparente. `MONITOREAR` y `SIN_VENTAJA_CLARA` son respuestas conservadoras en niveles distintos: la primera pertenece a la recomendación simple y la segunda al flujo contextual de compra. `COMPRA_PARCIAL` pertenece a optimización multi-material, mientras que `ESCALONAR` pertenece al flujo contextual de una necesidad de compra.

La optimización con PuLP modela cuánto comprar ahora y cuánto postergar bajo presupuesto limitado. La función objetivo busca maximizar el ahorro esperado por anticipar compras cuando el precio futuro proyectado es mayor que el actual, ponderando criticidad y respetando restricciones. Las restricciones principales son presupuesto disponible, cantidad objetivo y no negatividad.

Esta capa transforma el sistema en un DSS: la visualización sigue existiendo, pero el valor metodológico está en que el sistema devuelve una decisión trazable. La salida informa acción recomendada, cantidades, presupuesto utilizado, presupuesto restante, impacto económico estimado, confianza y advertencias.

## 1.10 Núcleo de IA no generativa, determinismo y armador de presupuesto

Para la defensa metodológica del proyecto, resulta importante distinguir entre “usar un modelo generativo” y “construir un sistema basado en IA”. BuildWise no delega su valor principal en un LLM externo. El núcleo de la solución está compuesto por modelos entrenados o calibrados con datos propios de la aplicación y por reglas determinísticas auditables. Esto aumenta la trazabilidad porque cada precio, recomendación o anomalía puede explicarse a partir de datos históricos, métricas y reglas conocidas.

El core de BuildWise se compone de cuatro piezas:

1. **Pronóstico de precios:** modelos de forecasting entrenados con series históricas del sistema y evaluados mediante backtesting temporal.
2. **Selección de modelos:** política que elige variante por material y horizonte en función de evidencia empírica, no por preferencia manual.
3. **Detección de anomalías:** Random Forest aplicado a la serie histórica para detectar precios fuera del comportamiento esperado.
4. **Armador de presupuesto y recomendación:** cálculo determinístico que combina precio vigente, forecast, cantidad, fecha, criticidad, tolerancia al riesgo y presupuesto disponible.

Esta organización hace que el armador de presupuesto forme parte del núcleo del proyecto. No es una pantalla auxiliar ni una funcionalidad administrativa: es la capa que convierte el resultado de los modelos en una decisión concreta de compra. El forecast estima escenarios futuros; la detección de anomalías controla calidad y comportamiento atípico; el armador de presupuesto traduce esa información en importes, diferencias proyectadas y acciones recomendadas.

El sistema aumenta el determinismo de tres maneras. Primero, los modelos predictivos se entrenan o calibran con datos propios del dominio, no con conocimiento general de un modelo generativo. Segundo, las reglas de decisión se ejecutan en backend y producen salidas estructuradas. Tercero, el LLM no puede modificar importes, métricas ni acciones recomendadas. Por lo tanto, dos ejecuciones con los mismos datos, parámetros y modelo seleccionado deben producir la misma recomendación económica, salvo cambios explícitos en la serie o en la configuración.

Random Forest se utiliza como IA no generativa. Su objetivo no es redactar, conversar ni crear valores nuevos, sino estimar un comportamiento esperado de la serie y marcar observaciones atípicas mediante residuos. Esta elección aporta valor metodológico porque reemplaza criterios arbitrarios por un modelo entrenado sobre el patrón histórico del material. La pregunta que responde no es “qué texto conviene mostrar”, sino “este precio está fuera de lo esperable para esta serie”.

El aporte de ingeniería se encuentra precisamente en evitar que la solución dependa de prompt engineering. Un prompt puede mejorar la presentación de una respuesta, pero no constituye por sí mismo una base sólida para una tesis de ingeniería si el sistema no controla de dónde provienen los valores. En BuildWise, los valores provienen de datos de la aplicación, modelos evaluados y reglas de negocio. La capa generativa puede ayudar a que el usuario exprese su necesidad o entienda la salida, pero no reemplaza el entrenamiento, la validación ni el cálculo.

Esta distinción también permite defender la posibilidad de utilizar modelos locales o intercambiables. El core no necesita que Gemini, Claude o GPT “sepan” el precio de un material. El sistema ya posee las series históricas y entrena modelos sobre ellas. Si en una etapa futura se reemplaza el proveedor generativo, el forecast, las anomalías, la optimización y el presupuesto deben seguir funcionando porque pertenecen al backend y no al proveedor conversacional.

## 1.11 Asistente de compra e integración con LLM

La capa conversacional se implementó como una interfaz acotada de ayuda al usuario, no como un motor de decisión. Su función es recibir texto libre, extraer intención, completar faltantes y redactar una explicación de una salida que ya fue calculada por backend. En el flujo correcto, la IA no define precios ni emite recomendaciones desde conocimiento general. Primero trabaja el sistema con sus datos; después el LLM comunica el resultado.

Cuando el usuario consulta un material fuera del catálogo del MVP, el sistema no delega la respuesta al modelo generativo. La consulta se corta en backend y se informa que no hay datos suficientes. Esto evita uno de los riesgos más frecuentes de los asistentes conversacionales: responder con seguridad sobre elementos no soportados por el sistema.

La elección de una API de IA intercambiable responde a un criterio operativo, no metodológico. El proveedor puede cambiarse entre la API institucional y Claude sin alterar el núcleo del sistema, porque la verdad del cálculo permanece en BuildWise.

La integración de IA generativa se diseñó con una restricción explícita: el LLM no calcula precios, no decide acciones y no inventa métricas. Su rol es interpretar lenguaje natural y redactar explicaciones a partir de contexto calculado por backend.

El asistente de compra se implementó para transformar una necesidad de obra en una recomendación de compra. Por ejemplo, un usuario puede escribir: “En septiembre voy a impermeabilizar un techo y necesito 30 unidades de Membrana Megaflex. ¿Me conviene comprar ahora?”. El sistema interpreta producto, cantidad, fase de obra, fecha u horizonte, presupuesto máximo y tolerancia al riesgo. Luego muestra esos campos en un formulario editable. Solo después de la validación humana se calcula la propuesta.

El alcance de compra se limita a `Cemento Portland`, `Pastina` y `Membrana Megaflex`. Tanto backend como frontend restringen el flujo a esos productos MVP. Si falta un dato, el sistema lo marca antes de calcular. Si el usuario informa presupuesto insuficiente y la señal económica favorece comprar ahora, el sistema puede recomendar `ESCALONAR`, indicando cuántas unidades podría adquirir inicialmente.

El cálculo puede apoyarse en el mismo precio base utilizado por el administrador, pero la salida mostrada al comprador corresponde al precio final o presupuesto estimado. Esta distinción permite que el dueño del sistema analice costos y márgenes, mientras que el comprador recibe una recomendación expresada en términos de importe final a pagar, diferencia proyectada y conveniencia temporal.

La arquitectura de cliente LLM permite usar un proveedor compatible con OpenAI Chat Completions o Anthropic Claude mediante configuración. Esta intercambiabilidad es importante porque el servicio de IA generativa puede cambiar sin alterar las reglas de negocio. Si falla el proveedor, el cálculo económico sigue siendo responsabilidad del backend.

La decisión de incorporar un asistente de compra en lugar de un asistente que solo explica gráficos responde al criterio de valor del MVP. Una interfaz explicativa se parece a consultar un tablero con lenguaje natural. En cambio, el asistente toma una necesidad concreta, la estructura, la valida y la convierte en presupuesto estimado y recomendación. Esto acerca el sistema al uso real de quien debe decidir cuándo y cuánto comprar.

## 1.12 Seguridad, roles y despliegue

El sistema incorpora autenticación con usuarios y roles. La distinción principal es entre usuario administrador y usuario comprador. El administrador puede acceder a funciones de configuración, carga, costos y márgenes, mientras que el comprador accede a consultas, análisis, precios finales y recomendaciones dentro del alcance permitido. Esta separación evita que operaciones sensibles, como carga de precios, precio de costo o configuración del sistema, queden disponibles para cualquier usuario.

El backend utiliza tokens firmados para mantener sesiones stateless. Esta decisión se alinea con el despliegue en contenedores, ya que no requiere almacenar sesión en memoria del servidor. La configuración sensible se resuelve mediante variables de entorno, incluyendo credenciales de base de datos y claves de proveedores LLM.

Docker Compose orquesta los servicios principales: frontend, API y PostgreSQL. También existe un servicio de bootstrap bajo perfil operativo para cargar datos iniciales. Esta separación permite levantar la aplicación web sin ejecutar importaciones pesadas en cada arranque, y ejecutar el bootstrap cuando se necesita reconstruir el entorno.

## 1.13 Iteraciones, aprendizajes y decisiones metodológicas

El desarrollo se organizó alrededor de aprendizajes concretos. La primera lección fue que la normalización por unidad base era indispensable para que el forecast tuviera sentido. La segunda fue que un único modelo global no era suficiente: los materiales y horizontes presentan comportamientos distintos. La tercera fue que la decisión de compra no podía quedar implícita en gráficos; debía generarse una salida operativa.

La evolución de anomalías también dejó un aprendizaje importante. Un umbral fijo era fácil de implementar, pero difícil de defender. Random Forest con residuos e IQR permitió justificar la detección desde el comportamiento histórico de cada material.

La capa de asistencia de compra mostró otra distinción metodológica: IA generativa no equivale a decisión automática. El sistema usa LLM para interpretación y redacción, pero mantiene los cálculos en servicios auditables. Esa separación reduce el riesgo de alucinación y mejora la defendibilidad del proyecto.

En síntesis, el desarrollo de BuildWise no fue una acumulación de funcionalidades. Fue una construcción incremental de capas: datos, forecast, selección, anomalías, decisión económica y asistencia de compra. Cada capa respondió a un problema identificado en la anterior.

La siguiente tabla resume las iteraciones principales desde el punto de vista metodológico. No reemplaza al backlog ni a las historias de usuario, sino que muestra cómo cada etapa produjo una decisión técnica verificable.

**Tabla 1.3. Iteraciones principales del desarrollo**

| Iteración | Foco de ingeniería | Evidencia generada | Decisión metodológica |
|---|---|---|---|
| Base de datos y catálogo | Materiales, presentaciones, fuentes y precios | Migraciones, seeds e importadores | Usar PostgreSQL y claves estables por material |
| Normalización | Comparabilidad de precios | Precio normalizado en unidad base | Modelar forecast sobre `ARS/kg` cuando corresponde |
| Forecast inicial | Primeras proyecciones | Prophet base y métricas iniciales | Tomar MAPE como métrica principal de lectura |
| Regresores | Contexto económico externo | Variantes con IPIM, ICC, CAC y dólar | Validar regresores por backtesting, no por intuición |
| Selector | Diferencias por material y horizonte | Tabla de mejores modelos | Resolver modelo por `material_key` y horizonte |
| Anomalías | Revisión de precios atípicos | Random Forest + residuos + IQR | Reemplazar umbral fijo por criterio dinámico |
| Armador de presupuesto | Conversión de forecast en importes | Presupuesto actual, proyectado y diferencia | Integrar el core de decisión económica |
| DSS | Conversión de forecast en decisión | Recomendaciones y optimización | Traducir predicción en acción operativa |
| Asistente de compra | Necesidad de obra en lenguaje natural | Interpretación, validación y propuesta | Usar LLM como interfaz, no como motor de cálculo |

Esta lectura por iteraciones permite defender que el proyecto no siguió un camino lineal rígido. La metodología fue incremental porque el conocimiento técnico se obtuvo al medir resultados. Por ejemplo, el uso de regresores no estaba justificado solamente por la teoría económica, sino por la reducción concreta del error observada en backtesting. Del mismo modo, el selector no fue una abstracción anticipada, sino una respuesta a la evidencia de que los mejores modelos variaban entre materiales y horizontes.

También se observa una evolución en el rol de la interfaz. Al comienzo, la interfaz podía entenderse como una forma de consultar datos. Luego pasó a ser una superficie para recorrer decisiones: forecast, anomalías, recomendaciones, optimización y asistencia de compra. Este cambio es relevante porque el objetivo de un DSS no es solo informar, sino asistir en la toma de decisiones.

## 1.14 Trazabilidad entre objetivos, componentes y evidencia

Para que el marco metodológico sea defendible, cada objetivo del proyecto debe poder conectarse con un componente implementado y con una evidencia verificable. Esta trazabilidad evita que el documento quede como una descripción general del sistema y permite mostrar cómo se respondió a cada necesidad de ingeniería.

**Tabla 1.4. Trazabilidad metodológica del MVP**

| Objetivo del proyecto | Componente que lo resuelve | Evidencia disponible | Riesgo controlado |
|---|---|---|---|
| Gestionar precios históricos de materiales | Catálogo, fuentes, presentaciones y precios | Base PostgreSQL, migraciones, seeds e importadores | Datos dispersos o no reproducibles |
| Comparar precios en una unidad consistente | Normalización por unidad base | Campo de precio normalizado y series mensuales | Confundir presentación de compra con variación real |
| Proyectar precios futuros | Módulo de forecasting | Backtesting, MAPE, MAE y folds | Elegir modelos sin validación temporal |
| Adaptar el modelo al material y horizonte | Selector de modelos | Tabla de mejores variantes por horizonte | Forzar un único modelo global |
| Detectar comportamientos atípicos | Random Forest + residuos + IQR | Alertas de anomalías por serie | Depender de porcentajes fijos en código |
| Armar presupuestos de compra | Cálculo de precio vigente, proyectado y totales | Presupuesto estimado y diferencia futura | Que la recomendación quede desconectada del impacto económico |
| Traducir forecast en decisión | Recomendaciones y optimización | Acciones `COMPRAR_AHORA`, `POSTERGAR`, `ESCALONAR` y `SIN_VENTAJA_CLARA` | Dejar al usuario interpretar curvas manualmente |
| Atender necesidades de compra | Asistente de compra | Interpretación editable y propuesta validada | Convertir la IA en una caja negra de decisión |
| Aumentar determinismo | Backend de cálculo, modelos propios y LLM periférico | Salidas estructuradas y pruebas automatizadas | Depender de valores generados por prompt |
| Mantener calidad funcional | Pruebas automatizadas | 148 pruebas exitosas en módulos críticos | Regresiones silenciosas entre capas |

La tabla muestra que el proyecto no se apoya en una única técnica. El valor surge de la integración controlada de varias piezas: ingeniería de datos, modelos temporales, detección de anomalías, reglas de negocio, optimización lineal e interfaz conversacional. Esta integración es precisamente el punto metodológico central del trabajo: no alcanza con obtener una curva de forecast si esa curva no se conecta con una decisión y con una explicación verificable.

La trazabilidad también permite delimitar qué afirmaciones pueden sostenerse con fuerza y cuáles deben presentarse con cautela. En `Cemento Portland`, la evidencia empírica es alta porque la serie real es amplia. En `Pastina` y `Membrana Megaflex`, la evidencia permite demostrar extensibilidad arquitectónica y funcional, pero no una generalización estadística fuerte. Esta diferencia debe mantenerse visible en el documento final para evitar una defensa excesiva del alcance.

Finalmente, la trazabilidad ayuda a distinguir evidencia técnica de evidencia de uso. Las pruebas automatizadas y las métricas de backtesting demuestran funcionamiento y desempeño bajo datos disponibles. En cambio, una validación con usuarios reales mediría adopción, claridad de recomendaciones e impacto económico efectivo. Esta última dimensión queda fuera del análisis empírico actual, por lo que no se utiliza para afirmar resultados que todavía no fueron medidos.

## 1.15 Estrategia de verificación y aseguramiento de calidad

La verificación del sistema se planteó en dos niveles: verificación funcional y verificación metodológica. La verificación funcional comprueba que los endpoints, schemas, reglas de negocio y componentes principales respondan correctamente. La verificación metodológica comprueba que los resultados utilizados para defender el proyecto no provengan de supuestos inválidos, fuga de información temporal o decisiones no trazables.

La estrategia de pruebas automatizadas se concentró en los módulos con mayor riesgo de regresión. Las recomendaciones de compra y la optimización presupuestaria requieren especial cuidado porque combinan valores numéricos, reglas de negocio y decisiones visibles para el usuario. Un error pequeño en signo, umbral o restricción puede cambiar una recomendación de comprar a postergar. Por ese motivo, estos módulos se probaron con escenarios concretos y salidas esperadas.

El asistente de compra también fue cubierto por pruebas porque introduce una frontera delicada: entrada en lenguaje natural, validación de datos interpretados y cálculo posterior. La prueba no busca demostrar que el LLM siempre interpreta perfecto, sino que el sistema maneja correctamente la estructura resultante, exige validación humana y no calcula propuestas cuando faltan datos obligatorios.

En el backend, los contratos de entrada y salida se validan mediante schemas. Esta decisión reduce errores de integración con el frontend y con consumidores futuros de la API. En particular, los endpoints relacionados con forecast, recomendaciones y chat transportan fechas, importes, cantidades, acciones recomendadas y advertencias; por lo tanto, una validación laxa podría generar errores difíciles de detectar en la interfaz.

**Tabla 1.5. Cobertura de verificación por componente**

| Componente | Tipo de verificación | Riesgo principal |
|---|---|---|
| Series y forecast | Tests de preparación y respuesta esperada | Series mal formadas o contratos inconsistentes |
| Recomendaciones simples | Escenarios de compra, espera y monitoreo | Umbrales de decisión incorrectos |
| Recomendaciones contextuales | Fecha, riesgo, fase y presupuesto | Acción final incoherente con contexto |
| Optimización | Restricción presupuestaria y cantidades | Comprar más de lo permitido o asignar mal recursos |
| Chat y asistente de compra | Interpretación, validación y propuesta | Usar datos incompletos o mal estructurados |
| Schemas y rutas | Validación de contratos HTTP | Cambios incompatibles entre frontend y backend |

Además de las pruebas automatizadas, el proyecto requiere una verificación manual de integración para la demo. Esta verificación consiste en levantar el entorno, cargar datos mínimos, ingresar al frontend, consultar forecast, revisar anomalías, ejecutar una recomendación contextual y probar el asistente de compra con una necesidad representativa. Esta secuencia permite demostrar que los módulos no solo funcionan aislados, sino que se conectan en un flujo operativo.

El criterio de aceptación de la demo se define de forma observable. La aplicación debe permitir iniciar sesión, consultar materiales del MVP, visualizar precios históricos, obtener forecast con métricas, identificar anomalías, generar recomendaciones y construir una propuesta de compra validada. Si alguno de esos pasos depende de una acción manual no documentada, se considera un riesgo de reproducibilidad.

La calidad también se evaluó desde la mantenibilidad. La separación por módulos reduce el acoplamiento entre decisiones de dominio y tecnología. Por ejemplo, cambiar el proveedor LLM no debería modificar las reglas de optimización; ajustar el selector de modelos no debería romper la interfaz de costos; incorporar un nuevo material no debería requerir reescribir el motor de forecast. Estas propiedades no se miden con una única métrica, pero se sostienen mediante organización de código, contratos claros y pruebas.

Finalmente, se mantuvo una distinción entre verificación y validación. La verificación responde si el sistema fue construido correctamente según sus reglas y contratos. La validación respondería si el sistema resuelve satisfactoriamente el problema para usuarios reales en condiciones productivas. El alcance del TIF3 permite defender principalmente verificación técnica y evidencia funcional del MVP. La validación completa con usuarios finales requeriría un estudio adicional con casos reales de compra, que no se utiliza como base para afirmar resultados en este documento.

---

# CAPÍTULO 2: ANÁLISIS DE RESULTADOS

El presente capítulo responde a la pregunta: ¿qué se obtuvo y qué significan esos resultados en relación con los objetivos del proyecto? El análisis se mantiene vinculado a la evidencia observada: métricas de forecast, cantidad de datos, comportamiento por material, cobertura de pruebas, salidas del sistema y limitaciones metodológicas.

## 2.1 Presentación de resultados en bruto

La primera evidencia corresponde a los datos disponibles para el material principal, `Cemento Portland`. La serie utilizada como referencia metodológica contiene 1624 registros crudos, 759 puntos diarios y 51 puntos mensuales entre 2022-01-03 y 2026-03-25. Esta densidad permite realizar backtesting temporal con mayor solidez que en los otros materiales del MVP.

**Tabla 2.1. Evolución de modelos para Cemento Portland**

| Variante | Regresores / criterio | Horizonte | MAPE |
|---|---|---:|---:|
| Prophet base | sin regresores | referencia | 13.90% |
| prophet_oficial_mayorista | dólar oficial + mayorista | referencia previa | 7.74% |
| prophet_ipim_nivel_general | IPIM nivel general | 3 meses | 4.93% |
| prophet_ipim_icc_var_materials | IPIM + ICC var_materials | 3 meses | 4.22% |
| ensemble_simple_top2 | promedio de dos mejores variantes | 3 meses | 4.08% |

**Tabla 2.2. Mejores resultados por material y horizonte**

| Material | Horizonte | Mejor modelo medido | MAPE |
|---|---:|---|---:|
| Cemento Portland | 3m | ensemble_simple_top2 | 4.08% |
| Cemento Portland | 3m | prophet_ipim_icc_var_materials | 4.22% |
| Cemento Portland | 6m | prophet_ipim_icc_var_materials | 5.52% |
| Cemento Portland | 12m | prophet_ipim_icc_var_materials | 4.51% |
| Pastina | 3m | prophet_ipim_nivel_general_lags | 3.37% |
| Pastina | 6m | ensemble_simple_top2 | 4.99% |
| Pastina | 12m | prophet_ipim_cac_var_materials | 4.94% |
| Membrana Megaflex | 3m | prophet_ipim_nivel_general_lags | 6.70% |
| Membrana Megaflex | 6m | prophet_ipim_nivel_general_lags | 7.23% |
| Membrana Megaflex | 12m | prophet_mayorista | 11.17% |

**Tabla 2.3. Confiabilidad relativa de materiales**

| Material | Datos reales | Datos estimados | Folds | Confiabilidad relativa |
|---|---:|---:|---:|---|
| Cemento Portland | 1624 precios | 0 | 9 | alta |
| Pastina | 10 registros | 41 | 9 | media |
| Membrana Megaflex | 9 registros | 43 | 5 | media-baja |

Además de las métricas de forecast, el sistema cuenta con pruebas automatizadas. En la verificación ampliada realizada sobre módulos de asistente de compra, chat, recomendaciones, estrategias de compra, optimización, series y schemas, se obtuvieron 148 pruebas exitosas. Esta evidencia no mide precisión predictiva, pero sí estabilidad funcional de las reglas y contratos implementados.

**Tabla 2.4. Evidencia funcional del DSS y del asistente de compra**

| Flujo evaluado | Entrada esperada | Salida del sistema | Evidencia metodológica |
|---|---|---|---|
| Forecast por material | Material y horizonte | Precio proyectado, métricas y confianza | Proyección trazable por modelo seleccionado |
| Recomendación contextual | Material, cantidad, fecha de uso, riesgo y presupuesto | Comprar, postergar, escalonar o sin ventaja clara | Decisión basada en forecast y reglas explícitas |
| Optimización presupuestaria | Lista de materiales, cantidades y presupuesto | Cantidad a comprar ahora y cantidad a postergar | Asignación lineal bajo restricción económica |
| Detección de anomalías | Serie histórica mensual | Meses marcados para revisión | Residuos dinámicos en lugar de umbral fijo |
| Asistente de compra | Consulta en lenguaje natural | Campos interpretados y presupuesto calculado | LLM limitado a interpretación y redacción |

[INSERTAR CAPTURA: pantalla de forecast de Cemento Portland con métricas visibles]

[INSERTAR CAPTURA: pantalla de recomendación contextual o costos]

[INSERTAR CAPTURA: pantalla del asistente de compra con necesidad validada]

Las capturas sugeridas no deben utilizarse como sustituto de las métricas, sino como evidencia de integración. La clase indica que el análisis de resultados debe presentar datos, describirlos e interpretarlos. Por eso, las capturas deben acompañarse de una lectura técnica: qué dato muestra la pantalla, qué decisión permite tomar y cómo se relaciona con el objetivo del MVP.

## 2.2 Descripción de los datos observados

Los datos muestran que `Cemento Portland` es el material con mayor solidez metodológica. La cantidad de registros reales y la continuidad mensual permiten evaluar modelos con mayor confianza. En este material, la incorporación de IPIM redujo de forma significativa el error frente al Prophet base. Luego, la incorporación de regresores sectoriales como ICC o CAC permitió mejoras adicionales.

En `Pastina`, los resultados de MAPE son bajos en varios horizontes, pero la serie no tiene la misma densidad real. La presencia de datos estimados obliga a interpretar el resultado con cautela. Un MAPE bajo sobre una serie híbrida no equivale automáticamente a un modelo igual de confiable que en una serie totalmente real.

En `Membrana Megaflex`, los resultados son más débiles, especialmente a 12 meses. El MAPE de 11.17% en el mejor modelo medido para ese horizonte indica que el pronóstico largo es menos preciso. A 3 y 6 meses, las variantes con lags muestran mejores resultados, pero la confiabilidad relativa sigue siendo media-baja.

También se observa que no existe un único modelo ganador. En `Cemento Portland`, `prophet_ipim_icc_var_materials` sostiene buenos resultados en 3, 6 y 12 meses. En `Pastina`, los mejores modelos cambian según horizonte. En `Membrana Megaflex`, el mejor modelo a 12 meses no coincide con los mejores modelos de corto y mediano plazo. Este comportamiento respalda la decisión de seleccionar por material y horizonte.

Otro dato relevante es la relación entre precisión y explicabilidad. El mejor MAPE puntual no siempre es la opción más conveniente para documentar como modelo principal. En un trabajo de ingeniería, especialmente cuando el resultado alimenta decisiones económicas, importa que la elección pueda explicarse y reproducirse. Por eso, una variante con regresores sectoriales claros puede ser preferible frente a una diferencia mínima de error si ofrece mayor trazabilidad.

También debe observarse que las métricas no se interpretan de manera aislada. Un MAPE de 4% sobre 51 puntos mensuales reales tiene una lectura distinta a un MAPE de 4% sobre una serie con fuerte proporción de estimaciones. Esta diferencia explica por qué el documento clasifica la confiabilidad por material y no solo por porcentaje de error. La métrica numérica informa desempeño; la calidad del dataset informa el grado de confianza que puede otorgarse a ese desempeño.

## 2.3 Interpretación de resultados en relación con los objetivos

El objetivo principal era construir un sistema reproducible de forecast y soporte a la decisión para precios de materiales. Los resultados observados permiten afirmar que el objetivo se alcanzó en el alcance del MVP, con distinta fortaleza según material.

En `Cemento Portland`, el MAPE de 4.22% de la mejor candidata por regresores se encuentra por debajo del umbral operativo de 5% que se había tomado como referencia para un material crítico. Esto indica que el modelo genera proyecciones suficientemente precisas para alimentar decisiones de compra en el horizonte evaluado. La mejora frente al Prophet base de 13.90% muestra que los regresores externos aportan valor.

La diferencia entre 4.22% y 4.08% también debe interpretarse con criterio metodológico. Aunque `ensemble_simple_top2` obtiene el mejor resultado puntual a 3 meses, `prophet_ipim_icc_var_materials` ofrece una explicación más clara y se sostiene en varios horizontes. Por eso, para tesis puede ser más defendible presentar el ensemble como evidencia exploratoria y la variante con IPIM + ICC como candidata metodológica fuerte.

En `Pastina`, los MAPE de 3.37%, 4.99% y 4.94% muestran que el sistema puede extender el enfoque a otros materiales. Sin embargo, la baja cantidad de registros reales impide otorgarle la misma confianza que al cemento. El resultado es útil operativamente, pero no debe usarse para afirmar que el modelo generaliza con igual solidez a cualquier producto.

En `Membrana Megaflex`, los resultados indican utilidad en 3 y 6 meses, pero debilidad en 12 meses. Esta diferencia confirma que el horizonte importa. El sistema no debe ofrecer la misma confianza para todas las ventanas temporales.

La capa DSS cumple el objetivo de traducir forecast en decisión. La recomendación no se basa solo en que el precio suba o baje, sino en umbral de decisión, criticidad, cantidad, presupuesto y confiabilidad. Esto permite que el usuario reciba una salida operativa sin reconstruir manualmente el razonamiento desde múltiples gráficos.

El asistente de compra cumple un objetivo adicional: transformar lenguaje natural en una propuesta validada. El LLM no reemplaza el DSS; actúa como interfaz para estructurar necesidades y redactar respuestas sobre cálculos internos.

Desde el punto de vista del comprador, esta integración cambia la forma de consumir el resultado. El sistema no exige que el usuario observe una curva, estime mentalmente el ahorro y luego arme un presupuesto por separado. En cambio, permite partir de una necesidad concreta: producto, cantidad, fecha y presupuesto. La recomendación queda expresada en términos de compra, pero apoyada en el cálculo técnico del backend.

La validación editable de los campos interpretados es un resultado funcional importante. Evita que una mala interpretación del lenguaje natural se convierta directamente en una propuesta económica. Esta decisión mantiene al usuario dentro del circuito de control y hace que la IA generativa sea una asistencia, no una autoridad automática.

## 2.4 Discrepancias y comportamientos inesperados

La primera discrepancia relevante es la diferencia entre materiales. Se esperaba que la batería experimental mejorara los tres productos, pero no necesariamente que cada uno tuviera un ganador distinto. Los resultados confirmaron que `Pastina` y `Membrana Megaflex` requieren lectura separada. Esto obligó a abandonar la idea de un modelo único global.

La segunda discrepancia aparece en `Membrana Megaflex` a 12 meses. La exploración profunda no superó el mejor resultado histórico documentado para ese horizonte. Esto sugiere que, para materiales con series híbridas y mayor volatilidad, los regresores o lags pueden mejorar horizontes cortos pero no garantizar desempeño en horizontes largos.

La tercera discrepancia está relacionada con la interpretación visual del forecast. Algunas curvas pueden parecer plausibles sin ser las mejores en backtesting. Esto justificó documentar explícitamente que la selección no se hace por forma visual de la curva.

La cuarta observación surgió en anomalías. Un umbral fijo era más simple, pero no explicaba adecuadamente la volatilidad esperada de cada serie. El paso a Random Forest + IQR mejoró la defendibilidad, aunque no elimina la necesidad de revisión humana de las marcas.

Finalmente, el asistente de compra introdujo una distinción importante: la IA generativa mejora la experiencia, pero no debe confundirse con el motor de decisión. Esta separación evitó que el proyecto dependa de la exactitud factual del LLM para cálculos críticos.

Estas discrepancias no invalidan el enfoque; al contrario, ayudaron a precisar el alcance. El análisis muestra que BuildWise funciona mejor cuando cada salida conserva su nivel de confianza: forecast fuerte para cemento, forecast exploratorio para materiales con series híbridas, anomalías como alertas de revisión y recomendaciones como asistencia trazable. Esta graduación evita que el sistema entregue certezas artificiales.

## 2.5 Limitaciones del análisis

El análisis tiene limitaciones que deben explicitarse.

Primero, `Cemento Portland` concentra la mayor fortaleza metodológica. Los resultados de `Pastina` y `Membrana Megaflex` son útiles para demostrar extensibilidad, pero su base de datos híbrida limita la confianza de las interpretaciones.

Segundo, las métricas de MAPE dependen del período observado y de los datos disponibles. Una mejora medida en backtesting no garantiza que el modelo mantenga el mismo error ante futuros shocks económicos no representados en la serie.

Tercero, la detección de anomalías marca atipicidad, no causalidad. El sistema puede indicar que un mes se alejó del patrón esperado, pero no puede determinar por sí solo si la causa fue error de carga, cambio de precio, shock de mercado o una característica real de la serie.

Cuarto, la optimización presupuestaria actual modela un problema lineal inicial. No considera todavía lotes enteros obligatorios, comparación entre cotizaciones, capacidad de acopio, vencimientos, logística o ventanas temporales múltiples. Estas variables podrían modificar la recomendación en un contexto operativo más complejo.

Quinto, el asistente de compra depende de un proveedor LLM para interpretar y redactar. Aunque los cálculos no dependen del modelo generativo, la calidad de la interpretación inicial puede variar. Por eso se incorporó validación humana obligatoria antes de calcular la propuesta.

Sexto, la evaluación presentada se concentra en métricas técnicas y funcionales. No incluye todavía una validación formal con usuarios finales ni una medición económica real posterior a compras ejecutadas. Por lo tanto, el análisis permite defender la lógica del sistema y la calidad de sus proyecciones dentro del MVP, pero no medir impacto financiero real en una empresa.

Séptimo, las recomendaciones dependen de parámetros de decisión como margen mínimo, tolerancia al riesgo, criticidad y presupuesto disponible. Estos parámetros fueron definidos para el MVP y permiten demostrar el flujo completo, pero en una implantación real deberían calibrarse según el perfil del comprador. Por ejemplo, una empresa con alto costo de acopio podría preferir postergar aun cuando el forecast sugiera una suba moderada.

Octavo, las capturas y demostraciones de interfaz prueban integración funcional, pero no sustituyen la evaluación cuantitativa. Una pantalla puede mostrar una recomendación coherente, pero la solidez metodológica proviene de los datos que la alimentan: serie histórica, modelo seleccionado, métricas de error, reglas de decisión y restricciones económicas. Por esa razón, el análisis debe mantener juntas ambas evidencias: resultados numéricos y evidencia visual de integración.

---

# FUENTES BIBLIOGRÁFICAS

Arrieta Guevara, M. M. (2024). *Guía para la elaboración del Marco Metodológico*. Universidad de Mendoza.

Hyndman, R. J., & Athanasopoulos, G. (2021). *Forecasting: Principles and Practice* (3rd ed.). OTexts. https://otexts.com/fpp3/

IEEE Computer Society. (2024). *Guide to the Software Engineering Body of Knowledge (SWEBOK Guide), Version 4.0*.

Mitchell, S., O'Sullivan, M., & Dunning, I. (2011). PuLP: A Linear Programming Toolkit for Python. The University of Auckland.

Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M., & Duchesnay, É. (2011). Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research, 12*, 2825-2830.

Taylor, S. J., & Letham, B. (2018). Forecasting at scale. *The American Statistician, 72*(1), 37-45.
