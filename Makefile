.PHONY: up down build logs shell migrate

up:
	docker compose up --build -d

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
