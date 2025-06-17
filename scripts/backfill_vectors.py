from __future__ import annotations

"""Bulk‐backfill existing ``videos`` rows with NV-Embed vectors.

This helper script scans for documents where ``content_features`` is **null**
(or missing) and updates them in batches using the Data API ``$vectorize``
operator.

Usage (module mode):
    python -m scripts.backfill_vectors [--dry-run] [--page-size N]

Environment / settings are taken from :pydata:`app.core.config.settings`.
"""

from dataclasses import dataclass
import argparse
import asyncio
import logging
import os
from typing import List, Dict, Any, Sequence

import httpx

from app.core.config import settings
from app.db.astra_client import get_table
from app.utils.text import clip_to_512_tokens

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

VIDEOS_TABLE_NAME = "videos"
PAGE_SIZE_DEFAULT = 100

# ---------------------------------------------------------------------------
# Dataclass helpers
# ---------------------------------------------------------------------------


@dataclass
class UpdateOp:  # noqa: D401 – simple container
    videoid: str
    vectorize_text: str

    def to_dict(self) -> Dict[str, Any]:  # noqa: D401
        return {
            "filter": {"videoid": self.videoid},
            "update": {
                "$set": {"content_features": {"$vectorize": self.vectorize_text}}
            },
        }


# ---------------------------------------------------------------------------
# Core backfill logic (async)
# ---------------------------------------------------------------------------


async def _fetch_batch(
    db_table, *, page_size: int, skip: int
) -> Sequence[Dict[str, Any]]:
    """Return at most *page_size* docs missing ``content_features`` starting at *skip*."""

    # Two filter strategies: explicit ``None`` or field absent.
    query_filter = {
        "$or": [{"content_features": None}, {"content_features": {"$exists": False}}]
    }

    find_kwargs = {
        "filter": query_filter,
        "limit": page_size,
    }
    if skip:
        find_kwargs["skip"] = skip

    cursor = db_table.find(**find_kwargs)

    # Collection cursors may be async or sync depending on driver version.  We
    # normalise to a list in either case.
    if hasattr(cursor, "to_list"):
        docs = await cursor.to_list()
    else:
        docs = cursor  # type: ignore[assignment]

    return docs


def _build_vectorize_text(doc: Dict[str, Any]) -> str:
    components: List[str] = []
    # Title / name
    if title := doc.get("name"):
        components.append(str(title))
    # Description
    if desc := doc.get("description"):
        components.append(str(desc))
    # Tags (set<text> stored as list on API side)
    if tags := doc.get("tags"):
        # Join by space for embedding – order is irrelevant
        components.append(" ".join(tags))

    raw = "\n".join(components)
    return clip_to_512_tokens(raw)


async def backfill_vectors(
    *, page_size: int = PAGE_SIZE_DEFAULT, dry_run: bool = False
):
    """Iterate through the *videos* table and populate missing vectors."""

    if not all([settings.ASTRA_DB_API_ENDPOINT, settings.ASTRA_DB_APPLICATION_TOKEN]):
        raise RuntimeError("Astra DB settings missing; cannot run backfill job.")

    db_table = await get_table(VIDEOS_TABLE_NAME)

    processed, updated = 0, 0
    skip = 0

    while True:
        batch = await _fetch_batch(db_table, page_size=page_size, skip=skip)
        if not batch:
            break

        ops: List[UpdateOp] = []
        for doc in batch:
            if not (vid := doc.get("videoid")):
                continue  # Safety guard for malformed rows
            text = _build_vectorize_text(doc)
            ops.append(UpdateOp(videoid=str(vid), vectorize_text=text))

        if ops:
            if dry_run:
                logger.info("[DRY-RUN] Would update %d documents", len(ops))
            else:
                _execute_update_many(ops)
                updated += len(ops)

        processed += len(batch)
        skip += len(batch)
        logger.info(
            "Processed %d (+%d) videos; vectors updated: %d",
            processed,
            len(batch),
            updated,
        )

    logger.info(
        "Backfill complete. Total processed: %d | updated: %d", processed, updated
    )


# ---------------------------------------------------------------------------
# REST call helper (sync)
# ---------------------------------------------------------------------------


def _execute_update_many(ops: Sequence[UpdateOp]):  # noqa: D401
    url = os.path.join(
        settings.ASTRA_DB_API_ENDPOINT.rstrip("/"),
        "collections",
        VIDEOS_TABLE_NAME,
        "updateMany",
    )
    headers = {
        "X-Cassandra-Token": settings.ASTRA_DB_APPLICATION_TOKEN,
        "Content-Type": "application/json",
    }
    payload = {"operations": [op.to_dict() for op in ops]}

    resp = httpx.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def _main():  # noqa: D401
    parser = argparse.ArgumentParser(
        description="Backfill videos.content_features vectors"
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=PAGE_SIZE_DEFAULT,
        help="Fetch page size from Data API (default: 100)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyse only; do not send updateMany requests",
    )

    args = parser.parse_args()

    asyncio.run(backfill_vectors(page_size=args.page_size, dry_run=args.dry_run))


if __name__ == "__main__":
    _main()
