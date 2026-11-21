import sys
import os
import json
import time
sys.path.insert(0, os.path.abspath("."))
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
from backend.app.agents.orchestration_agent import orchestration_agent
from backend.app.repositories.candidate_repo import candidate_repo
from backend.app.database.models import init_db
import httpx

init_db()

resumes_to_test = [
    "01-SUSHIL-CV.pdf (1).pdf",
    "Sourabh_Aggarwal_AOM-Resume_2026.pdf.pdf",
    "Suresh-AI-Professor-of-Practice-Resume-USA-Dayanandsagar.docx.pdf",
    "HanqingZhao_Curriculum-vitae.pdf.pdf",
    "Dr Tushar Sharma Profile for Placement Department.pdf"
]

print("=" * 80)
print("FACULTYSCREEN VERIFICATION PIPELINE: 5 REPRESENTATIVE RESUMES")
print("=" * 80)

results = []

for filename in resumes_to_test:
    file_path = Path(filename)
    if not file_path.exists():
        print(f"File not found: {filename}")
        continue

    print(f"\n>>> Processing: {filename} ...")
    start_t = time.time()
    profile = orchestration_agent.process_document(file_path, force_reprocess=True)
    candidate_repo.save_profile(profile, is_uploaded=True)
    elapsed = round(time.time() - start_t, 2)

    top_degree = profile.education[0].normalized_degree if profile.education else "N/A"
    top_inst = profile.education[0].institution if profile.education else "N/A"

    teaching_roles = [e for e in profile.employment if e.category == "teaching"]

    cand_summary = {
        "filename": filename,
        "name": profile.name,
        "highest_degree": top_degree,
        "institution": top_inst,
        "teaching_years": profile.experience.teaching_years,
        "research_years": profile.experience.research_years,
        "industry_years": profile.experience.industry_years,
        "admin_years": profile.experience.administrative_years,
        "total_years": profile.experience.total_years,
        "teaching_roles_count": len(teaching_roles),
        "teaching_roles": [f"{r.title} at {r.organization} ({r.duration_years}y)" for r in teaching_roles],
        "eligibility_status": profile.screening.eligibility_status,
        "overall_score": profile.screening.overall_score,
        "processing_time": elapsed
    }
    results.append(cand_summary)

    print(f"  ✓ Processed in {elapsed}s")
    print(f"    Name: {cand_summary['name']}")
    print(f"    Highest Degree: {cand_summary['highest_degree']} ({cand_summary['institution']})")
    print(f"    Teaching Exp: {cand_summary['teaching_years']} yrs ({len(teaching_roles)} roles)")
    for tr in cand_summary['teaching_roles'][:3]:
        print(f"       • {tr}")
    print(f"    Research Exp: {cand_summary['research_years']} yrs | Industry: {cand_summary['industry_years']} yrs | Total: {cand_summary['total_years']} yrs")
    print(f"    Status: {cand_summary['eligibility_status'].upper()} | Score: {cand_summary['overall_score']}")

# Now verify via API endpoint
print("\n" + "=" * 80)
print("VERIFYING API ENDPOINT /api/candidates...")
print("=" * 80)
try:
    resp = httpx.get("http://127.0.0.1:8000/api/candidates?limit=10")
    if resp.status_code == 200:
        api_data = resp.json()
        print(f"API Returned {len(api_data.get('candidates', []))} candidates:")
        for c in api_data.get("candidates", [])[:5]:
            print(f"  - {c.get('name')}: Teaching={c.get('teaching_years')}y, Research={c.get('research_years')}y, Status={c.get('eligibility_status')}")
    else:
        print(f"API returned status {resp.status_code}")
except Exception as e:
    print(f"API query note: {e}")

print("\n" + "=" * 80)
print("SUMMARY JSON:")
print(json.dumps(results, indent=2))
