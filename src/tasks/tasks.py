import asyncio
import logging
from pathlib import Path

from aiogram import Bot
from taskiq import Context, TaskiqDepends

from src.db.database import async_session_maker
from src.db.models import User
from src.services.audio import convert_ogg_to_mp3
from src.services.notion import create_notion_page
from src.services.openai_llm import summarize_text
from src.services.whisper import transcribe_audio
from src.tasks.broker import broker

logger = logging.getLogger(__name__)


def get_bot(context: Context = TaskiqDepends()) -> Bot:
    """Dependency Injection для отримання екземпляра бота зі state."""
    return context.state.bot


@broker.task(task_name="summarize_audio_task")
async def summarize_task(transcribed_text: str) -> dict:
    """Підзадача для сумаризації."""
    result = await summarize_text(transcribed_text)
    return result.model_dump()


@broker.task(task_name="export_to_notion_task")
async def export_to_notion_task(summary_data: dict, user_id: int) -> str:
    """Підзадача для експорту в Notion. Дістає ключі з БД."""

    # Йдемо в базу за ключами
    async with async_session_maker() as session:
        user = await session.get(User, user_id)
        if not user or not user.notion_api_key or not user.notion_db_id:
            raise ValueError("Ключі Notion не налаштовані для цього користувача.")

        api_key = user.notion_api_key
        db_id = user.notion_db_id

    max_retries = 3
    base_delay = 2
    for attempt in range(1, max_retries + 1):
        try:
            summary = summary_data.get("summary", "Текст відсутній.")
            action_items = summary_data.get("action_items", [])
            # Передаємо ключі у сервіс
            return await create_notion_page(summary, action_items, api_key, db_id)
        except Exception as e:
            logger.warning(f"Помилка експорту в Notion (спроба {attempt}): {e}")
            if attempt == max_retries:
                raise e
            await asyncio.sleep(base_delay**attempt)
    raise RuntimeError("Помилка експорту в Notion")


@broker.task(task_name="transcribe_audio_task")
async def transcribe_task(
    file_path_str: str, user_id: int, bot: Bot = TaskiqDepends(get_bot)
) -> str:
    """
    Головний Pipeline. Керує всіма етапами та оновлює статус у Telegram.
    """
    file_path = Path(file_path_str)
    max_retries = 3
    base_delay = 2

    # Відправляємо первинний статус і запам'ятовуємо об'єкт повідомлення
    status_msg = await bot.send_message(
        user_id, "🎙 <i>Аудіо отримано. Розпізнаю текст...</i>"
    )

    for attempt in range(1, max_retries + 1):
        try:
            # 1. Конвертація та транскрипція
            mp3_path = await convert_ogg_to_mp3(file_path)
            text = await transcribe_audio(mp3_path)

            # Оновлюємо статус
            await bot.edit_message_text(
                "🧠 <i>Текст розпізнано. Генерую summary та action items...</i>",
                chat_id=user_id,
                message_id=status_msg.message_id,
            )

            # 2. Сумаризація (викликаємо напряму)
            summary_data = await summarize_task(text)

            # Оновлюємо статус
            await bot.edit_message_text(
                "💾 <i>Дані структуровано. Зберігаю сторінку в Notion...</i>",
                chat_id=user_id,
                message_id=status_msg.message_id,
            )

            # 3. Експорт у Notion
            # ... всередині transcribe_task ...

            # 3. Експорт у Notion (тепер передаємо і user_id)
            page_url = await export_to_notion_task(summary_data, user_id)

            # ...

            # 4. Фінальне повідомлення
            final_text = (
                f"✅ <b>Готово!</b>\n\n"
                f"<b>Розпізнаний текст:</b> <i>{text[:300]}{'...' if len(text) > 300 else ''}</i>\n\n"
                f"🔗 <a href='{page_url}'>Відкрити нотатку в Notion</a>"
            )
            await bot.edit_message_text(
                final_text, chat_id=user_id, message_id=status_msg.message_id
            )

            logger.info(f"Пайплайн успішно завершено для файлу {file_path}")

            # Очищення тимчасових файлів
            file_path.unlink(missing_ok=True)
            mp3_path.unlink(missing_ok=True)

            return page_url

        except Exception as e:
            logger.warning(f"Помилка пайплайну (спроба {attempt}): {e}")
            if attempt == max_retries:
                await bot.edit_message_text(
                    "❌ <i>Вибачте, сталася помилка під час обробки вашого аудіо. Спробуйте ще раз.</i>",
                    chat_id=user_id,
                    message_id=status_msg.message_id,
                )
                raise e
            await asyncio.sleep(base_delay**attempt)

    raise RuntimeError("Неочікуване завершення пайплайну")
