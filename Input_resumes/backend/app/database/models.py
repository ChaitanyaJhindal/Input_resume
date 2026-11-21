import json
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, create_engine, text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from backend.app.config import settings

Base = declarative_base()

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(String(64), primary_key=True, index=True)  # cand_...
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(64), nullable=True)
    location = Column(String(255), nullable=True)
    current_designation = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)

    highest_degree = Column(String(128), nullable=True, index=True)
    highest_institution = Column(String(255), nullable=True)
    highest_institution_category = Column(String(64), nullable=True, index=True)
    institution_tier = Column(String(64), nullable=True)

    teaching_years = Column(Float, default=0.0)
    research_years = Column(Float, default=0.0)
    industry_years = Column(Float, default=0.0)
    total_years = Column(Float, default=0.0)

    publications_count = Column(Integer, default=0)

    eligibility_status = Column(String(32), default="needs_review", index=True)  # eligible, needs_review, disqualified
    overall_score = Column(Float, default=0.0)
    confidence = Column(Float, default=0.9)
    review_status = Column(String(64), default="Automatically processed", index=True)
    review_notes = Column(Text, nullable=True)
    reviewer_verdict = Column(String(64), nullable=True)

    file_name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_hash = Column(String(64), nullable=False)
    is_uploaded = Column(Boolean, default=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    educations = relationship("Education", back_populates="candidate", cascade="all, delete-orphan")
    employments = relationship("Employment", back_populates="candidate", cascade="all, delete-orphan")
    publications = relationship("Publication", back_populates="candidate", cascade="all, delete-orphan")
    rule_results = relationship("RuleResult", back_populates="candidate", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="candidate", cascade="all, delete-orphan")

class Education(Base):
    __tablename__ = "education"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String(64), ForeignKey("candidates.id"), nullable=False, index=True)
    degree = Column(String(255), nullable=False)
    normalized_degree = Column(String(128), nullable=False)
    field = Column(String(255), nullable=True)
    institution = Column(String(255), nullable=False)
    institution_normalized = Column(String(255), nullable=True)
    institution_category = Column(String(64), nullable=True)
    institution_tier = Column(String(64), nullable=True)
    graduation_year = Column(Integer, nullable=True)
    confidence = Column(Float, default=0.9)
    evidence = Column(Text, nullable=True)
    source_page = Column(Integer, default=1)

    candidate = relationship("Candidate", back_populates="educations")

class Employment(Base):
    __tablename__ = "employment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String(64), ForeignKey("candidates.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    organization = Column(String(255), nullable=False)
    category = Column(String(64), default="teaching")  # teaching, research, industry, administrative
    start_date = Column(String(64), nullable=True)
    end_date = Column(String(64), nullable=True)
    duration_years = Column(Float, default=0.0)
    is_current = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)

    candidate = relationship("Candidate", back_populates="employments")

class Publication(Base):
    __tablename__ = "publications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String(64), ForeignKey("candidates.id"), nullable=False, index=True)
    title = Column(Text, nullable=False)
    venue = Column(String(255), nullable=True)
    year = Column(Integer, nullable=True)
    doi = Column(String(128), nullable=True)
    indexed = Column(String(128), nullable=True)
    evidence = Column(Text, nullable=True)

    candidate = relationship("Candidate", back_populates="publications")

class RuleResult(Base):
    __tablename__ = "rule_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String(64), ForeignKey("candidates.id"), nullable=False, index=True)
    rule_id = Column(String(64), nullable=False)
    rule_name = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False)  # pass, fail, unknown
    reason = Column(Text, nullable=False)
    evidence = Column(Text, nullable=True)
    confidence = Column(Float, default=0.95)
    is_mandatory = Column(Boolean, default=True)
    weight = Column(Integer, default=20)

    candidate = relationship("Candidate", back_populates="rule_results")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String(64), ForeignKey("candidates.id"), nullable=True, index=True)
    action = Column(String(128), nullable=False)  # e.g., INGESTED, REVIEWED, RE_SCREENED
    actor = Column(String(128), default="system")
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="audit_logs")

# Database Engine & Session
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE candidates ADD COLUMN is_uploaded BOOLEAN DEFAULT 0;"))
            conn.commit()
    except Exception:
        pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
