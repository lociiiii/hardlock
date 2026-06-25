.PHONY: dev migrate down logs ps shell

COMPOSE := docker compose

# Start Postgres, Redis, and FastAPI with hot reload (dev)
dev:
	$(COMPOSE) up --build

# Run Alembic migrations against the compose Postgres instance
migrate:
	$(COMPOSE) run --rm --entrypoint alembic api upgrade head

# Stop all services
down:
	$(COMPOSE) down

# Follow API logs
logs:
	$(COMPOSE) logs -f api

# Show running containers
ps:
	$(COMPOSE) ps

# Open a shell in the API container
shell:
	$(COMPOSE) exec api sh
