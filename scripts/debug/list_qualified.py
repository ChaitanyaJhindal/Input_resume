import httpx
import sys

sys.stdout.reconfigure(encoding='utf-8')

try:
    res = httpx.get('http://127.0.0.1:8000/api/candidates?limit=100').json()
    candidates = res.get('candidates', [])
    eligible = [c for c in candidates if c.get('eligibility_status') in ['eligible', 'qualified']]
    print(f"TOTAL CANDIDATES EVALUATED: {len(candidates)}")
    print(f"TOTAL QUALIFIED CANDIDATES: {len(eligible)}\n")

    for i, c in enumerate(eligible, 1):
        print(f"{i}. Candidate: {c.get('name')}")
        print(f"   Resume File: {c.get('file_name')}")
        print(f"   Highest Degree: {c.get('highest_degree')} - {c.get('highest_institution')}")
        print(f"   Teaching Experience: {c.get('teaching_years')} years")
        print(f"   Research Experience: {c.get('research_years')} years")
        print(f"   Publications Count: {c.get('publications_count')}")
        print(f"   Overall Score: {c.get('overall_score')}/100")
        print(f"   Eligibility Status: {c.get('eligibility_status').upper()}")
        print("-" * 60)
except Exception as e:
    print("Error:", e)
