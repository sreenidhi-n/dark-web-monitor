.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help up down build restart logs worker-logs shell-backend shell-db migrate makemigration create-admin test lint tor-check

help:
	@echo ""
	@echo "  Dark Web Monitor — available commands"
	@echo ""
	@echo "  make up               Start all services in the background"
	@echo "  make down             Stop and remove containers"
	@echo "  make build            Rebuild images"
	@echo "  make restart          down + up"
	@echo "  make logs             Tail all service logs"
	@echo "  make worker-logs      Tail Celery worker logs"
	@echo "  make shell-backend    Open a bash shell in the backend container"
	@echo "  make shell-db         Open psql in the postgres container"
	@echo "  make migrate          Run pending Alembic migrations"
	@echo "  make makemigration    Generate a migration  (usage: make makemigration name='add_users')"
	@echo "  make test             Run pytest in the backend container"
	@echo "  make lint             Run ruff in the backend container"
	@echo "  make tor-check        Verify the backend can reach Tor"
	@echo "  make create-admin     Create the first admin user  (usage: make create-admin email=a@b.com password=secret)"
	@echo ""

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

restart: down up

logs:
	$(COMPOSE) logs -f

worker-logs:
	$(COMPOSE) logs -f worker

shell-backend:
	$(COMPOSE) exec backend bash

shell-db:
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER} -d $${POSTGRES_DB}

migrate:
	$(COMPOSE) exec backend alembic upgrade head

makemigration:
	$(COMPOSE) exec backend alembic revision --autogenerate -m "$(name)"

test:
	$(COMPOSE) exec backend pytest

lint:
	$(COMPOSE) exec backend ruff check app/

create-admin:
	$(COMPOSE) exec backend python scripts/create_admin.py $(email) $(password)

tor-check:
	$(COMPOSE) exec backend python -c "\
from app.crawler.tor_session import TorSession; \
from app.config import settings; \
s = TorSession(settings.tor_proxy); \
ok = s.verify_tor(); \
print('Tor OK:', ok) if ok else print('ERROR: not routing through Tor')"
