import re

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.db.database import async_session_maker
from src.db.models import User

router = Router(name="commands_router")


class NotionSetup(StatesGroup):
    waiting_for_api_key = State()
    waiting_for_db_id = State()


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

        if not user.notion_api_key or not user.notion_db_id:
            await message.answer(
                "Привіт! Я твій персональний AI-помічник. 🎙\n\n"
                "Щоб я міг магічним чином перетворювати твої голосові на структуровані нотатки, "
                "нам потрібно один раз налаштувати зв'язок з твоїм Notion.\n\n"
                "<b>Крок 1: Створення ключа (API Key)</b> 🔑\n"
                "1. Перейди сюди: https://www.notion.so/my-integrations\n"
                "2. Натисни кнопку <b>New integration</b>.\n"
                "3. Назви її, наприклад, <i>Voice Notes Bot</i> і натисни Submit.\n"
                "4. Скопіюй <b>Internal Integration Secret</b> (він починається на <code>secret_...</code>).\n\n"
                "👇 <b>Надішли цей ключ сюди повідомленням:</b>",
                disable_web_page_preview=True,
            )
            await state.set_state(NotionSetup.waiting_for_api_key)
        else:
            await message.answer(
                "Привіт! Твій Notion вже підключено. Просто надішли мені голосове повідомлення! 🎙\n\n<i>(Щоб змінити базу, натисни /reset)</i>"
            )


@router.message(NotionSetup.waiting_for_api_key)
async def process_api_key(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        return

    await state.update_data(api_key=message.text.strip())

    await message.answer(
        "Ключ прийнято! ✅\n\n"
        "<b>Крок 2: Підготовка бази даних</b> 📁\n"
        "1. Створи нову базу даних у Notion (наприклад, вибери <i>Table view</i> на порожній сторінці).\n"
        "2. ⚠️ <b>НАЙВАЖЛИВІШЕ:</b> У правому верхньому куті сторінки натисни на <code>...</code> -> <b>Add connections</b> -> знайди і вибери свою інтеграцію <i>Voice Notes Bot</i>.\n"
        "3. Натисни <b>Share</b> і скопіюй посилання на сторінку (Copy link).\n\n"
        "👇 <b>Надішли мені це повне посилання:</b>"
    )
    await state.set_state(NotionSetup.waiting_for_db_id)


@router.message(NotionSetup.waiting_for_db_id)
async def process_db_id(message: types.Message, state: FSMContext) -> None:
    if not message.text or not message.from_user:
        return

    raw_input = message.text.strip()

    # Розумний парсинг ID: видаляємо дефіси і шукаємо 32 символи (hex)
    clean_input = raw_input.replace("-", "")
    match = re.search(r"([a-f0-9]{32})", clean_input.lower())

    if not match:
        await message.answer(
            "⚠️ Не зміг розпізнати посилання. \n"
            "Воно має виглядати приблизно так: \n"
            "<code>https://www.notion.so/workspace/1234567890abcdef1234567890abcdef?v=...</code>\n\n"
            "Спробуй скопіювати посилання ще раз."
        )
        return

    # Отримуємо чистий 32-значний ID
    db_id = match.group(1)

    data = await state.get_data()
    api_key = data.get("api_key")

    async with async_session_maker() as session:
        user = await session.get(User, message.from_user.id)
        if user:
            user.notion_api_key = api_key
            user.notion_db_id = db_id
            await session.commit()

    await state.clear()

    await message.answer(
        "🎉 <b>Бінго! Налаштування завершено.</b>\n\n"
        "Тепер ти можеш просто надиктовувати мені свої думки, і я буду автоматично розкладати їх по поличках у твоєму Notion. Спробуй записати перше голосове прямо зараз! 🎙"
    )


@router.message(Command("reset"))
async def cmd_reset(message: types.Message, state: FSMContext) -> None:
    if not message.from_user:
        return

    async with async_session_maker() as session:
        user = await session.get(User, message.from_user.id)
        if user:
            user.notion_api_key = None
            user.notion_db_id = None
            await session.commit()

    await state.clear()
    await message.answer("🔄 Налаштування Notion скинуто!")
    await cmd_start(message, state)
