.DEFAULT_GOAL := help
SHELL = bash

BASE_FOLDER = base

.PHONY: install
install: ## install dependencies
	poetry install --extras local
	poetry run pre-commit install
	pre-commit install --hook-type commit-msg

.PHONY: up
up: ## update dependencies
	poetry up

.PHONY: lint
lint: ## lint code
	poetry run isort ${BASE_FOLDER} example_app tests
	poetry run black ${BASE_FOLDER} example_app tests
	poetry run flake8 ${BASE_FOLDER} example_app tests

.PHONY: test-unit
test-unit: ## run unit tests
	poetry run pytest tests --rununit

.PHONY: test
test: ## run all tests except integration
	poetry run pytest tests -vv --cov-report term-missing --cov=${BASE_FOLDER}

.PHONY: example
example:
	poetry run uvicorn \
		--env-file ./example_app/.env.example --no-access-log --host 0.0.0.0 --port 8080 \
		"example_app.main:asgi_app"
