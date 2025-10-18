# Проблемы с базой данных для будущей оптимизации

## Текущие проблемы:

### 1. Лишние столбцы в business_snapshots
- `period_type` - всегда 'monthly', можно убрать
- `period_date` - дублирует created_at, можно убрать
- `employees` - редко используется, можно сделать nullable
- `monthly_costs` - дублирует expenses, можно убрать

### 2. Неэффективная структура
- `business_snapshots` содержит и сырые данные, и метрики - лучше разделить
- `conversation_sessions.collected_data` как JSON - лучше нормализовать
- Отсутствуют индексы для частых запросов

### 3. Предлагаемая новая структура:
```sql
-- Основные данные бизнеса
businesses (business_id, user_id, business_name, industry, created_at, updated_at)

-- Сырые данные от пользователя
business_data (data_id, business_id, revenue, expenses, profit, clients, average_check, investments, marketing_costs, employees, created_at)

-- Рассчитанные метрики
business_metrics (metrics_id, data_id, profit_margin, roi, ltv_cac_ratio, ..., health_scores, created_at)

-- Сессии диалогов (упрощенные)
conversations (conversation_id, user_id, business_id, status, created_at, updated_at)

-- Сообщения (связь через conversation_id)
messages (message_id, conversation_id, user_message, bot_response, message_type, created_at)
```

### 4. Индексы для оптимизации:
- businesses.user_id
- business_data.business_id
- business_metrics.data_id
- messages.conversation_id
- conversations.user_id

## Приоритеты:
1. Убрать лишние столбцы
2. Добавить индексы
3. Разделить сырые данные и метрики
4. Нормализовать JSON поля
