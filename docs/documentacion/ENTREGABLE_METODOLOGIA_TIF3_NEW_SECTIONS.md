# CAPÍTULO 1: MARCO REFERENCIAL

## 1.1 Identificación del Problema: La Construcción en un Contexto de Volatilidad Económica

La industria de la construcción en la República Argentina se encuentra inmersa en un ecosistema macroeconómico caracterizado por una inflación persistente y una volatilidad cambiaria que distorsiona las señales de precios de manera sistémica. Este fenómeno no solo afecta la rentabilidad de las empresas del sector, sino que compromete la viabilidad técnica de los presupuestos de obra a mediano y largo plazo.

El problema central identificado radica en la **incertidumbre de costos**. En un entorno donde los precios de insumos críticos (como el acero, cemento o materiales áridos) pueden experimentar variaciones superiores al 10% mensual, la planificación financiera tradicional se vuelve obsoleta. Las empresas constructoras enfrentan tres desafíos críticos:
1.  **Dispersión de Precios:** La falta de precios de referencia claros genera que un mismo insumo posea valores significativamente distintos según el proveedor o el momento de la consulta, dificultando la detección de oportunidades de compra o la identificación de sobreprecios.
2.  **Obsolescencia Presupuestaria:** El tiempo que transcurre entre la licitación de una obra y su ejecución efectiva suele erosionar el margen de ganancia proyectado debido a la escalada de costos no anticipada.
3.  **Carencia de Herramientas Predictivas:** La mayoría de las PyMEs del sector dependen de métodos empíricos o proyecciones lineales simples (como el uso de promedios históricos sin considerar variables macroeconómicas), lo cual es insuficiente para capturar la complejidad de la economía argentina.

## 1.2 Justificación del Proyecto: Valor Estratégico y Predictibilidad

La implementación de BuildWise (SICONS) se justifica por la necesidad imperativa de dotar a las empresas constructoras de una capacidad analítica defensiva y estratégica. El valor del proyecto no reside únicamente en la automatización del registro de precios, sino en la transformación de datos crudos en inteligencia accionable.

Desde una perspectiva económica, el ahorro directo se manifiesta mediante la optimización del *timing* de compra. Un sistema que predice una aceleración en el precio del cemento permite que el gestor de compras adelante adquisiciones cuando el forecast, la criticidad y el presupuesto disponible justifican esa decisión.

Desde el punto de vista organizacional, la predictibilidad presupuestaria permite una mejor negociación con proveedores y clientes. Contar con un Sistema de Soporte a la Decisión (DSS) que integra regresores macroeconómicos (IPC, ICC, Dólar) otorga una ventaja competitiva: la capacidad de anticipar el impacto de una devaluación o un ajuste tarifario sobre los costos operativos reales.

## 1.3 Estado del Arte: De la Planilla de Cálculo al Machine Learning

Tradicionalmente, la gestión de precios en la construcción ha dependido de herramientas de baja complejidad y alta intervención manual:
-   **Planillas de Cálculo (Excel):** Aunque versátiles, carecen de escalabilidad, son propensas a errores de carga y no permiten el modelado de series temporales complejas ni la integración automática de señales externas.
-   **Software de Presupuestación (ERP Sectoriales):** Si bien gestionan inventarios y cómputos, suelen ser sistemas retrospectivos. Informan cuánto costó un material, pero rara vez ofrecen una visión prospectiva basada en modelos estadísticos avanzados.

En la frontera tecnológica actual, el auge del **Business Intelligence (BI)** y la **Ciencia de Datos** ha comenzado a permear en la industria constructora. Los enfoques modernos de DSS integran algoritmos de Machine Learning para el análisis de series de tiempo. Sin embargo, la mayoría de estas soluciones son desarrollos a medida para grandes corporaciones o están diseñadas para mercados estables (EE.UU./Europa). 

