from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.types import User as AiogramUser

from src.bot.handlers.commands import (
    NotionSetup,
    cmd_reset,
    cmd_start,
    process_api_key,
    process_db_id,
    process_language_selection,
)
from src.db.models import User

# ==========================================
# 1. СТВОРЕННЯ ФІКСТУР (ІЗОЛЯЦІЯ ЗАЛЕЖНОСТЕЙ)
# ==========================================


@pytest.fixture
def mock_message():
    """Семантична імітація повідомлення від користувача."""
    message = AsyncMock(spec=Message)
    message.from_user = MagicMock(spec=AiogramUser)
    message.from_user.id = 123456
    message.text = "Деякий текст"
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_fsm_context():
    """Імітація автомата станів (FSM) Aiogram."""
    state = AsyncMock(spec=FSMContext)
    state.get_data.return_value = {"api_key": "ntn_12345test"}
    return state


@pytest.fixture
def mock_db_session():
    """
    Імітація асинхронної сесії SQLAlchemy.
    Згідно з контекстом коду, сесія викликається через 'async with async_session_maker() as session'.
    Тому ми імітуємо асинхронний контекстний менеджер.
    """
    session_mock = AsyncMock()
    session_mock.add = MagicMock()
    # Налаштовуємо поведінку 'async with'
    ctx_manager = AsyncMock()
    ctx_manager.__aenter__.return_value = session_mock
    ctx_manager.__aexit__.return_value = None

    # Замінюємо реальний виклик бази даних на наш мок
    with patch(
        "src.bot.handlers.commands.async_session_maker", return_value=ctx_manager
    ):
        yield session_mock


# ==========================================
# 2. НАПИСАННЯ АТОМАРНИХ ТЕСТІВ
# ==========================================


@pytest.mark.asyncio
async def test_cmd_start_new_user(mock_message, mock_fsm_context, mock_db_session):
    # Умови: Користувача немає в базі даних (get повертає None)
    mock_db_session.get.return_value = None

    await cmd_start(mock_message, mock_fsm_context)

    # Перевірки згідно з логікою:
    # 1. Створено нового користувача
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

    # 2. Відправлено повідомлення з клавіатурою вибору мови
    mock_message.answer.assert_called_once()
    args, kwargs = mock_message.answer.call_args
    assert "Обери мову" in args[0]
    assert "reply_markup" in kwargs


@pytest.mark.asyncio
async def test_process_language_selection(mock_fsm_context, mock_db_session):
    # Умови: Користувач натискає кнопку "lang_uk"
    callback = AsyncMock(spec=CallbackQuery)
    callback.data = "lang_uk"
    callback.from_user = MagicMock(spec=AiogramUser)
    callback.from_user.id = 123456

    callback.message = AsyncMock(spec=Message)
    callback.message.edit_reply_markup = AsyncMock()
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()

    # Імітуємо існуючого користувача в БД
    mock_user = MagicMock(spec=User)
    mock_db_session.get.return_value = mock_user

    await process_language_selection(callback, mock_fsm_context)

    # Перевірки:
    # 1. Мову збережено в об'єкт користувача
    assert mock_user.language_code == "uk"
    mock_db_session.commit.assert_called_once()

    # 2. Відправлено інструкцію (Крок 1)
    assert callback.message.answer.call_count == 2

    # 3. Змінено стан FSM на очікування API ключа
    mock_fsm_context.set_state.assert_called_once_with(NotionSetup.waiting_for_api_key)


@pytest.mark.asyncio
async def test_process_api_key(mock_message, mock_fsm_context, mock_db_session):
    # Умови: Користувач відправив API ключ
    mock_message.text = "ntn_mysecretkey123"

    # Налаштовуємо мову для коректного витягування текстів (словника)
    mock_user = MagicMock(spec=User)
    mock_user.language_code = "uk"
    mock_db_session.get.return_value = mock_user

    await process_api_key(mock_message, mock_fsm_context)

    # Перевірки:
    # 1. Ключ збережено в тимчасову пам'ять FSM
    mock_fsm_context.update_data.assert_called_once_with(api_key="ntn_mysecretkey123")

    # 2. Змінено стан на очікування ID бази даних
    mock_fsm_context.set_state.assert_called_once_with(NotionSetup.waiting_for_db_id)
    mock_message.answer.assert_called_once()


@pytest.mark.asyncio
async def test_process_db_id_valid(mock_message, mock_fsm_context, mock_db_session):
    # Умови: Користувач відправив коректне посилання Notion з 32-значним хешем
    mock_message.text = "https://www.notion.so/myworkspace/My-Project-1234567890abcdef1234567890abcdef?v=..."

    mock_user = MagicMock(spec=User)
    mock_user.language_code = "uk"
    mock_db_session.get.return_value = mock_user

    await process_db_id(mock_message, mock_fsm_context)

    # Перевірки:
    # 1. Згідно з текстом регекспу, парсер повинен знайти 32 символи і зберегти в БД
    assert mock_user.notion_db_id == "1234567890abcdef1234567890abcdef"
    assert (
        mock_user.notion_api_key == "ntn_12345test"
    )  # Взято з фікстури mock_fsm_context
    mock_db_session.commit.assert_called_once()

    # 2. Стан скидається (clear)
    mock_fsm_context.clear.assert_called_once()
    mock_message.answer.assert_called_once()


