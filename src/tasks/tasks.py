import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot  # ДОДАНО
from taskiq import Context, TaskiqDepends

from src.core.config import settings  # ДОДАНО
from src.db.database import async_session_maker
from src.db.models import User
from src.services.audio import convert_ogg_to_mp3
from src.services.notion import create_notion_page
from src.services.openai_llm import summarize_text, transcribe_audio
from src.tasks.broker import broker

logger = logging.getLogger(__name__)


@broker.task(task_name="export_to_notion_task", retry_on_error=True)
async def export_to_notion_task(
    summary_data: dict, user_id: int, lang_code: str = "uk"
) -> str:
    async with async_session_maker() as session:
        user = await session.get(User, user_id)
        if not user or not user.notion_api_key or not user.notion_db_id:
            raise ValueError("Ключі Notion не налаштовані для цього користувача.")

        api_key = user.notion_api_key
        db_id = user.notion_db_id

    summary = summary_data.get("summary", "Текст відсутній.")
    action_items = summary_data.get("action_items", [])

    # Більше жодних циклів (for attempt...) та sleep()!
    # Просто викликаємо функцію. Якщо Notion API видасть помилку,
    # Taskiq перехопить Exception і сам покладе задачу в чергу на повторне виконання.
    return await create_notion_page(summary, action_items, api_key, db_id, lang_code)


async def notify_user(
    bot: Bot, user_id: int, lang_code: str, status: str, url: str | None = None
) -> None:
    """Відправляє повідомлення користувачу залежно від етапу обробки."""
    if status == "processing":
        text = (
            "⏳ Опрацьовую запис... / Processing audio..."
            if lang_code == "uk"
            else "⏳ Processing your voice note..."
        )
    elif status == "success":
        text = (
            f"🎉 <b>Готово!</b> Ось твоя нотатка:\n{url}"
            if lang_code == "uk"
            else f"🎉 <b>Done!</b> Here is your note:\n{url}"
        )
    elif status == "error":
        text = (
            "❌ <b>Помилка:</b> Щось пішло не так під час обробки аудіо."
            if lang_code == "uk"
            else "❌ <b>Error:</b> Something went wrong during processing."
        )
    else:
        return

    try:
        await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Не вдалося відправити повідомлення користувачу {user_id}: {e}")


@broker.task(task_name="transcribe_audio_task")
async def transcribe_task(
    file_path: str, user_id: int, context: Context = TaskiqDepends()
) -> None:
    logger.info(f"Починаємо обробку файлу: {file_path}")

    async with async_session_maker() as session:
        user = await session.get(User, user_id)
        lang_code = user.language_code if (user and user.language_code) else "uk"

    bot = context.state.bot

    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не знайдено: {file_path}")

        # Відправляємо статус через допоміжну функцію
        await notify_user(bot, user_id, lang_code, "processing")

        # Чистий пайплайн обробки
        mp3_path = await convert_ogg_to_mp3(Path(file_path))
        transcribed_text = await transcribe_audio(str(mp3_path))
        summary_data = await summarize_text(transcribed_text, lang_code)
        page_url = await export_to_notion_task(summary_data, user_id, lang_code)

        logger.info(f"Пайплайн успішно завершено! Посилання на Notion: {page_url}")

        # Сповіщаємо про успіх
        await notify_user(bot, user_id, lang_code, "success", url=page_url)

    except Exception as e:
        logger.error(f"Помилка у пайплайні транскрибації: {e}")
        # Сповіщаємо про помилку
        await notify_user(bot, user_id, lang_code, "error")
        raise e
    finally:
        # Видаляємо тимчасові файли
        if os.path.exists(file_path):
            os.remove(file_path)
        mp3_path_to_remove = file_path.replace(".ogg", ".mp3")
        if os.path.exists(mp3_path_to_remove):
            os.remove(mp3_path_to_remove)
