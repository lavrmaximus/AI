-- Добавляем индекс для правильной сортировки по времени
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC);

-- Или по ID (если хотите сортировать по ID)
CREATE INDEX IF NOT EXISTS idx_messages_id ON messages(id DESC);
