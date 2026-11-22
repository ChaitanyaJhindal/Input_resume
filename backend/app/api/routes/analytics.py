from fastapi import APIRouter
from backend.app.database.repository import candidate_repo
from backend.app.groq.pool import groq_pool
from backend.app.pipelines.orchestrator import orchestrator
from backend.app.services.jev.jev_router import jev_router
from backend.app.services.screening_service import screening_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/overview")
def get_analytics_overview():
    """
    Computes aggregate metrics, degree distributions, experience brackets,
    rule pass rates, grounding quality, and decision telemetry for the recruiter dashboard.
    """
    discovered = orchestrator.discover_resumes()
    total_discovered = len(discovered)

    all_candidates, total_candidates = candidate_repo.list_candidates(limit=1000)

    # Status counts
    eligible_count = sum(1 for c in all_candidates if c.get("eligibility_status") == "eligible")
    needs_review_count = len(candidate_repo.get_review_queue())
    disqualified_count = sum(1 for c in all_candidates if c.get("eligibility_status") == "disqualified")
    uploaded_count = sum(1 for c in all_candidates if c.get("is_uploaded"))

    # Distributions
    degree_dist: dict[str, int] = {}
    institution_cat_dist: dict[str, int] = {}
    exp_dist = {"0-2 yrs": 0, "2-5 yrs": 0, "5-10 yrs": 0, "10+ yrs": 0}
    score_brackets = {"85-100%": 0, "70-84%": 0, "50-69%": 0, "0-49%": 0}
    grounding_brackets = {"High (90-100%)": 0, "Moderate (75-89%)": 0, "Low (<75%)": 0}

    configured_rules = screening_service.rules_config.get("rules", [])
    rule_stats: dict[str, dict] = {
        r.get("id", "UNKNOWN"): {
            "rule_id": r.get("id", "UNKNOWN"),
            "name": r.get("name", r.get("id", "UNKNOWN")),
            "passed": 0,
            "failed": 0,
            "total": 0,
            "is_mandatory": bool(r.get("is_mandatory", True)),
        }
        for r in configured_rules
    }

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

        score = float(c.get("overall_score") or 0.0)
        if score >= 85.0:
            score_brackets["85-100%"] += 1
        elif score >= 70.0:
            score_brackets["70-84%"] += 1
        elif score >= 50.0:
            score_brackets["50-69%"] += 1
        else:
            score_brackets["0-49%"] += 1

        gs = c.get("grounding_score")
        if gs is not None:
            gs_val = float(gs)
            if gs_val >= 0.90:
                grounding_brackets["High (90-100%)"] += 1
            elif gs_val >= 0.75:
                grounding_brackets["Moderate (75-89%)"] += 1
            else:
                grounding_brackets["Low (<75%)"] += 1

        for ev in c.get("rules_evaluated") or []:
            r_id = ev.get("rule_id")
            if not r_id:
                continue
            entry = rule_stats.setdefault(
                r_id,
                {
                    "rule_id": r_id,
                    "name": ev.get("name", r_id),
                    "passed": 0,
                    "failed": 0,
                    "total": 0,
                    "is_mandatory": bool(ev.get("is_mandatory", True)),
                },
            )
            entry["total"] += 1
            if ev.get("status") == "pass":
                entry["passed"] += 1
            else:
                entry["failed"] += 1

    rule_pass_rates = []
    for entry in rule_stats.values():
        total_r = entry["total"]
        pct = round((entry["passed"] / total_r) * 100.0, 1) if total_r > 0 else 0.0
        rule_pass_rates.append({
            **entry,
            "pass_rate_pct": pct,
        })

    avg_teaching_exp = round(total_teaching_exp / len(all_candidates), 1) if all_candidates else 0.0

    persisted_tele = candidate_repo.get_telemetry_and_latency_summary()
    live_tele = jev_router.get_telemetry()
    telemetry = {
        "deterministic_resolutions": max(persisted_tele["deterministic_resolutions"], live_tele.get("deterministic_resolutions", 0)),
        "jev_decision_calls": max(persisted_tele["jev_decision_calls"], live_tele.get("jev_decision_calls", 0)),
        "groq_api_calls": max(persisted_tele["groq_api_calls"], live_tele.get("groq_api_calls", 0)),
        "escalations": max(persisted_tele["escalations"], live_tele.get("escalations", 0)),
        "total_latency_ms": round(live_tele.get("total_latency_ms", 0.0), 2),
    }

    sorted_degrees = sorted(degree_dist.items(), key=lambda kv: kv[1], reverse=True)
    sorted_institutions = sorted(institution_cat_dist.items(), key=lambda kv: kv[1], reverse=True)

    return {
        "metrics": {
            "total_resumes": max(total_discovered, total_candidates),
            "source_resumes": total_discovered,
            "uploaded_resumes": uploaded_count,
            "processed": total_candidates,
            "eligible": eligible_count,
            "needs_review": needs_review_count,
            "disqualified": disqualified_count,
            "average_teaching_years": avg_teaching_exp,
            "average_processing_time_sec": persisted_tele["average_processing_time_sec"],
        },
        "distributions": {
            "degree": [{"name": k, "count": v} for k, v in sorted_degrees],
            "institution_category": [{"name": k, "count": v} for k, v in sorted_institutions],
            "experience": [{"bracket": k, "count": v} for k, v in exp_dist.items()],
            "rule_pass_rates": rule_pass_rates,
            "score_brackets": [{"bracket": k, "count": v} for k, v in score_brackets.items()],
            "grounding_brackets": [{"bracket": k, "count": v} for k, v in grounding_brackets.items()],
        },
        "telemetry": telemetry,
        "groq_pool": groq_pool.get_telemetry(),
    }
