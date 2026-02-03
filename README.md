# Финансовый Луч 💸

**Интеллектуальный AI-аналитик для бизнеса с Telegram ботом и веб-интерфейсом**

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)

## 📋 Описание проекта

Финансовый Луч - это комплексная система для анализа и мониторинга бизнеса, сочетающая мощь ИИ с удобным интерфейсом Telegram бота и веб-дашборда. Система автоматически рассчитывает 22 ключевые бизнес-метрики, предоставляет персональные рекомендации и отслеживает динамику развития бизнеса.

### 🎯 Основные возможности

- **🤖 Умный Telegram бот** - естественный диалог для сбора данных о бизнесе
- **📊 22 бизнес-метрики** - от рентабельности до срока банкротства
- **🎯 AI-анализ** - персональные рекомендации и комментарии
- **📈 Веб-дашборд** - визуализация данных и трендов
- **💾 История анализов** - отслеживание динамики развития
- **🔄 Мульти-бизнес** - управление несколькими бизнесами
- **📱 Адаптивный интерфейс** - работает на всех устройствах
- **✨ Современный UI** - Glassmorphism дизайн с анимациями

## 🏗️ Архитектура

### Основные компоненты

```
├── 🤖 tgbot.py              # Telegram бот (основной интерфейс)
├── 🌐 WEBSite.py            # Flask веб-приложение
├── 🗄️ database.py           # Работа с PostgreSQL
├── 🧠 ai.py                 # ИИ функции (G4F + GPT-4)
├── 📈 business_analyzer.py  # Анализ бизнеса и расчет метрик
├── 💬 conversation_manager.py # Умное управление диалогами
├── 📊 metrics_calculator.py # Расчет 22 бизнес-метрик
├── 📋 report_formatter.py   # Форматирование отчетов
├── ⚙️ env_utils.py          # Утилиты окружения
└── 🐳 Dockerfile           # Контейнеризация
```

### Технологии

- **Backend**: Python 3.11, Flask, AsyncIO
- **База данных**: PostgreSQL
- **AI**: G4F (GPT-4), кастомные промпты
- **Бот**: python-telegram-bot v20.7
- **Развертывание**: Docker, Railway/Heroku
- **Фронтенд**: HTML5, CSS3 (Tailwind + Glassmorphism), JavaScript (Chart.js)

## 📊 Формулы и Метрики

Система рассчитывает 22 ключевые метрики по следующим формулам:

### 💰 Финансовые показатели
1. **Прибыль (Profit)**: `Выручка - Расходы`
2. **Рентабельность (Profit Margin)**: `(Прибыль / Выручка) * 100`
   - Показывает, какой процент выручки становится прибылью.
3. **Точка безубыточности (в клиентах)**: `Расходы / Средний чек`
   - Сколько клиентов нужно для покрытия расходов.
4. **Запас прочности (Safety Margin)**: `((Выручка - Расходы) / Выручка) * 100`
   - Насколько выручка превышает точку безубыточности (в %).
5. **Срок жизни (Runway)**: `Инвестиции / (Расходы - Выручка)`
   - Сколько месяцев бизнес проживет при текущих убытках.

### 👥 Клиентские метрики
6. **Средний чек**: `Выручка / Клиенты`
7. **LTV (за период)**: `Выручка / Клиенты`
   - Средняя выручка на одного клиента за анализируемый период (ARPU).
8. **CAC**: `Маркетинг / Новые клиенты`
   - Стоимость привлечения одного нового клиента.
9. **LTV/CAC Ratio**: `LTV / CAC`
   - Эффективность маркетинга (Цель > 3.0).
10. **Прибыль на клиента**: `Прибыль / Клиенты`

### 📈 Рост и Эффективность
11. **ROI**: `((Прибыль - Инвестиции) / Инвестиции) * 100`
    - Возврат инвестиций.
12. **Индекс прибыльности**: `(Прибыль * 12) / Инвестиции`
    - Отношение годовой прибыли к инвестициям.
13. **ROE (Рентабельность капитала)**: `(Прибыль / Активы) * 100`
    - *Активы оцениваются как Инвестиции + 50% Выручки.*
14. **Оборачиваемость активов**: `Выручка / Активы`
15. **SGR (Устойчивый рост)**: `(Прибыль / Инвестиции) * 100 * 0.6`
    - Максимальный рост без внешних займов (при реинвестиции 60%).
16. **Темп роста выручки**: `((Текущая - Прошлая) / Прошлая) * 100`

### 🏥 Расчет Business Health Score (0-100)

Общая оценка здоровья — это среднее арифметическое трех показателей:

**1. Финансовое здоровье (Max 100)**
- **Рентабельность**: до 40 баллов (сравнение с бенчмарком).
- **Запас прочности**: до 30 баллов (>30% = 30б).
- **Срок жизни**: до 30 баллов (>12 мес = 30б).

**2. Здоровье роста (Max 100)**
- **ROI**: до 40 баллов.
- **Темп роста**: до 30 баллов (>20% = 30б).
- **SGR**: до 30 баллов (>15% = 30б).

**3. Эффективность (Max 100)**
- **LTV/CAC**: до 50 баллов (>1.5x нормы = 50б).
- **Оборачиваемость**: до 30 баллов (>2.0 = 30б).
- **Индекс прибыльности**: до 20 баллов (>2.0 = 20б).

**Интерпретация:**
- 🟢 **90-100**: Отлично
- 🟡 **70-89**: Хорошо
- 🟠 **50-69**: Стабильно
- 🔴 **<50**: Критично

## 🚀 Установка и запуск

