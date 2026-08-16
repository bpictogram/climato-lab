FROM python:3.12-slim AS base

WORKDIR /app

COPY pyproject.toml .
COPY src/ ./src/


FROM base AS runtime

RUN python -m pip install --no-cache-dir .

CMD ["python", "-m", "climato"]


FROM base AS dev

RUN python -m pip install --no-cache-dir -e .

CMD ["python", "-m", "climato"]
