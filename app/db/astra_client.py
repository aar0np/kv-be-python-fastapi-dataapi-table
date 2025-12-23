# NOTE: Starting from astrapy v2 the old `astrapy.db` import path has been
# removed.  To stay compatible with both the v1 (core) and the new Data API
# client, we lazily attempt the legacy import first and fall back to a thin
# wrapper that relies on the new `DataAPIClient` + `AsyncDatabase` classes.

import logging
#from astrapy import DataAPIClient, AsyncCollection  # type: ignore  # noqa: F401,F811
from astrapy import DataAPIClient, AsyncCollection
from typing import Optional
# astrapy v2 is available – define wrapper using actual client

# Optional imports for more granular connection error handling.  These are
# only used for *type checking* in the `except` clause; failure to import is
# safe because we fall back to the generic handler.

try:
    import httpx  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – not installed in some envs
    httpx = None  # type: ignore

try:
    from httpcore import ConnectError as HttpcoreConnectError  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – indirect dep may be absent
    HttpcoreConnectError = None  # type: ignore

class _AstraDBV2Wrapper:  # noqa: D401
    """Compatibility shim for astrapy v2."""

    def __init__(self, *, api_endpoint: str, token: str, namespace: str):
        client = DataAPIClient(token=token)
        self._db = client.get_async_database(
            api_endpoint,
            keyspace=namespace,
        )

    def collection(self, table_name: str):  # type: ignore
        return self._db.get_collection(table_name)

    async def create_collection(self, name: str, **kwargs):  # noqa: D401
        """Proxy to the underlying AsyncDatabase.create_collection."""
        return await self._db.create_collection(name, **kwargs)

AstraDB = _AstraDBV2Wrapper  # type: ignore
AstraDBCollection = AsyncCollection  # type: ignore

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
        # Extra debug information to help diagnose connectivity problems. The token
        # is intentionally truncated to avoid leaking secrets in logs.
        logger.debug(
            "AstraDB connection settings – endpoint=%s | keyspace=%s | token_prefix=%s…",
            settings.ASTRA_DB_API_ENDPOINT,
            settings.ASTRA_DB_KEYSPACE,
            settings.ASTRA_DB_APPLICATION_TOKEN[:8],
        )
        # The concrete class of `AstraDB` depends on the import section above
        # (legacy vs. v2).  Both variants share the same constructor signature
        # thanks to the wrapper defined for v2.
        db_instance = AstraDB(
            api_endpoint=settings.ASTRA_DB_API_ENDPOINT,
            token=settings.ASTRA_DB_APPLICATION_TOKEN,
            namespace=settings.ASTRA_DB_KEYSPACE,
        )
        # You might want to add a simple check to confirm connection, e.g., listing collections or a specific health check if available
        # For now, we assume initialization is successful if no exceptions are raised.
        logger.info("AstraDB client initialized successfully.")
    except Exception as e:
        # Handle connection-level failures with a cleaner log message to avoid
        # dumping an unreadable stack-trace to the console during normal start-up.
        is_connect_error = False

        if httpx is not None and isinstance(e, httpx.ConnectError):
            is_connect_error = True
        elif HttpcoreConnectError is not None and isinstance(e, HttpcoreConnectError):
            is_connect_error = True
        elif isinstance(e, ConnectionError):  # built-in
            is_connect_error = True

        if is_connect_error:
            logger.error(
                "Unable to establish connection to AstraDB – check API endpoint/token."
            )
            # Optionally include short context
            logger.debug("Connection error details: %s", e)
        else:
            # Unexpected failure – keep full traceback for debugging.
            logger.error("Failed to initialize AstraDB client: %s", e, exc_info=True)

        # Maintain previous behaviour of surfacing the error so the app knows
        # startup failed.
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


async def get_table(table_name: str) -> AsyncCollection:
    db = await get_astra_db()
    return db.collection(table_name)
