# Convenience commands. Run from the repository root.
.PHONY: setup db api web web-prod migrate test e2e check backup

setup: db
	cd backend && [ -f .env ] || cp .env.example .env
	cd backend && uv sync
	cd frontend && npm install
	$(MAKE) migrate

db:
	docker compose up -d db
	@until docker exec dgs-workspace-db pg_isready -U dgs >/dev/null 2>&1; do sleep 0.5; done
	@docker exec dgs-workspace-db psql -U dgs -d dgs_workspace -tc \
	  "SELECT 1 FROM pg_database WHERE datname='dgs_workspace_test'" | grep -q 1 || \
	  docker exec dgs-workspace-db psql -U dgs -d dgs_workspace -c "CREATE DATABASE dgs_workspace_test"
	@echo "PostgreSQL ready on localhost:5433"

migrate:
	cd backend && uv run alembic upgrade head

api:
	cd backend && uv run uvicorn app.main:app --reload --port 8010

web:
	cd frontend && npm run dev

web-prod:
	cd frontend && npm run build && npm run start

test:
	cd backend && uv run pytest
	cd frontend && npm test

e2e:
	cd frontend && npx playwright test

check:
	cd backend && uv run ruff check app tests && uv run ruff format --check app tests
	cd frontend && npm run lint && npm run typecheck

backup:
	mkdir -p backups
	docker exec dgs-workspace-db pg_dump -U dgs -Fc dgs_workspace > backups/workspace-$$(date +%F-%H%M).dump
	@echo "Backup written to backups/ (git-ignored)"
