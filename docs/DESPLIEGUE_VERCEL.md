# Despliegue en Vercel

Este repositorio tiene backend FastAPI y frontend Vite/React. Vercel se usa para publicar el frontend.

## 1. Subir el repositorio a GitHub

Vercel despliega desde un repositorio remoto. Si los cambios locales todavia no estan subidos:

```bash
git add .vercelignore vercel.json frontend/vercel.json docs/DESPLIEGUE_VERCEL.md
git commit -m "Configurar despliegue en Vercel"
git push
```

## 2. Crear el proyecto en Vercel

1. Entrar a <https://vercel.com>.
2. Importar el repositorio `BuildWise`.
3. Opcion recomendada: en `Root Directory`, seleccionar `frontend`.
4. Si se despliega desde la raiz del repositorio, `vercel.json` y `.vercelignore` evitan que Vercel intente detectar el backend FastAPI.
5. Vercel deberia detectar Vite automaticamente. Si hace falta, configurar:
   - `Framework Preset`: `Vite`;
   - `Install Command`: `npm ci`;
   - `Build Command`: `npm run build`;
   - `Output Directory`: `dist`.

Si Vercel usa la raiz del repositorio sin esta configuracion, detecta el backend Python e intenta desplegar FastAPI, lo que puede producir errores como:

```text
No `project` table found in: /vercel/path0/pyproject.toml
No FastAPI entrypoint found
```

## 3. Configurar la URL del backend

El frontend necesita una API publicada. En Vercel, agregar esta variable de entorno:

```env
VITE_BUILDWISE_API_URL=https://tu-backend.example.com
```

No incluir una barra final.

## 4. Backend

El backend actual usa FastAPI, PostgreSQL y Docker Compose. Para produccion conviene publicarlo aparte, por ejemplo en Render, Railway, Fly.io o un VPS. Cuando tengas esa URL, cargarla como `VITE_BUILDWISE_API_URL` en Vercel y redeployar.

## 5. Verificacion

Antes de desplegar, el build local debe pasar:

```bash
cd frontend
npm run build
```
