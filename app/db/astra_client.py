import logging
from typing import Optional

# Attempt to import AstraDB; provide stubs if unavailable (e.g., during CI without the package)
try:
    from astrapy.db import AstraDB, AstraDBCollection  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - only for test envs without astrapy
    class AstraDB:  # Minimal stub
        def __init__(self, *args, **kwargs):
            pass

        def collection(self, *args, **kwargs):  # type: ignore
            class _StubCollection:  # noqa: D401
                async def find_one(self, *a, **kw):
                    return None

                async def insert_one(self, *a, **kw):
                    return {}

                async def update_one(self, *a, **kw):
                    return {}

            return _StubCollection()

    class AstraDBCollection:  # Minimal stub
        async def find_one(self, *a, **kw):
            return None

        async def insert_one(self, *a, **kw):
            return {}

        async def update_one(self, *a, **kw):
            return {}

from app.core.config import settings

logger = logging.getLogger(__name__)
db_instance: Optional[AstraDB] = None


async def init_astra_db():
    global db_instance
    if not all(
        [
            settings.ASTRA_DB_API_ENDPOINT,
            settings.ASTRA_DB_APPLICATION_TOKEN,
            settings.ASTRA_DB_KEYSPACE,
        ]
    ):
        logger.error(
            "AstraDB settings are not fully configured. Please check ASTRA_DB_API_ENDPOINT, ASTRA_DB_APPLICATION_TOKEN, and ASTRA_DB_KEYSPACE."
        )
        raise ValueError("AstraDB settings are not fully configured.")

    try:
        logger.info(
            f"Initializing AstraDB client for keyspace: {settings.ASTRA_DB_KEYSPACE} at {settings.ASTRA_DB_API_ENDPOINT[:30]}..."
        )  # Log only part of endpoint
        db_instance = AstraDB(
            api_endpoint=settings.ASTRA_DB_API_ENDPOINT,
            token=settings.ASTRA_DB_APPLICATION_TOKEN,
            namespace=settings.ASTRA_DB_KEYSPACE,
        )
        # You might want to add a simple check to confirm connection, e.g., listing collections or a specific health check if available
        # For now, we assume initialization is successful if no exceptions are raised.
        logger.info("AstraDB client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize AstraDB client: {e}", exc_info=True)
        # db_instance remains None
        raise


async def get_astra_db() -> AstraDB:
    global db_instance
    if db_instance is None:
        logger.info("AstraDB instance not found, attempting to initialize...")
        await init_astra_db()  # This will raise an error if init fails
        if (
            db_instance is None
        ):  # Should not happen if init_astra_db doesn't raise, but defensive
            logger.error(
                "AstraDB initialization failed and did not raise an error, which is unexpected."
            )
            raise RuntimeError("AstraDB could not be initialized.")
    return db_instance


async def get_table(table_name: str) -> AstraDBCollection:
    db = await get_astra_db()
    return db.collection(table_name)
