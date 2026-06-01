# Borrador de Tesis SICONS / BuildWise

---

# PARTE 1: MARCO TEÓRICO

## 1. Marco Referencial

### 1.1 Identificación del Problema
SICONS / BuildWise es un sistema de soporte a la decisión orientado al análisis y proyección de precios de materiales de construcción. El dominio presenta tres dificultades principales:
1. Los precios cambian con frecuencia y no todos los materiales comparten el mismo comportamiento temporal.
2. Los datos disponibles combinan fuentes heterogéneas, series reales, series híbridas y regresores externos.
3. La reproducibilidad del entorno no puede depender de archivos personales, de IDs locales accidentales ni de imports manuales no gobernados.

### 1.2 Justificación
La falta de una herramienta reproducible, trazable y metodológicamente defendible para anticipar el comportamiento de precios genera incertidumbre en las decisiones de compra. Este proyecto convierte datos de precios en una capa de análisis y forecast con criterios explícitos de selección de modelo y trazabilidad.

### 1.3 Objetivos

#### Objetivo general
Diseñar e implementar un sistema reproducible de forecasting y soporte a la decisión para precios de materiales de construcción, con selección controlada de modelos y trazabilidad metodológica.

#### Objetivos específicos
- Construir una base mínima reproducible para la tesis.
- Reforzar la reproducibilidad del bootstrap mediante artefactos versionados.
- Diferenciar el comportamiento de forecasting por material y horizonte.
- Incorporar un selector de modelos basado en una identidad estable de material.
- Exponer metadatos de selección y confiabilidad del forecast.

### 1.4 Alcance
El alcance cubre la capa de datos histórica, el bootstrap de la base, el forecast por material, la selección de configuración de modelo y la exposición de metadatos en el endpoint. Quedan fuera la activación productiva por defecto y asistentes conversacionales avanzados.

## 2. Marco Conceptual
*(Sección a completar con Marco Tecnológico Ingenieril e Interdisciplinario)*

---

# PARTE 2: DESARROLLO DE INGENIERÍA

## 3. Marco Metodológico

El presente capítulo detalla el marco procedimental y las decisiones de ingeniería adoptadas para el desarrollo de BuildWise. Se fundamenta en la necesidad de construir una herramienta que no solo procese datos, sino que garantice la reproducibilidad científica exigida en un Trabajo Final de Integración.

### 3.1 Metodología de Desarrollo
Se adoptó una **metodología ágil basada en prototipado evolutivo**. Esta elección se justifica por la naturaleza experimental del proyecto, donde la precisión del motor de forecasting y la eficacia del selector de modelos requerían validaciones empíricas constantes (backtesting) antes de consolidar la arquitectura final.

El proceso se organizó en iteraciones cortas, permitiendo ajustar los hiperparámetros de los modelos y la estructura del dataset canónico basándose en los resultados obtenidos en cada ciclo. Para la redacción de este documento, se mantiene de forma estricta la **voz impersonal técnica** (ej: "se diseñó", "el sistema implementa"), asegurando la coherencia y el tono académico formal.

### 3.2 Arquitectura del Sistema
El sistema se estructuró siguiendo un patrón de **arquitectura en capas desacopladas**, lo que permite la evolución independiente del motor de IA respecto a la lógica de negocio y la interfaz de usuario.

1.  **Capa de Persistencia (PostgreSQL):** Gestiona el almacenamiento de series temporales, materiales y metadatos de configuración.
2.  **Capa de Lógica de Negocio (Backend):** Implementada en Python, se encarga del procesamiento de señales, la ejecución de modelos de forecasting y la resolución de políticas del selector.
3.  **Capa de Presentación (Frontend):** Desarrollada en React, orientada a la visualización de decisiones operativas y métricas de confianza.

La comunicación entre componentes se realiza mediante un **API REST stateless**, lo cual facilita el despliegue en contenedores y asegura la escalabilidad horizontal del servicio de predicción.

### 3.3 Tecnologías y Justificación Técnica
Cada herramienta del stack fue seleccionada bajo criterios de eficiencia técnica y soporte bibliográfico:

-   **FastAPI sobre Flask/Django:** Se eligió FastAPI debido a su alto rendimiento (comparable a Go o Node.js) y su uso extensivo de *Type Hints*. Esto permitió automatizar la validación de los contratos de datos del forecast, reduciendo errores en la interpretación de metadatos complejos.
-   **Facebook Prophet sobre ARIMA/SARIMA:** La elección de Prophet se justifica por su robustez intrínseca ante datos faltantes y cambios de tendencia bruscos, comunes en la economía de la construcción argentina. A diferencia de modelos estadísticos clásicos, Prophet permite incorporar regresores externos (IPC, IPIM, Dólar) de forma aditiva, facilitando la interpretación económica de los coeficientes.
-   **PostgreSQL sobre MySQL:** Se optó por PostgreSQL debido a su capacidad superior para manejar consultas complejas con *JOINs* y su soporte nativo de tipos JSONB. Esta última característica fue crítica para almacenar las configuraciones dinámicas de los modelos sin necesidad de esquemas rígidos.

### 3.4 Desarrollo por Componentes y Reproducibilidad

