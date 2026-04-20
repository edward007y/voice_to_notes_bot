import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
from aiogram import Bot
from aiogram.types import Message, Voice
from aiogram.types import User as AiogramUser

from src.bot.handlers.voice import handle_voice_message
from src.services.audio import convert_ogg_to_mp3
from src.services.openai_llm import summarize_text
from src.services.openai_llm import transcribe_audio as llm_transcribe_audio

# ==========================================
# Тести для src.services.audio
# ==========================================


@pytest.mark.asyncio
async def test_convert_ogg_to_mp3_success(tmp_path):
    # Перевірка успішної конвертації файлу
    test_file = tmp_path / "test.ogg"
    test_file.touch()

    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"stdout", b"stderr")
    mock_process.returncode = 0

    with patch(
        "asyncio.create_subprocess_exec", return_value=mock_process
    ) as mock_exec:
        result = await convert_ogg_to_mp3(test_file)

        assert result == test_file.with_suffix(".mp3")
        mock_exec.assert_called_once()
        assert str(test_file) in mock_exec.call_args[0]


@pytest.mark.asyncio
async def test_convert_ogg_to_mp3_file_not_found():
    # Перевірка захисту від неіснуючого файлу
    fake_path = Path("non_existent.ogg")

    with pytest.raises(FileNotFoundError, match="Вхідний файл не знайдено"):
        await convert_ogg_to_mp3(fake_path)


@pytest.mark.asyncio
async def test_convert_ogg_to_mp3_ffmpeg_error(tmp_path):
    # Перевірка обробки помилок від ffmpeg (не нульовий код повернення)
    test_file = tmp_path / "error.ogg"
    test_file.touch()

    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"", b"Invalid data found")
    mock_process.returncode = 1

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with pytest.raises(RuntimeError, match="Не вдалося конвертувати аудіо"):
            await convert_ogg_to_mp3(test_file)


# ==========================================
# Тести для src.services.openai_llm
# ==========================================


@pytest.mark.asyncio
@patch("src.services.openai_llm.client")
async def test_summarize_text_success(mock_client):
    # Перевірка валідного парсингу JSON від LLM
    expected_data = {"summary": "Тестове резюме", "action_items": ["Завдання 1"]}

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(expected_data)
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await summarize_text("Деякий текст", "uk")
    assert result == expected_data


@pytest.mark.asyncio
@patch("src.services.openai_llm.client")
async def test_summarize_text_empty_response(mock_client):
    # Перевірка реакції на порожню відповідь (TODO: можливо, варто повертати дефолтний dict замість fallback)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = ""
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await summarize_text("Деякий текст", "uk")

    # Згідно з імплементацією, помилка перехоплюється блоком except і повертається dict
    assert "Помилка генерації" in result["summary"]
    assert result["action_items"] == []


# ==========================================
# Тести для src.bot.handlers.voice
# ==========================================


@pytest.fixture
def mock_message():
    message = AsyncMock(spec=Message)
    message.voice = MagicMock(spec=Voice)
    message.from_user = MagicMock(spec=AiogramUser)
    message.from_user.id = 12345
    message.message_id = 67890
    message.voice.file_id = "test_file_id"

    message.reply = AsyncMock()

    return message


@pytest.mark.asyncio
async def test_handle_voice_message_too_short(mock_message):
    # Граничне значення: аудіо менше 2 секунд
    mock_bot = AsyncMock(spec=Bot)
    mock_message.voice.duration = 1

    await handle_voice_message(mock_message, mock_bot)

    mock_message.reply.assert_called_once_with(
        "⚠️ Голосове повідомлення занадто коротке. Запишіть хоча б пару секунд."
    )
    mock_bot.download.assert_not_called()


@pytest.mark.asyncio
async def test_handle_voice_message_too_long(mock_message):
    # Граничне значення: аудіо більше 300 секунд
    mock_bot = AsyncMock(spec=Bot)
    mock_message.voice.duration = 301

    await handle_voice_message(mock_message, mock_bot)

    mock_message.reply.assert_called_once_with(
        "⏳ Вибачте, але я можу обробляти аудіо тривалістю не більше 5 хвилин."
    )
    mock_bot.download.assert_not_called()


@pytest.mark.asyncio
@patch("src.bot.handlers.voice.transcribe_task")
async def test_handle_voice_message_success(mock_task, mock_message):
    # Happy Path: коректна тривалість, виклик брокера
    mock_bot = AsyncMock(spec=Bot)
    mock_message.voice.duration = 150
    mock_task.kiq = AsyncMock()

    await handle_voice_message(mock_message, mock_bot)

    mock_bot.download.assert_called_once()
    mock_task.kiq.assert_called_once()

    # Перевіряємо, чи правильні аргументи передані в задачу
    args, _ = mock_task.kiq.call_args
    assert "12345_67890.ogg" in args[0]
    assert args[1] == 12345


# ==========================================
# ТЕСТИ ДЛЯ transcribe_audio (src.services.openai_llm)
# ==========================================


@pytest.mark.asyncio
@patch("src.services.openai_llm.client")
@patch("builtins.open", new_callable=mock_open, read_data=b"audio_bytes")
async def test_llm_transcribe_success(mock_file, mock_client):
    """Happy Path: Успішна транскрибація через LLM сервіс."""
    mock_response = MagicMock()
    mock_response.text = "Текст з аудіо"
    mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)

    # Використовуємо аліас llm_transcribe_audio, щоб не плутати з whisper
    result = await llm_transcribe_audio("fake_path.mp3")

    assert result == "Текст з аудіо"
    mock_client.audio.transcriptions.create.assert_called_once()
    mock_file.assert_called_once_with("fake_path.mp3", "rb")


@pytest.mark.asyncio
@patch("src.services.openai_llm.client")
@patch("builtins.open", new_callable=mock_open, read_data=b"audio_bytes")
@patch("src.services.openai_llm.logger")
async def test_llm_transcribe_exception(mock_logger, mock_file, mock_client):
    """Error Handling: Обробка та логування виключень від API."""
    mock_client.audio.transcriptions.create.side_effect = Exception("OpenAI API Down")

    with pytest.raises(Exception, match="OpenAI API Down"):
        await llm_transcribe_audio("fake_path.mp3")

    mock_logger.error.assert_called_once()
    args, _ = mock_logger.error.call_args
    assert "Помилка під час транскрибації Whisper" in args[0]


@pytest.mark.asyncio
async def test_handle_voice_message_no_voice(mock_message):
    """Перевірка early return, якщо у повідомленні немає об'єкта voice."""
    mock_message.voice = None
    mock_bot = AsyncMock()

    await handle_voice_message(mock_message, mock_bot)

    # Жодних дій не повинно відбутися
    mock_message.reply.assert_not_called()
    mock_bot.download.assert_not_called()
