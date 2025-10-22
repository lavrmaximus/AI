FROM python:3.11-slim

# Устанавливаем только PostgreSQL клиент (не нужен SQLite)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Устанавливаем переменную окружения для продакшена
ENV ENVIRONMENT=production

# Открываем порт (Railway автоматически назначает PORT)
EXPOSE 8080

CMD ["python", "main.py"]