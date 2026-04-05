# GPT-4o-mini prompts and processing
import logging

from openai import AsyncOpenAI
from pydantic import BaseModel, Field, ValidationError

from src.core.config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY.get_secret_value())


class SummaryResult(BaseModel):
    summary: str = Field(
        description="Стислий, але змістовний підсумок транскрибованого тексту."
    )
    action_items: list[str] = Field(
        description="Список конкретних задач (to-do) або домовленостей. Порожній список, якщо задач немає."
    )


SYSTEM_PROMPT = """
Ти — професійний бізнес-асистент. Твоє завдання — проаналізувати транскрибований текст голосового повідомлення.
1. Напиши стисле резюме (summary) головної думки тексту.
2. Виділи чіткі задачі, доручення або наступні кроки (action items). 
Відповідай виключно українською мовою. Будь лаконічним.
"""


async def summarize_text(text: str) -> SummaryResult:
    if not text or not text.strip():
        logger.warning("Отримано порожній текст для сумаризації.")
        return SummaryResult(
            summary="Текст відсутній або не містить інформації.", action_items=[]
        )

    try:
        logger.info("Відправка тексту на аналіз до LLM...")
        response = await client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            response_format=SummaryResult,
        )

        result = response.choices[0].message.parsed

        # Перевірка для Pylance та обробка можливої відмови моделі
        if result is None:
            raise ValueError(
                f"Модель відмовилася надати результат. Причина: {response.choices[0].message.refusal}"
            )

        logger.info("Сумаризація успішно завершена та провалідована локально.")
        return result

    except ValidationError as e:
        # Локальна валідація Pydantic провалилася (AI повернув невалідну структуру)
        logger.error(f"AI повернув невалідні дані. Помилка валідації: {e}")
        return SummaryResult(
            summary="Не вдалося структурувати відповідь через помилку формату.",
            action_items=[],
        )
    except Exception as e:
        logger.error(f"Помилка під час роботи з LLM API: {e}")
        raise
