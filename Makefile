.PHONY: dev dev-backend dev-frontend lint lint-backend lint-frontend test test-backend test-frontend build docker-build

dev:
	$(MAKE) dev-backend & $(MAKE) dev-frontend

dev-backend:
	cd backend && uv run uvicorn main:app --reload --host 0.0.0.0 --port 48765

dev-frontend:
	cd frontend && npm run dev

lint: lint-backend lint-frontend

lint-backend:
	cd backend && uv run ruff check . && uv run ruff format --check .

lint-frontend:
	cd frontend && npm run lint && npm run format:check

test: test-backend test-frontend

test-backend:
	cd backend && uv run pytest -m "not e2e and not integration"

test-frontend:
	cd frontend && npx vitest run

build:
	cd frontend && npm run build

docker-build:
	docker compose build
