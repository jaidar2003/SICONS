# Efectividad Forecasting Otros Materiales

Fuente consolidada:

- `tmp/experiments/otros_materiales_benchmark_master.csv`

Convencion:

- `efectividad_informal = 100 - MAPE`
- La metrica principal sigue siendo `MAPE`
- La efectividad informal se usa solo como apoyo comunicacional
- No comparar `3`, `6` y `12` meses como equivalentes

## Pastina

### Horizonte 3 meses

| Modelo | MAPE | Efectividad informal | MAE |
|---|---:|---:|---:|
| `prophet_blue_ipc` | `5.00` | `95.00%` | `120.90` |
| `prophet_oficial_ipc_blue` | `5.12` | `94.88%` | `122.62` |
| `prophet_oficial_ipc` | `5.29` | `94.71%` | `129.44` |
| `prophet_ipc` | `5.34` | `94.66%` | `129.00` |
| `prophet_mayorista_ipc` | `5.40` | `94.60%` | `131.49` |

### Horizonte 6 meses

| Modelo | MAPE | Efectividad informal | MAE |
|---|---:|---:|---:|
| `prophet_ipc` | `4.92` | `95.08%` | `117.08` |
| `prophet_blue_ipc` | `5.19` | `94.81%` | `122.29` |
| `prophet_mayorista_ipc` | `5.42` | `94.58%` | `127.36` |
| `prophet_oficial_ipc` | `5.50` | `94.50%` | `128.79` |
| `prophet_oficial_ipc_mayorista` | `5.94` | `94.06%` | `134.95` |

### Horizonte 12 meses

| Modelo | MAPE | Efectividad informal | MAE |
|---|---:|---:|---:|
| `prophet_ipc` | `5.49` | `94.51%` | `131.35` |
| `prophet_mayorista_ipc` | `6.05` | `93.95%` | `141.17` |
| `prophet_oficial_ipc_mayorista` | `6.38` | `93.62%` | `145.53` |
| `prophet_blue_ipc` | `6.39` | `93.61%` | `150.68` |
| `prophet_oficial_ipc` | `6.92` | `93.08%` | `160.30` |

## Membrana Megaflex

### Horizonte 3 meses

| Modelo | MAPE | Efectividad informal | MAE |
|---|---:|---:|---:|
| `prophet_ipc` | `8.31` | `91.69%` | `734.37` |
| `prophet_oficial_ipc_mayorista` | `8.63` | `91.37%` | `760.91` |
| `prophet_blue_ipc` | `9.09` | `90.91%` | `794.36` |
| `prophet_mayorista_ipc` | `9.30` | `90.70%` | `809.14` |
| `prophet_oficial_ipc` | `9.83` | `90.17%` | `862.56` |

### Horizonte 6 meses

| Modelo | MAPE | Efectividad informal | MAE |
|---|---:|---:|---:|
| `prophet_oficial_ipc_mayorista` | `9.51` | `90.49%` | `794.53` |
| `prophet_mayorista_ipc` | `10.11` | `89.89%` | `842.88` |
| `prophet_ipc` | `10.26` | `89.74%` | `839.34` |
| `prophet_oficial_ipc` | `11.33` | `88.67%` | `942.15` |
| `prophet_oficial_ipc_blue` | `11.62` | `88.38%` | `963.03` |

### Horizonte 12 meses

| Modelo | MAPE | Efectividad informal | MAE |
|---|---:|---:|---:|
| `prophet_mayorista` | `11.17` | `88.83%` | `911.50` |
| `prophet_mayorista_ipc` | `13.30` | `86.70%` | `1123.75` |
| `prophet_oficial_ipc_mayorista` | `13.67` | `86.33%` | `1160.85` |
| `prophet_oficial_mayorista` | `14.70` | `85.30%` | `1232.35` |
| `prophet_oficial_ipc` | `16.17` | `83.83%` | `1368.44` |

## Resumen actual

- `Pastina`
  - mejor a `3m`: `prophet_blue_ipc`
  - mejor a `6m`: `prophet_ipc`
  - mejor a `12m`: `prophet_ipc`

- `Membrana Megaflex`
  - mejor a `3m`: `prophet_ipc`
  - mejor a `6m`: `prophet_oficial_ipc_mayorista`
  - mejor a `12m`: `prophet_mayorista`
