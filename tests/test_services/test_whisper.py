from pathlib import Path
from unittest.mock import AsyncMock, mock_open, patch

import pytest

from src.services.whisper import transcribe_audio


@pytest.mark.asyncio
@patch("src.services.whisper.client")
async def test_whisper_transcribe_success(mock_client, tmp_path):
    """Happy Path: Успішна транскрибація існуючого файлу."""
    fake_file = tmp_path / "test_audio.mp3"
    fake_file.touch()

    mock_client.audio.transcriptions.create = AsyncMock(
        return_value="Розпізнаний текст Whisper"
    )

    with patch("builtins.open", mock_open(read_data=b"data")):
        result = await transcribe_audio(fake_file)

    assert result == "Розпізнаний текст Whisper"
    mock_client.audio.transcriptions.create.assert_called_once()


@pytest.mark.asyncio
async def test_whisper_transcribe_file_not_found():
    """Error Handling: Захист від неіснуючого файлу."""
    fake_path = Path("non_existent_audio.mp3")

    with pytest.raises(FileNotFoundError, match="Аудіофайл не знайдено"):
        await transcribe_audio(fake_path)
