# Guía para la Elaboración del Marco Metodológico y Análisis de Resultados (TIF 3)

Esta guía resume los lineamientos académicos para el Trabajo Final de Integración (TIF 3), basados en la cátedra de la Facultad de Ingeniería - Universidad de Mendoza.

## 1. Estructura General del TFG

### Parte 1: Marco Teórico
- **Capítulo 1: Marco Referencial:** Identificación, Justificación, Estado del arte, Objetivos.
- **Capítulo 2: Marco Conceptual:** Marco tecnológico ingenieril, Marco interdisciplinario.

### Parte 2: Desarrollo de Ingeniería
- **Capítulo 1: Marco Metodológico:** Desarrollo de ingeniería (Metodología).
- **Capítulo 2: Análisis de Resultados.**

### Parte 3: Cierre
- **Conclusiones.**
- **Anexos.**
- **Fuentes Bibliográficas.**

---

## 2. Marco Metodológico (Capítulo 1 del Desarrollo)

El corazón procedimental del TIF. No es un listado de pasos o historias de usuario, sino la demostración de decisiones fundamentadas.

### Elementos Clave
1.  **Metodología de Desarrollo:** Ágil (Scrum/Kanban), orientada a objetos, mixta, etc. **Justificar** por qué es la más adecuada.
2.  **Normas de Escritura:** Consistencia. O 1ra persona del plural ("Desarrollamos") o 3ra impersonal ("Se desarrolló").
3.  **Bibliografía:** Citar fuentes fiables (IEEE, ACM, libros de Ing. de Software, documentación oficial) bajo Normas **APA 7ma**.
4.  **Secciones Típicas:**
    - Arquitectura del sistema (capas, módulos, flujos).
    - Tecnologías y herramientas (Justificar elección vs. alternativas descartadas).
    - Desarrollo por componente (Qué hace, cómo se construyó).
    - Integración (Interacción entre partes y sistemas externos).
    - Iteraciones o Sprints (Objetivos, entregables y aprendizajes).

### Criterio de Justificación
Evitar lo insuficiente ("Se usó React"). Usar lo correcto: **Descripción + Justificación**.
*Ejemplo: "Se eligió PostgreSQL sobre MySQL por su soporte nativo de datos JSON y robustez en consultas complejas..."*

### Código Fuente
- No incluir bloques enteros.
- Fragmentos representativos (10-20 líneas) para ilustrar decisiones de diseño complejas.
- Obligatorio: Explicación técnica asociada.

---

## 3. Análisis de Resultados (Capítulo 2 del Desarrollo)

Responde a: *¿Qué obtuve y qué significa lo que obtuve?*

### Pautas de Redacción
1.  **Presentar resultados en bruto:** Métricas, gráficos, tablas, capturas.
2.  **Describir datos:** Explicar qué se observa sin interpretar todavía (ej. "El modelo obtuvo 91% accuracy").
3.  **Interpretar vs. Objetivos:** ¿Alcanza el umbral planteado? ¿Por qué quedó por encima o por debajo?
4.  **Analizar discrepancias:** Determinar dónde falla el sistema y qué explica la diferencia entre escenarios.
5.  **Señalar limitaciones del análisis:** Qué no se pudo medir, sesgos, qué quedó fuera del alcance.

**⚠️ STOP:** No recomendar trabajo futuro ni generalizar aquí (eso va en Conclusiones).

---

## 4. Conclusiones (Capítulo Final)

Responde a: *¿Qué aprendí y qué valor tiene?*
- Éxito general del proyecto.
- Aporte al campo o disciplina.
- **Trabajo futuro (Exclusivo de esta sección).**
- Aprendizajes del proceso.
- Comparación con el estado del arte.

---

## Tabla Espejo: Análisis vs. Conclusión

| Si en el Análisis (Cap. 2) se dijo... | En las Conclusiones se dirá... |
| :--- | :--- |
| "La latencia promedio fue de 120 ms, dentro del umbral." | "El sistema cumple requisitos de tiempo real, validando la arquitectura." |
| "El módulo falló en condiciones de baja iluminación." | "La robustez ante condiciones adversas es la principal limitación y dirección futura." |
| "Los usuarios completaron el 85% de las tareas." | "La interfaz alcanzó un nivel satisfactorio, confirmando el enfoque centrado en el usuario." |
