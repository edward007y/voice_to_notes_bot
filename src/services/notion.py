import logging
from datetime import datetime

from notion_client import AsyncClient

logger = logging.getLogger(__name__)


async def create_notion_page(
    summary: str, action_items: list[str], api_key: str, db_id: str
) -> str:
    """
    Створює сторінку в базі даних Notion, використовуючи персональні ключі користувача.
    """
    logger.info("Початок експорту даних у Notion...")

    # Ініціалізуємо клієнта з персональним ключем юзера
    notion = AsyncClient(auth=api_key)

    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = f"Голосова нотатка від {date_str}"

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
        response = await notion.pages.create(
            # Використовуючи персональний ID бази
            parent={"database_id": db_id},
            properties={"Name": {"title": [{"text": {"content": title}}]}},
            children=children_blocks,
        )

        page_url = response.get("url")
        logger.info(f"Сторінку успішно створено: {page_url}")
        return page_url

    except Exception as e:
        logger.error(f"Помилка під час експорту в Notion: {e}")
        raise
