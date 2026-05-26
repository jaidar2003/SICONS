# Estado real de la entrega

Este documento deja explícito qué está implementado y qué pasos son obligatorios para cerrar la entrega en un entorno real.

## Implementado en este repositorio

- Modelo JDL para e-commerce monolítico (`jdl/e-commerce-monolith.jdl`).
- Suite mínima de 2 tests unitarios de ejemplo.
- Suite mínima de 3 tests E2E de ejemplo con login por API.
- Stack `docker-compose` con Postgres + ELK.
- Base de cliente Ionic/PWA con consumo de API y fallback cache local.
- Pipeline Jenkins declarativo para build/test/docker push.

## Pendiente para cierre final

1. Generar proyecto JHipster real y versionarlo.
2. Ajustar tests unitarios sobre clases/servicios reales de dominio.
3. Ajustar E2E Cypress a rutas/selectores reales del frontend generado.
4. Integrar logs del backend hacia Logstash (appender JSON/TCP).
5. Configurar Jenkins con credenciales y ejecutar pipeline en verde.
6. Publicar imagen real en Docker Hub.

## Comandos de validación esperados

```bash
# backend
./mvnw clean test
npm ci
npm run cy:run

# infraestructura
docker compose -f docker/docker-compose.yml up -d

# ionic pwa
npm run build
npx http-server www
```
