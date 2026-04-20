from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import Bot
from taskiq import Context, TaskiqState

from src.db.models import User
from src.tasks.tasks import export_to_notion_task, notify_user, transcribe_task

# ==========================================
# 1. СТВОРЕННЯ ФІКСТУР (ІЗОЛЯЦІЯ)
# ==========================================


@pytest.fixture
def mock_db_session():
    """Імітація асинхронної сесії SQLAlchemy для завдань."""
    session_mock = AsyncMock()
    ctx_manager = AsyncMock()
    ctx_manager.__aenter__.return_value = session_mock
    ctx_manager.__aexit__.return_value = None

    with patch("src.tasks.tasks.async_session_maker", return_value=ctx_manager):
        yield session_mock


@pytest.fixture
def mock_bot():
    """Імітація Telegram-бота."""
    bot = AsyncMock(spec=Bot)
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def mock_taskiq_context(mock_bot):
    """Імітація контексту виконання Taskiq."""
    context = MagicMock(spec=Context)
    context.state = MagicMock(spec=TaskiqState)
    context.state.bot = mock_bot
    return context


# ==========================================
# 2. ТЕСТИ ДЛЯ export_to_notion_task
# ==========================================


@pytest.mark.asyncio
@patch("src.tasks.tasks.create_notion_page")
async def test_export_to_notion_task_success(mock_create_notion_page, mock_db_session):
    mock_create_notion_page.return_value = "https://notion.so/test_url"

    mock_user = MagicMock(spec=User)
    mock_user.notion_api_key = "valid_key"
    mock_user.notion_db_id = "valid_db"
    mock_db_session.get.return_value = mock_user

    result = await export_to_notion_task({"summary": "Текст", "action_items": []}, 123)

    assert result == "https://notion.so/test_url"
    mock_create_notion_page.assert_called_once_with(
        "Текст", [], "valid_key", "valid_db", "uk"
    )


@pytest.mark.asyncio
async def test_export_to_notion_task_missing_keys(mock_db_session):
    # Користувач є, але немає ключів
    mock_user = MagicMock(spec=User)
    mock_user.notion_api_key = None
    mock_db_session.get.return_value = mock_user

    with pytest.raises(ValueError, match="Ключі Notion не налаштовані"):
        await export_to_notion_task({}, 123)


# ==========================================
# 3. ТЕСТИ ДЛЯ notify_user
# ==========================================


@pytest.mark.asyncio
async def test_notify_user_success_en(mock_bot):
    """Семантична перевірка англійської локалізації повідомлення про успіх."""
    await notify_user(mock_bot, 123, "en", "success", "http://url")
    args, kwargs = mock_bot.send_message.call_args
    assert "Done!" in kwargs["text"]


@pytest.mark.asyncio
async def test_notify_user_unknown_status(mock_bot):
    # Невідомий статус має бути проігнорований (early return)
    await notify_user(mock_bot, 123, "uk", "unknown_status")
    mock_bot.send_message.assert_not_called()


@pytest.mark.asyncio
@patch("src.tasks.tasks.logger")
async def test_notify_user_exception(mock_logger, mock_bot):
    # Семантична перевірка: якщо бот заблоковано юзером, воркер не повинен впасти
    mock_bot.send_message.side_effect = Exception("Bot blocked")

    await notify_user(mock_bot, 123, "uk", "error")

    mock_logger.error.assert_called_once()
    assert "Не вдалося відправити повідомлення" in mock_logger.error.call_args[0][0]


# ==========================================
# 4. ТЕСТИ ДЛЯ transcribe_task (ГОЛОВНИЙ ПАЙПЛАЙН)
# ==========================================
@pytest.mark.asyncio
async def test_notify_user_english_branches(mock_bot):
    """Семантичне покриття рядка 46: всі статуси для англійської мови."""
    await notify_user(mock_bot, 123, "en", "processing")
    await notify_user(mock_bot, 123, "en", "error")
    # Перевіряємо, що бот надіслав повідомлення двічі
    assert mock_bot.send_message.call_count == 2


