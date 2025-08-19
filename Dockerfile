FROM python:3.12-slim

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


# Устанавливаем системные зависимости для mysqlclient и других пакетов
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    pkg-config \
    python3-tk \
    tk-dev \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY src/ ./src/
COPY .env ./
COPY static/ ./static/
COPY storage/ ./storage/
COPY templates/ ./templates/

# Открываем порт
EXPOSE 8000

# Команда для запуска
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]