# syntax=docker/dockerfile:1.4

# Этап сборки
FROM python:3.11-slim as builder

# 1. Сначала устанавливаем curl и системные зависимости
RUN apt-get update && \
    apt-get install -y curl gcc python3-dev build-essential && \
    rm -rf /var/lib/apt/lists/*

# 2. Установка Poetry
ENV POETRY_VERSION=2.1.2 \
    POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

# 3. Установка зависимостей Python
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root --no-ansi

# Финальный образ
FROM python:3.11-slim

# Установка Node.js и зависимостей
RUN apt-get update && \
    apt-get install -y curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    # Явное создание симлинков
    ln -sf /usr/bin/node /usr/local/bin/node && \
    ln -sf /usr/bin/npm /usr/local/bin/npm && \
    # Установка PostgreSQL
    apt-get install -y gnupg2 lsb-release && \
    curl -sSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg && \
    echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update && \
    apt-get install -y postgresql-client-16 && \
    # Очистка
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Проверка Node.js
RUN node -v && npm -v && which node

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 3. Копирование кода приложения
COPY . .

# 4. Настройка окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    NODE_ENV=production

# Явное указание пути к Node.js для exejs
ENV NODE_PATH=/usr/bin/node

ENV PATH="/usr/bin:/usr/local/bin:${PATH}" \
    NODE_PATH="/usr/lib/node_modules"

CMD ["bash", "-c", "cd app && alembic upgrade head && python -m app.main"]