# REGISTRO_DECISIONES_TRABAJO

Este documento registra decisiones operativas tomadas durante el cierre del MVP. Complementa `docs/DECISIONES_TESIS.md`, que queda reservado para decisiones metodologicas mas formales.

## Criterio de uso

- Registrar decisiones que afecten alcance, defensa, demo, HU, contratos API o criterios de cierre.
- Mantener frases breves y accionables.
- Cuando una decision sea metodologicamente relevante para tesis, replicarla o resumirla tambien en `docs/DECISIONES_TESIS.md`.

---

## RD-01 - Presentar BuildWise como DSS MVP

- Fecha: mayo de 2026
- Decision: presentar el sistema actual como `DSS de compra trazable en estado MVP`.
- Motivo: el sistema ya transforma datos historicos y forecast en recomendacion economica accionable.
- Alcance: no se presenta como asistente conversacional completo ni como sistema proactivo.
- Evidencia: `HU21`, `HU22`, `HU23`, `HU28` y `HU28b`.

## RD-02 - Congelar alcance funcional antes de Epica 6/7

- Fecha: mayo de 2026
- Decision: no agregar chat, alertas proactivas, sustitutos, mas materiales ni nuevos modelos para el cierre MVP.
- Motivo: el riesgo principal ya no es funcionalidad faltante, sino evidencia, consistencia y defensa.
- Impacto: el trabajo restante se concentra en demo reproducible, documentacion, tests y salida DSS clara.

## RD-03 - Renumerar HU agregadas con sufijo `b`

- Fecha: mayo de 2026
- Decision: evitar `HU34` y `HU35` como numeros nuevos independientes.
- Renumeracion:
  - `HU34` -> `HU27b`
  - `HU35` -> `HU28b`
- Motivo: mantener agrupacion conceptual sin mezclar numeracion de epicas.
- Impacto: `HU27b` queda en asistencia conversacional futura; `HU28b` queda como cierre DSS de recomendacion operativa trazable.

## RD-04 - Definir `HU28b` como salida estrella del DSS

- Fecha: mayo de 2026
- Decision: usar `/compras/recomendacion-operativa` como endpoint principal de demostracion DSS.
- Motivo: consolida accion, cantidades, presupuesto, impacto economico, confianza, supuestos y advertencias en una unica salida.
- Campos clave:
  - `fecha_calculo`
  - `decision_resumen`
  - `accion_recomendada`
  - `cantidad_comprar_ahora`
  - `cantidad_postergar`
  - `presupuesto_utilizado`
  - `presupuesto_restante`
  - `impacto_economico_estimado`
  - `impacto_economico_pct`
  - `confianza`
  - `supuestos`
  - `advertencias`

## RD-05 - Preparar demo reproducible del DSS

- Fecha: mayo de 2026
- Decision: documentar una demo con tres casos individuales y un caso multi-material restrictivo.
- Casos:
  - `Cemento Portland`
  - `Pastina`
  - `Membrana Megaflex`
  - optimizacion multi-material con presupuesto limitado
- Evidencia documental: `docs/DEMO_DSS.md`.
- Motivo: demostrar que el sistema responde que comprar, que postergar, cuanto impacta y bajo que supuestos.

## RD-06 - Verificacion tecnica enfocada

- Fecha: mayo de 2026
- Decision: usar el siguiente comando como verificacion critica del DSS:

```bash
.venv/bin/python -m pytest --no-cov tests/test_purchase_recommendations.py tests/test_purchase_strategies.py tests/test_purchase_optimization.py
```

- Motivo: el ejecutable `pytest` del entorno local puede apuntar a una ruta historica invalida; usar el interprete del venv evita ese problema.
- Ultimo resultado registrado: `33 passed`.

## RD-07 - Mensaje unico de defensa

- Fecha: mayo de 2026
- Decision: alinear README, HU, demo y tesis con la siguiente idea:

```text
BuildWise no se limita a visualizar indicadores. Integra forecast, criticidad y restricciones presupuestarias para emitir una recomendacion operativa trazable.
```

- Frase oral corta:

```text
La visualizacion es la interfaz; el nucleo metodologico es la decision trazable de compra.
```

- Motivo: separar claramente el sistema de un dashboard descriptivo.
