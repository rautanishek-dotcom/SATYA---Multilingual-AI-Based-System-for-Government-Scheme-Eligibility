"""Compatibility package that exposes ``backend.document_intelligence``."""

from __future__ import annotations

from pathlib import Path

__path__ = [str(Path(__file__).resolve().parent.parent / "backend" / "document_intelligence")]
