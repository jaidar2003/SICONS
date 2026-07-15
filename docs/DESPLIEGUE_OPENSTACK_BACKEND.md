# Despliegue del backend en OpenStack

Esta guia publica el backend FastAPI y PostgreSQL en una VM de OpenStack usando Docker Compose. El frontend sigue publicado en Vercel.

## 1. Preparar la VM

Crear una instancia Ubuntu 22.04/24.04 con al menos:

- 2 vCPU;
- 4 GB RAM, ideal 8 GB si se recompila CmdStan en la VM;
- 30 GB de disco;
- IP flotante publica.

Abrir en el security group:

- `22/tcp` para SSH;
- `80/tcp` para emision/renovacion de certificado;
- `443/tcp` para la API publica.

## 2. Instalar Docker

En la VM:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
```

Cerrar la sesion SSH y volver a entrar para que aplique el grupo `docker`.

## 3. Clonar el proyecto

```bash
git clone https://github.com/juanmanuelaidar/BuildWise.git
cd BuildWise
```

## 4. Configurar variables

```bash
cp .env.openstack.example .env.openstack
nano .env.openstack
```

Cambiar como minimo:

```env
POSTGRES_PASSWORD=una-clave-fuerte
AUTH_SECRET_KEY=otra-clave-fuerte
API_DOMAIN=api-buildwise.tu-dominio.edu.ar
CORS_ORIGINS=https://buildwise-tif.vercel.app,http://localhost:3000,http://127.0.0.1:3000
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_SENDER=
SMTP_USE_TLS=true
SMTP_USE_SSL=false
SMTP_TIMEOUT_SECONDS=10
ADMIN_NOTIFICATION_EMAIL=
```

`ADMIN_NOTIFICATION_EMAIL` es opcional. Cuando se configura junto con SMTP, el backend notifica al administrador cada registro pendiente. No incluir `.env.openstack` en Git. Ver [notificación administrativa de registros](admin-registration-email.md).

`API_DOMAIN` debe tener un registro DNS apuntando a la IP flotante de OpenStack. Caddy usa ese dominio para emitir HTTPS automaticamente.

## 5. Levantar backend

```bash
docker compose -f docker-compose.openstack.yml --env-file .env.openstack up -d --build
```

Ver logs:

```bash
docker compose -f docker-compose.openstack.yml --env-file .env.openstack logs -f api caddy
```

Verificar:

```bash
curl https://api-buildwise.tu-dominio.edu.ar/health
```

Debe responder:

```json
{"status":"ok"}
```

## 6. Cargar datos iniciales

Ejecutar una vez:

```bash
docker compose -f docker-compose.openstack.yml --env-file .env.openstack --profile ops run --rm bootstrap
```

## 7. Conectar Vercel con OpenStack

En Vercel, proyecto `buildwise-tif`:

`Settings` -> `Environment Variables`

Agregar:

```env
VITE_BUILDWISE_API_URL=https://api-buildwise.tu-dominio.edu.ar
```

Despues hacer `Redeploy`.

## 8. Actualizar backend

El workflow `Deploy Backend` se ejecuta despues de que `CI` aprueba un push a `main`. Un runner de GitHub construye una imagen inmutable en GHCR; el runner autoservido de la VM solamente la descarga y reinicia los servicios. El deploy:

- verifica que el commit a desplegar sea exactamente el validado por CI;
- actualiza `main` solamente mediante fast-forward;
- descarga la imagen identificada por el SHA validado y aplica migraciones Alembic al iniciar la API;
- espera el health check y registra logs si falla.

La ejecucion manual equivalente es:

```bash
git pull --ff-only origin main
BACKEND_IMAGE=ghcr.io/juanmanuelaidar/buildwise-api:<sha> \
  docker compose -f docker-compose.openstack.yml --env-file .env.openstack up -d --no-build --wait --wait-timeout 300
```

El runner debe tener las etiquetas `self-hosted`, `linux`, `x64` y `buildwise-production`. La configuracion `.env.openstack` permanece solamente en la VM.
