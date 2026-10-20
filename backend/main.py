"""Vercel loads this module as `main:app`. Local dev uses `app.main:app` directly."""

from app.main import app

__all__ = ["app"]