BuildWise se posiciona en esta brecha tecnológica, aplicando técnicas de vanguardia como los modelos aditivos de Prophet y la detección de anomalías mediante Random Forest, pero calibrados específicamente para las anomalías y dinámicas propias del mercado argentino, donde la correlación entre variables macroeconómicas y precios locales es un factor determinante que los modelos convencionales suelen ignorar.

---

# CAPÍTULO 2: MARCO CONCEPTUAL

## 2.1 Marco Tecnológico y de Ingeniería de Software

El desarrollo de un sistema robusto de análisis predictivo exige un stack tecnológico que equilibre la eficiencia computacional con la flexibilidad para el procesamiento de datos.

### 2.1.1 Lenguaje de Programación y Backend
-   **Python 3.11:** Se erige como el lenguaje predilecto debido a su madurez en el ecosistema de Inteligencia Artificial. Su capacidad para integrar librerías de bajo nivel con sintaxis de alto nivel permite un desarrollo ágil de algoritmos complejos.
-   **FastAPI:** Este framework de última generación aprovecha las capacidades asíncronas de Python (`asyncio`) y la validación de tipos estáticos de `Pydantic`. Su elección se fundamenta en la necesidad de servir predicciones en tiempo real con latencias mínimas y contratos de datos estrictos (OpenAPI).

### 2.1.2 Persistencia y Gestión de Datos
-   **PostgreSQL:** Como motor de base de datos relacional, garantiza la integridad referencial necesaria para un catálogo de materiales complejo. Su robustez en el manejo de transacciones y soporte para consultas analíticas avanzadas lo hace ideal para almacenar series históricas de gran volumen.
-   **SQLAlchemy y Alembic:** El uso de un ORM moderno permite desacoplar la lógica de negocio del esquema físico, mientras que Alembic asegura la trazabilidad y reproducibilidad del esquema de datos mediante migraciones versionadas.

### 2.1.3 Inteligencia Artificial y Forecasting: El Paradigma de Modelos Aditivos
-   **Prophet (Meta):** Seleccionado como el motor principal de predicción. A diferencia de los modelos autorregresivos tradicionales (ARIMA), Prophet trata el problema de series temporales como un ejercicio de ajuste de curvas (*curve-fitting*). 
    -   *Justificación Técnica vs. ARIMA:* Mientras que ARIMA requiere una estacionalidad regular y es sensible a valores faltantes, Prophet maneja de forma nativa los huecos en la serie y los cambios bruscos de tendencia (puntos de cambio o *changepoints*). En la economía argentina, donde las devaluaciones generan saltos discretos en el nivel de precios, la capacidad de Prophet para detectar y modelar estos puntos de cambio de forma automática es superior a la rigidez de los modelos integrados.
    -   *Justificación Técnica vs. Deep Learning (LSTM):* Aunque las Redes de Memoria a Largo Plazo (LSTM) son potentes, requieren volúmenes de datos masivos para evitar el sobreajuste (*overfitting*). BuildWise opera con series mensuales de aproximadamente 10-15 años (120-180 puntos), un conjunto de datos pequeño para redes neuronales profundas pero ideal para modelos bayesianos como Prophet. Además, la interpretabilidad de Prophet permite que un experto en construcción valide los componentes de tendencia y estacionalidad, algo imposible en modelos de "caja negra" como LSTM.
-   **Machine Learning (Scikit-learn):** Se emplea **Random Forest Regressor** específicamente para detección de anomalías en la serie mensual.
    -   *Justificación Técnica:* el Random Forest estima un precio mensual esperado a partir de variables temporales y rezagos de la propia serie del material. Luego se analizan los residuos con un criterio robusto basado en IQR. Esto reemplaza el umbral fijo de variación y evita marcar como anomalía una suba que puede ser normal para la dinámica histórica del material.

## 2.2 Marco Interdisciplinario: Economía, Gestión de la Construcción y Logística Estratégica

El éxito de BuildWise depende de la correcta interpretación de los fenómenos económicos que rigen el sector, integrando conocimientos de tres dominios científicos.

