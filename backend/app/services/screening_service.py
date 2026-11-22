import re
import threading
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.app.config import settings
from backend.app.schemas.resume import ResumeProfile, RuleEvaluation, ScreeningResult
from backend.app.services.education_service import EducationService

class ScreeningService:
    """
    Configurable, explainable screening rule engine.
    Evaluates candidate facts against YAML screening rules without opaque LLM scoring.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or (settings.config_dir / "screening_rules.yaml")
        self._lock = threading.RLock()
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
        with self._lock:
            self.rules_config = self._load_rules()

    def evaluate_candidate(self, profile: ResumeProfile) -> ScreeningResult:
        with self._lock:
            rules = list(self.rules_config.get("rules", []))
            thresholds = dict(self.rules_config.get("settings", {}))
        passing_score = thresholds.get("overall_passing_score_percentage", 70.0)
        auto_approve_conf = thresholds.get("minimum_confidence_for_auto_approval", 0.85)
        needs_review_conf_floor = thresholds.get("needs_review_confidence_floor", 0.65)

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
            failure_msg = r.get("failure_message")
            total_weight += weight

            # Extract actual candidate value from profile
            actual_value, evidence_snippet, field_conf = self._extract_field_value(profile, field)
            overall_confidence_sum += field_conf

            # Evaluate condition
            passed, detail = self._evaluate_condition(actual_value, operator, required_value)
            if not passed and failure_msg:
                reason = f"{failure_msg} ({detail})"
            else:
                reason = detail

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

        if avg_confidence < needs_review_conf_floor:
            flags.append(f"Average extraction confidence ({avg_confidence:.2f}) below review floor ({needs_review_conf_floor:.2f})")

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
            top_edu = EducationService.select_highest_education(profile.education)
            if top_edu:
                return top_edu.normalized_degree, (top_edu.evidence or top_edu.degree), top_edu.confidence
            return "None", "No education records identified", 0.5

        elif field_path == "education.highest_institution_category":
            top_edu = EducationService.select_highest_education(profile.education)
            if top_edu:
                return top_edu.institution_category or "Other", top_edu.institution_normalized or top_edu.institution, top_edu.confidence
            return "Other", "No institution listed", 0.5

        elif field_path == "education.institution_tier":
            top_edu = EducationService.select_highest_education(profile.education)
            if top_edu:
                return top_edu.institution_tier or "Other", top_edu.institution_normalized or top_edu.institution, top_edu.confidence
            return "Other", "No institution listed", 0.5

        elif field_path == "experience.teaching_years":
            val = profile.experience.teaching_years
            roles = [e for e in profile.employment if e.category == "teaching"]
            conf = 0.94 if roles else (0.90 if (profile.employment or val > 0) else 0.70)
            evidence = f"Computed {val} years across {len(roles)} teaching roles"
            return val, evidence, conf

        elif field_path == "experience.research_years":
            val = profile.experience.research_years
            roles = [e for e in profile.employment if e.category == "research"]
            conf = 0.94 if roles else (0.90 if (profile.employment or val > 0) else 0.70)
            evidence = f"Computed {val} years across {len(roles)} research roles"
            return val, evidence, conf

        elif field_path == "experience.industry_years":
            val = profile.experience.industry_years
            roles = [e for e in profile.employment if e.category == "industry"]
            conf = 0.94 if roles else (0.90 if (profile.employment or val > 0) else 0.70)
            evidence = f"Computed {val} years across {len(roles)} corporate/industrial roles"
            return val, evidence, conf

        elif field_path == "experience.administrative_years":
            val = profile.experience.administrative_years
            roles = [e for e in profile.employment if e.category == "administrative"]
            conf = 0.94 if roles else (0.90 if (profile.employment or val > 0) else 0.70)
            evidence = f"Computed {val} years across {len(roles)} administrative/leadership roles"
            return val, evidence, conf

        elif field_path == "experience.total_years":
            val = profile.experience.total_years
            conf = 0.94 if (profile.employment or val > 0) else 0.70
            evidence = f"Computed {val} total years across {len(profile.employment)} roles"
            return val, evidence, conf

        elif field_path == "research.publications_count":
            val = len(profile.research.publications)
            pubs_sample = ", ".join([p.title[:30] + "..." for p in profile.research.publications[:2]]) if val > 0 else "None"
            conf = 0.95 if val > 0 else 0.85
            evidence = f"{val} publications extracted ({pubs_sample})"
            return val, evidence, conf

        return None, None, 0.5

    def _evaluate_condition(self, actual: Any, operator: str, expected: Any) -> tuple[bool, str]:
        if operator == "==":
            passed = actual == expected
            return passed, f"Actual value is '{actual}', expected '{expected}'"
        elif operator == "!=":
            passed = actual != expected
            return passed, f"Actual value is '{actual}', must not be '{expected}'"
        elif operator in (">=", "<=", ">", "<"):
            try:
                actual_num = float(actual if actual is not None else 0)
                expected_num = float(expected if expected is not None else 0)
                if operator == ">=":
                    passed = actual_num >= expected_num
                elif operator == "<=":
                    passed = actual_num <= expected_num
                elif operator == ">":
                    passed = actual_num > expected_num
                else:
                    passed = actual_num < expected_num
                return passed, f"Actual is {actual} (Required {operator} {expected})"
            except (ValueError, TypeError):
                return False, f"Could not compare {actual} with {expected}"
        elif operator == "in":
            if isinstance(expected, list):
                passed = actual in expected
                return passed, f"Actual '{actual}' {'is included in' if passed else 'is not among'} {expected}"
            return False, "Operator 'in' requires list"
        elif operator == "not_in":
            if isinstance(expected, list):
                passed = actual not in expected
                return passed, f"Actual '{actual}' {'is not in' if passed else 'is excluded by'} {expected}"
            return False, "Operator 'not_in' requires list"
        elif operator == "contains":
            if isinstance(actual, list):
                passed = expected in actual or any(str(expected).lower() in str(item).lower() for item in actual)
                return passed, f"List {'contains' if passed else 'does not contain'} '{expected}'"
            actual_str = "" if actual is None else str(actual)
            expected_str = "" if expected is None else str(expected)
            passed = expected_str.lower() in actual_str.lower()
            return passed, f"Actual '{actual_str}' {'contains' if passed else 'does not contain'} '{expected_str}'"
        elif operator == "regex":
            try:
                pattern = str(expected or "")
                actual_str = "" if actual is None else str(actual)
                passed = re.search(pattern, actual_str, re.IGNORECASE) is not None
                return passed, f"Actual '{actual_str}' {'matched' if passed else 'did not match'} pattern '{pattern}'"
            except re.error as err:
                return False, f"Invalid regex pattern '{expected}': {err}"
        return False, f"Unknown operator {operator}"

screening_service = ScreeningService()
