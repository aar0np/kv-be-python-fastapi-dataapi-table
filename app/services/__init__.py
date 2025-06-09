"""Service layer package initializer.

This re-exports individual domain services so that callers can simply
``from app.services import user_service, video_service``.
"""

from importlib import import_module
from types import ModuleType
from typing import TYPE_CHECKING

# Lazily import modules to avoid circular dependencies where possible.

__all__ = [
    "user_service",
    "video_service",
    "recommendation_service",
    "comment_service",
    "flag_service",
]

if TYPE_CHECKING:
    # During type checking we want the actual modules.
    from . import user_service as user_service  # noqa: F401
    from . import video_service as video_service  # noqa: F401
    from . import recommendation_service as recommendation_service  # noqa: F401
    from . import comment_service as comment_service  # noqa: F401
    from . import flag_service as flag_service  # noqa: F401
else:
    # At runtime perform the import lazily to keep import graph lighter.
    def __getattr__(name: str) -> ModuleType:  # noqa: D401
        if name in __all__:
            module = import_module(f"app.services.{name}")
            globals()[name] = module
            return module
        raise AttributeError(name)
