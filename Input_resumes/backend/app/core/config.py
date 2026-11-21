"""
Configuration re-export for backward compatibility.
Primary settings live in backend.app.config.
"""
from backend.app.config import Settings, settings

__all__ = ["Settings", "settings"]
