# OpenAI Whisper API client
from pathlib import Path

from openai import AsyncOpenAI

from src.core.config import settings

# Ініціалізація асинхронного клієнта OpenAI
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY.get_secret_value())


async def transcribe_audio(file_path: Path) -> str:
    """
    Транскрибує аудіофайл за допомогою OpenAI Whisper API.

    :param file_path: Шлях до локального аудіофайлу.
    :return: Розпізнаний текст.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Аудіофайл не знайдено: {file_path}")

    # Відкриваємо файл у бінарному режимі для відправки
    with open(file_path, "rb") as audio_file:
        response = await client.audio.transcriptions.create(
            model="whisper-1", file=audio_file, response_format="text"
        )

    # Оскільки response_format="text", API повертає звичайний рядок
    return str(response)
