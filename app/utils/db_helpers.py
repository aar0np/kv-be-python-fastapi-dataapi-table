from __future__ import annotations

"""Utility helpers for interacting with the Astra Data API tables in a way that
is agnostic to *table* vs. *collection* quirks.

At the time of writing the Data API only supports `countDocuments` on
**collections**.  Invoking the command on a **table** results in a
``DataAPIResponseException`` with error code ``UNSUPPORTED_TABLE_COMMAND``.

`safe_count` wraps the call and transparently falls back to a supplied
client-side count (typically `len(docs)` fetched earlier). This lets service
layers share the same pagination logic regardless of the underlying storage
object.
"""

from typing import Any, Dict

from astrapy.exceptions.data_api_exceptions import DataAPIResponseException  # type: ignore

__all__ = ["safe_count"]


async def safe_count(
    db_table,
    *,
    query_filter: Dict[str, Any],
    fallback_len: int,
) -> int:
    """Return the number of rows matching *query_filter*.

    If the backing object is a **table** (where ``countDocuments`` is not
    supported) the function silently returns *fallback_len* instead of raising
    an exception.  The same applies to stub collections used in unit-tests.
    """

    try:
        return await db_table.count_documents(filter=query_filter, upper_bound=10**9)
    except (TypeError, DataAPIResponseException) as exc:  # pragma: no cover – fallback
        if isinstance(exc, DataAPIResponseException) and "UNSUPPORTED_TABLE_COMMAND" not in str(exc):
            # An unexpected Data API error – surface to caller.
            raise
        return fallback_len 