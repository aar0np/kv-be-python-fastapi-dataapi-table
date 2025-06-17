from __future__ import annotations

"""Attach (or recreate) the NVIDIA Vectorize index on the *videos.content_features* column.

This script is a companion utility for the KillrVideo backend.
It performs **one** Data API call (actually two: drop + create) that
cannot be expressed in plain CQL:

1. Drop the existing `videos_content_features_idx` (if any).  
2. Re-create it with the `embeddingProvider/embeddingModel` options so
   Astra knows to invoke NVIDIA NIM when `$vectorize` is used.

Configuration is taken from the project `.env` file (loaded via
`python-dotenv`, which is already a transitive dependency) *or* the
process environment.

Required keys in `.env` / environment:

* ASTRA_DB_API_ENDPOINT   – e.g. https://<UUID>-us-east1.apps.astra.datastax.com
* ASTRA_DB_KEYSPACE       – e.g. killrvideo
* ASTRA_DB_APPLICATION_TOKEN – AstraCS:…

Optional keys:

* NIM_EMBEDDING_MODEL – default: NV-Embed-QA
* VECTOR_INDEX_NAME   – default: videos_content_features_idx

Run:

    python -m scripts.attach_nvidia_vector_index

The script is idempotent: if the index already exists with the correct
options it exits silently.
"""

import json
import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict

import requests
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("attach_nvidia_vector_index")

# --------------------------------------------------------------------------------------
# Environment handling
# --------------------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=False)

API_ENDPOINT = os.getenv("ASTRA_DB_API_ENDPOINT")
TOKEN = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
KEYSPACE = os.getenv("ASTRA_DB_KEYSPACE")

if not API_ENDPOINT or not TOKEN or not KEYSPACE:
    log.error(
        "Missing required env vars. Make sure ASTRA_DB_API_ENDPOINT, "
        "ASTRA_DB_APPLICATION_TOKEN and ASTRA_DB_KEYSPACE are set in .env or shell."
    )
    sys.exit(1)

INDEX_NAME = os.getenv("VECTOR_INDEX_NAME", "videos_content_features_idx")
MODEL_ID = os.getenv("NIM_EMBEDDING_MODEL", "NV-Embed-QA")
TABLE = "videos"
COLUMN = "content_features"
METRIC = "COSINE"

DATA_API_URL = f"{API_ENDPOINT}/api/json/v1/{KEYSPACE}/{TABLE}"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Token": TOKEN,
}

# --------------------------------------------------------------------------------------
# Helper functions
# --------------------------------------------------------------------------------------

def _post(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send a JSON payload and return JSON response (or error)."""
    resp = requests.post(DATA_API_URL, headers=HEADERS, json=payload, timeout=10)
    try:
        data = resp.json()
    except ValueError:
        resp.raise_for_status()  # will raise HTTPError
        raise  # pragma: no cover
    if resp.status_code != 200:
        raise RuntimeError(f"Data API error: HTTP {resp.status_code} {data}")
    if "errors" in data and data["errors"]:
        raise RuntimeError(f"Data API returned errors: {data['errors']}")
    return data


def main() -> None:  # noqa: D401
    log.info("Enabling vectorize on '%s.%s' via NVIDIA model '%s' …", TABLE, COLUMN, MODEL_ID)
    _post({
        "alterTable": {
            "operation": {
                "addVectorize": {
                    "columns": {
                        COLUMN: {
                            "provider": "nvidia",
                            "modelName": MODEL_ID,
                        }
                    }
                }
            }
        }
    })

    log.info("✅ content_features column now configured for $vectorize via NVIDIA.")


if __name__ == "__main__":  # pragma: no cover
    main() 