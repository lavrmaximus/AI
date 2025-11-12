import os
import glob
import time
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI

# =============================================================================
# КОНФИГУРАЦИЯ
# =============================================================================
class Config:
    # 1. Название модели из LM Studio (скопированное через "Copy Model Path")
    MODEL_NAME = "eleutherai_-_mistral-7b-v0.1-population-first-ft"

    # 2. Системный промпт (инструкция для модели)
    PROMPT = """
Опиши файл голым текстом без маркировки, заголовков, списков и выделений. 
Описывай каждую важную часть кода отдельным абзацем: функции, классы, основные блоки логики. 
Для каждой части укажи её назначение, что она делает и почему это важно. 
Только чистый текст, без форматирования.
Вот пример:
```
Функция safe_markdown_text обеспечивает безопасную отправку текста в Telegram с MarkdownV2 форматированием. Сначала экранирует все специальные символы Markdown (звездочки, подчеркивания, скобки), чтобы избежать ошибок парсинга, а затем возвращает звездочки обратно для отображения жирного текста. Это критически важно для корректного отображения сообщений в боте.
```
и так нужно разобрать весь код в отдельные абзацы.
    """

    # 3. Настройки обработки файлов
    FILE_EXTENSIONS = ['.py', '.js', '.html', '.css']
    EXCLUDED_DIRS = {'.venv', '.git', '__pycache__', 'reports', 'logs'}
    
    # Устанавливаем 1, чтобы не перегружать локальную модель.
    # Можете попробовать осторожно увеличить, если у вас мощный ПК.
    MAX_WORKERS = 1

# =============================================================================
# ОСНОВНАЯ ЛОГИКА
# =============================================================================

class CodeDocumenter:
    def __init__(self, config):
        self.config = config
        self.report_dir = f"reports/{datetime.now().strftime('%d.%m.%Y %H-%M')}"
        print(f"Отчеты будут сохранены в: {self.report_dir}")
        os.makedirs(self.report_dir, exist_ok=True)
        
        try:
            # Настраиваем клиент для подключения к локальному серверу LM Studio
            self.client = OpenAI(
                base_url="http://localhost:1234/v1",
                api_key="lm-studio", # Ключ не проверяется, но должен быть указан
            )
        except Exception as e:
            raise RuntimeError("Не удалось инициализировать клиент OpenAI.") from e

    def document_file(self, file_path):
        try:
            print(f"🔄 Начинаю обработку: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            completion = self.client.chat.completions.create(
                model=self.config.MODEL_NAME,
                messages=[
                    {"role": "system", "content": self.config.PROMPT},
                    {"role": "user", "content": code}
                ],
                temperature=0.7, # Можно настроить креативность
            )
            response = completion.choices[0].message.content

            if not response:
                print(f"⚠️  ПРЕДУПРЕЖДЕНИЕ: получен пустой ответ для {file_path}, отчет не создан.")
                return

            base_filename = os.path.basename(file_path)
            report_filename = f"{base_filename}.txt"
            report_path = os.path.join(self.report_dir, report_filename)

            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(response)
                
            print(f"✅ {file_path} -> {report_path}")

        except Exception:
            print(f"""
=========================== ОШИБКА ===========================
❌ Не удалось обработать файл: {file_path}
""")
            traceback.print_exc()
            print("==============================================================")

def main():
    config = Config()
    documenter = CodeDocumenter(config)
    
    all_files = []
    for ext in config.FILE_EXTENSIONS:
        all_files.extend(glob.glob(f'**/*{ext}', recursive=True))
        
    print(f"Найдено всего {len(all_files)} файлов с указанными расширениями.")

    filtered_files = [
        f for f in all_files
        if not f.endswith('AUTO.py') and not config.EXCLUDED_DIRS.intersection(os.path.normpath(f).split(os.sep))
    ]

    if not filtered_files:
        print("❌ Нет файлов для обработки.")
        return
    
    print(f"📁 Найдено {len(filtered_files)} файлов для обработки:")
    for f in filtered_files:
        print(f'  - {f}')
    
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        executor.map(documenter.document_file, filtered_files)
    
    print("\n🎯 Все файлы обработаны!")

if __name__ == "__main__":
    main()