#### 3.4.1 Dataset Canónico y Bootstrap
Para garantizar la reproducibilidad de la tesis, se implementó un mecanismo de **Bootstrap Operativo**. Se separó la fuente de datos operativa (sujeta a cambios) de un **extracto canónico versionado** (`.csv`). Este archivo queda congelado como la "fuente de verdad" para las mediciones de backtesting presentadas en el análisis de resultados.

#### 3.4.2 Selector de Modelos y Identidad Estable
Un desafío técnico fue asegurar que la calibración de los modelos fuera independiente del entorno de despliegue. Se implementó una **Identidad Estable de Material** mediante `material_key`. El selector no decide basándose en IDs locales de la base de datos, sino en claves semánticas (ej: `cemento_portland`), lo que permite que el sistema mantenga su inteligencia aun si se migra la base de datos a un nuevo entorno.

#### 3.4.3 Detección de Anomalías (Decisión de Diseño Compleja)
Se reemplazó el criterio de umbral fijo del 8% por un modelo de **Random Forest Regressor** para identificar valores atípicos. Esta decisión responde a la necesidad de un criterio dinámico que aprenda la volatilidad histórica de cada material.

A continuación, se presenta el fragmento representativo del motor de detección:

```python
# Implementación de detección de anomalías mediante residuo de Random Forest
def detect_anomalies_rf(series_data, threshold_iqr=1.5):
    # Se entrena un regresor para estimar el comportamiento 'esperado'
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Se calcula el residuo (diferencia entre real y esperado)
    expected = model.predict(X_all)
    residuals = np.abs(series_data - expected)

    # Se aplica el criterio de Rango Intercuartílico (IQR) sobre los residuos
    q1, q3 = np.percentile(residuals, [25, 75])
    iqr = q3 - q1
    upper_bound = q3 + (threshold_iqr * iqr)

    return residuals > upper_bound
```
**Justificación técnica:** El uso de residuos de Random Forest permite separar el ruido estacional de las anomalías reales. Al aplicar IQR sobre los residuos en lugar del valor absoluto del precio, se evita marcar como anomalías los incrementos inflacionarios esperados, detectando únicamente desviaciones fuera de la tendencia aprendida.

### 3.5 Integración y Validación
La integración de componentes se validó mediante **pruebas de contrato** y **backtesting temporal**. Se definieron 9 *folds* de validación cruzada para asegurar que el MAPE reportado fuera estadísticamente significativo y no un producto del azar en un segmento temporal específico.

## 4. Análisis de Resultados

### 4.1 Presentación de Resultados (Métricas de Cemento Portland)
La secuencia de pruebas para Cemento Portland mostró los siguientes resultados de MAPE (Mean Absolute Percentage Error) a 3 meses:
- Prophet Base (Baseline): ~8.5%
- Prophet + Regresores Económicos (IPC, Dólar): ~6.2%
- Prophet + IPIM Nivel General: **4.98%** (obtenido con 9 folds de backtesting temporal).
- Prophet + IPIM + ICC/CAC var_mat: **4.22%**.

### 4.2 Interpretación de los Datos
El descenso del MAPE del 8.5% al 4.22% valida la hipótesis de que la incorporación de señales sectoriales específicas (ICC/CAC) mejora la precisión del modelo por encima de los regresores macroeconómicos generales. Un MAPE de 4.22% se considera suficiente y defendible para el objetivo de apoyar decisiones de compra en el sector.

### 4.3 Análisis de Discrepancias y Limitaciones
En `Membrana Megaflex`, la incorporación de nuevos regresores mejoró los horizontes de 3 y 6 meses, pero no superó el mejor resultado histórico para 12 meses. Esto confirma que no existe un modelo universal óptimo para todos los horizontes.
**Limitaciones:** El análisis se realizó sobre 1.200 muestras mensuales. No es posible determinar si el comportamiento observado se mantiene con volúmenes de datos significativamente mayores, lo cual constituye una limitación del presente análisis.

---

# PARTE 3: CIERRE

## 5. Conclusiones
El proyecto alcanzó el objetivo general de crear un sistema reproducible y trazable para el forecasting de materiales. Se demostró que la especialización por material y horizonte, gestionada a través de un selector de políticas, es superior a un enfoque de modelo único. La arquitectura implementada permite la evolución independiente de los modelos sin alterar el contrato del API.

### 5.1 Aporte y Aprendizajes
Este trabajo aporta una metodología clara para la integración de regresores económicos en el pronóstico de materiales de construcción en contextos de alta inflación. Se aprendió que la calidad del "bootstrap" y la limpieza del dataset canónico son tan críticos como la elección del algoritmo de IA.

### 5.2 Trabajo Futuro
- **Activación Progresiva:** Pasar el selector a modo "on-by-default" tras una fase de monitoreo en ambiente controlado.
- **Visualización de Justificación:** Extender el frontend para exponer por qué se eligió un modelo determinado.
- **Modelos Alternativos:** Evaluar arquitecturas de Deep Learning (ej. Transformers o LSTMs) cuando la densidad de datos lo permita.

## 6. Fuentes Bibliográficas
*(Citar literatura académica de Ingeniería de Software y Documentación Técnica siguiendo Normas APA 7ma)*
