"""Test configuration and stubs for external libraries."""

import sys
import types

# ---------------------------------------------------------------------------
# Stub for `astrapy` when the real package is not installed (CI / unit tests)
# ---------------------------------------------------------------------------
if "astrapy" not in sys.modules:  # pragma: no cover
    astrapy_stub = types.ModuleType("astrapy")
    db_stub = types.ModuleType("astrapy.db")

    class _StubCollection:  # noqa: D401
        async def find_one(self, *args, **kwargs):  # noqa: D401
            return None

        async def insert_one(self, *args, **kwargs):  # noqa: D401
            return {}

        async def update_one(self, *args, **kwargs):  # noqa: D401
            return {}

    class _StubDB:  # noqa: D401
        def __init__(self, *args, **kwargs):
            pass

        def collection(self, *args, **kwargs):  # noqa: D401
            return _StubCollection()

    db_stub.AstraDB = _StubDB  # type: ignore[attr-defined]
    db_stub.AstraDBCollection = _StubCollection  # type: ignore[attr-defined]

    astrapy_stub.db = db_stub  # type: ignore[attr-defined]
    sys.modules["astrapy"] = astrapy_stub
    sys.modules["astrapy.db"] = db_stub

    # Stub submodules used in code (e.g., astrapy.exceptions.data_api_exceptions)
    exceptions_stub = types.ModuleType("astrapy.exceptions")

    class _DataAPIResponseException(Exception):
        pass

    exceptions_stub.data_api_exceptions = types.ModuleType(
        "astrapy.exceptions.data_api_exceptions"
    )
    exceptions_stub.data_api_exceptions.DataAPIResponseException = _DataAPIResponseException  # type: ignore[attr-defined]

    # Register in sys.modules hierarchy so that "from astrapy.exceptions.data_api_exceptions" works
    sys.modules["astrapy.exceptions"] = exceptions_stub
    sys.modules["astrapy.exceptions.data_api_exceptions"] = exceptions_stub.data_api_exceptions

# ---------------------------------------------------------------------------
# Patch httpx.AsyncClient to accept `app` kwarg using ASGITransport (for tests)
# ---------------------------------------------------------------------------
try:
    import httpx
    from httpx import ASGITransport  # type: ignore

    class _PatchedAsyncClient(httpx.AsyncClient):  # type: ignore
        def __init__(self, *args, app=None, base_url="http://test", **kwargs):
            if app is not None:
                kwargs["transport"] = ASGITransport(app=app, raise_app_exceptions=False)
            super().__init__(*args, base_url=base_url, **kwargs)

    httpx.AsyncClient = _PatchedAsyncClient  # type: ignore
    sys.modules["httpx"].AsyncClient = _PatchedAsyncClient  # type: ignore
except ImportError:  # pragma: no cover
    pass
