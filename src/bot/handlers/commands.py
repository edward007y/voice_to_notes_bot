from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.db.database import async_session_maker
from src.db.models import User

router = Router(name="commands_router")


# Визначаємо стани (кроки), в яких може перебувати користувач
class NotionSetup(StatesGroup):
    waiting_for_api_key = State()
    waiting_for_db_id = State()


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    """Обробник команди /start. Перевіряє юзера в БД."""
    if not message.from_user:
        return

    # Відкриваємо сесію бази даних
    async with async_session_maker() as session:
        # Шукаємо користувача за його Telegram ID
        user = await session.get(User, message.from_user.id)

        # Якщо юзера немає в базі, створюємо його
        if not user:
            user = User(telegram_id=message.from_user.id)
            session.add(user)
            await session.commit()

        # Якщо в юзера немає ключів Notion, починаємо процес збору
        if not user.notion_api_key or not user.notion_db_id:
            await message.answer(
                "Привіт! Я твій персональний AI-помічник. 🤖\n\n"
                "Щоб я міг зберігати твої голосові нотатки, мені потрібен доступ до твоєї бази даних у Notion.\n\n"
                "Будь ласка, надішли свій <b>Notion API Key</b> (Internal Integration Secret):"
            )
            # Переводимо бота в стан очікування API ключа
            await state.set_state(NotionSetup.waiting_for_api_key)
        else:
            await message.answer(
                "Привіт! Твій Notion вже підключено. Чекаю на голосові повідомлення! 🎙"
            )


# ... попередній код (cmd_start) ...


@router.message(Command("reset"))
async def cmd_reset(message: types.Message, state: FSMContext) -> None:
    """Обробник команди /reset. Очищає ключі користувача в БД."""
    if not message.from_user:
        return

    async with async_session_maker() as session:
        user = await session.get(User, message.from_user.id)
        if user:
            # Видаляємо старі ключі
            user.notion_api_key = None
            user.notion_db_id = None
            await session.commit()

    # Про всяк випадок очищаємо поточний стан (якщо юзер був посеред вводу)
    await state.clear()

    await message.answer("🔄 Твої налаштування Notion успішно скинуто!")

    # Одразу викликаємо /start, щоб запропонувати ввести нові ключі
    await cmd_start(message, state)


# ... далі йдуть process_api_key та process_db_id ...


@router.message(NotionSetup.waiting_for_api_key)
async def process_api_key(message: types.Message, state: FSMContext) -> None:
    """Зберігає API ключ у пам'ять FSM і просить DB ID."""
    if not message.text:
        return

    # Зберігаємо ключ у тимчасове сховище стану
    await state.update_data(api_key=message.text.strip())

    await message.answer(
        "Чудово! ✅\n\n"
        "Тепер надішли <b>Notion Database ID</b> (послідовність з 32 символів із посилання на твою базу):"
    )
    # Переходимо на наступний крок
    await state.set_state(NotionSetup.waiting_for_db_id)


@router.message(NotionSetup.waiting_for_db_id)
async def process_db_id(message: types.Message, state: FSMContext) -> None:
    """Отримує DB ID, дістає API ключ з пам'яті FSM і зберігає все в PostgreSQL."""
    if not message.text or not message.from_user:
        return

    # Отримуємо тимчасові дані (API ключ)
    data = await state.get_data()
    api_key = data.get("api_key")
    db_id = message.text.strip()

    # Зберігаємо ключі в базу даних
    async with async_session_maker() as session:
        user = await session.get(User, message.from_user.id)
        if user:
            user.notion_api_key = api_key
            user.notion_db_id = db_id
            await session.commit()

    # Очищуємо стан, оскільки налаштування завершено
    await state.clear()

    await message.answer(
        "🎉 <b>Готово!</b> Твої ключі успішно збережено.\n\n"
        "Тепер ти можеш просто відправляти мені голосові повідомлення, і я буду автоматично структурувати їх у твій Notion!"
    )
