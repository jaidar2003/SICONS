.PHONY: dev up down logs ps restart rebuild

dev:
	docker compose up -d --build

up: dev

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
