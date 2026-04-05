# Notion API operations
import logging
from datetime import datetime

from notion_client import AsyncClient

from src.core.config import settings

logger = logging.getLogger(__name__)

# Ініціалізація асинхронного клієнта Notion
notion = AsyncClient(auth=settings.NOTION_API_KEY.get_secret_value())


async def create_notion_page(summary: str, action_items: list[str]) -> str:
    """
    Створює сторінку в базі даних Notion з результатами розпізнавання.

    :param summary: Текст сумаризації.
    :param action_items: Список задач.
    :return: URL створеної сторінки.
    """
    logger.info("Початок експорту даних у Notion...")

    # Формуємо заголовок з поточною датою
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = f"Голосова нотатка від {date_str}"

    # Базові блоки сторінки
    children_blocks = [
        {
            "object": "block",
            "heading_2": {"rich_text": [{"text": {"content": "📝 Сумаризація"}}]},
        },
        {
            "object": "block",
            "paragraph": {"rich_text": [{"text": {"content": summary}}]},
        },
    ]

    # Додаємо задачі у вигляді чекліста (to_do блоків), якщо вони є
    if action_items:
        children_blocks.append(
            {
                "object": "block",
                "heading_2": {"rich_text": [{"text": {"content": "✅ Action Items"}}]},
            }
        )
        for item in action_items:
            children_blocks.append(
                {
                    "object": "block",
                    "to_do": {"rich_text": [{"text": {"content": item}}]},
                }
            )

    try:
        # Відправляємо запит до Notion API
        response = await notion.pages.create(
            parent={"database_id": settings.NOTION_DATABASE_ID},
            properties={"Name": {"title": [{"text": {"content": title}}]}},
            children=children_blocks,
        )

        page_url = response.get("url")
        logger.info(f"Сторінку успішно створено: {page_url}")
        return page_url

    except Exception as e:
        logger.error(f"Помилка під час експорту в Notion: {e}")
        raise
