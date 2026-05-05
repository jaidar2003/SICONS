# Base de datos BuildWise

El esquema de PostgreSQL se versiona con Alembic en `db/migrations`.

## Migraciones

Aplicar hasta la ultima version:

```bash
.venv/bin/python -m alembic upgrade head
```

Ver revision actual:

```bash
.venv/bin/python -m alembic current
```

Crear una migracion nueva:

```bash
.venv/bin/python -m alembic revision -m "descripcion_del_cambio"
```

Crear una migracion autogenerada a partir de modelos SQLAlchemy:

```bash
.venv/bin/python -m alembic revision --autogenerate -m "descripcion_del_cambio"
```

## Seed demo

El seed principal esta implementado en Python para poder ejecutarlo desde Docker sin depender de `psql` dentro del contenedor de API:

```bash
.venv/bin/python -m app.operations.bootstrap.seed
```

## Modelo inicial

- `materiales`: catalogo de productos y su unidad base.
- `presentaciones`: formatos comerciales vinculados a cada material.
- `fuentes`: origen del dato de precio.
- `precios_historicos`: serie de precios con valor original y valor normalizado.

`precio_normalizado` se guarda en la unidad base del material. Por ejemplo, una bolsa de cemento de 25 kg a 5500 ARS queda como 220 ARS por kg.
