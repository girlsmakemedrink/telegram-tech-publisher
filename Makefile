.PHONY: dev lint typecheck sec test smoke-github smoke-telegram

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
