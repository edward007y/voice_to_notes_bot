# Commands handler - /start, /help, /settings
from aiogram import Router, types
from aiogram.filters import CommandStart

router = Router(name="commands_router")


@router.message(CommandStart())
async def cmd_start(message: types.Message) -> None:
    """Обробник команди /start."""
    await message.answer(
        "Привіт! Я Voice-to-Notes бот. Відправ мені голосове повідомлення, "
        "і я перетворю його на текст, зроблю summary та збережу в Notion."
    )
