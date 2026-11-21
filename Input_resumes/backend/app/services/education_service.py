import re
from typing import Optional, Tuple

class EducationService:
    @staticmethod
    def normalize_degree(raw_degree: str) -> Tuple[str, float]:
        """
        Classifies degree title into the standard taxonomy:
        - Undergraduate
        - Postgraduate / Masters
        - PhD / Doctorate
        - Postdoctoral
        - Diploma
        - Certification
        - Other

        Returns: (normalized_degree, confidence)
        """
        if not raw_degree:
            return "Other", 0.0
        
        deg = raw_degree.lower().strip()

        # Postdoctoral
        if any(term in deg for term in ["postdoc", "post-doc", "post doctoral", "postdoctoral"]):
            return "Postdoctoral", 0.98

        # Doctorate / PhD / FPM
        if any(term in deg for term in [
            "ph.d", "phd", "doctor of philosophy", "d.phil", "doctorate", "d.sc",
            "fellow programme in management", "fpm", "fellowship in management", "fellow in management"
        ]):
            return "PhD / Doctorate", 0.99

        # Postgraduate / Masters / Executive Masters
        if any(term in deg for term in [
            "m.tech", "mtech", "m.e", "m.s", "ms ", "m.sc", "msc", "m.com", "m.a",
            "mba", "m.b.a", "mca", "m.c.a", "master", "post graduate", "postgraduate",
            "mphil", "m.phil", "llm", "m.ed", "executive management program",
            "executive program", "executive mba", "pgdm", "advanced studies"
        ]):
            return "Postgraduate / Masters", 0.95

        # Undergraduate / Bachelors
        if any(term in deg for term in [
            "b.tech", "btech", "b.e", "b.s", "bs ", "b.sc", "bsc", "b.com", "b.a",
            "bba", "b.b.a", "bca", "b.c.a", "bachelor", "undergraduate", "llb", "b.ed", "mbbs"
        ]):
            return "Undergraduate", 0.95

        # Diploma
        if any(term in deg for term in ["diploma", "pgd", "pg diploma", "polytechnic"]):
            return "Diploma", 0.90

        # Certification / Training
        if any(term in deg for term in [
            "certificate", "certification", "certified", "course", "bootcamp",
            "specialization", "training", "program", "programme"
        ]):
            return "Certification", 0.90

        return "Other", 0.75

education_service = EducationService()
