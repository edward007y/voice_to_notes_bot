import asyncio
import logging
from pathlib import Path

from aiogram import Bot
from taskiq import Context, TaskiqDepends

from src.services.audio import convert_ogg_to_mp3
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
