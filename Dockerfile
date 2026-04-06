# ==========================================
# Stage 1: Builder (Збірка залежностей)
# ==========================================
FROM python:3.13-slim AS builder

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN pip install poetry==1.8.2

WORKDIR /app

# Копіюємо тільки файли залежностей для ефективного кешування
COPY pyproject.toml poetry.lock ./

# Встановлюємо залежності (без dev-пакетів)
RUN poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR

# ==========================================
# Stage 2: Runtime (Фінальний легкий образ)
# ==========================================
FROM python:3.13-slim AS runtime

# Встановлюємо ffmpeg (потрібен для воркера)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копіюємо віртуальне середовище з першого етапу
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

# Копіюємо код проєкту
COPY src ./src

# Команда запуску за замовчуванням (може бути перевизначена в docker-compose)
CMD ["python", "src/bot/main.py"]