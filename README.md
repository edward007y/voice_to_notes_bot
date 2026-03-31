# Voice to Notes Bot

Telegram bot для перетворення голосових повідомлень на текстові нотатки з використанням OpenAI Whisper та GPT-4o-mini.

## Структура проєкту

```
voice_to_notes_bot/
├── src/
│   ├── bot/
│   │   ├── handlers/     # Обробники команд та повідомлень
│   │   ├── middlewares/  # Середовище обробки запитів
│   │   └── main.py       # Точка входу бота
│   ├── tasks/            # Фонові завдання (taskiq)
│   ├── services/         # Сервіси зовнішніх API
│   ├── core/             # Конфігурація та база даних
│   └── main.py           # Глобальний entrypoint
├── tests/                # Тести
├── alembic/              # Міграції бази даних
├── data/                 # Тимчасові файли
├── docker/               # Docker конфігурації
└── pyproject.toml        # Залежності Poetry
```

## Встановлення

1. Клонуйте репозиторій
2. Встановіть залежності: `poetry install`
3. Налаштуйте змінні середовища: `cp .env.example .env`
4. Запустіть міграції: `alembic upgrade head`
5. Запустіть бота: `python -m src.bot.main`
6. Запустіть воркер: `taskiq worker`

## Ліцензія

MIT