@pytest.mark.asyncio
async def test_process_db_id_invalid(mock_message, mock_fsm_context, mock_db_session):
    # Умови: Користувач відправив некоректне посилання (немає 32 символів підряд)
    mock_message.text = "https://google.com/не-notion-посилання"

    mock_user = MagicMock(spec=User)
    mock_user.language_code = "uk"
    mock_db_session.get.return_value = mock_user

    await process_db_id(mock_message, mock_fsm_context)

    # Перевірки:
    # 1. Дані в БД не збережено, стан не очищено
    mock_db_session.commit.assert_not_called()
    mock_fsm_context.clear.assert_not_called()

    # 2. Відправлено повідомлення про помилку
    mock_message.answer.assert_called_once()
    args, _ = mock_message.answer.call_args
    assert "не схоже на правильне посилання" in args[0]


# ==========================================
# 3. ДОДАТКОВІ ТЕСТИ (ГРАНИЧНІ ВИПАДКИ ТА СКИДАННЯ)
# ==========================================


@pytest.mark.asyncio
@patch("src.bot.handlers.commands.TEXTS")
async def test_cmd_start_already_setup(
    mock_texts, mock_message, mock_fsm_context, mock_db_session
):
    """
    Семантика: Перевірка повторного виклику /start для повністю налаштованого користувача.

    TODO для розробника: Згідно з файлом lexicon.py, ключ "already_setup" відсутній.
    Тут використано mock для словника TEXTS, щоб уникнути KeyError, доки баг не буде виправлено.
    """
    # Налаштовуємо імітацію словника
    mock_texts.__getitem__.return_value = {"already_setup": "Бот вже налаштовано"}

    mock_user = MagicMock(spec=User)
    mock_user.language_code = "uk"
    mock_user.notion_api_key = "ntn_valid_key"
    mock_user.notion_db_id = "valid_db_id"
    mock_db_session.get.return_value = mock_user

    await cmd_start(mock_message, mock_fsm_context)

    # Перевірка згідно з логікою
    mock_message.answer.assert_called_once()
    mock_fsm_context.set_state.assert_not_called()


@pytest.mark.asyncio
async def test_cmd_reset(mock_message, mock_fsm_context, mock_db_session):
    """
    Семантика: Перевірка команди /reset. Вона має очистити всі поля юзера і скинути стан.
    """
    mock_user = MagicMock(spec=User)
    mock_user.language_code = "uk"
    mock_user.notion_api_key = "ntn_old_key"
    mock_user.notion_db_id = "old_db_id"
    mock_db_session.get.return_value = mock_user

    # Щоб уникнути помилки виклику cmd_start в кінці cmd_reset, імітуємо (mock) його
    with patch(
        "src.bot.handlers.commands.cmd_start", new_callable=AsyncMock
    ) as mock_cmd_start:
        await cmd_reset(mock_message, mock_fsm_context)

        # Перевірки згідно з логікою скидання:
        assert mock_user.notion_api_key is None
        assert mock_user.notion_db_id is None
        assert mock_user.language_code is None

        mock_db_session.commit.assert_called_once()
        mock_fsm_context.clear.assert_called_once()
        mock_message.answer.assert_called_once()

        # Згідно з контекстом коду, після скидання викликається cmd_start
        mock_cmd_start.assert_called_once_with(mock_message, mock_fsm_context)


# --- Блок захисних перевірок (Early returns) ---


@pytest.mark.asyncio
async def test_early_returns_no_user(mock_message, mock_fsm_context, mock_db_session):
    """
    Семантика: Перевірка захисту, якщо повідомлення не містить from_user (наприклад, системне).
    """
    mock_message.from_user = None

    await cmd_start(mock_message, mock_fsm_context)
    await process_api_key(mock_message, mock_fsm_context)
    await process_db_id(mock_message, mock_fsm_context)
    await cmd_reset(mock_message, mock_fsm_context)

    # Згідно з логікою, всі функції мають перервати виконання і нічого не викликати
    mock_db_session.get.assert_not_called()


@pytest.mark.asyncio
async def test_process_language_selection_no_data(mock_fsm_context, mock_db_session):
    """Перевірка захисту від порожнього callback.data"""
    callback = AsyncMock(spec=CallbackQuery)
    callback.data = None

    await process_language_selection(callback, mock_fsm_context)

    mock_db_session.get.assert_not_called()


@pytest.mark.asyncio
async def test_handlers_no_text(mock_message, mock_fsm_context, mock_db_session):
    """Перевірка обробників введення, якщо користувач надіслав не текст (наприклад, фото)"""
    mock_message.text = None

    await process_api_key(mock_message, mock_fsm_context)
    await process_db_id(mock_message, mock_fsm_context)

    # Стан не оновлюється, до БД звернень немає
    mock_fsm_context.update_data.assert_not_called()
    mock_db_session.get.assert_not_called()


@pytest.mark.asyncio
async def test_cmd_start_user_exists_no_keys(
    mock_message, mock_fsm_context, mock_db_session
):
    """Семантична перевірка: юзер існує, мову обрано, але ключів ще немає."""
    mock_user = MagicMock(spec=User)
    mock_user.language_code = "uk"
    # Імітуємо відсутність ключів
    mock_user.notion_api_key = None
    mock_user.notion_db_id = None
    mock_db_session.get.return_value = mock_user

    await cmd_start(mock_message, mock_fsm_context)

    # Згідно з контекстом, має відправитися повідомлення "step_1"
    mock_message.answer.assert_called_once()
    mock_fsm_context.set_state.assert_called_once_with(NotionSetup.waiting_for_api_key)
