import json
import logging

from openai import AsyncOpenAI

from src.core.config import settings

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY.get_secret_value())


async def transcribe_audio(file_path: str) -> str:
    """Транскрибує аудіофайл за допомогою Whisper."""
    logger.info(f"Відправка аудіо на транскрибацію: {file_path}")
    try:
        with open(file_path, "rb") as audio_file:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1", file=audio_file
            )
        logger.info("Транскрибація успішно завершена.")
        return transcript.text
    except Exception as e:
        logger.error(f"Помилка під час транскрибації Whisper: {e}")
        raise e


async def summarize_text(text: str, language_code: str = "uk") -> dict:
    """Сумаризує текст та виділяє завдання, використовуючи задану мову."""
    target_language = "English" if language_code == "en" else "Ukrainian"
    logger.info(f"Відправка тексту до LLM (Мова: {target_language})...")

    # Жорсткий промт для керування мовою виводу
    system_prompt = f"""You are a professional assistant that analyzes transcribed voice notes.

    CRITICAL INSTRUCTION:
    Your entire response MUST be written in {target_language}.
    Even if the transcribed text is in another language, you MUST translate the summary and action items into {target_language}.

    Analyze the provided text. Extract the main points into a comprehensive summary and create a list of actionable items (to-dos) if any exist.

    Return ONLY a valid JSON object with this exact structure:
    {{
        "summary": "Main summary text here in {target_language}...",
        "action_items": ["Action item 1 in {target_language}", "Action item 2 in {target_language}"]
    }}
    """

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )

        result_text = response.choices[0].message.content
        if not result_text:
            raise ValueError("Отримано порожню відповідь від LLM.")

        data = json.loads(result_text)
        logger.info("Сумаризація успішно завершена.")
        return data

    except Exception as e:
        logger.error(f"Помилка під час взаємодії з LLM: {e}")
        return {
            "summary": f"Помилка генерації / Generation error. Text:\n{text}",
            "action_items": [],
        }
