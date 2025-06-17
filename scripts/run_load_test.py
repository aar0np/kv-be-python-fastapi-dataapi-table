from __future__ import annotations

"""Convenience wrapper to launch the semantic-search Locust test headless.

Example usage::

- Positional URL (recommended):

    python -m scripts.run_load_test https://staging.killrvideo.com \
        --users 200 --spawn-rate 20 --duration 5m

- Legacy flag form (still supported):

    python -m scripts.run_load_test --host https://staging.killrvideo.com
"""

import argparse
import subprocess
import sys
from pathlib import Path


DEFAULT_USERS = 200
DEFAULT_SPAWN_RATE = 20
DEFAULT_DURATION = "5m"


def main() -> None:  # noqa: D401 – entry point
    parser = argparse.ArgumentParser(description="Run Locust load test (headless)")
    parser.add_argument(
        "url",
        metavar="URL",
        help="Base URL of the KillrVideo deployment (e.g. https://staging.killrvideo.com)",
    )
    # Backwards-compat optional flag (not shown in usage)
    parser.add_argument("--host", dest="_host_legacy", help=argparse.SUPPRESS)
    parser.add_argument("--users", type=int, default=DEFAULT_USERS, help="Number of concurrent users (default: 200)")
    parser.add_argument("--spawn-rate", type=int, default=DEFAULT_SPAWN_RATE, help="User hatch rate per second (default: 20)")
    parser.add_argument("--duration", default=DEFAULT_DURATION, help="Test duration (Locust time format, default: 5m)")
    parser.add_argument(
        "--locust-file",
        default=str(Path("load/semantic_search.py")),
        help="Path to the Locust test file (default: load/semantic_search.py)",
    )

    args = parser.parse_args()

    cmd = [
        "locust",
        "-f",
        args.locust_file,
        "--headless",
        "-u",
        str(args.users),
        "-r",
        str(args.spawn_rate),
        "-t",
        args.duration,
        "--host",
        args._host_legacy if args._host_legacy else args.url,
    ]

    print("Running:", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)


if __name__ == "__main__":  # pragma: no cover
    main() 