### Предварительные требования

- Python 3.11+
- PostgreSQL база данных
- Telegram Bot Token (от @BotFather)

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd financial-ray
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
# Telegram Bot
BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# PostgreSQL Database (Production)
DATABASE_URL=postgresql://user:password@host:port/database
PGHOST=your_postgres_host
PGDATABASE=your_database_name
PGUSER=your_username
PGPASSWORD=your_password
PGPORT=5432

# Railway/Heroku (автоматически)
RAILWAY_PUBLIC_DOMAIN=your-app-name.railway.app
PORT=8080
```

### 4. Инициализация базы данных

База данных инициализируется автоматически при первом запуске. Структура включает:

- `users` - пользователи
- `businesses` - бизнесы пользователей
- `business_snapshots` - снимки данных бизнеса
- `conversation_sessions` - сессии диалогов
- `messages` - логи сообщений

### 5. Запуск

#### Локальная разработка (с polling)

```bash
python main.py
```

Приложение запустится в режиме разработки с polling для Telegram бота.

#### Продакшн (Railway/Heroku)

```bash
# Через Docker
docker build -t financial-ray .
docker run -p 8080:8080 financial-ray

# Или через Procfile (автоматически на Railway)
web: python main.py
```

## 🔧 Конфигурация

### Переменные окружения

| Переменная | Описание | Пример |
|------------|----------|---------|
| `BOT_TOKEN` | Telegram Bot Token | `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `DATABASE_URL` | PostgreSQL URL | `postgresql://user:pass@host:5432/db` |
| `RAILWAY_PUBLIC_DOMAIN` | Домен приложения | `myapp.railway.app` |
| `PORT` | Порт сервера | `8080` |

### Автоматическое определение окружения

Система автоматически определяет тип развертывания:

- **Railway/Heroku**: Использует PostgreSQL и webhooks
- **Локально**: Использует PostgreSQL и polling
- **Docker**: Продакшн режим

## 💡 Использование

### Через Telegram бота

1. **Запуск**: `/start`
2. **Создание бизнеса**: `/new_business`
3. **Свободный ввод данных**:
   ```
   У меня кофейня, выручка 500к в месяц, расходы 300к,
   150 клиентов, средний чек 3300 рублей
   ```
4. **Просмотр истории**: `/history`
5. **Редактирование**: `/edit_business`
6. **Справка по метрикам**: `/help_metrics`

### Через веб-интерфейс

- **Главная страница**: `https://your-domain.com/`
- **Дашборд**: `https://your-domain.com/dashboard?user_id=123`
- **Аналитика**: `https://your-domain.com/analytics?user_id=123`

## 🔄 API Endpoints

### Публичные endpoints

- `GET /` - Главная страница
- `GET /dashboard` - Дашборд бизнеса
- `GET /analytics` - Страница аналитики
- `POST /webhook` - Webhook для Telegram

### API endpoints

- `GET /api/users` - Список пользователей
- `GET /api/businesses/<user_id>` - Бизнесы пользователя
- `GET /api/business-history/<business_id>` - История бизнеса
- `GET /api/business-kpi/<business_id>` - KPI метрики
- `GET /api/business-ai-analysis/<business_id>` - AI анализ
- `GET /api/system-stats` - Системная статистика

## 🧠 ИИ компоненты

### Классификация сообщений

Автоматически определяет тип входящего сообщения:
- **BUSINESS_DATA**: содержит данные о бизнесе
- **BUSINESS_QUESTION**: вопросы о бизнесе
- **GENERAL_CHAT**: общий разговор

### Извлечение данных

Использует GPT-4 для извлечения структурированных данных из свободного текста:

```json
{
  "business_name": "Кофейня на углу",
  "revenue": 500000,
  "expenses": 300000,
  "clients": 150,
  "average_check": 3300
}
```

### Генерация рекомендаций

AI анализирует метрики и генерирует персональные рекомендации по улучшению бизнеса.

## 📈 База данных

### Основные таблицы

```sql
-- Пользователи
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Бизнесы
CREATE TABLE businesses (
    business_id SERIAL PRIMARY KEY,
    user_id TEXT,
    business_name TEXT,
    business_type TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Снимки бизнеса (22 метрики)
CREATE TABLE business_snapshots (
    snapshot_id SERIAL PRIMARY KEY,
    business_id INTEGER,
    -- ... 35+ полей с метриками
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

## 🐳 Docker развертывание

```dockerfile
FROM python:3.11-slim

# Установка PostgreSQL клиента
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY . .

# Продакшн режим
ENV ENVIRONMENT=production
EXPOSE 8080

CMD ["python", "main.py"]
```

## 🔍 Мониторинг и логирование

### Логи

- **Продакшн**: логи в stdout/stderr
- **Локально**: файлы в папке `logs/`
- **Веб**: логи в `user_access.log`

### Метрики системы

- Количество пользователей
- Общее число анализов
- Активные пользователи за день

## 🤝 Contributing

1. Fork проект
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📝 Лицензия

Этот проект лицензирован под CC BY-NC 4.0 - см. файл [LICENSE](LICENSE) для деталей.

**Запрещено коммерческое использование без письменного разрешения автора.**

## 👨‍💻 Автор

**Лавринов Максим**
- Telegram: [@your_telegram]
- Email: [your_email@example.com]
- GitHub: [your_github]

## 🙏 Благодарности

- OpenAI за GPT-4
- Telegram за Bot API
- Railway за хостинг
- Сообщество Python разработчиков

---

*Создано с ❤️ для предпринимателей и бизнес-аналитиков*
