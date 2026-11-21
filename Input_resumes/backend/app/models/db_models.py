"""
Re-export database models for backward compatibility.
Primary models reside in backend.app.database.models.
"""
from backend.app.database.models import (
    Base, Candidate, Education, Employment, Publication, RuleResult, AuditLog,
    engine, SessionLocal, init_db
)

__all__ = [
    "Base", "Candidate", "Education", "Employment", "Publication", "RuleResult", "AuditLog",
    "engine", "SessionLocal", "init_db"
]
