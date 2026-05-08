# Efectividad Forecasting de Tres Materiales

Materiales incluidos:

- `Cemento Portland`
- `Pastina`
- `Membrana Megaflex`

Fuentes consolidadas:

- `tmp/experiments/cemento_forecast_benchmark_master.csv`
- `tmp/experiments/otros_materiales_benchmark_master.csv`

Convencion:

- `efectividad_informal = 100 - MAPE`
- La metrica principal de decision sigue siendo `MAPE`
- La efectividad informal se usa como lectura comunicacional complementaria
- No deben compararse horizontes `3`, `6` y `12` como si fueran equivalentes

## Enfasis: Cemento Portland

`Cemento Portland` es el material de mayor peso metodologico del sistema porque se apoya en una serie real, densa y continua. Por eso el benchmark experimental se profundizo mucho mas que en los otros materiales y hoy concentra la mayor evidencia para defender un criterio de mejora y amesetamiento relativo.

### Horizonte 3 meses

| Modelo | Regresores / features | MAPE | Efectividad informal | Estado |
|---|---|---:|---:|---|
| `ensemble_simple_top2` | promedio(`prophet_ipim_nivel_general`, `prophet_ipim_nivel_general_medias_moviles`) | `4.08` | `95.92%` | `candidato` |
| `prophet_ipim_icc_var_materials` | `ipim_nivel_general + icc_var_materials` | `4.22` | `95.78%` | `candidato` |
| `prophet_ipim_cac_var_materials` | `ipim_nivel_general + var_materials` | `4.33` | `95.67%` | `candidato` |
| `prophet_ipim_cac_var_general` | `ipim_nivel_general + var_general` | `4.62` | `95.38%` | `candidato` |
| `prophet_ipim_icc_var_general` | `ipim_nivel_general + icc_var_general` | `4.64` | `95.36%` | `candidato` |
| `prophet_ipim_nivel_general` | `ipim_nivel_general` | `4.93` | `95.07%` | `baseline` |

### Horizonte 6 meses

| Modelo | Regresores / features | MAPE | Efectividad informal | Estado |
|---|---|---:|---:|---|
| `prophet_ipim_icc_var_materials` | `ipim_nivel_general + icc_var_materials` | `5.52` | `94.48%` | `candidato` |
| `prophet_ipim_cac_var_materials` | `ipim_nivel_general + var_materials` | `5.99` | `94.01%` | `candidato` |
| `prophet_ipim_icc_var_general` | `ipim_nivel_general + icc_var_general` | `6.71` | `93.29%` | `candidato` |
| `prophet_ipim_cac_var_general` | `ipim_nivel_general + var_general` | `6.85` | `93.15%` | `candidato` |
| `prophet_ipim_nivel_general` | `ipim_nivel_general` | `7.51` | `92.49%` | `baseline` |

### Horizonte 12 meses

| Modelo | Regresores / features | MAPE | Efectividad informal | Estado |
|---|---|---:|---:|---|
| `prophet_ipim_icc_var_materials` | `ipim_nivel_general + icc_var_materials` | `4.51` | `95.49%` | `candidato` |
| `prophet_ipim_cac_var_materials` | `ipim_nivel_general + var_materials` | `4.69` | `95.31%` | `candidato` |
| `prophet_ipim_icc_var_general` | `ipim_nivel_general + icc_var_general` | `5.16` | `94.84%` | `candidato` |
| `prophet_ipim_cac_var_general` | `ipim_nivel_general + var_general` | `5.94` | `94.06%` | `candidato` |
| `prophet_ipim_nivel_general` | `ipim_nivel_general` | `10.38` | `89.62%` | `baseline` |

### Lectura actual para Cemento

- Mejor baseline productivo actual: `prophet_ipim_nivel_general`
- Mejor candidata experimental por regresores: `prophet_ipim_icc_var_materials`
- Segunda mejor candidata experimental: `prophet_ipim_cac_var_materials`
- Mejor resultado puntual a `3` meses: `ensemble_simple_top2`

Desde el punto de vista metodologico, la candidata mas defendible hoy no es el ensemble sino `prophet_ipim_icc_var_materials`, porque mejora al baseline en los tres horizontes y se sostiene sobre regresores interpretables.

## Pastina

### Horizonte 3 meses

| Modelo | MAPE | Efectividad informal | MAE |
|---|---:|---:|---:|
| `prophet_blue_ipc` | `5.00` | `95.00%` | `120.90` |
| `prophet_oficial_ipc_blue` | `5.12` | `94.88%` | `122.62` |
| `prophet_oficial_ipc` | `5.29` | `94.71%` | `129.44` |

### Horizonte 6 meses

| Modelo | MAPE | Efectividad informal | MAE |
|---|---:|---:|---:|
| `prophet_ipc` | `4.92` | `95.08%` | `117.08` |
| `prophet_blue_ipc` | `5.19` | `94.81%` | `122.29` |
| `prophet_mayorista_ipc` | `5.42` | `94.58%` | `127.36` |

### Horizonte 12 meses

| Modelo | MAPE | Efectividad informal | MAE |
|---|---:|---:|---:|
| `prophet_ipc` | `5.49` | `94.51%` | `131.35` |
| `prophet_mayorista_ipc` | `6.05` | `93.95%` | `141.17` |
| `prophet_oficial_ipc_mayorista` | `6.38` | `93.62%` | `145.53` |

### Lectura actual para Pastina

- mejor a `3m`: `prophet_blue_ipc`
- mejor a `6m`: `prophet_ipc`
- mejor a `12m`: `prophet_ipc`

## Membrana Megaflex

### Horizonte 3 meses

| Modelo | MAPE | Efectividad informal | MAE |
|---|---:|---:|---:|
| `prophet_ipc` | `8.31` | `91.69%` | `734.37` |
| `prophet_oficial_ipc_mayorista` | `8.63` | `91.37%` | `760.91` |
| `prophet_blue_ipc` | `9.09` | `90.91%` | `794.36` |

### Horizonte 6 meses

| Modelo | MAPE | Efectividad informal | MAE |
|---|---:|---:|---:|
| `prophet_oficial_ipc_mayorista` | `9.51` | `90.49%` | `794.53` |
| `prophet_mayorista_ipc` | `10.11` | `89.89%` | `842.88` |
| `prophet_ipc` | `10.26` | `89.74%` | `839.34` |

### Horizonte 12 meses

| Modelo | MAPE | Efectividad informal | MAE |
|---|---:|---:|---:|
| `prophet_mayorista` | `11.17` | `88.83%` | `911.50` |
| `prophet_mayorista_ipc` | `13.30` | `86.70%` | `1123.75` |
| `prophet_oficial_ipc_mayorista` | `13.67` | `86.33%` | `1160.85` |

### Lectura actual para Membrana

- mejor a `3m`: `prophet_ipc`
- mejor a `6m`: `prophet_oficial_ipc_mayorista`
- mejor a `12m`: `prophet_mayorista`

## Cierre comparativo

- `Cemento Portland` es el material con mayor profundidad experimental y hoy muestra el mayor potencial de mejora adicional mediante regresores sectoriales como `IPIM`, `ICC` y `CAC`.
- `Pastina` mantiene desempenos altos y relativamente estables, con `MAPE` alrededor de `5%` en los tres horizontes evaluados.
- `Membrana Megaflex` sigue siendo el material mas dificil de pronosticar de los tres, con efectividades inferiores y cambios mas notorios segun horizonte.
- La evidencia total refuerza que no existe un unico mejor modelo universal: la configuracion optima depende del material y del horizonte temporal.
