.PHONY: dev up down logs ps restart rebuild bootstrap bootstrap-all

dev:
	docker compose up -d --build

up: dev

bootstrap:
	docker compose --profile ops run --rm bootstrap

bootstrap-all: dev bootstrap

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
