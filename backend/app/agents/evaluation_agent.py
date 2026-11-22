import json
import logging
import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.app.config import config_manager, settings
from backend.app.groq.pool import groq_pool
from backend.app.schemas.jd import (
    CandidateJDEvaluation,
    CompensatingStrength,
    DimensionScores,
    JDWeights,
    JobDescriptionSpec,
    RecommendationTier,
    RequirementMatch,
)
from backend.app.schemas.resume import NotableHighlight, ResumeProfile
from backend.app.services.education_service import EducationService
from backend.app.services.validation_service import ValidationService
from backend.app.utils.json_utils import parse_llm_json, safe_float, safe_str_list

logger = logging.getLogger("FacultyScreen.DynamicEvaluationAgent")

_TOKEN_RE = re.compile(r"[a-z0-9]{2,}")
_SEMANTIC_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "must", "have", "has",
    "years", "year", "yrs", "minimum", "least", "experience", "required",
    "preferred", "strong", "equivalent", "excellence", "role", "position",
    "candidate", "professor", "faculty", "practice", "assistant", "associate",
    "department", "school", "university", "college", "degree", "hold", "holds",
    "demonstrated", "proven", "ability", "relevant", "field", "discipline",
}


class DynamicEvaluationAgent:
    """
    Holistic JD-driven candidate evaluator.
    Combines deterministic/semantic alignment signals with committee-style LLM evaluation
    (with deterministic fallback in mock/offline mode) and a strict grounding gate.
    Scores can be recalculated instantaneously when JD weights change without re-calling Groq.
    """

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [t for t in _TOKEN_RE.findall((text or "").lower()) if t not in _SEMANTIC_STOPWORDS]

    @classmethod
    def _semantic_similarity(cls, query_text: str, candidate_text: str) -> float:
        q_tokens = cls._tokenize(query_text)
        c_tokens = cls._tokenize(candidate_text)
        if not q_tokens or not c_tokens:
            return 0.0
        q_counts = Counter(q_tokens)
        c_counts = Counter(c_tokens)
        intersection = set(q_counts.keys()) & set(c_counts.keys())
        dot = sum(q_counts[t] * c_counts[t] for t in intersection)
        q_norm = math.sqrt(sum(v * v for v in q_counts.values()))
        c_norm = math.sqrt(sum(v * v for v in c_counts.values()))
        if q_norm == 0 or c_norm == 0:
            return 0.0
        cosine = dot / (q_norm * c_norm)
        recall = len(intersection) / max(1, len(set(q_tokens)))
        return round(min(100.0, (0.30 * cosine + 0.70 * recall) * 100.0), 1)

    @staticmethod
    def _build_candidate_corpus(profile: ResumeProfile) -> str:
        parts: List[str] = [
            profile.name or "",
            profile.current_designation or "",
            profile.summary or "",
            f"{profile.experience.total_years} years total {profile.experience.teaching_years} years teaching "
            f"{profile.experience.research_years} years research {profile.experience.industry_years} years industry "
            f"{profile.experience.administrative_years} years administrative",
        ]
        for edu in profile.education:
            parts.extend([edu.degree, edu.normalized_degree, edu.field or "", edu.institution_normalized or edu.institution, edu.thesis_title or ""])
        for emp in profile.employment:
            parts.extend([emp.title, emp.organization, emp.category, emp.description or ""])
        for crs in profile.courses_taught:
            parts.extend([crs.course_name, crs.course_code or "", crs.level, crs.institution or ""])
        parts.extend(profile.teaching_interests)
        parts.extend(profile.skills)
        parts.extend(profile.awards)
        parts.extend(profile.certifications)
        parts.extend(profile.academic_service)
        for pub in profile.research.publications:
            parts.extend([pub.title, pub.venue or ""])
        parts.extend(profile.research.research_domains)
        for pat in profile.research.patents:
            parts.append(str(pat.get("title") or ""))
        for rp in profile.research.research_projects:
            parts.append(str(rp.get("title") or ""))
        for hl in profile.notable_highlights:
            parts.extend([hl.title, hl.impact or ""])
        return " ".join(p for p in parts if p)

    @classmethod
    def _compute_pre_signals(cls, jd: JobDescriptionSpec, profile: ResumeProfile) -> Dict[str, Any]:
        corpus = cls._build_candidate_corpus(profile)
        focused_domains = " ".join(jd.required_domains + jd.preferred_courses)
        jd_domain_text = focused_domains if focused_domains.strip() else " ".join([
            jd.title,
            jd.summary or "",
            " ".join(r.label for r in jd.requirements),
        ])
        semantic_score = cls._semantic_similarity(jd_domain_text, corpus)

        top_edu = EducationService.select_highest_education(profile.education)
        top_deg = top_edu.normalized_degree if top_edu else "Other"

        teaching_base = min(65.0, profile.experience.teaching_years * 16.0)
        courses_bonus = min(25.0, len(profile.courses_taught) * 12.0)
        sup_count = (
            profile.supervision.phd_completed * 2
            + profile.supervision.phd_ongoing
            + profile.supervision.masters_guided
        )
        sup_bonus = min(15.0, sup_count * 4.0)
        teaching_fit = round(min(100.0, teaching_base + courses_bonus + sup_bonus), 1)

        pub_score = min(40.0, len(profile.research.publications) * 10.0)
        grant_score = min(25.0, len(profile.research.research_projects) * 15.0)
        patent_score = min(25.0, len(profile.research.patents) * 15.0)
        ext_h = profile.external_verification.h_index if profile.external_verification else None
        ext_bonus = min(20.0, (ext_h or 0) * 3.0)
        applied_impact_bonus = min(20.0, profile.experience.industry_years * 2.5) if jd.allow_compensating_strengths else 0.0
        research_impact = round(min(100.0, pub_score + grant_score + patent_score + ext_bonus + applied_impact_bonus), 1)

        alt_score = min(
            100.0,
            min(45.0, profile.experience.industry_years * 6.0)
            + min(25.0, profile.experience.administrative_years * 8.0)
            + min(15.0, len(profile.awards) * 10.0)
            + min(20.0, (len(profile.certifications) + len(profile.research.patents)) * 10.0),
        )

        return {
            "highest_degree": top_deg,
            "highest_institution": (top_edu.institution_normalized or top_edu.institution) if top_edu else None,
            "domain_semantic_fit": semantic_score,
            "teaching_fit": teaching_fit,
            "research_and_impact": research_impact,
            "alternative_strength_signal": round(alt_score, 1),
            "teaching_years": profile.experience.teaching_years,
            "research_years": profile.experience.research_years,
            "industry_years": profile.experience.industry_years,
            "administrative_years": profile.experience.administrative_years,
            "publications_count": len(profile.research.publications),
            "grants_count": len(profile.research.research_projects),
            "patents_count": len(profile.research.patents),
            "courses_taught_count": len(profile.courses_taught),
        }

    @staticmethod
    def recompute_composite_and_tier(
        dimension_scores: DimensionScores,
        weights: JDWeights,
        requirement_matrix: List[RequirementMatch],
        allow_compensating_strengths: bool = True,
    ) -> Tuple[float, RecommendationTier]:
        w_sum = (
            max(0.0, weights.requirement_fit)
            + max(0.0, weights.domain_semantic_fit)
            + max(0.0, weights.teaching_fit)
            + max(0.0, weights.research_and_impact)
            + max(0.0, weights.alternative_strength_credit)
        )
        if w_sum <= 0:
            w_sum = 1.0

        composite = (
            dimension_scores.requirement_fit * max(0.0, weights.requirement_fit)
            + dimension_scores.domain_semantic_fit * max(0.0, weights.domain_semantic_fit)
            + dimension_scores.teaching_fit * max(0.0, weights.teaching_fit)
            + dimension_scores.research_and_impact * max(0.0, weights.research_and_impact)
            + dimension_scores.alternative_strength_credit * max(0.0, weights.alternative_strength_credit)
        ) / w_sum
        composite = round(max(0.0, min(100.0, composite)), 1)

        eval_cfg = config_manager.get_evaluation_config()
        strong_th = float(eval_cfg["strong_match_threshold"])
        alt_th = float(eval_cfg["alternative_fit_threshold"])
        cond_th = float(eval_cfg["conditional_threshold"])

        has_compensated = any(r.status == "compensated" for r in requirement_matrix)
        strict_must_failed = any(
            r.priority == "must_have" and r.status == "gap"
            for r in requirement_matrix
        )

        if has_compensated and allow_compensating_strengths and composite >= alt_th:
            tier: RecommendationTier = "strong_alternative_fit"
        elif not strict_must_failed and composite >= strong_th:
            tier = "strong_match"
        elif composite >= cond_th:
            tier = "conditional_review"
        else:
            tier = "low_alignment"

        return composite, tier

    @classmethod
    def _deterministic_evaluate(
        cls,
        jd: JobDescriptionSpec,
        profile: ResumeProfile,
        pre: Dict[str, Any],
    ) -> CandidateJDEvaluation:
        corpus = cls._build_candidate_corpus(profile)
        top_deg = pre["highest_degree"]
        req_matches: List[RequirementMatch] = []
        comp_strengths: List[CompensatingStrength] = []

        earned_weight = 0.0
        total_weight = sum(max(1, r.weight) for r in jd.requirements) or 1

        # Build natural grounded alternative evidence strictly citing actual CV records
        alt_pieces: List[str] = []
        ind_roles = [e for e in profile.employment if e.category == "industry"]
        if ind_roles:
            alt_pieces.append(f"{ind_roles[0].title} at {ind_roles[0].organization} ({profile.experience.industry_years} years industry)")
        elif profile.experience.industry_years >= 2.0:
            alt_pieces.append(f"{profile.experience.industry_years} years industry")
        if profile.research.patents:
            alt_pieces.append(str(profile.research.patents[0].get("title") or "Patent"))
        if profile.research.research_projects:
            alt_pieces.append(str(profile.research.research_projects[0].get("title") or "Research Project"))
        if profile.awards:
            alt_pieces.append(profile.awards[0])
        if profile.courses_taught:
            alt_pieces.append(profile.courses_taught[0].course_name)

        for req in jd.requirements:
            low_lbl = req.label.lower()
            status: str = "gap"
            score = 20.0
            evidence: Optional[str] = None
            rationale = ""

            if req.category == "qualification":
                wants_phd = any(k in low_lbl for k in ("phd", "ph.d", "doctorate", "doctoral"))
                wants_masters = any(k in low_lbl for k in ("master", "m.tech", "mba", "pg"))
                if wants_phd and top_deg in {"PhD / Doctorate", "Postdoctoral"}:
                    status, score = "met", 100.0
                    evidence = pre["highest_institution"] or top_deg
                    rationale = f"Holds {top_deg} matching doctoral requirement."
                elif wants_phd and top_deg == "PhD (In Progress)":
                    status, score = "partially_met", 65.0
                    evidence = pre["highest_institution"] or top_deg
                    rationale = "Doctoral degree currently in progress."
                elif wants_masters and top_deg in {"PhD / Doctorate", "Postdoctoral", "Postgraduate / Masters"}:
                    status, score = "met", 100.0
                    evidence = top_deg
                    rationale = f"Qualification ({top_deg}) satisfies postgraduate criterion."
                elif not wants_phd and not wants_masters and top_deg != "Other":
                    status, score = "met", 90.0
                    evidence = top_deg
                    rationale = f"Holds recognized degree ({top_deg})."
                elif (
                    jd.allow_compensating_strengths
                    and req.strictness != "strict"
                    and alt_pieces
                    and pre["alternative_strength_signal"] >= 35.0
                ):
                    status, score = "compensated", 74.0
                    evidence = "; ".join(alt_pieces[:3])
                    rationale = "Direct degree criterion not met, offset by substantial verified alternative experience/achievements."
                    comp_strengths.append(
                        CompensatingStrength(
                            missed_requirement=req.label,
                            compensating_evidence=evidence,
                            rationale=rationale,
                            strength_level="strong" if pre["alternative_strength_signal"] >= 60 else "moderate",
                        )
                    )
                else:
                    rationale = f"Highest verified qualification is {top_deg}."

            elif req.category in {"experience", "teaching", "research", "leadership"}:
                num_match = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)", low_lbl)
                req_years = float(num_match.group(1)) if num_match else 1.0
                if req.category == "teaching":
                    actual_y = profile.experience.teaching_years
                elif req.category == "research":
                    actual_y = max(profile.experience.research_years, float(len(profile.research.publications)))
                elif req.category == "leadership":
                    actual_y = profile.experience.administrative_years
                else:
                    actual_y = profile.experience.total_years

                if actual_y >= req_years:
                    status, score = "met", 100.0
                    matching_roles = [e for e in profile.employment if e.category == req.category]
                    evidence = (
                        f"{matching_roles[0].title} at {matching_roles[0].organization}"
                        if matching_roles
                        else f"{actual_y} years {req.category}"
                    )
                    rationale = f"Meets or exceeds target ({actual_y} vs {req_years})."
                elif actual_y >= req_years * 0.5 and actual_y > 0:
                    status, score = "partially_met", 65.0
                    evidence = f"{actual_y} years {req.category}"
                    rationale = f"Partial alignment ({actual_y} vs {req_years} target)."
                elif (
                    jd.allow_compensating_strengths
                    and req.strictness != "strict"
                    and alt_pieces
                    and pre["alternative_strength_signal"] >= 40.0
                ):
                    status, score = "compensated", 70.0
                    evidence = "; ".join(alt_pieces[:3])
                    rationale = "Compensated by strong adjacent professional or scholarly record."
                    comp_strengths.append(
                        CompensatingStrength(
                            missed_requirement=req.label,
                            compensating_evidence=evidence,
                            rationale=rationale,
                            strength_level="moderate",
                        )
                    )
                else:
                    rationale = f"Recorded {req.category} signal ({actual_y}) below target ({req_years})."

            else:
                sim = cls._semantic_similarity(req.label, corpus)
                if sim >= 55.0:
                    status, score = "met", round(sim, 1)
                    evidence = ", ".join(profile.skills[:4]) or profile.current_designation
                    rationale = "Strong topical and domain alignment in CV."
                elif sim >= 30.0:
                    status, score = "partially_met", round(sim, 1)
                    evidence = ", ".join(profile.skills[:3]) or None
                    rationale = "Moderate keyword/domain overlap."
                else:
                    rationale = "Limited explicit evidence in CV for this criterion."

            earned_weight += (score / 100.0) * max(1, req.weight)
            req_matches.append(
                RequirementMatch(
                    requirement_id=req.id,
                    label=req.label,
                    category=req.category,
                    priority=req.priority,
                    status=status,  # type: ignore[arg-type]
                    score=round(score, 1),
                    evidence=evidence,
                    rationale=rationale,
                )
            )

        req_fit = round((earned_weight / total_weight) * 100.0, 1)
        dims = DimensionScores(
            requirement_fit=req_fit,
            domain_semantic_fit=pre["domain_semantic_fit"],
            teaching_fit=pre["teaching_fit"],
            research_and_impact=pre["research_and_impact"],
            alternative_strength_credit=pre["alternative_strength_signal"],
        )

        dynamic_score, tier = cls.recompute_composite_and_tier(
            dims, jd.weights, req_matches, jd.allow_compensating_strengths
        )

        highlights = list(profile.notable_highlights[:5])
        if not highlights:
            if profile.awards:
                highlights.append(NotableHighlight(category="award", title=profile.awards[0], evidence=profile.awards[0]))
            if profile.research.patents:
                pat_title = str(profile.research.patents[0].get("title") or "Patent")
                highlights.append(NotableHighlight(category="patent", title=pat_title, evidence=pat_title))
            if profile.courses_taught:
                highlights.append(
                    NotableHighlight(
                        category="teaching",
                        title=f"Taught {len(profile.courses_taught)} documented courses",
                        impact=", ".join(c.course_name for c in profile.courses_taught[:3]),
                    )
                )

        brief = (
            f"{profile.name} holds {top_deg} with {profile.experience.total_years} total career years "
            f"({profile.experience.teaching_years} yrs teaching, {profile.experience.industry_years} yrs industry) "
            f"and {len(profile.research.publications)} extracted publications. "
            f"Composite alignment with '{jd.title}' is {dynamic_score}% ({tier.replace('_', ' ')})."
        )

        probes = [
            f"Discuss how your background maps to '{jd.requirements[0].label[:80]}'." if jd.requirements else "Walk us through your core teaching philosophy.",
            "Outline courses or curricula you are prepared to design or deliver in the first year.",
        ]

        return CandidateJDEvaluation(
            jd_id=jd.jd_id,
            candidate_id=profile.candidate_id,
            dynamic_score=dynamic_score,
            recommendation_tier=tier,
            confidence=0.88,
            grounding_score=profile.metadata.grounding_score if profile.metadata else 1.0,
            dimension_scores=dims,
            requirement_matrix=req_matches,
            compensating_strengths=comp_strengths,
            standout_highlights=highlights,
            executive_brief=brief,
            interview_probes=probes,
            evaluated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )

    @classmethod
    def _apply_grounding_gate(cls, evaluation: CandidateJDEvaluation, profile: ResumeProfile) -> CandidateJDEvaluation:
        corpus = cls._build_candidate_corpus(profile)
        norm_corpus = ValidationService._normalize_text(corpus)
        if not norm_corpus:
            return evaluation

        checked = 0
        verified = 0

        for r in evaluation.requirement_matrix:
            if r.evidence:
                checked += 1
                if ValidationService._is_grounded(r.evidence, norm_corpus, min_overlap=0.30):
                    verified += 1
                else:
                    r.evidence = None

        grounded_comp: List[CompensatingStrength] = []
        for cs in evaluation.compensating_strengths:
            checked += 1
            if ValidationService._is_grounded(cs.compensating_evidence, norm_corpus, min_overlap=0.30):
                verified += 1
                grounded_comp.append(cs)
        evaluation.compensating_strengths = grounded_comp

        grounded_hl: List[NotableHighlight] = []
        for hl in evaluation.standout_highlights:
            checked += 1
            if ValidationService._is_grounded(f"{hl.title} {hl.evidence or ''}", norm_corpus, min_overlap=0.30):
                verified += 1
                grounded_hl.append(hl)
        evaluation.standout_highlights = grounded_hl

        if checked > 0:
            gs = round(verified / checked, 2)
            base_gs = profile.metadata.grounding_score if profile.metadata else 1.0
            evaluation.grounding_score = round(min(base_gs, gs), 2)
            if gs < 0.75:
                evaluation.confidence = round(min(evaluation.confidence, gs), 2)
        return evaluation

    def evaluate_candidate_against_jd(
        self,
        jd: JobDescriptionSpec,
        profile: ResumeProfile,
    ) -> CandidateJDEvaluation:
        pre = self._compute_pre_signals(jd, profile)
        det_eval = self._deterministic_evaluate(jd, profile, pre)

        if settings.mock_mode or groq_pool.size == 0:
            return self._apply_grounding_gate(det_eval, profile)

        try:
            t_cfg = config_manager.get_task_config("dynamic_evaluator", "reasoning")
            sys_prompt = config_manager.get_prompt("dynamic_evaluator", "system")

            compact_profile = {
                "candidate_id": profile.candidate_id,
                "name": profile.name,
                "current_designation": profile.current_designation,
                "summary": profile.summary,
                "education": [e.model_dump() for e in profile.education[:6]],
                "experience": profile.experience.model_dump(),
                "employment": [
                    {
                        "title": emp.title,
                        "organization": emp.organization,
                        "category": emp.category,
                        "start_date": emp.start_date,
                        "end_date": emp.end_date,
                        "duration_years": emp.duration_years,
                        "description": (emp.description or "")[:240],
                    }
                    for emp in profile.employment[:8]
                ],
                "courses_taught": [c.model_dump() for c in profile.courses_taught[:10]],
                "teaching_interests": profile.teaching_interests[:10],
                "supervision": profile.supervision.model_dump(),
                "publications_count": len(profile.research.publications),
                "top_publications": [p.title for p in profile.research.publications[:5]],
                "patents": profile.research.patents[:5],
                "research_projects": profile.research.research_projects[:5],
                "awards": profile.awards[:6],
                "certifications": profile.certifications[:6],
                "skills": profile.skills[:15],
                "notable_highlights": [h.model_dump() for h in profile.notable_highlights[:5]],
                "external_verification": profile.external_verification.model_dump() if profile.external_verification else None,
            }

            user_prompt = config_manager.get_prompt(
                "dynamic_evaluator",
                "user_template",
                default="JD:\n{jd_spec_json}\n\nCandidate:\n{candidate_profile_json}\n\nPreSignals:\n{pre_signals_json}",
                jd_spec_json=jd.model_dump_json(),
                candidate_profile_json=json.dumps(compact_profile),
                pre_signals_json=json.dumps(pre),
            )
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ]
            completion = groq_pool.execute_completion(
                model=t_cfg["model"],
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=t_cfg["max_tokens"],
                temperature=t_cfg["temperature"],
                **t_cfg.get("extra_completion_kwargs", {}),
            )
            parsed, _ = parse_llm_json(completion.choices[0].message.content)
            if not parsed:
                return self._apply_grounding_gate(det_eval, profile)

            raw_dims = parsed.get("dimension_scores") if isinstance(parsed.get("dimension_scores"), dict) else {}
            dims = DimensionScores(
                requirement_fit=max(0.0, min(100.0, safe_float(raw_dims.get("requirement_fit"), det_eval.dimension_scores.requirement_fit))),
                domain_semantic_fit=max(0.0, min(100.0, safe_float(raw_dims.get("domain_semantic_fit"), pre["domain_semantic_fit"]))),
                teaching_fit=max(0.0, min(100.0, safe_float(raw_dims.get("teaching_fit"), pre["teaching_fit"]))),
                research_and_impact=max(0.0, min(100.0, safe_float(raw_dims.get("research_and_impact"), pre["research_and_impact"]))),
                alternative_strength_credit=max(0.0, min(100.0, safe_float(raw_dims.get("alternative_strength_credit"), pre["alternative_strength_signal"]))),
            )

            req_lookup = {r.id: r for r in jd.requirements}
            matrix: List[RequirementMatch] = []
            for rm in parsed.get("requirement_matrix") or []:
                if not isinstance(rm, dict):
                    continue
                rid = str(rm.get("requirement_id") or "")
                jd_req = req_lookup.get(rid)
                raw_st = str(rm.get("status") or "gap").strip().lower()
                if raw_st not in {"met", "partially_met", "compensated", "gap"}:
                    raw_st = "gap"
                if raw_st == "compensated" and (not jd.allow_compensating_strengths or (jd_req and jd_req.strictness == "strict")):
                    raw_st = "gap"
                matrix.append(
                    RequirementMatch(
                        requirement_id=rid or f"REQ_{len(matrix) + 1}",
                        label=jd_req.label if jd_req else str(rm.get("label") or rid),
                        category=jd_req.category if jd_req else "other",
                        priority=jd_req.priority if jd_req else "must_have",
                        status=raw_st,  # type: ignore[arg-type]
                        score=max(0.0, min(100.0, safe_float(rm.get("score"), 0.0))),
                        evidence=str(rm.get("evidence")).strip() if rm.get("evidence") else None,
                        rationale=str(rm.get("rationale") or "").strip(),
                    )
                )
            if not matrix:
                matrix = det_eval.requirement_matrix

            comp_list: List[CompensatingStrength] = []
            if jd.allow_compensating_strengths:
                for cs in parsed.get("compensating_strengths") or []:
                    if isinstance(cs, dict) and cs.get("compensating_evidence"):
                        comp_list.append(
                            CompensatingStrength(
                                missed_requirement=str(cs.get("missed_requirement") or "Qualification / Tenure"),
                                compensating_evidence=str(cs.get("compensating_evidence")).strip(),
                                rationale=str(cs.get("rationale") or "").strip(),
                                strength_level="strong" if str(cs.get("strength_level", "")).lower() == "strong" else "moderate",
                            )
                        )

            hl_list: List[NotableHighlight] = []
            for hl in parsed.get("standout_highlights") or []:
                if isinstance(hl, dict) and hl.get("title"):
                    hl_list.append(
                        NotableHighlight(
                            category=str(hl.get("category") or "achievement").strip().lower(),
                            title=str(hl.get("title")).strip(),
                            impact=str(hl.get("impact")).strip() if hl.get("impact") else None,
                            evidence=str(hl.get("evidence")).strip() if hl.get("evidence") else None,
                        )
                    )
            if not hl_list:
                hl_list = det_eval.standout_highlights

            dyn_score, tier = self.recompute_composite_and_tier(
                dims, jd.weights, matrix, jd.allow_compensating_strengths
            )

            llm_eval = CandidateJDEvaluation(
                jd_id=jd.jd_id,
                candidate_id=profile.candidate_id,
                dynamic_score=dyn_score,
                recommendation_tier=tier,
                confidence=max(0.0, min(1.0, safe_float(parsed.get("confidence"), 0.88))),
                grounding_score=profile.metadata.grounding_score if profile.metadata else 1.0,
                dimension_scores=dims,
                requirement_matrix=matrix,
                compensating_strengths=comp_list,
                standout_highlights=hl_list,
                executive_brief=str(parsed.get("executive_brief") or det_eval.executive_brief).strip(),
                interview_probes=safe_str_list(parsed.get("interview_probes")) or det_eval.interview_probes,
                evaluated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            )
            return self._apply_grounding_gate(llm_eval, profile)

        except Exception as e:
            logger.warning(f"LLM evaluation failed for {profile.candidate_id} vs {jd.jd_id}, using deterministic evaluation: {e}")
            return self._apply_grounding_gate(det_eval, profile)


evaluation_agent = DynamicEvaluationAgent()
