from fastapi import APIRouter
from backend.app.repositories.candidate_repo import candidate_repo
from backend.app.pipelines.orchestrator import orchestrator
from backend.app.services.jev.jev_router import jev_router

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/overview")
def get_analytics_overview():
    """
    Computes aggregate metrics, degree distributions, experience brackets,
    and decision telemetry for the recruiter dashboard.
    """
    discovered = orchestrator.discover_resumes()
    total_discovered = len(discovered)

    all_candidates, total_candidates = candidate_repo.list_candidates(limit=1000)

    # Status counts
    eligible_count = sum(1 for c in all_candidates if c.get("eligibility_status") == "eligible")
    needs_review_count = sum(1 for c in all_candidates if c.get("eligibility_status") == "needs_review" or c.get("review_status") == "Needs review")
    disqualified_count = sum(1 for c in all_candidates if c.get("eligibility_status") == "disqualified")

    # Distributions
    degree_dist = {}
    institution_cat_dist = {}
    exp_dist = {"0-2 yrs": 0, "2-5 yrs": 0, "5-10 yrs": 0, "10+ yrs": 0}

    total_teaching_exp = 0.0
    for c in all_candidates:
        deg = c.get("highest_degree") or "Unclassified"
        degree_dist[deg] = degree_dist.get(deg, 0) + 1

        cat = c.get("highest_institution_category") or "Other"
        institution_cat_dist[cat] = institution_cat_dist.get(cat, 0) + 1

        t_exp = c.get("teaching_years", 0.0)
        total_teaching_exp += t_exp
        if t_exp <= 2.0:
            exp_dist["0-2 yrs"] += 1
        elif t_exp <= 5.0:
            exp_dist["2-5 yrs"] += 1
        elif t_exp <= 10.0:
            exp_dist["5-10 yrs"] += 1
        else:
            exp_dist["10+ yrs"] += 1

    avg_teaching_exp = round(total_teaching_exp / len(all_candidates), 1) if all_candidates else 0.0

    telemetry = jev_router.get_telemetry()

    return {
        "metrics": {
            "total_resumes": total_discovered,
            "processed": total_candidates,
            "eligible": eligible_count,
            "needs_review": needs_review_count,
            "disqualified": disqualified_count,
            "average_teaching_years": avg_teaching_exp,
            "average_processing_time_sec": 1.8
        },
        "distributions": {
            "degree": [{"name": k, "count": v} for k, v in degree_dist.items()],
            "institution_category": [{"name": k, "count": v} for k, v in institution_cat_dist.items()],
            "experience": [{"bracket": k, "count": v} for k, v in exp_dist.items()]
        },
        "telemetry": telemetry
    }
