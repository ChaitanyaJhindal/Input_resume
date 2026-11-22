import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.app.agents.orchestration_agent import orchestration_agent

sys.stdout.reconfigure(encoding='utf-8')

pdf_path = Path("Input_resumes/01-SUSHIL-CV.pdf (1).pdf")
print(f"Processing {pdf_path.name} with force_reprocess=True...")
profile = orchestration_agent.process_document(pdf_path, force_reprocess=True)

print("=== PIPELINE RESULT ===")
print("Name:", profile.name)
print("Highest Degree:", profile.education[0].normalized_degree if profile.education else "None")
print("Teaching Years:", profile.experience.teaching_years)
print("Research Years:", profile.experience.research_years)
print("Industry Years:", profile.experience.industry_years)
print("Total Years:", profile.experience.total_years)
print("Eligibility Status:", profile.screening.eligibility_status)
print("Overall Score:", profile.screening.overall_score)
print(f"Employment Count: {len(profile.employment)}")
for emp in profile.employment:
    print(f"  - [{emp.category.upper()}] {emp.title} at {emp.organization} ({emp.duration_years} yrs)")
