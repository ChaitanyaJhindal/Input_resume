import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import settings
from backend.app.models.db_models import init_db
from backend.app.pipelines.orchestrator import orchestrator
from backend.app.repositories.candidate_repo import candidate_repo
from backend.app.api.routes import resumes, candidates, screening, analytics, settings as settings_route

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("FacultyScreen.Main")

app = FastAPI(
    title="FacultyScreen API",
    description="AI-powered Professor Resume Screening & Curation Platform for University Recruitment",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local dev (Next.js at :3000)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(resumes.router, prefix="/api")
app.include_router(candidates.router, prefix="/api")
app.include_router(screening.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(settings_route.router, prefix="/api")

@app.on_event("startup")
def on_startup():
    logger.info("Initializing FacultyScreen database and services...")
    init_db()
    logger.info("FacultyScreen database ready. Waiting for user uploads or manual sync.")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": "FacultyScreen",
        "version": "1.0.0",
        "mock_mode": settings.mock_mode
    }

@app.get("/")
def root():
    return {
        "message": "Welcome to FacultyScreen - AI Professor Resume Screening & Curation Platform",
        "docs_url": "/docs",
        "api_v1": "/api"
    }
