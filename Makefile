POETRY=poetry

.PHONY: install bot migrate seed format lint

install:
$(POETRY) install

bot:
$(POETRY) run python -m app.main

migrate:
$(POETRY) run alembic upgrade head

seed:
$(POETRY) run python seed.py

format:
$(POETRY) run ruff check --fix .

lint:
$(POETRY) run ruff check .
