.PHONY: up down build logs shell migrate test

up:
	docker compose up --build

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
