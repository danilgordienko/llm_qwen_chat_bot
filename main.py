import os
import time
import threading
import requests
from dotenv import load_dotenv
import telebot

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5-1.5b-instruct")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN не задан в .env")

bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode=None)

# Словарь для хранения контекста: { user_id: "role: user: ...\nrole: assistant: ...\n" }
user_contexts = {}
context_lock = threading.Lock()

# Параметры LM Studio / OpenAI-совместимого endpoint
CHAT_COMPLETIONS_PATH = "/chat/completions"  # OpenAI-compatible path
LM_CHAT_URL = LM_STUDIO_BASE_URL.rstrip("/") + "/v1" + CHAT_COMPLETIONS_PATH  # полный URL
MAX_CONTEXT_CHARS = 20_000

def append_to_context(user_id: int, role: str, content: str):
    """Добавляем роль и контент в контекст пользователя."""
    entry = f'{{"role":"{role}","content":"{content}"}}\n'
    with context_lock:
        prev = user_contexts.get(user_id, "")
        new = prev + entry
        # если слишком длинно — обрезаем старые символы
        if len(new) > MAX_CONTEXT_CHARS:
            new = new[-MAX_CONTEXT_CHARS:]
        user_contexts[user_id] = new

def get_context_messages(user_id: int):
    """
    Преобразуем строку истории (храним как простую последовательность JSON-подобных записей)
    в список сообщений для OpenAI-совместимого API: [{"role":"user","content":"..."}, ...]
    """
    with context_lock:
        raw = user_contexts.get(user_id, "")
    msgs = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # line формат: {"role":"<role>","content":"<content>"}
        try:
            import json
            obj = json.loads(line)
            msgs.append({"role": obj["role"], "content": obj["content"]})
        except Exception:
            continue
    return msgs

def clear_context(user_id: int):
    with context_lock:
        user_contexts[user_id] = ""

def call_lmstudio_chat(model: str, messages: list, temperature: float = 0.2, max_tokens: int = 512):
    """
    Возвращает текст ответа модели.
    """
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(LM_CHAT_URL, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        # Структура ответа совместима с OpenAI: data.choices[0].message.content
        content = ""
        if "choices" in data and len(data["choices"]) > 0:
            choice = data["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                content = choice["message"]["content"]
            elif "delta" in choice:
                # собираем все куски
                fragments = []
                for ch in data["choices"]:
                    if "delta" in ch and "content" in ch["delta"]:
                        fragments.append(ch["delta"]["content"])
                content = "".join(fragments)
        elif "output" in data and isinstance(data["output"], list) and len(data["output"]) > 0:
            # берём первый текстовый фрагмент
            for item in data["output"]:
                if item.get("type") == "message" and "content" in item:
                    content = item["content"]
                    break
        else:
            # Попробуем найти поле с текстом в произвольном месте
            content = str(data)
        return content
    except Exception as e:
        return f"Ошибка при вызове LM Studio: {e}"

@bot.message_handler(commands=['start', 'help'])
def handle_start(message):
    user_id = message.from_user.id
    bot.reply_to(message, "Привет! Я бот, использующий локальную модель через LM Studio.\n"
                          "Я сохраняю контекст диалога. Отправьте сообщение — я отвечу.\n"
                          "Используйте /clear чтобы очистить историю.")

@bot.message_handler(commands=['clear'])
def handle_clear(message):
    user_id = message.from_user.id
    clear_context(user_id)
    bot.reply_to(message, "Контекст очищен. Начинаем диалог заново.")

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_all_text(message):
    user_id = message.from_user.id
    user_text = message.text.strip()
    # Добавляем запрос пользователя в контекст
    append_to_context(user_id, "user", user_text)

    # Формируем messages для LM Studio
    system_prompt = {"role": "system", "content": "You are a helpful assistant."}
    history = get_context_messages(user_id)
    messages = [system_prompt] + history

    # Вызов модели
    bot.send_chat_action(message.chat.id, 'typing')
    lm_response = call_lmstudio_chat(MODEL_NAME, messages)

    # Добавляем ответ модели в контекст
    append_to_context(user_id, "assistant", lm_response)

    # Отправляем пользователю (разбиваем на куски, если очень длинно)
    MAX_TELEGRAM_MSG = 4000
    for i in range(0, len(lm_response), MAX_TELEGRAM_MSG):
        bot.send_message(message.chat.id, lm_response[i:i+MAX_TELEGRAM_MSG])

if __name__ == "__main__":
    print("Bot started. LM Studio URL:", LM_CHAT_URL)
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        print("Stopped by user")
