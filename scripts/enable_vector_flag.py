from __future__ import annotations

"""Toggle the *VECTOR_SEARCH_ENABLED* flag and optionally trigger DB migration.

Usage (module mode):

    python -m scripts.enable_vector_flag           # Enable flag, run migration
    python -m scripts.enable_vector_flag --disable # Disable flag

The script works by rewriting the project's ``.env`` file in place. If the
flag line is missing it is appended.  A best-effort attempt is then made to
run the migrations via ``scripts.migrate`` (no-op if the module is absent).
"""

import argparse
import logging
import pathlib
import subprocess
import sys
import importlib


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# Project root is two levels up from this file (scripts/enable_vector_flag.py)
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


def _rewrite_env_file(enable: bool) -> None:  # noqa: D401
    """Update the .env file in-place to reflect *enable* state."""

    if not _ENV_FILE.exists():
        raise FileNotFoundError(
            ".env file not found. Aborting toggle of VECTOR_SEARCH_ENABLED."
        )

    lines = _ENV_FILE.read_text().splitlines(keepends=False)
    flag_written = False
    for i, line in enumerate(lines):
        if line.strip().startswith("VECTOR_SEARCH_ENABLED"):
            lines[i] = f"VECTOR_SEARCH_ENABLED={'true' if enable else 'false'}"
            flag_written = True
            break

    if not flag_written:
        # Append newline if file doesn't end with one
        if lines and lines[-1] and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append(f"VECTOR_SEARCH_ENABLED={'true' if enable else 'false'}")

    _ENV_FILE.write_text("\n".join(lines) + "\n")
    logger.info("VECTOR_SEARCH_ENABLED=%s written to %s", enable, _ENV_FILE)


def _run_migrations() -> None:  # noqa: D401
    """Attempt to execute migrations via scripts.migrate if present."""

    try:
        migrate_mod = importlib.import_module("scripts.migrate")
    except ModuleNotFoundError:
        logger.warning("scripts.migrate not found – skipping migration step.")
        return

    if hasattr(migrate_mod, "main"):
        logger.info("Running DB migrations via scripts.migrate.main() …")
        migrate_mod.main()  # type: ignore[attr-defined]
    elif hasattr(migrate_mod, "run"):
        logger.info("Running DB migrations via scripts.migrate.run() …")
        migrate_mod.run()  # type: ignore[attr-defined]
    else:
        # Fallback to module execution in subprocess to preserve CLI semantics
        logger.info("Running 'python -m scripts.migrate' as subprocess …")
        subprocess.run([sys.executable, "-m", "scripts.migrate"], check=False)


def main() -> None:  # noqa: D401 – entry point
    parser = argparse.ArgumentParser(description="Toggle VECTOR_SEARCH_ENABLED flag")
    parser.add_argument(
        "--disable",
        action="store_true",
        help="Disable vector search instead of enabling it",
    )
    parser.add_argument(
        "--skip-migration",
        action="store_true",
        help="Do not attempt to run DB migrations after toggling",
    )

    args = parser.parse_args()
    enable = not args.disable

    _rewrite_env_file(enable)

    if not args.skip_migration and enable:
        _run_migrations()


if __name__ == "__main__":  # pragma: no cover
    main()
