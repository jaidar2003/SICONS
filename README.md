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

4. Verificar que la base esta lista:

```bash
docker compose exec postgres pg_isready -U sicons -d sicons
```

5. Entrar a `psql`:

```bash
docker compose exec postgres psql -U sicons -d sicons
```

La primera vez que se crea el volumen, PostgreSQL ejecuta automaticamente los scripts de `db/`:

- `001_initial_schema.sql`
- `002_seed_materiales.sql`

Si cambias esos scripts despues de haber levantado la base, tenes que recrear el volumen para que se ejecuten de nuevo:

```bash
docker compose down -v
docker compose up -d postgres
```

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

Al crear un precio historico con `presentacion_id`, la API calcula `precio_normalizado` como `precio_original / cantidad_base`.

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

Los tests viven en `tests/` y se ejecutan con:

```bash
.venv/bin/python -m pytest
```
