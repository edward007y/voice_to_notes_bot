import asyncio
import logging
from pathlib import Path

from aiogram import Bot
from taskiq import Context, TaskiqDepends

from src.services.audio import convert_ogg_to_mp3
from src.services.notion import create_notion_page
from src.services.openai_llm import summarize_text
from src.services.whisper import transcribe_audio
from src.tasks.broker import broker

logger = logging.getLogger(__name__)


def get_bot(context: Context = TaskiqDepends()) -> Bot:
    """Dependency Injection для отримання екземпляра бота зі state."""
    return context.state.bot


# ... попередній код файлу ...


@broker.task(task_name="transcribe_audio_task")
async def transcribe_task(
    file_path_str: str, user_id: int, bot: Bot = TaskiqDepends(get_bot)
) -> str:
    """
    Повний пайплайн обробки: повідомлення -> конвертація -> транскрипція -> результат.
    """
    file_path = Path(file_path_str)
    max_retries = 3
    base_delay = 2

    # Проміжне повідомлення
    await bot.send_message(
        user_id, "🎙 <i>Аудіо отримано. Починаю конвертацію та розпізнавання...</i>"
    )

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Спроба {attempt}/{max_retries}: обробка {file_path}")

            mp3_path = await convert_ogg_to_mp3(file_path)
            text = await transcribe_audio(mp3_path)

            await bot.send_message(user_id, f"📝 <b>Результат:</b>\n\n{text}")
            logger.info(f"Транскрипція успішна для {file_path}")

            file_path.unlink(missing_ok=True)
            mp3_path.unlink(missing_ok=True)

            return text

        except Exception as e:
            logger.warning(f"Помилка транскрипції (спроба {attempt}): {e}")
            if attempt == max_retries:
                await bot.send_message(
                    user_id, "❌ Вибачте, сталася помилка при розпізнаванні аудіо."
                )
                raise e
            await asyncio.sleep(base_delay**attempt)

    # Додаємо fallback-помилку для Pylance, щоб закрити "all code paths"
    raise RuntimeError("Неочікуване завершення циклу транскрипції")


@broker.task(task_name="summarize_audio_task")
async def summarize_task(transcribed_text: str) -> dict:
    """
    Фонова задача для сумаризації тексту та виділення action items.

    :param transcribed_text: Текст, отриманий після транскрипції.
    :return: Словник з полями 'summary' та 'action_items'.
    """
    logger.info("Початок виконання задачі сумаризації...")

    # Викликаємо наш сервіс
    result = await summarize_text(transcribed_text)

    logger.info("Задача сумаризації успішно завершена.")

    # Повертаємо dict, щоб Redis міг легко зберегти це як JSON
    return result.model_dump()


@broker.task(task_name="export_to_notion_task")
async def export_to_notion_task(summary_data: dict) -> str:
    """
    Фонова задача для експорту результатів у Notion.
    Включає retry-логіку на випадок rate limits або збоїв мережі.

    :param summary_data: Словник з ключами 'summary' та 'action_items'.
    :return: URL створеної сторінки в Notion.
    """
    max_retries = 3
    base_delay = 2

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                f"Початок експорту в Notion (спроба {attempt}/{max_retries})..."
            )

            # Витягуємо дані зі словника
            summary = summary_data.get("summary", "Текст відсутній.")
            action_items = summary_data.get("action_items", [])

            # Викликаємо сервіс Notion
            page_url = await create_notion_page(summary, action_items)

            logger.info("Експорт у Notion успішно завершено.")
            return page_url

        except Exception as e:
            logger.warning(f"Помилка експорту в Notion (спроба {attempt}): {e}")
            if attempt == max_retries:
                logger.error("Експорт у Notion остаточно скасовано після 3 спроб.")
                raise e

            # Експоненційна затримка: 2s, 4s, 8s...
            await asyncio.sleep(base_delay**attempt)

    raise RuntimeError("Неочікуване завершення циклу експорту в Notion")
