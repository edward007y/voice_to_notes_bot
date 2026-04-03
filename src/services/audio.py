import asyncio
import logging
from pathlib import Path

# Налаштування логера
logger = logging.getLogger(__name__)


async def convert_ogg_to_mp3(input_path: Path) -> Path:
    """
    Конвертує аудіофайл з формату .ogg у .mp3 за допомогою ffmpeg.

    :param input_path: Шлях до вхідного файлу .ogg
    :return: Шлях до згенерованого файлу .mp3
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Вхідний файл не знайдено: {input_path}")

    # Формуємо шлях до нового файлу (змінюємо розширення)
    output_path = input_path.with_suffix(".mp3")

    logger.info(f"Початок конвертації: {input_path} -> {output_path}")

    # Запускаємо ffmpeg асинхронно
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-i",
        str(input_path),  # Вхідний файл
        "-y",  # Перезаписувати файл, якщо існує
        "-q:a",
        "0",  # Найкраща якість для mp3 (VBR)
        "-map",
        "a",  # Брати тільки аудіопотік
        str(output_path),  # Вихідний файл
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Очікуємо завершення процесу та збираємо логи
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_msg = stderr.decode().strip()
        logger.error(f"Помилка ffmpeg (код {process.returncode}): {error_msg}")
        raise RuntimeError(f"Не вдалося конвертувати аудіо. FFmpeg error: {error_msg}")

    logger.info("Конвертація успішно завершена.")
    return output_path
