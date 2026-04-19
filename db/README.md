# Base de datos SICONS

Scripts iniciales para PostgreSQL.

Con Docker Compose, estos scripts se ejecutan automaticamente la primera vez que se crea el volumen de PostgreSQL.

## Orden de ejecucion

```bash
psql "$DATABASE_URL" -f db/001_initial_schema.sql
psql "$DATABASE_URL" -f db/002_seed_materiales.sql
```

## Modelo inicial

- `materiales`: catalogo de productos y su unidad base.
- `presentaciones`: formatos comerciales vinculados a cada material.
- `fuentes`: origen del dato de precio.
- `precios_historicos`: serie de precios con valor original y valor normalizado.

`precio_normalizado` se guarda en la unidad base del material. Por ejemplo, una bolsa de cemento de 25 kg a 5500 ARS queda como 220 ARS por kg.
