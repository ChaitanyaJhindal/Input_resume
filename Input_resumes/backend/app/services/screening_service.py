import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.schemas.resume import ResumeProfile, RuleEvaluation, ScreeningResult

class ScreeningService:
    """
    Configurable, explainable screening rule engine.
    Evaluates candidate facts against YAML screening rules without opaque LLM scoring.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or (settings.config_dir / "screening_rules.yaml")
        self.rules_config = self._load_rules()

    def _load_rules(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {
                "rules": [],
                "settings": {
                    "overall_passing_score_percentage": 70.0,
                    "minimum_confidence_for_auto_approval": 0.85,
                    "needs_review_confidence_floor": 0.65
                }
            }
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {"rules": [], "settings": {}}

    def reload_rules(self):
        self.rules_config = self._load_rules()

    def evaluate_candidate(self, profile: ResumeProfile) -> ScreeningResult:
        rules = self.rules_config.get("rules", [])
        thresholds = self.rules_config.get("settings", {})
        passing_score = thresholds.get("overall_passing_score_percentage", 70.0)
        auto_approve_conf = thresholds.get("minimum_confidence_for_auto_approval", 0.85)

        evaluations: List[RuleEvaluation] = []
        flags: List[str] = []
        decision_path: List[str] = []
        total_weight = 0
        earned_weight = 0.0
        mandatory_failed = False
        overall_confidence_sum = 0.0

        for r in rules:
            rule_id = r.get("id", "UNKNOWN_RULE")
            name = r.get("name", rule_id)
            field = r.get("field", "")
            operator = r.get("operator", "==")
            required_value = r.get("required_value")
            is_mandatory = r.get("is_mandatory", True)
            weight = r.get("weight", 20)
            total_weight += weight

            # Extract actual candidate value from profile
            actual_value, evidence_snippet, field_conf = self._extract_field_value(profile, field)
            overall_confidence_sum += field_conf

            # Evaluate condition
            passed, reason = self._evaluate_condition(actual_value, operator, required_value)

            if passed:
                status = "pass"
                earned_weight += weight
                decision_path.append(f"[PASS] {name}: {reason}")
            else:
                status = "fail"
                decision_path.append(f"[FAIL] {name}: {reason}")
                if is_mandatory:
                    mandatory_failed = True
                    flags.append(f"Mandatory requirement failed: {name} ({reason})")
                else:
                    flags.append(f"Preferred requirement missed: {name}")

            evaluations.append(RuleEvaluation(
                rule_id=rule_id,
                name=name,
                status=status,
                reason=reason,
                evidence=evidence_snippet,
                confidence=field_conf,
                is_mandatory=is_mandatory,
                weight=weight
            ))

        # Calculate final percentage score
        score_percentage = (earned_weight / total_weight * 100.0) if total_weight > 0 else 0.0
        avg_confidence = (overall_confidence_sum / len(rules)) if rules else 0.9

        # Determine Eligibility Status
        if mandatory_failed:
            eligibility_status = "disqualified"
        elif score_percentage >= passing_score and avg_confidence >= auto_approve_conf:
            eligibility_status = "eligible"
        else:
            eligibility_status = "needs_review"
            if avg_confidence < auto_approve_conf:
                flags.append(f"Screening confidence ({avg_confidence:.2f}) below auto-approval threshold ({auto_approve_conf:.2f})")

        return ScreeningResult(
            eligibility_status=eligibility_status,
            overall_score=round(score_percentage, 1),
            confidence=round(avg_confidence, 2),
            flags=flags,
            rules_evaluated=evaluations,
            decision_path=decision_path
        )

    def _extract_field_value(self, profile: ResumeProfile, field_path: str) -> tuple[Any, Optional[str], float]:
        """
        Dynamically extracts candidate value, supporting nested fields such as
        'education.highest_degree', 'experience.teaching_years', 'research.publications_count'.
        """
        if field_path == "education.highest_degree":
            # Find highest normalized degree
            degrees = [e.normalized_degree for e in profile.education]
            if any("PhD" in d or "Doctorate" in d or "Postdoctoral" in d for d in degrees):
                phd_entry = next((e for e in profile.education if "PhD" in e.normalized_degree or "Doctorate" in e.normalized_degree), None)
                return "PhD / Doctorate", (phd_entry.evidence or phd_entry.degree if phd_entry else "PhD"), 0.96
            elif any("Masters" in d or "Postgraduate" in d for d in degrees):
                m_entry = next((e for e in profile.education if "Masters" in e.normalized_degree), None)
                return "Postgraduate / Masters", (m_entry.evidence or m_entry.degree if m_entry else "Masters"), 0.92
            elif degrees:
                return degrees[0], profile.education[0].degree, 0.88
            return "None", "No education records identified", 0.5

        elif field_path == "education.highest_institution_category":
            if profile.education:
                top_edu = profile.education[0]
                return top_edu.institution_category or "Other", top_edu.institution_normalized or top_edu.institution, top_edu.confidence
            return "Other", "No institution listed", 0.5

        elif field_path == "experience.teaching_years":
            val = profile.experience.teaching_years
            evidence = f"Computed {val} years across {len([e for e in profile.employment if e.category == 'teaching'])} teaching roles"
            return val, evidence, 0.94

        elif field_path == "experience.research_years":
            val = profile.experience.research_years
            evidence = f"Computed {val} years across research roles"
            return val, evidence, 0.92

        elif field_path == "experience.industry_years":
            val = profile.experience.industry_years
            evidence = f"Computed {val} years across corporate/industrial roles"
            return val, evidence, 0.92

        elif field_path == "research.publications_count":
            val = len(profile.research.publications)
            pubs_sample = ", ".join([p.title[:30] + "..." for p in profile.research.publications[:2]]) if val > 0 else "None"
            evidence = f"{val} publications extracted ({pubs_sample})"
            return val, evidence, 0.95

        return None, None, 0.5

    def _evaluate_condition(self, actual: Any, operator: str, expected: Any) -> tuple[bool, str]:
        if operator == "==":
            passed = actual == expected
            return passed, f"Actual value is '{actual}', expected '{expected}'"
        elif operator == ">=":
            try:
                passed = float(actual or 0) >= float(expected or 0)
                return passed, f"Actual is {actual} (Required >= {expected})"
            except (ValueError, TypeError):
                return False, f"Could not compare {actual} with {expected}"
        elif operator == "<=":
            try:
                passed = float(actual or 0) <= float(expected or 0)
                return passed, f"Actual is {actual} (Required <= {expected})"
            except (ValueError, TypeError):
                return False, f"Could not compare {actual} with {expected}"
        elif operator == "in":
            if isinstance(expected, list):
                passed = actual in expected
                return passed, f"Actual '{actual}' {'is included in' if passed else 'is not among'} {expected}"
            return False, f"Operator 'in' requires list"
        return False, f"Unknown operator {operator}"

screening_service = ScreeningService()
