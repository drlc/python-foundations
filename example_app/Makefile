.DEFAULT_GOAL := help
SHELL = bash

BASE_FOLDER = example_app

.PHONY: dev
dev:
	poetry run uvicorn \
		--env-file ./.env.example --no-access-log --host 0.0.0.0 --port 8080 \
		"main:asgi_app"

POSTGRES_USER = local-user
POSTGRES_PASSWORD = local-pwd
POSTGRES_DB = local-database
POSTGRES_SCHEMA = ex

.PHONY: migrate
migrate:
	@docker run --rm --network host -v ${PWD}/migrations:/migrations migrate/migrate -path=/migrations/ \
		-database "postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5432/${POSTGRES_DB}?sslmode=disable" \
		${MIGRATE_COMM}

.PHONY: migrate-up
migrate-up:
	@docker compose exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} \
		-c "CREATE SCHEMA IF NOT EXISTS ${POSTGRES_SCHEMA};"
	@make migrate MIGRATE_COMM='up'

.PHONY: migrate-down
migrate-down:
	@make migrate MIGRATE_COMM='down --all'
