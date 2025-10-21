-- Исправление порядка колонок в таблице messages
-- Перемещаем user_id в начало, чтобы веб-интерфейс сортировал по нему

-- Создаем новую таблицу с правильным порядком колонок
CREATE TABLE messages_new (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    session_id INTEGER,
    user_message TEXT,
    bot_response TEXT,
    message_type TEXT,
    FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id)
);

-- Копируем данные
INSERT INTO messages_new (id, user_id, session_id, user_message, bot_response, message_type, created_at)
SELECT id, user_id, session_id, user_message, bot_response, message_type, created_at
FROM messages;

-- Удаляем старую таблицу
DROP TABLE messages;

-- Переименовываем новую таблицу
ALTER TABLE messages_new RENAME TO messages;

-- Восстанавливаем значение последовательности, связанной с messages.id
SELECT setval(
  pg_get_serial_sequence('messages','id'),
  COALESCE((SELECT MAX(id) FROM messages), 1),
  true
);
