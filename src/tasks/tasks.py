import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot  # ДОДАНО
from taskiq import TaskiqDepends

from src.core.config import settings  # ДОДАНО
from src.db.database import async_session_maker
from src.db.models import User
from src.services.audio import convert_ogg_to_mp3
from src.services.notion import create_notion_page
from src.services.openai_llm import summarize_text, transcribe_audio
from src.tasks.broker import broker

logger = logging.getLogger(__name__)


@broker.task(task_name="export_to_notion_task")
async def export_to_notion_task(
    summary_data: dict, user_id: int, lang_code: str = "uk"
) -> str:
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
            # Передаємо мову у створення сторінки Notion
            return await create_notion_page(
                summary, action_items, api_key, db_id, lang_code
            )
        except Exception as e:
            logger.warning(f"Помилка експорту в Notion (спроба {attempt}): {e}")
            if attempt == max_retries:
                raise e
            await asyncio.sleep(base_delay**attempt)
    raise RuntimeError("Помилка експорту в Notion")


@broker.task(task_name="transcribe_audio_task")
async def transcribe_task(file_path: str, user_id: int) -> None:
    logger.info(f"Починаємо обробку файлу: {file_path}")

    # 0. Дістаємо мову
    async with async_session_maker() as session:
        user = await session.get(User, user_id)
        lang_code = user.language_code if (user and user.language_code) else "uk"

    # Створюємо екземпляр бота для відправки повідомлень з воркера
    bot = Bot(token=settings.bot_token.get_secret_value())

    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не знайдено: {file_path}")

        # Відправляємо статус "В процесі" користувачу
        status_msg = (
            "⏳ Опрацьовую запис... / Processing audio..."
            if lang_code == "uk"
            else "⏳ Processing your voice note..."
        )
        await bot.send_message(chat_id=user_id, text=status_msg)

        # 1. Транскрибація
        # Стало (обгортаємо file_path у Path):
        mp3_path = await convert_ogg_to_mp3(Path(file_path))
        transcribed_text = await transcribe_audio(str(mp3_path))

        # 2. Сумаризація
        summary_data = await summarize_text(transcribed_text, lang_code)

        # 3. Експорт у Notion
        page_url = await export_to_notion_task(summary_data, user_id, lang_code)

        logger.info(f"Пайплайн успішно завершено! Посилання на Notion: {page_url}")

        # 4. ВІДПРАВЛЯЄМО РЕЗУЛЬТАТ КОРИСТУВАЧУ
        success_text = (
            f"🎉 <b>Готово!</b> Ось твоя нотатка:\n{page_url}"
            if lang_code == "uk"
            else f"🎉 <b>Done!</b> Here is your note:\n{page_url}"
        )
        await bot.send_message(chat_id=user_id, text=success_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Помилка у пайплайні транскрибації: {e}")
        error_text = (
            "❌ <b>Помилка:</b> Щось пішло не так під час обробки аудіо."
            if lang_code == "uk"
            else "❌ <b>Error:</b> Something went wrong during processing."
        )
        await bot.send_message(chat_id=user_id, text=error_text, parse_mode="HTML")
        raise e
    finally:
        # Обов'язково закриваємо сесію бота
        await bot.session.close()

        # Видаляємо тимчасові файли
        if os.path.exists(file_path):
            os.remove(file_path)
        mp3_path_to_remove = file_path.replace(".ogg", ".mp3")
        if os.path.exists(mp3_path_to_remove):
            os.remove(mp3_path_to_remove)
