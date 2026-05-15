# DEMO_DSS

Este documento deja un guion reproducible para demostrar que `BuildWise` funciona como DSS de compra trazable dentro del alcance MVP.

## Mensaje central

`BuildWise` no se limita a visualizar indicadores. Integra `forecast`, `criticidad` y `restricciones presupuestarias` para emitir una recomendacion operativa trazable: que comprar ahora, que postergar, con que impacto economico esperado y bajo que supuestos/confianza.

Frase corta para defensa:

```text
La visualizacion es la interfaz; el nucleo metodologico es la decision trazable de compra.
```

## Preparacion

1. Levantar backend y frontend.
2. Autenticarse con usuario de prueba.
3. Obtener IDs reales de materiales:

```http
GET /materiales
```

Materiales MVP esperados:

- `Cemento Portland`
- `Pastina`
- `Membrana Megaflex`

En los ejemplos se usan IDs de referencia `1`, `2` y `3`. Si la base local devuelve otros IDs, reemplazarlos en los payloads.

## Caso 1 - Recomendacion individual por material

Endpoint:

```http
POST /materiales/{material_id}/recomendacion-compra
```

Payload base:

```json
{
  "horizonte_meses": 3,
  "criticidad": "alta",
  "cantidad_objetivo": 100
}
```

Ejecutar el mismo caso para:

- `Cemento Portland`
- `Pastina`
- `Membrana Megaflex`

Evidencia que debe mostrarse:

- `decision`
- `precio_actual`
- `precio_proyectado_horizonte`
- `variacion_esperada_pct`
- `impacto_economico_estimado`
- `mape`
- `umbral_decision_pct`
- `supera_umbral_decision`
- `confiabilidad`
- `justificacion`
- `advertencias`

Lectura esperada:

```text
forecast -> decision -> impacto ARS/% -> confianza/umbral -> advertencias
```

Nota para explicar el umbral:

- `umbral_decision_pct = 5%` indica la variacion minima necesaria para emitir una accion fuerte cuando la confiabilidad no obliga a ser mas conservador.
- Si la variacion esperada queda por debajo de ese valor, por ejemplo `4.8291%`, el sistema recomienda monitorear o declara que no hay ventaja clara.
- El umbral evita que diferencias pequenas, potencialmente explicables por ruido del forecast, disparen recomendaciones tajantes.

## Caso 2 - Comparacion de estrategias

Endpoint:

```http
POST /materiales/{material_id}/comparacion-estrategias-compra
```

Payload:

```json
{
  "horizonte_meses": 3,
  "cantidad_objetivo": 100,
  "porcentaje_compra_inmediata": 0.5
}
```

Evidencia que debe mostrarse:

- estrategias `COMPRAR_AHORA`, `ESPERAR_AL_HORIZONTE` y `COMPRA_PARCIAL`;
- costo estimado por estrategia;
- diferencia ARS/% contra la mejor estrategia;
- `mejor_estrategia`;
- `ahorro_estimado`;
- `umbral_decision_pct`;
- `ventaja_significativa`;
- `justificacion`.

## Caso 3 - Presupuesto restrictivo multi-material

Este caso es el mas importante para demostrar DSS: el sistema no solo muestra datos, sino que decide como asignar presupuesto limitado.

Endpoint:

```http
POST /compras/recomendacion-operativa
```

Payload de demo:

```json
{
  "presupuesto_total": 180000,
  "horizonte_meses": 3,
  "materiales": [
    {
      "material_id": 1,
      "cantidad_objetivo": 100,
      "criticidad": "alta"
    },
    {
      "material_id": 2,
      "cantidad_objetivo": 40,
      "criticidad": "media"
    },
    {
      "material_id": 3,
      "cantidad_objetivo": 20,
      "criticidad": "baja"
    }
  ]
}
```

Si los IDs reales no son `1`, `2` y `3`, reemplazarlos con los devueltos por `GET /materiales`.

Evidencia que debe mostrarse:

- `fecha_calculo`
- `decision_resumen`
- `presupuesto_total`
- `presupuesto_utilizado`
- `presupuesto_restante`
- `ahorro_total_estimado`
- accion por material: `COMPRAR_AHORA`, `COMPRA_PARCIAL` o `POSTERGAR`
- cantidad a comprar ahora;
- cantidad a postergar;
- impacto economico estimado;
- confianza;
- criticidad;
- supuestos;
- advertencias.

Lectura esperada:

```text
Con presupuesto insuficiente, el sistema prioriza materiales por ahorro esperado ajustado por criticidad y respeta la restriccion presupuestaria.
```

## Respuestas clave de defensa

### Que comprar ahora

Se responde con `accion_recomendada` y `cantidad_comprar_ahora`.

### Que postergar

Se responde con `accion_recomendada = POSTERGAR` o con `cantidad_postergar > 0`.

### Cuanto cambia en plata y porcentaje

Se responde con `impacto_economico_estimado`, `variacion_esperada_pct` y diferencias ARS/% de estrategias.

### Con que confianza y bajo que supuestos

Se responde con `confiabilidad`, `mape`, `umbral_decision_pct`, `supuestos` y `advertencias`.

## Criterio de cierre

La demo queda completa si el jurado puede ver, sin reconstruir manualmente el razonamiento desde graficos separados:

- que datos se usaron;
- que horizonte se evaluo;
- que accion recomienda el sistema;
- que impacto economico estima;
- que confianza o advertencias aplican;
- que restriccion presupuestaria se respeto.
