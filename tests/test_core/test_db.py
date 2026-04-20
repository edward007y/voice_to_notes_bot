from unittest.mock import AsyncMock, patch

import pytest

from src.core.db import get_session
from src.db.database import init_models


@pytest.mark.asyncio
@patch("src.core.db.async_session_maker")
async def test_get_session(mock_session_maker):
    """Семантична перевірка генератора сесій та блоку finally."""
    mock_session = AsyncMock()

    # Імітація асинхронного контекстного менеджера
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_session
    mock_session_maker.return_value = mock_ctx

    # Згідно з контекстом, get_session є AsyncGenerator
    async for session in get_session():
        assert session == mock_session

    # Перевіряємо, що після виходу з генератора сесія закрилася (блок finally)
    mock_session.close.assert_called_once()


@pytest.mark.asyncio
@patch("src.db.database.engine")
async def test_init_models(mock_engine):
    """Перевірка ініціалізації таблиць БД."""
    mock_conn = AsyncMock()

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_conn
    mock_engine.begin.return_value = mock_ctx

    await init_models()

    # Перевірка виклику створення таблиць через run_sync
    mock_conn.run_sync.assert_called_once()
