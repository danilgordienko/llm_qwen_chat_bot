# Telegram Bot с LM Studio

Telegram-бот с поддержкой контекстного диалога через локальную языковую модель в LM Studio.

## Возможности

- Подключение к LM Studio через OpenAI-совместимый API
- Сохранение истории диалога для каждого пользователя
- Команда `/clear` для очистки контекста

## Требования

- Python 3.8+
- LM Studio с запущенным локальным сервером
- Языковая модель (например, Qwen2.5-1.5B-Instruct-GGUF)

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/danilgordienko/llm_qwen_chat_bot
cd llm_qwen_chat_bot
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` в корневой папке:
```env
TELEGRAM_TOKEN=8431803277:AAGKmtVnilYU1C8qbcPDYmiQ_OtS7WWthCg
LM_STUDIO_BASE_URL=http://localhost:1234
MODEL_NAME=qwen2.5-1.5b-instruct
```

## Настройка LM Studio

1. Скачайте и установите [LM Studio](https://lmstudio.ai/)
2. Загрузите модель Qwen2.5-1.5B-Instruct-GGUF
3. Запустите локальный сервер в LM Studio:
   - Откройте вкладку "Local Server"
   - Загрузите модель
   - Нажмите "Start Server"

## Запуск
```bash
python main.py
```

## Использование

- Отправьте любое сообщение боту — он ответит с учетом контекста
- `/start` или `/help` — показать приветствие
- `/clear` — очистить историю диалога

## Примечания

- Максимальная длина контекста: 20,000 символов
- Старые сообщения автоматически удаляются при превышении лимита
- Каждый пользователь имеет отдельную историю диалога
