# 🎙️ voice_to_notes_bot

> A Telegram bot that converts voice messages into structured Notion pages — transcribed, summarized, and enriched with action items. Each user connects their own Notion workspace via a personal API key.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0?logo=telegram&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B-336791?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7.x-DC382D?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 🚀 Features

- **Voice-to-text** — transcribes Telegram voice messages (`.ogg`) via OpenAI Whisper API
- **AI summarization** — extracts a structured summary and action items using GPT-4o-mini
- **Personal Notion export** — notes land in each user's own Notion database using their personal integration token
- **Smart URL parsing** — automatically extracts the 32-character database ID from any Notion URL
- **Multi-language support** — users select their language via inline keyboard; GPT responds and Notion tags are created in the chosen language
- **Guided onboarding** — FSM-based step-by-step setup collects Notion credentials interactively
- **Async task queue** — audio processing runs in background Taskiq workers; the bot stays responsive throughout
- **Resilient error handling** — exponential backoff on API failures, audio duration validation (1 s – 5 min), worker concurrency limit (max 3 tasks)
- **Fully containerized** — one command starts the entire stack: bot, worker, Redis, PostgreSQL

---

## 🛠️ Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Language | [Python](https://python.org) | 3.11+ |
| Bot Framework | [aiogram](https://docs.aiogram.dev) | 3.x |
| Task Queue | [Taskiq](https://taskiq-python.github.io) | latest stable |
| Message Broker | [Redis](https://redis.io) | 7.x |
| Database | [PostgreSQL](https://postgresql.org) | 15+ |
| ORM | [SQLAlchemy](https://sqlalchemy.org) | 2.x (async) |
| Config | [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | 2.x |
| HTTP Client | [httpx](https://www.python-httpx.org) | latest stable |
| Audio Conversion | [ffmpeg](https://ffmpeg.org) | latest stable |
| Speech-to-Text | [OpenAI Whisper API](https://platform.openai.com/docs/guides/speech-to-text) | latest |
| LLM | [GPT-4o-mini](https://platform.openai.com/docs/models) | latest |
| Notion SDK | [notion-client](https://github.com/ramnes/notion-sdk-py) | latest stable |
| Containerization | Docker + Docker Compose | latest |

---

## 📦 Installation

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose installed
- Telegram Bot token — create one via [@BotFather](https://t.me/BotFather)
- OpenAI API key — required for Whisper transcription and GPT-4o-mini summarization

> **Notion credentials are not required in `.env`.** Each user provides their own Notion Integration Token and Database ID directly inside the bot during onboarding.

### 1. Clone the repository

```bash
git clone https://github.com/[INSERT USERNAME]/voice_to_notes_bot.git
cd voice_to_notes_bot
```

### 2. Configure environment

```bash
cp .env.example .env
```

Fill in `.env`:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# OpenAI (Whisper + GPT-4o-mini)
OPENAI_API_KEY=your_openai_api_key

# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=voice_notes
DATABASE_URL=postgresql+asyncpg://postgres:your_secure_password@postgres:5432/voice_notes

# Redis
REDIS_URL=redis://redis:6379/0
```

### 3. Build and run

```bash
docker-compose up --build
```

Starts four services: `bot`, `worker`, `postgres`, `redis`.

---

## ▶️ Usage

### Bot commands

| Command | Description |
|---|---|
| `/start` | Register and launch the onboarding wizard |
| `/reset` | Clear your Notion credentials and restart setup |
| `/help` | Show usage instructions |

### Onboarding flow

When a new user sends `/start`, the bot launches a guided FSM-based setup:

1. **Select language** — choose via inline keyboard (stored in DB, applied to all future responses)
2. **Provide Notion Integration Token** — paste your token from [notion.so/my-integrations](https://www.notion.so/my-integrations)
3. **Provide Notion Database URL or ID** — paste the full Notion URL or the raw 32-character ID; the bot extracts the ID automatically via regex

Once configured, just send any voice message.

### Processing pipeline

```
Voice message received
  → .ogg saved to data/
  → ffmpeg converts .ogg → .mp3
  → Whisper API transcribes audio → text
  → "Transcription complete, processing…" sent to user
  → GPT-4o-mini generates Summary + Action Items (in user's language)
  → Notion page created in user's personal database
  → User receives a direct link to the Notion page
```

---

## 🔑 Notion Setup (Per User)

Each user independently connects their own Notion workspace through the bot:

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations) → **New integration**
2. Copy the **Internal Integration Token**
3. Open (or create) a Notion database where your notes will be saved
4. Share the database with your integration: **Share → Invite → select your integration**
5. Copy the database URL — the bot extracts the 32-character ID automatically from any Notion link
6. Send `/start` to the bot and follow the onboarding wizard

Credentials are stored per-user in PostgreSQL and used exclusively for that user's exports.

---

## 🗂️ Project Structure

```
voice_to_notes_bot/
├── src/
│   ├── bot/
│   │   ├── handlers/
│   │   │   ├── commands.py      # /start (FSM onboarding), /reset, /help
│   │   │   └── voice.py         # Voice message handler
│   │   ├── lexicon.py           # Localization strings (i18n)
│   │   └── main.py              # Bot entry point, Dispatcher setup
│   ├── tasks/
│   │   ├── broker.py            # RedisAsyncBroker configuration
│   │   └── tasks.py             # transcribe, summarize, export_to_notion + Telegram notifications
│   ├── services/
│   │   ├── audio.py             # ffmpeg audio conversion (.ogg → .mp3)
│   │   ├── openai_llm.py        # GPT-4o-mini prompts with language support
│   │   └── notion.py            # Notion API client with localized page titles/tags
│   ├── db/
│   │   ├── database.py          # SQLAlchemy async engine + session factory
│   │   └── models.py            # User model: telegram_id, notion_token, db_id, lang_code
│   └── core/
│       └── config.py            # Pydantic Settings
├── data/                        # Temporary audio files (auto-cleaned after processing)
├── .env                         # Secrets — not committed to git
├── .env.example                 # Environment variable template
├── .gitignore
├── docker-compose.yml           # Bot, Worker, Redis, Postgres services
└── pyproject.toml               # Poetry dependencies
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Verify the full stack starts cleanly: `docker-compose up --build`
4. Open a pull request with a clear description of the change

---

## 📄 License

[INSERT LICENSE TYPE] — see [LICENSE](LICENSE) for details.
