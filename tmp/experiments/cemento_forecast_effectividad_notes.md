# Efectividad Forecasting Cemento Portland

Fuente consolidada:

- `tmp/experiments/cemento_forecast_benchmark_master.csv`

Convencion:

- `efectividad_informal = 100 - MAPE`
- La metrica principal sigue siendo `MAPE`
- La efectividad informal se usa solo como lectura comunicacional de apoyo
- No comparar horizontes `3`, `6` y `12` como si fueran equivalentes

## Horizonte 3 meses

| Modelo | Regresores / features | MAPE | Efectividad informal | Estado |
|---|---|---:|---:|---|
| `ensemble_simple_top2` | promedio(`prophet_ipim_nivel_general`, `prophet_ipim_nivel_general_medias_moviles`) | `4.08` | `95.92%` | `candidato` |
| `prophet_ipim_icc_var_materials` | `ipim_nivel_general + icc_var_materials` | `4.22` | `95.78%` | `candidato` |
| `prophet_ipim_cac_var_materials` | `ipim_nivel_general + var_materials` | `4.33` | `95.67%` | `candidato` |
| `prophet_ipim_cac_var_general` | `ipim_nivel_general + var_general` | `4.62` | `95.38%` | `candidato` |
| `prophet_ipim_icc_var_general` | `ipim_nivel_general + icc_var_general` | `4.64` | `95.36%` | `candidato` |
| `prophet_ipim_nivel_general` | `ipim_nivel_general` | `4.93` | `95.07%` | `baseline` |
| `prophet_ipim_icc_var_labour` | `ipim_nivel_general + icc_var_labour` | `5.09` | `94.91%` | `descartado` |
| `prophet_ipim_cac_general` | `ipim_nivel_general + general` | `5.23` | `94.77%` | `descartado` |
| `prophet_ipim_cac_labour_force` | `ipim_nivel_general + labour_force` | `5.34` | `94.66%` | `descartado` |
| `prophet_ipim_cac_var_labour` | `ipim_nivel_general + var_labour` | `5.53` | `94.47%` | `descartado` |
| `prophet_cac_materials` | `materials` | `5.86` | `94.14%` | `descartado` |
| `prophet_ipim_cac_materials` | `ipim_nivel_general + materials` | `6.52` | `93.48%` | `descartado` |
| `prophet_cac_general` | `general` | `6.57` | `93.43%` | `descartado` |
| `prophet_ipim_nivel_general_medias_moviles` | `ipim_nivel_general + ma_3m + ma_6m` | `6.82` | `93.18%` | `descartado` |
| `prophet_ipim_nivel_general_variaciones` | `ipim_nivel_general + var_1m_pct + var_3m_pct + var_6m_pct` | `7.72` | `92.28%` | `descartado` |
| `prophet_ipim_nivel_general_lags` | `ipim_nivel_general + lag_1m + lag_3m + lag_6m` | `8.26` | `91.74%` | `descartado` |
| `prophet_cac_labour_force` | `labour_force` | `13.14` | `86.86%` | `descartado` |
| `prophet_cac_var_labour` | `var_labour` | `14.24` | `85.76%` | `descartado` |
| `prophet_cac_var_materials` | `var_materials` | `14.53` | `85.47%` | `descartado` |
| `prophet_cac_var_general` | `var_general` | `14.65` | `85.35%` | `descartado` |

## Horizonte 6 meses

| Modelo | Regresores / features | MAPE | Efectividad informal | Estado |
|---|---|---:|---:|---|
| `prophet_ipim_icc_var_materials` | `ipim_nivel_general + icc_var_materials` | `5.52` | `94.48%` | `candidato` |
| `prophet_ipim_cac_var_materials` | `ipim_nivel_general + var_materials` | `5.99` | `94.01%` | `candidato` |
| `prophet_ipim_icc_var_general` | `ipim_nivel_general + icc_var_general` | `6.71` | `93.29%` | `candidato` |
| `prophet_ipim_cac_var_general` | `ipim_nivel_general + var_general` | `6.85` | `93.15%` | `candidato` |
| `prophet_ipim_nivel_general` | `ipim_nivel_general` | `7.51` | `92.49%` | `baseline` |
| `prophet_ipim_icc_var_labour` | `ipim_nivel_general + icc_var_labour` | `7.84` | `92.16%` | `descartado` |
| `prophet_ipim_cac_var_labour` | `ipim_nivel_general + var_labour` | `8.56` | `91.44%` | `descartado` |

## Horizonte 12 meses

| Modelo | Regresores / features | MAPE | Efectividad informal | Estado |
|---|---|---:|---:|---|
| `prophet_ipim_icc_var_materials` | `ipim_nivel_general + icc_var_materials` | `4.51` | `95.49%` | `candidato` |
| `prophet_ipim_cac_var_materials` | `ipim_nivel_general + var_materials` | `4.69` | `95.31%` | `candidato` |
| `prophet_ipim_icc_var_general` | `ipim_nivel_general + icc_var_general` | `5.16` | `94.84%` | `candidato` |
| `prophet_ipim_cac_var_general` | `ipim_nivel_general + var_general` | `5.94` | `94.06%` | `candidato` |
| `prophet_ipim_icc_var_labour` | `ipim_nivel_general + icc_var_labour` | `10.20` | `89.80%` | `candidato` |
| `prophet_ipim_nivel_general` | `ipim_nivel_general` | `10.38` | `89.62%` | `baseline` |
| `prophet_ipim_cac_var_labour` | `ipim_nivel_general + var_labour` | `10.60` | `89.40%` | `descartado` |

## Resumen actual

- Mejor baseline productivo actual: `prophet_ipim_nivel_general`
- Mejor candidata experimental por regresores: `prophet_ipim_icc_var_materials`
- Segunda mejor candidata experimental: `prophet_ipim_cac_var_materials`
- Mejor resultado puntual global a `3` meses: `ensemble_simple_top2`, aunque su lectura metodologica debe separarse de la de regresores explicativos
