from __future__ import annotations

"""Central place to resolve the running application version.

Priority order:
1. If the package is installed (e.g. in Docker image) use the version
   recorded in its distribution metadata (importlib).
2. If not installed (editable/dev mode) fall back to the environment
   variable ``APP_VERSION`` if present.
3. Otherwise default to ``0.0.0-dev``.
"""

from importlib.metadata import PackageNotFoundError, version as pkg_version
import os

PACKAGE_NAME = "killrvideo-python-fastapi-backend"

try:
    __version__: str = pkg_version(PACKAGE_NAME)
except PackageNotFoundError:  # running in editable mode / source checkout
    __version__ = os.getenv("APP_VERSION", "0.0.0-dev")

__all__ = ["__version__", "PACKAGE_NAME"] 