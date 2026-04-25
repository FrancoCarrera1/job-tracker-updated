.PHONY: up down logs shell-backend shell-db migrate test fmt

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

shell-backend:
	docker compose exec backend bash

shell-db:
	docker compose exec postgres psql -U jobtracker -d jobtracker

migrate:
	docker compose run --rm backend alembic upgrade head

test:
	docker compose run --rm backend pytest

fmt:
	docker compose run --rm backend ruff check --fix app
	docker compose run --rm backend ruff format app
