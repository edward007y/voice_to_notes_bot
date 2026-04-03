from pathlib import Path

from aiogram import Bot, F, Router, types

from src.tasks.tasks import transcribe_task

router = Router(name="voice_router")

DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)


@router.message(F.voice)
async def handle_voice_message(message: types.Message, bot: Bot) -> None:
    """Обробник голосових повідомлень."""
    # Додано перевірку на наявність from_user
    if not message.voice or not message.from_user:
        return

    file_id = message.voice.file_id
    file_path_local = DATA_DIR / f"{message.from_user.id}_{message.message_id}.ogg"

    # ... попередній код ...

    # Завантаження файлу
    await bot.download(file=file_id, destination=file_path_local)

    # Відправка задачі у Taskiq Broker у кросплатформному форматі (з прямими слешами)
    await transcribe_task.kiq(file_path_local.as_posix(), message.from_user.id)
