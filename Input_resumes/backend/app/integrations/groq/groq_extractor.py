"""
Backward-compatibility re-export for GroqExtractor.
The primary implementation lives in backend.app.groq.extractor.
"""
from backend.app.groq.extractor import (
    EXTRACTION_SYSTEM_PROMPT,
    GroqExtractor,
    groq_extractor,
)

__all__ = ["EXTRACTION_SYSTEM_PROMPT", "GroqExtractor", "groq_extractor"]
