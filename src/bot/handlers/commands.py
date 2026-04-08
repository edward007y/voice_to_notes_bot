import re

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.bot.lexicon import TEXTS
from src.db.database import async_session_maker
from src.db.models import User

router = Router(name="commands_router")


class NotionSetup(StatesGroup):
    waiting_for_api_key = State()
    waiting_for_db_id = State()


# Кнопки вибору мови
def get_language_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang_uk"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
            ]
        ]
    )


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    if not message.from_user:
        return

    async with async_session_maker() as session:
        user = await session.get(User, message.from_user.id)
        if not user:
            user = User(telegram_id=message.from_user.id)
            session.add(user)
            await session.commit()

        # Якщо мову ще не обрано - показуємо кнопки
        if not user.language_code:
            await message.answer(
                "👋 Привіт! Обери мову / Hello! Choose your language:",
                reply_markup=get_language_keyboard(),
            )
            return

        # Якщо мова є, перевіряємо ключі
        lang = user.language_code
        if not user.notion_api_key or not user.notion_db_id:
            await message.answer(TEXTS[lang]["step_1"], disable_web_page_preview=True)
            await state.set_state(NotionSetup.waiting_for_api_key)
        else:
            await message.answer(TEXTS[lang]["already_setup"])


# Обробник натискання на кнопки мови
# Обробник натискання на кнопки мови
# Обробник натискання на кнопки мови
@router.callback_query(F.data.startswith("lang_"))
async def process_language_selection(
    callback: types.CallbackQuery, state: FSMContext
) -> None:
    if not callback.data:
        return

    lang_code = callback.data.split("_")[1]  # Отримаємо 'uk' або 'en'

    async with async_session_maker() as session:
        user = await session.get(User, callback.from_user.id)
        if user:
            user.language_code = lang_code
            await session.commit()

    # ДОДАНО: Перевірка на те, що це звичайне (доступне) повідомлення
    if isinstance(callback.message, types.Message):
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(TEXTS[lang_code]["lang_saved"])
        await callback.message.answer(
            TEXTS[lang_code]["step_1"], disable_web_page_preview=True
        )

    await state.set_state(NotionSetup.waiting_for_api_key)
    await callback.answer()


@router.message(NotionSetup.waiting_for_api_key)
async def process_api_key(message: types.Message, state: FSMContext) -> None:
    # ДОДАНО: перевірка not message.from_user
    if not message.text or not message.from_user:
        return

    await state.update_data(api_key=message.text.strip())

    # Дістаємо мову юзера для правильної відповіді
    async with async_session_maker() as session:
        user = await session.get(User, message.from_user.id)
        lang = user.language_code if (user and user.language_code) else "uk"

    await message.answer(TEXTS[lang]["step_2"], disable_web_page_preview=True)
    await state.set_state(NotionSetup.waiting_for_db_id)


@router.message(NotionSetup.waiting_for_db_id)
async def process_db_id(message: types.Message, state: FSMContext) -> None:
    if not message.text or not message.from_user:
        return

    raw_input = message.text.strip()
    clean_input = raw_input.replace("-", "")
    match = re.search(r"([a-f0-9]{32})", clean_input.lower())

    async with async_session_maker() as session:
        user = await session.get(User, message.from_user.id)
        lang = user.language_code if (user and user.language_code) else "uk"

        if not match:
            await message.answer(TEXTS[lang]["invalid_link"])
            return

        db_id = match.group(1)
        data = await state.get_data()

        if user:
            user.notion_api_key = data.get("api_key")
            user.notion_db_id = db_id
            await session.commit()

    await state.clear()
    await message.answer(TEXTS[lang]["setup_done"])


@router.message(Command("reset"))
async def cmd_reset(message: types.Message, state: FSMContext) -> None:
    if not message.from_user:
        return

    async with async_session_maker() as session:
        user = await session.get(User, message.from_user.id)
        lang = user.language_code if (user and user.language_code) else "uk"
        if user:
            user.notion_api_key = None
            user.notion_db_id = None
            user.language_code = None  # ДОДАЛИ ЦЕ: Тепер мова теж скидається!
            await session.commit()

    await state.clear()
    await message.answer(TEXTS[lang]["reset"])
    await cmd_start(message, state)  # Це одразу викличе появу кнопок вибору мови
