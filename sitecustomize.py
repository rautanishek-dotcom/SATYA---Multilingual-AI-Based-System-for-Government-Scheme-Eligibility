"""Ensure the backend package directory is importable from the repo root.

This project historically imports modules like ``database`` and ``routes.auth``
as top-level modules. When verification runs from the repository root, Python
does not automatically place ``backend/`` on ``sys.path``. Importing this module
at interpreter startup preserves the existing module layout without forcing a
large-scale import rewrite.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"

if BACKEND.is_dir():
    backend_path = str(BACKEND)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
