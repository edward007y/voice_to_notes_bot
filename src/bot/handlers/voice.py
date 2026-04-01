# Voice message handler
from pathlib import Path

from aiogram import Bot, F, Router, types

router = Router(name="voice_router")

# Гарантуємо наявність директорії data/ на рівні ініціалізації модуля
DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)


@router.message(F.voice)
async def handle_voice_message(message: types.Message, bot: Bot) -> None:
    """Обробник голосових повідомлень."""
    # Перевіряємо наявність voice та from_user для уникнення помилок
    if not message.voice or not message.from_user:
        return

    file_id = message.voice.file_id
    # Тепер Pylance точно знає, що message.from_user не є None
    file_path_local = DATA_DIR / f"{message.from_user.id}_{message.message_id}.ogg"

    # Завантаження файлу з серверів Telegram
    await bot.download(file=file_id, destination=file_path_local)

    await message.reply(
        f"Голосове повідомлення збережено у локальну папку: {file_path_local}"
    )
