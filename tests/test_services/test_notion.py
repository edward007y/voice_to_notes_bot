from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.notion import create_notion_page

# ==========================================
# 1. СТВОРЕННЯ ФІКСТУР (ІЗОЛЯЦІЯ)
# ==========================================


@pytest.fixture
def mock_notion_client():
    """
    Семантична імітація клієнта Notion API.
    """
    with patch("src.services.notion.AsyncClient") as MockClient:
        client_instance = MagicMock()
        # Метод pages.create в notion_client є асинхронним
        client_instance.pages.create = AsyncMock()
        MockClient.return_value = client_instance
        yield client_instance


# ==========================================
# 2. ТЕСТИ ДЛЯ create_notion_page
# ==========================================


@pytest.mark.asyncio
async def test_create_notion_page_success_uk(mock_notion_client):
    """Happy Path: Українська мова та наявність завдань (action_items)."""
    # Імітуємо успішну відповідь від API
    mock_notion_client.pages.create.return_value = {
        "url": "https://notion.so/test-page-uk"
    }

    result = await create_notion_page(
        summary="Текст нотатки",
        action_items=["Купити молоко", "Подзвонити мамі"],
        api_key="ntn_secret",
        db_id="db_123",
        language_code="uk",
    )

    assert result == "https://notion.so/test-page-uk"
    mock_notion_client.pages.create.assert_called_once()

    # Перевірка структури запиту
    call_kwargs = mock_notion_client.pages.create.call_args.kwargs
    assert call_kwargs["parent"] == {"database_id": "db_123"}

    # Згідно з логікою, має бути 5 блоків:
    # 1. Заголовок summary, 2. Текст summary, 3. Заголовок action items, 4. to_do 1, 5. to_do 2
    children = call_kwargs["children"]
    assert len(children) == 5
    # Перевірка локалізації
    assert "Сумаризація" in str(children)
    assert "Завдання" in str(children)


@pytest.mark.asyncio
async def test_create_notion_page_success_en_no_actions(mock_notion_client):
    """Happy Path: Англійська мова та відсутність завдань."""
    mock_notion_client.pages.create.return_value = {
        "url": "https://notion.so/test-page-en"
    }

    result = await create_notion_page(
        summary="English text",
        action_items=[],  # Порожній список завдань
        api_key="ntn_secret",
        db_id="db_123",
        language_code="en",
    )

    assert result == "https://notion.so/test-page-en"

    # Перевірка структури запиту
    call_kwargs = mock_notion_client.pages.create.call_args.kwargs
    children = call_kwargs["children"]

    # Згідно з логікою, має бути лише 2 блоки: заголовок і текст
    assert len(children) == 2
    # Перевірка англійської локалізації
    assert "Summary" in str(children)
    assert "Action Items" not in str(children)


@pytest.mark.asyncio
async def test_create_notion_page_exception(mock_notion_client):
    """Error Handling: Збій під час виклику Notion API."""
    mock_notion_client.pages.create.side_effect = Exception("Notion API Timeout")

    # Перевіряємо, що виключення прокидається далі
    with pytest.raises(Exception, match="Notion API Timeout"):
        await create_notion_page(
            summary="Текст", action_items=[], api_key="ntn_secret", db_id="db_123"
        )