@pytest.mark.asyncio
async def test_export_to_notion_task_no_user(mock_db_session):
    """Семантичне покриття рядка 86: користувач відсутній у базі даних (None)."""
    mock_db_session.get.return_value = None

    with pytest.raises(ValueError, match="Ключі Notion не налаштовані"):
        await export_to_notion_task({"summary": "Текст", "action_items": []}, 123)


# ==========================================
# 4. ТЕСТИ ДЛЯ transcribe_task (ГОЛОВНИЙ ПАЙПЛАЙН)
# ==========================================


@pytest.mark.asyncio
@patch("src.tasks.tasks.os")
@patch("src.tasks.tasks.convert_ogg_to_mp3", new_callable=AsyncMock)
@patch("src.tasks.tasks.transcribe_audio", new_callable=AsyncMock)
@patch("src.tasks.tasks.summarize_text", new_callable=AsyncMock)
@patch("src.tasks.tasks.export_to_notion_task", new_callable=AsyncMock)
async def test_transcribe_task_success(
    mock_export,
    mock_summarize,
    mock_transcribe,
    mock_convert,
    mock_os,
    mock_db_session,
    mock_taskiq_context,
):
    # Успішний сценарій
    mock_os.path.exists.return_value = True
    # Семантично правильно повертати Path для сумісності
    mock_convert.return_value = Path("path.mp3")
    mock_transcribe.return_value = "Розпізнаний текст"
    mock_summarize.return_value = {"summary": "Текст", "action_items": []}
    mock_export.return_value = "http://notion.url"

    mock_user = MagicMock(spec=User)
    mock_user.language_code = "uk"
    mock_db_session.get.return_value = mock_user

    with patch("src.tasks.tasks.notify_user", new_callable=AsyncMock) as mock_notify:
        await transcribe_task("path.ogg", 123, context=mock_taskiq_context)

        # Перевірки пайплайну
        mock_convert.assert_called_once()
        mock_transcribe.assert_called_once()
        mock_summarize.assert_called_once()
        mock_export.assert_called_once()

        # Перевірка сповіщень (processing, потім success)
        assert mock_notify.call_count == 2

        # Перевірка блоку finally (видалення 2 файлів)
        assert mock_os.remove.call_count == 2


@pytest.mark.asyncio
@patch("src.tasks.tasks.os")
@patch("src.tasks.tasks.convert_ogg_to_mp3", new_callable=AsyncMock)
async def test_transcribe_task_pipeline_error(
    mock_convert, mock_os, mock_db_session, mock_taskiq_context
):
    """Семантична перевірка обробки виключень та блоку finally (рядки 97-100)."""
    mock_os.path.exists.return_value = True
    mock_convert.side_effect = Exception("Збій конвертації")

    mock_user = MagicMock(spec=User)
    mock_user.language_code = "uk"
    mock_db_session.get.return_value = mock_user

    with patch("src.tasks.tasks.notify_user", new_callable=AsyncMock) as mock_notify:
        # Перевіряємо, що помилка прокидається далі
        with pytest.raises(Exception, match="Збій конвертації"):
            await transcribe_task("path.ogg", 123, context=mock_taskiq_context)

        # Перевіряємо відправку статусу 'error'
        mock_notify.assert_called_with(
            mock_taskiq_context.state.bot, 123, "uk", "error"
        )
        # Перевіряємо, що файли все одно видаляються
        assert mock_os.remove.call_count == 2


@pytest.mark.asyncio
async def test_export_to_notion_task_no_db_id(mock_db_session):
    """Семантичне покриття рядка 86: відсутній ID бази даних (notion_db_id)."""
    mock_user = MagicMock()
    mock_user.notion_api_key = "ntn_valid_key"
    mock_user.notion_db_id = None  # Імітуємо відсутність саме цього ключа
    mock_db_session.get.return_value = mock_user

    # Використовуємо загальний Exception, щоб перехопити будь-яку помилку валідації
    with pytest.raises(Exception):
        await export_to_notion_task({"summary": "Текст", "action_items": []}, 123)
