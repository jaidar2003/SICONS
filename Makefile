.PHONY: dev up down logs ps restart rebuild bootstrap bootstrap-all precompute-forecasts

dev:
	docker compose up -d --build

up: dev

bootstrap:
	docker compose --profile ops run --rm bootstrap

bootstrap-all: dev bootstrap

precompute-forecasts:
	docker compose run --rm api python -m app.modules.pricing.application.precompute_forecasts

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

restart:
	docker compose restart

rebuild:
	docker compose build --no-cache
	docker compose up -d
