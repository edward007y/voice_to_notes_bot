import logging
from datetime import datetime

from notion_client import AsyncClient

logger = logging.getLogger(__name__)


async def create_notion_page(
    summary: str,
    action_items: list[str],
    api_key: str,
    db_id: str,
    language_code: str = "uk",
) -> str:
    logger.info("Початок експорту даних у Notion...")
    notion = AsyncClient(auth=api_key)
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Локалізація заголовків Notion
    if language_code == "en":
        title = f"Voice Note from {date_str}"
        summary_heading = "📝 Summary"
        action_heading = "✅ Action Items"
    else:
        title = f"Голосова нотатка від {date_str}"
        summary_heading = "📝 Сумаризація"
        action_heading = "✅ Завдання"

    children_blocks = [
        {
            "object": "block",
            "heading_2": {"rich_text": [{"text": {"content": summary_heading}}]},
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
                "heading_2": {"rich_text": [{"text": {"content": action_heading}}]},
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
