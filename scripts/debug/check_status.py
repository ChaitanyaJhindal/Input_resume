import httpx
import sys

sys.stdout.reconfigure(encoding='utf-8')

res = httpx.get('http://127.0.0.1:8000/api/candidates?limit=15').json()
print(f"Total candidates in DB: {res['total']}")
for c in res.get('candidates', [])[:10]:
    t_exp = c.get('teaching_years', 0)
    r_exp = c.get('research_years', 0)
    tot_exp = c.get('total_years', 0)
    inst = c.get('highest_institution') or 'N/A'
    deg = c.get('highest_degree') or 'N/A'
    status = c.get('eligibility_status', 'unknown').upper()
    print(f"- {c.get('name')}: Teaching={t_exp}y | Research={r_exp}y | Total={tot_exp}y | Degree: {deg} ({inst}) | Status: {status}")
