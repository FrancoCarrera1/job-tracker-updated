FROM mcr.microsoft.com/playwright/python:v1.48.0-noble

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
RUN pip install --upgrade pip && pip install -e .

COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini

RUN mkdir -p /app/storage/resumes /app/storage/screenshots

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
