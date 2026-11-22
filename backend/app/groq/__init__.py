"""
Groq LLM & Multimodal Vision package:
- pool: Distributed round-robin API key pool with automatic 429 failover.
- extractor: PDF/multimodal document parsing with real fact extraction.
"""
from backend.app.groq.pool import GroqKeyPool, groq_pool
from backend.app.groq.extractor import GroqExtractor, groq_extractor

__all__ = [
    "GroqKeyPool",
    "groq_pool",
    "GroqExtractor",
    "groq_extractor",
]
