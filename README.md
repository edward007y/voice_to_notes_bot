# voice_to_notes_bot 🎙️

> A Telegram bot that converts voice messages into structured Notion pages — transcribed, summarized, and enriched with action items automatically.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
![aiogram](https://img.shields.io/badge/aiogram-3.x-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Build](https://img.shields.io/badge/build-passing-brightgreen)

---

## 🚀 Features

- **Voice-to-text transcription** — converts Telegram `.ogg` voice messages to text via OpenAI Whisper API
- **AI summarization** — generates a structured summary and extracts action items using GPT-4o-mini
- **Personal Notion export** — each user connects their own Notion integration; notes are saved to their personal Notion workspace
- **Async task queue** — audio processing runs in background Taskiq workers, keeping the bot responsive
- **Per-user API key storage** — users register their own Notion API key and database ID via `/settings`; credentials are stored securely in PostgreSQL
- **Graceful error handling** — retry with exponential backoff on API failures, validation for audio duration (1s–5min limit)
- **Fully containerized** — one `docker-compose up --build` command spins up the entire stack

---

## 🛠 Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Language | [Python](https://python.org) | 3.11+ |
| Bot Framework | [aiogram](https://docs.aiogram.dev) | 3.x |
| Task Queue | [Taskiq](https://taskiq-python.github.io) | latest stable |
| Message Broker | [Redis](https://redis.io) | 7.x |
| Database | [PostgreSQL](https://postgresql.org) | 15+ |
| ORM | [SQLAlchemy](https://sqlalchemy.org) | 2.x (async) |
| Migrations | [Alembic](https://alembic.sqlalchemy.org) | latest stable |
| Config | [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | 2.x |
| HTTP Client | [httpx](https://www.python-httpx.org) | latest stable |
| Audio Processing | [ffmpeg](https://ffmpeg.org) | latest stable |
| Speech-to-Text | [OpenAI Whisper API](https://platform.openai.com/docs/guides/speech-to-text) | latest |
| LLM | [GPT-4o-mini](https://platform.openai.com/docs/models) | latest |
| Notion SDK | [notion-client](https://github.com/ramnes/notion-sdk-py) | latest stable |
| Containerization | Docker + Docker Compose | latest |

---

## 📦 Installation

### Prerequisites

- Docker & Docker Compose installed
- Telegram Bot token (from [@BotFather](https://t.me/BotFather))
- OpenAI API key (for Whisper + GPT-4o-mini)

### 1. Clone the repository

```bash
git clone https://github.com/[INSERT USERNAME]/voice_to_notes_bot.git
cd voice_to_notes_bot
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=voice_notes
DATABASE_URL=postgresql+asyncpg://postgres:your_password@postgres:5432/voice_notes

# Redis
REDIS_URL=redis://redis:6379/0
```

> **Note:** Notion API keys and database IDs are configured **per user** directly in the bot via `/settings` — they are not required in `.env`.

### 3. Build and run

```bash
docker-compose up --build
```

This command starts four services: `bot`, `worker`, `postgres`, and `redis`.

### 4. Apply database migrations

```bash
docker-compose exec bot alembic upgrade head
```

---

## ▶️ Usage

### For end users

1. Start the bot: send `/start` in Telegram
2. Connect your Notion workspace via `/settings`:
   - Provide your **Notion Internal Integration Token**
   - Provide your **Notion Database ID** (the target database where notes will be saved)
3. Send any voice message (up to 5 minutes)
4. The bot transcribes, summarizes, and creates a Notion page automatically
5. You receive a direct link to the created Notion page

### Bot commands

| Command | Description |
|---|---|
| `/start` | Register and get started |
| `/help` | Show usage instructions |
| `/settings` | Connect or update your Notion API key and database ID |

### Processing pipeline

```
Voice message → .ogg saved → ffmpeg converts to .mp3
    → Whisper API transcribes → GPT-4o-mini summarizes
    → Notion page created with Summary + Action Items
    → User receives link to the page
```

---

## 🗂 Project Structure

```
voice_to_notes_bot/
├── src/
│   ├── bot/
│   │   ├── handlers/
│   │   │   ├── commands.py      # /start, /help, /settings
│   │   │   └── voice.py         # Voice message handler
│   │   ├── middlewares/
│   │   │   ├── taskiq.py        # Task queue integration
│   │   │   └── user_check.py    # User registration/verification
│   │   └── main.py              # Bot entry point, Dispatcher setup
│   ├── tasks/
│   │   ├── broker.py            # RedisAsyncBroker configuration
│   │   └── tasks.py             # transcribe, summarize, export_to_notion tasks
│   ├── services/
│   │   ├── whisper.py           # OpenAI Whisper API client
│   │   ├── openai_llm.py        # GPT-4o-mini prompts and response handling
│   │   └── notion.py            # Notion API operations
│   └── core/
│       ├── config.py            # Pydantic Settings
│       └── db.py                # SQLAlchemy async engine + session
├── alembic/                     # Database migrations
├── tests/                       # pytest test suite
├── docker/
│   ├── Dockerfile.bot
│   └── Dockerfile.worker
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

---

## 🔑 Notion Setup (Per User)

Each user configures their own Notion connection independently:

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations) and create a new **Internal Integration**
2. Copy the **Integration Token**
3. Open (or create) the Notion database where notes should be saved
4. Share the database with your integration (click **Share → Invite → your integration**)
5. Copy the **Database ID** from the database URL:
   `https://notion.so/workspace/`**`<DATABASE_ID>`**`?v=...`
6. Send `/settings` to the bot and provide both values

Credentials are stored encrypted in PostgreSQL and used exclusively for that user's exports.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Run tests: `pytest tests/ -v`
4. Submit a pull request with a clear description

Please ensure new features include corresponding tests and that `docker-compose up --build` passes without errors.

---

## 📄 License

[INSERT LICENSE TYPE] — see [LICENSE](LICENSE) for details.
