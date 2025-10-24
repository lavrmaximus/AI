import g4f
import os
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

class CodeDocumenter:
    def __init__(self):
        self.prompt = """
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
        self.report_dir = f"reports/{datetime.now().strftime('%d.%m.%Y %H-%M')}"
        os.makedirs(self.report_dir, exist_ok=True)
        
    def document_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            response = g4f.ChatCompletion.create(
                model=g4f.models.gpt_4,
                messages=[
                    {"role": "user", "content": f"{self.prompt}:\n```python\n{code}\n```"}
                ],
                stream=False
            )
            
            filename = os.path.basename(file_path).replace('.py', '.txt')
            report_path = f"{self.report_dir}/{filename}"
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(response)
                
            print(f"✅ {file_path} -> {report_path}")
            
        except Exception as e:
            print(f"❌ Ошибка в {file_path}: {e}")

def main():
    documenter = CodeDocumenter()
    py_files = [f for f in os.listdir('.') if f.endswith('.py') and f != 'AUTO.py']
    
    if not py_files:
        print("❌ Нет .py файлов для обработки")
        return
    
    print(f"📁 Обрабатываю {len(py_files)} файлов...")
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        executor.map(documenter.document_file, py_files)
    
    print("🎯 Все файлы обработаны!")

if __name__ == "__main__":
    main()