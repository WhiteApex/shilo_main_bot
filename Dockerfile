FROM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
RUN pip install --upgrade pip poetry && poetry config virtualenvs.in-project true && poetry install --no-root

FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY --from=builder /root/.cache/pypoetry/ /root/.cache/pypoetry/
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
COPY . .
CMD ["python", "-m", "app.main"]
