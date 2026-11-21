import sys
import os
import glob
import json
import time

sys.path.insert(0, os.path.abspath("."))
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
from backend.app.agents.orchestration_agent import orchestration_agent
from backend.app.repositories.candidate_repo import candidate_repo
from backend.app.database.models import init_db

init_db()

candidate_files = [
    "01-SUSHIL-CV.pdf (1).pdf",
    "Sourabh_Aggarwal_AOM-Resume_2026.pdf.pdf",
    "HanqingZhao_Curriculum-vitae.pdf.pdf",
    "Sagar_Baviskar_CV.pdf.pdf",
    "Resume_RS.pdf",
    "NeetiGuptaAcademicCV4.docx.pdf",
    "Vartika_Chandra_Saman_CV.pdf.pdf",
    "Dequn-Teng-CV37.pdf.pdf",
    "John-Sarfo-CV-4-1.pdf.pdf",
    "Kenneth_Reaves_Academic_CV2.docx (1).pdf",
    "VITAE_2026_Jeffrey-Thomas_academic_ent.doc (1).pdf",
    "Mudit K Agarwal_1 (1).pdf",
    "Dr Tushar Sharma Profile for Placement Department.pdf",
    "Suresh-AI-Professor-of-Practice-Resume-USA-Dayanandsagar.docx.pdf"
]

qualified_list = []
disqualified_list = []

for f in candidate_files:
    p = Path(f)
    if not p.exists():
        continue
    try:
        profile = orchestration_agent.process_document(p, force_reprocess=True)
        candidate_repo.save_profile(profile, is_uploaded=True)
        
        info = {
            "file": f,
            "name": profile.name,
            "status": profile.screening.eligibility_status,
            "score": profile.screening.overall_score,
            "degree": profile.education[0].normalized_degree if profile.education else "None",
            "institution": profile.education[0].institution if profile.education else "None",
            "teaching_years": profile.experience.teaching_years,
            "research_years": profile.experience.research_years,
            "publications": len(profile.research.publications),
            "teaching_roles": [f"{e.title} at {e.organization} ({e.duration_years}y)" for e in profile.employment if e.category == "teaching"]
        }
        
        if profile.screening.eligibility_status in ["eligible", "qualified"]:
            qualified_list.append(info)
            print(f" QUALIFIED: {info['name']} ({f}) - Score: {info['score']}, Teaching: {info['teaching_years']}y, Pubs: {info['publications']}")
        else:
            disqualified_list.append(info)
            reasons = [r.reason for r in profile.screening.rules_evaluated if r.status == "fail" and r.is_mandatory]
            print(f" Disqualified: {info['name']} ({f}) - Failed: {reasons}")
    except Exception as e:
        print(f"Error processing {f}: {e}")

print("\n" + "=" * 80)
print(f"RESULTS SUMMARY: {len(qualified_list)} QUALIFIED, {len(disqualified_list)} DISQUALIFIED")
print("=" * 80)
for q in qualified_list:
    print(f"\n* {q['name']} ({q['file']})")
    print(f"  - Degree: {q['degree']} from {q['institution']}")
    print(f"  - Teaching Experience: {q['teaching_years']} years")
    for r in q['teaching_roles'][:4]:
        print(f"    * {r}")
    print(f"  - Research Experience: {q['research_years']} years")
    print(f"  - Publications: {q['publications']}")
    print(f"  - Overall Score: {q['score']}/100")
