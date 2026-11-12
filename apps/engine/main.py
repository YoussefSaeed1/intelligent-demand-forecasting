"""Vercel entrypoint: the platform loads the top-level `app`."""

from engine_service.app import app

__all__ = ["app"]
