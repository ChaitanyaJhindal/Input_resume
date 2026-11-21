.PHONY: help install test test-unit test-integration run-backend run-frontend process-all clean

help:
	@echo "FacultyScreen Commands:"
	@echo "  make install           - Install python and web dependencies"
	@echo "  make test              - Run pytest on unit and integration suites"
	@echo "  make run-backend       - Start FastAPI uvicorn server on :8000"
	@echo "  make run-frontend      - Start Next.js development server on :3000"
	@echo "  make process-all       - Process all discovered resumes through pipeline"

install:
	uv pip install -e .
	cd apps/web && npm install

test:
	python -m pytest tests/

test-unit:
	python -m pytest tests/unit/

test-integration:
	python -m pytest tests/integration/

run-backend:
	python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

run-frontend:
	cd apps/web && npm run dev

process-all:
	python -c "from backend.app.pipelines.orchestrator import orchestrator; orchestrator.process_all_resumes()"