### 2.2.1 Economía de la Construcción e Inflación de Costos
En la Argentina, el costo de la construcción se mide a través de índices oficiales que sirven como referencia para la actualización de contratos. BuildWise no solo consume estos índices, sino que los utiliza como **señales de control** para desestacionalizar los precios reales.
-   **ICC (Índice del Costo de la Construcción):** Elaborado por el INDEC, mide las variaciones que experimenta el costo de la construcción privada en la Ciudad Autónoma de Buenos Aires y partidos del GBA.
-   **CAC (Índice de la Cámara Argentina de la Construcción):** Es el índice de referencia para el sector privado, utilizado para redeterminar precios en contratos de obra.
BuildWise integra estos índices como **regresores externos**, asumiendo que el precio de un material no solo depende de su historia, sino de la inercia inflacionaria capturada por estos indicadores. La técnica de **regresión dinámica** incorporada permite al modelo "aprender" cuánto tiempo tarda un aumento en el índice CAC en trasladarse al precio de mostrador de un material específico (efecto de rezago o *lag*).

### 2.2.3 Optimización de la Cadena de Suministro y Teoría de Inventarios
La gestión de compras en construcción se basa en el principio de **abastecimiento estratégico**. El sistema aplica conceptos de investigación operativa para resolver el problema de cuándo comprar (oportunidad) y cuánto comprar (volumen), bajo restricciones de flujo de caja. 
-   **Modelo de Lote Económico de Compra (EOQ) Adaptado:** En contextos estables, el EOQ minimiza costos de mantenimiento vs. costos de pedido. En contextos inflacionarios, BuildWise redefine esta función de costo incluyendo el **costo de oportunidad por desvalorización monetaria**. 
-   **Programación Lineal:** La optimización lineal permite maximizar el valor futuro de las existencias actuales frente a la inflación proyectada, resolviendo sistemas de inecuaciones que consideran el presupuesto disponible, la capacidad de acopio y la curva de demanda proyectada de la obra.

---

# 5. DESARROLLO DE INGENIERÍA POR COMPONENTE (EXTENSIÓN)

## 5.7 Módulo de Seguridad y Autenticación (Auth Module)

La integridad de la información sensible en BuildWise se garantiza mediante un módulo de seguridad basado en estándares industriales. La arquitectura de seguridad se divide en dos capas principales:

### 5.7.1 Cifrado de Credenciales y Hashing
A diferencia de sistemas que almacenan contraseñas en texto plano o con algoritmos obsoletos, BuildWise implementa **PBKDF2 (Password-Based Key Derivation Function 2)** con el algoritmo de hash **SHA-256**. Se utiliza un factor de iteración de 260.000 rondas y una sal (*salt*) aleatoria de 16 bytes por cada usuario. Esta configuración protege el sistema contra ataques de fuerza bruta y tablas de arco iris, asegurando que incluso en caso de una filtración de la base de datos, las credenciales permanezcan seguras.

### 5.7.2 Gestión de Sesiones mediante JWT (JSON Web Tokens)
Para la autorización en el API, se ha desarrollado una implementación personalizada de JWT que evita dependencias pesadas y garantiza un control total sobre el ciclo de vida del token.
-   **Firma:** Los tokens se firman mediante el algoritmo **HMAC-SHA256**, utilizando una clave secreta gestionada a través de variables de entorno.
-   **Estructura del Payload:** El token transporta la identidad del usuario (`sub`), su nombre de usuario, rol y una marca de tiempo de expiración (`exp`).
-   **Validación:** El sistema verifica la integridad de la firma y la vigencia del token en cada petición protegida, implementando un mecanismo de autenticación *stateless* que facilita la escalabilidad horizontal del backend.

## 5.8 Asistente Comercial e Integración de LLM (Chat Module)

El módulo de Chat transforma la interacción con los datos de un reporte estático a una experiencia conversacional. Este componente actúa como un intermediario inteligente entre el usuario y la base de datos analítica.

