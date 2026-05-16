.PHONY: up-dev up-prod down logs shell migrate check test ruff ruff-format mypy

up-dev:
	docker compose up --build

up-prod:
	docker compose -f docker-compose.prod.yml up -d

down:
	docker compose down

logs:
	docker compose logs -f

shell:
	docker compose exec backend python manage.py shell_plus

migrate:
	docker compose exec backend python manage.py migrate

check:
	docker compose exec backend python manage.py check

test:
	cd backend && python -m pytest tests/ -v \
		--cov=. \
		--cov-report=term-missing \
		--cov-report=xml:coverage.xml

ruff:
	cd backend/ && poetry run ruff check .

ruff-format:
	cd backend/ && poetry run ruff format --check .

mypy:
	cd backend/ && poetry run mypy .
