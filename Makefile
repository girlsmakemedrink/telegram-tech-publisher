.PHONY: dev lint typecheck sec test smoke-github smoke-telegram tick dry-run status validate daemon

dev:
	uv sync
	cp -n .env.example .env || true

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy src

sec:
	uv run bandit -r src -ll

test:
	uv run pytest -v --cov=src --cov-fail-under=80

smoke-github:
	uv run python -m telegram_tech_publisher.cli smoke-github

smoke-telegram:
	uv run python -m telegram_tech_publisher.cli smoke-telegram

tick:
	uv run telegram-tech-publisher tick

dry-run:
	uv run telegram-tech-publisher dry-run

status:
	uv run telegram-tech-publisher status

validate:
	uv run telegram-tech-publisher validate

daemon:
	uv run telegram-tech-publisher daemon