### 5.8.1 Arquitectura del Cliente de IA
Se implementó un diseño de cliente polimórfico capaz de interactuar con un proveedor compatible con **OpenAI Chat Completions** o con **Anthropic (Claude)**. El sistema utiliza una abstracción que estandariza las peticiones y respuestas, permitiendo cambiar el motor de IA subyacente mediante configuración, sin alterar la lógica de negocio.

### 5.8.2 Gestión de Contexto y Prompts
La inteligencia del asistente reside en la técnica de **In-Context Learning**. Antes de cada interacción, el sistema inyecta un "System Prompt" que define la personalidad y las restricciones del asistente (ej: "Eres un experto en costos de construcción en Argentina"). 
El módulo gestiona una ventana de contexto que incluye:
-   **Historial de Conversación:** Permite mantener la coherencia en hilos de consulta largos.
-   **Inyección de Datos Calculados:** Cuando un usuario consulta por un precio, forecast o recomendación, el sistema recupera o calcula esos valores con servicios internos y los incluye como contexto en la petición al LLM. El modelo generativo redacta o estructura la respuesta, pero no inventa importes, decisiones ni métricas.

## 5.9 Diseño del Esquema de Base de Datos (ER Model)

El modelo de datos de BuildWise ha sido normalizado para soportar la complejidad de las series temporales y la diversidad de fuentes de información.

### 5.9.1 Entidades Nucleares
-   **Materiales:** Almacena la definición abstracta de un insumo (nombre, categoría, unidad base). La clave estable usada para calibraciones se deriva del nombre del material, por ejemplo `cemento-portland`.
-   **Presentaciones:** Define la forma comercial del material (ej: Bolsa de 50kg, Pallet, m3). Esta tabla es crítica para realizar la **normalización de precios**, permitiendo comparar el costo de un material independientemente de su packaging.
-   **Fuentes:** Registra el origen de la información (corralones, índices oficiales, sitios web). Permite ponderar la fiabilidad de los datos.

### 5.9.2 Entidades Operativas y de Señales
-   **Precios Históricos:** Es la tabla de mayor volumen. Registra el precio original, el precio normalizado, la moneda, la fecha y el tipo de dato (Real o Estimado). Incluye índices compuestos sobre `(material_id, fecha DESC)` para optimizar el rendimiento de los algoritmos de forecasting.
-   **External Index Values:** Almacena los valores de los regresores macroeconómicos y sectoriales disponibles, como IPC, IPIM, dólar e índices de construcción. Está diseñada para permitir la carga masiva de series temporales externas que alimentan a los modelos de Prophet.
-   **Alertas y Márgenes:** Gestionan la capa de personalización del usuario, permitiendo definir márgenes comerciales y disparar notificaciones cuando se detectan oportunidades de compra o anomalías.

## 5.10 Metodología de Despliegue y DevOps

Para garantizar que BuildWise sea un sistema listo para producción y fácil de mantener, se adoptó una filosofía de **Infraestructura como Código (IaC)**.

### 5.10.1 Contenerización con Docker
El sistema completo está orquestado mediante contenedores Docker. Esto elimina el problema del "en mi máquina funciona", asegurando que las versiones de Python, las librerías de ciencia de datos y el motor de base de datos sean idénticos en desarrollo, testing y producción. Se utilizan archivos `Dockerfile` optimizados para reducir el tamaño de las imágenes y `docker-compose.yml` para gestionar la comunicación entre el backend y PostgreSQL.

### 5.10.2 Automatización con Makefile y Entornos
Se implementó un `Makefile` como punto de entrada único para las operaciones de desarrollo. Esto permite automatizar tareas complejas como:
-   Levantamiento de infraestructura (`make up`).
-   Ejecución de tests mediante `.venv/bin/python -m pytest -q`.
-   Gestión de migraciones de base de datos mediante Alembic.
La configuración del sistema se desacopla mediante el uso de archivos `.env`, permitiendo inyectar secretos (claves de API de IA, credenciales de DB) de forma segura y diferenciada según el entorno de ejecución.
