"""Compatibility package that exposes ``backend.routes`` as ``routes``."""

from __future__ import annotations

from pathlib import Path

__path__ = [str(Path(__file__).resolve().parent.parent / "backend" / "routes")]
