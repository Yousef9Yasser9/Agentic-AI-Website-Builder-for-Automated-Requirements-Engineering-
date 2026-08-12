"""
Deterministic backend writers for generated FastAPI apps.

Canonical import path: ``generated_apps.generator.deterministic_backend``.
Implementation lives in ``_impl.py`` so an accidental empty sibling package
cannot shadow this module and break Build & Run seed imports.
"""

from generated_apps.generator.deterministic_backend._impl import (
    DETERMINISTIC_BACKEND_FILES,
    apply_deterministic_guard,
    entity_class_name,
    ensure_valid_models,
    make_jinja_env,
    render_deterministic_file,
    resource_name,
    slugify,
    write_deterministic_crud,
    write_deterministic_models,
    write_deterministic_schemas,
    write_deterministic_seed,
)

__all__ = [
    "DETERMINISTIC_BACKEND_FILES",
    "apply_deterministic_guard",
    "entity_class_name",
    "ensure_valid_models",
    "make_jinja_env",
    "render_deterministic_file",
    "resource_name",
    "slugify",
    "write_deterministic_crud",
    "write_deterministic_models",
    "write_deterministic_schemas",
    "write_deterministic_seed",
]
