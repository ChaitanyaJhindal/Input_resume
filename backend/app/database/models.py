import json
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, UniqueConstraint, create_engine, event, text
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
    administrative_years = Column(Float, default=0.0)
    total_years = Column(Float, default=0.0)

    publications_count = Column(Integer, default=0)

    eligibility_status = Column(String(32), default="needs_review", index=True)  # eligible, needs_review, disqualified
    overall_score = Column(Float, default=0.0)
    confidence = Column(Float, default=0.9)
    review_status = Column(String(64), default="Automatically processed", index=True)
    review_notes = Column(Text, nullable=True)
    reviewer_verdict = Column(String(64), nullable=True)

    processing_time_seconds = Column(Float, default=0.0)
    page_count = Column(Integer, default=1)
    groq_api_calls = Column(Integer, default=0)
    jev_decision_calls = Column(Integer, default=0)
    deterministic_resolutions = Column(Integer, default=0)
    escalations = Column(Integer, default=0)
    grounding_score = Column(Float, default=1.0)
    profile_extras_json = Column(Text, nullable=True)

    courses_taught_count = Column(Integer, default=0)
    has_google_scholar = Column(Boolean, default=False)
    has_orcid = Column(Boolean, default=False)
    external_citations = Column(Integer, nullable=True)
    external_h_index = Column(Integer, nullable=True)
    academic_links_json = Column(Text, nullable=True)
    external_verification_json = Column(Text, nullable=True)

    file_name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_hash = Column(String(64), nullable=False)
    is_uploaded = Column(Boolean, default=False, index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

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
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    candidate = relationship("Candidate", back_populates="audit_logs")


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    department = Column(String(255), nullable=True)
    level = Column(String(128), nullable=True)
    role_archetype = Column(String(64), default="balanced")
    raw_text = Column(Text, nullable=False)
    file_name = Column(String(255), nullable=True)
    file_path = Column(Text, nullable=True)
    parsed_spec_json = Column(Text, nullable=False)
    weights_json = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    evaluations = relationship("JDEvaluation", back_populates="job_description", cascade="all, delete-orphan")


class JDEvaluation(Base):
    __tablename__ = "jd_evaluations"
    __table_args__ = (UniqueConstraint("jd_id", "candidate_id", name="uq_jd_candidate"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    jd_id = Column(String(64), ForeignKey("job_descriptions.id"), nullable=False, index=True)
    candidate_id = Column(String(64), ForeignKey("candidates.id"), nullable=False, index=True)

    dynamic_score = Column(Float, default=0.0, index=True)
    recommendation_tier = Column(String(64), default="conditional_review", index=True)
    confidence = Column(Float, default=0.85)
    grounding_score = Column(Float, default=1.0)

    dimension_scores_json = Column(Text, nullable=False)
    requirement_matrix_json = Column(Text, nullable=False)
    compensating_strengths_json = Column(Text, nullable=True)
    standout_highlights_json = Column(Text, nullable=True)
    executive_brief = Column(Text, nullable=True)
    interview_probes_json = Column(Text, nullable=True)

    approval_status = Column(String(64), default="pending", index=True)
    approval_notes = Column(Text, nullable=True)
    approved_by = Column(String(128), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    evaluated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    job_description = relationship("JobDescription", back_populates="evaluations")
    candidate = relationship("Candidate")

# Database Engine & Session
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _configure_sqlite_pragmas(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    migrations = [
        "ALTER TABLE candidates ADD COLUMN is_uploaded BOOLEAN DEFAULT 0;",
        "ALTER TABLE candidates ADD COLUMN administrative_years FLOAT DEFAULT 0.0;",
        "ALTER TABLE candidates ADD COLUMN processing_time_seconds FLOAT DEFAULT 0.0;",
        "ALTER TABLE candidates ADD COLUMN page_count INTEGER DEFAULT 1;",
        "ALTER TABLE candidates ADD COLUMN groq_api_calls INTEGER DEFAULT 0;",
        "ALTER TABLE candidates ADD COLUMN jev_decision_calls INTEGER DEFAULT 0;",
        "ALTER TABLE candidates ADD COLUMN deterministic_resolutions INTEGER DEFAULT 0;",
        "ALTER TABLE candidates ADD COLUMN escalations INTEGER DEFAULT 0;",
        "ALTER TABLE candidates ADD COLUMN grounding_score FLOAT DEFAULT 1.0;",
        "ALTER TABLE candidates ADD COLUMN profile_extras_json TEXT;",
        "ALTER TABLE candidates ADD COLUMN courses_taught_count INTEGER DEFAULT 0;",
        "ALTER TABLE candidates ADD COLUMN has_google_scholar BOOLEAN DEFAULT 0;",
        "ALTER TABLE candidates ADD COLUMN has_orcid BOOLEAN DEFAULT 0;",
        "ALTER TABLE candidates ADD COLUMN external_citations INTEGER;",
        "ALTER TABLE candidates ADD COLUMN external_h_index INTEGER;",
        "ALTER TABLE candidates ADD COLUMN academic_links_json TEXT;",
        "ALTER TABLE candidates ADD COLUMN external_verification_json TEXT;",
    ]
    for stmt in migrations:
        try:
            with engine.connect() as conn:
                conn.execute(text(stmt))
                conn.commit()
        except Exception:
            pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
