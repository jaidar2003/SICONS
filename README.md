# SICONS

## Desarrollo local con Docker

1. Crear la configuracion local:

```bash
cp .env.example .env
```

2. Levantar PostgreSQL:

```bash
docker compose up -d postgres
```

3. Levantar tambien la API:

```bash
docker compose up -d api
```

Al arrancar, la API ejecuta:

```bash
alembic upgrade head
python -m app.db.seed
```

4. Verificar que la base esta lista:

```bash
docker compose exec postgres pg_isready -U sicons -d sicons
```

5. Entrar a `psql`:

```bash
docker compose exec postgres psql -U sicons -d sicons
```

El esquema se versiona con Alembic. Los datos demo se cargan con un seed idempotente, por lo que correrlo mas de una vez no duplica registros.

## Conexion

```env
DATABASE_URL=postgresql://sicons:sicons@localhost:5432/sicons
```

## API

Con Docker:

```bash
docker compose up -d api
```

Con la venv local:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

URLs:

- API: http://localhost:8000
- Documentacion interactiva: http://localhost:8000/docs
- Healthcheck: http://localhost:8000/health
- Frontend: http://localhost:3000

Endpoints iniciales:

- `GET /materiales`
- `POST /materiales`
- `GET /presentaciones`
- `POST /presentaciones`
- `GET /fuentes`
- `POST /fuentes`
- `GET /precios-historicos`
- `POST /precios-historicos`
- `GET /materiales/{material_id}/precios`
- `GET /materiales/{material_id}/serie-precios`

Al crear un precio historico con `presentacion_id`, la API calcula `precio_normalizado` como `precio_original / cantidad_base`.

El endpoint de serie historica limpia agrupa registros por fecha, calcula promedio diario, equivalencias comerciales para 25 kg y 50 kg, fuentes y variacion porcentual contra el punto anterior:

```bash
curl "http://localhost:8000/materiales/1/serie-precios?desde=2025-07-01&hasta=2026-03-31"
```

## Migraciones

Aplicar migraciones:

```bash
.venv/bin/python -m alembic upgrade head
```

Ver revision actual:

```bash
.venv/bin/python -m alembic current
```

Crear una nueva migracion:

```bash
.venv/bin/python -m alembic revision -m "descripcion_del_cambio"
```

Crear una migracion autogenerada desde los modelos:

```bash
.venv/bin/python -m alembic revision --autogenerate -m "descripcion_del_cambio"
```

Ejecutar seed demo:

```bash
.venv/bin/python -m app.db.seed
```

## Estructura del backend

```text
app/
├── api/routes/       # Endpoints HTTP por recurso
├── core/             # Configuracion de la aplicacion
├── db/               # Base ORM y sesiones SQLAlchemy
├── models/           # Modelos SQLAlchemy por entidad
├── schemas/          # Schemas Pydantic por entidad
├── services/         # Logica de negocio reutilizable
└── main.py           # Ensambla la app FastAPI
```

```text
db/
├── migrations/       # Migraciones Alembic
└── seed/             # Seeds SQL auxiliares/documentales
```

Los tests viven en `tests/` y se ejecutan con:

```bash
.venv/bin/python -m pytest
```
