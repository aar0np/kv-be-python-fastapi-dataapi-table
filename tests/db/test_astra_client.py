import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.db import astra_client


@pytest.fixture(autouse=True)
def reset_db_instance():
    astra_client.db_instance = None
    yield
    astra_client.db_instance = None


@pytest.mark.asyncio
async def test_init_astra_db_success(monkeypatch):
    monkeypatch.setattr(astra_client.settings, "ASTRA_DB_API_ENDPOINT", "test_endpoint")
    monkeypatch.setattr(
        astra_client.settings, "ASTRA_DB_APPLICATION_TOKEN", "test_token"
    )
    monkeypatch.setattr(astra_client.settings, "ASTRA_DB_KEYSPACE", "test_keyspace")

    with patch(
        "app.db.astra_client.AstraDB", new_callable=MagicMock
    ) as mock_astra_db_class:
        # If AstraDB().collection() is called or any other method on instance, configure here
        # mock_db_instance.collection = AsyncMock()

        await astra_client.init_astra_db()
        assert astra_client.db_instance is not None
        mock_astra_db_class.assert_called_once_with(
            api_endpoint="test_endpoint", token="test_token", namespace="test_keyspace"
        )


@pytest.mark.asyncio
async def test_init_astra_db_missing_config(monkeypatch):
    monkeypatch.setattr(astra_client.settings, "ASTRA_DB_API_ENDPOINT", None)
    with pytest.raises(ValueError, match="AstraDB settings are not fully configured."):
        await astra_client.init_astra_db()
    assert astra_client.db_instance is None


@pytest.mark.asyncio
async def test_get_astra_db_not_initialized_calls_init(monkeypatch):
    monkeypatch.setattr(astra_client.settings, "ASTRA_DB_API_ENDPOINT", "test_endpoint")
    monkeypatch.setattr(
        astra_client.settings, "ASTRA_DB_APPLICATION_TOKEN", "test_token"
    )
    monkeypatch.setattr(astra_client.settings, "ASTRA_DB_KEYSPACE", "test_keyspace")

    with patch(
        "app.db.astra_client.AstraDB", new_callable=MagicMock
    ) as mock_astra_db_class:
        await astra_client.get_astra_db()
        assert astra_client.db_instance is not None
        mock_astra_db_class.assert_called_once()


@pytest.mark.asyncio
async def test_get_astra_db_already_initialized(monkeypatch):
    # First, initialize it
    monkeypatch.setattr(astra_client.settings, "ASTRA_DB_API_ENDPOINT", "test_endpoint")
    monkeypatch.setattr(
        astra_client.settings, "ASTRA_DB_APPLICATION_TOKEN", "test_token"
    )
    monkeypatch.setattr(astra_client.settings, "ASTRA_DB_KEYSPACE", "test_keyspace")

    mock_initial_instance = MagicMock()
    astra_client.db_instance = mock_initial_instance

    with patch(
        "app.db.astra_client.init_astra_db", new_callable=AsyncMock
    ) as mock_init_db:
        db = await astra_client.get_astra_db()
        assert db is mock_initial_instance
        mock_init_db.assert_not_called()  # Should not call init_astra_db again


@pytest.mark.asyncio
async def test_get_table(monkeypatch):
    mock_db_instance = AsyncMock(spec=astra_client.AstraDB)
    mock_collection = AsyncMock(spec=astra_client.AstraDBCollection)
    mock_db_instance.collection.return_value = mock_collection

    # Ensure get_astra_db returns our mock_db_instance
    with patch(
        "app.db.astra_client.get_astra_db", new_callable=AsyncMock
    ) as mock_get_db:
        mock_get_db.return_value = mock_db_instance

        table = await astra_client.get_table("test_table")
        assert table is mock_collection
        mock_db_instance.collection.assert_called_once_with("test_table")
