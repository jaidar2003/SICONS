# Implementación completa (todo de una)

## 1) Generar backend JHipster desde JDL

```bash
npm i -g generator-jhipster
jhipster jdl jdl/e-commerce-monolith.jdl
```

## 2) Tests unitarios (2)

- `ProductTest`
- `ShoppingCartTest`

Ejecutar:

```bash
cd backend
./mvnw test
```

## 3) E2E Cypress (3)

- `auth-api-login.cy.js`
- `product-create.cy.js`
- `cart-flow.cy.js`

Ejecución:

```bash
cd backend
npm ci
npm run cy:run
```

## 4) Docker + ELK

```bash
cd docker
docker compose up -d
```

Kibana: http://localhost:5601  
App: http://localhost:8080

## 5) Ionic + API JHipster

- Servicio API: `mobile/src/app/services/api.service.ts`
- Pantalla productos: `mobile/src/app/pages/products/*`

## 6) PWA offline

- Configuración en `mobile/ngsw-config.json`
- Cache local fallback en `products.page.ts`

## 7) Jenkins + Docker Hub

Pipeline en `Jenkinsfile`:

- build backend
- unit tests
- cypress e2e
- build imagen
- push a Docker Hub

Variables necesarias en Jenkins:

- `DOCKERHUB_USER`
- credencial `dockerhub-creds`
