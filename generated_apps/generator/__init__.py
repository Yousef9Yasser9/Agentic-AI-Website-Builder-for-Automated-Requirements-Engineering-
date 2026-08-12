"""Generated app engine public exports."""

from __future__ import annotations

__all__ = [
    "apply_deterministic_guard",
    "ensure_valid_models",
    "write_deterministic_crud",
    "write_deterministic_models",
    "write_deterministic_schemas",
    "write_deterministic_seed",
]


def __getattr__(name: str):
    if name in __all__:
        from generated_apps.generator import deterministic_backend

        return getattr(deterministic_backend, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
