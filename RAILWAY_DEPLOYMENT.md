# 🚀 Развертывание на Railway

## Переменные окружения

Установите следующие переменные окружения в Railway:

### Обязательные:
- `BOT_TOKEN` - токен вашего Telegram бота
- `DATABASE_URL` - URL подключения к PostgreSQL (Railway автоматически создает)

### Дополнительные (если DATABASE_URL не работает):
- `PGHOST` - хост PostgreSQL
- `PGPORT` - порт PostgreSQL (обычно 5432)
- `PGDATABASE` - имя базы данных
- `PGUSER` - пользователь PostgreSQL
- `PGPASSWORD` - пароль PostgreSQL
- `PGSSLMODE` - режим SSL (обычно require)

### Системные:
- `ENVIRONMENT=production` - автоматически устанавливается в Dockerfile

## Особенности развертывания

1. **База данных**: Используется PostgreSQL (SQLite отключен)
2. **Логи**: Выводятся только в stdout/stderr (файлы не создаются)
3. **Файлы**: Локальные файлы не создаются на сервере
4. **Порт**: Railway автоматически назначает PORT

## Миграция данных

Если у вас есть данные в SQLite, используйте локально:
```bash
python migrate_sqlite_to_postgres.py
```

## Проверка работы

После развертывания проверьте:
1. Бот отвечает на команды
2. Создание бизнеса работает
3. Анализ выполняется корректно
4. Логи отображаются в Railway Dashboard

## Отладка

Логи доступны в Railway Dashboard в разделе "Deployments" → "View Logs"
