from pathlib import Path

from aiogram import Bot, F, Router, types

from src.tasks.tasks import transcribe_task

router = Router(name="voice_router")

DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)


@router.message(F.voice)
async def handle_voice_message(message: types.Message, bot: Bot) -> None:
    """Обробник голосових повідомлень із валідацією тривалості."""
    if not message.voice or not message.from_user:
        return

    # Отримуємо тривалість аудіо в секундах
    duration = message.voice.duration

    # Задача 4.1: Ігноруємо занадто короткі (випадкові) повідомлення
    if duration < 2:
        await message.reply(
            "⚠️ Голосове повідомлення занадто коротке. Запишіть хоча б пару секунд."
        )
        return

    # Задача 4.3: Ліміт на 5 хвилин (300 секунд)
    if duration > 300:
        await message.reply(
            "⏳ Вибачте, але я можу обробляти аудіо тривалістю не більше 5 хвилин."
        )
        return

    # Якщо все ок — продовжуємо обробку
    file_id = message.voice.file_id
    file_path_local = DATA_DIR / f"{message.from_user.id}_{message.message_id}.ogg"

    # Завантаження файлу
    await bot.download(file=file_id, destination=file_path_local)

    # Відправка задачі у Taskiq Broker
    await transcribe_task.kiq(file_path_local.as_posix(), message.from_user.id)
