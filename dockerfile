FROM python:3.11-slim

# Устанавливаем SQLite
RUN apt-get update && apt-get install -y sqlite3 libsqlite3-dev

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

CMD ["python", "main.py"]