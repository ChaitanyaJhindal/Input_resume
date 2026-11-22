# Canonical Resume Profile Schema

FacultyScreen strictly enforces strongly-typed Pydantic schemas for machine interchange.

## Core Schema Structure

```json
{
  "candidate_id": "cand_e0c25ad3b3",
  "name": "Dr. Sushil S. Chaurasia",
  "email": "chaurasia.sushil@gmail.com",
  "phone": "+1-(506) 461-0809",
  "location": "Lincoln, New Brunswick, Canada",
  "current_designation": "Senior Economist-Policy and Economic Outlook",
  "summary": "Strategy and business policy scholar...",
  "education": [
    {
      "degree": "Ph.D. in Strategy and Innovation",
      "normalized_degree": "PhD / Doctorate",
      "field": "Business Strategy & Technology Entrepreneurship",
      "institution": "University of New Brunswick",
      "institution_normalized": "University of New Brunswick",
      "institution_category": "International University",
      "institution_tier": "Tier 1",
      "graduation_year": 2020,
      "confidence": 0.98,
      "evidence": "Earned Ph.D. in Strategy and Innovation, UNB Faculty of Management (2020)",
      "source_page": 1
    }
  ],
  "experience": {
    "total_years": 8.0,
    "teaching_years": 6.0,
    "research_years": 6.0,
    "industry_years": 3.0,
    "administrative_years": 0.0
  },
  "employment": [
    {
      "title": "Acting Scientific Director",
      "organization": "University of New Brunswick",
      "category": "research",
      "start_date": "2025",
      "end_date": "Present",
      "duration_years": 1.0,
      "is_current": true,
      "description": "Leading applied strategic policy research...",
      "evidence": "Secondment Scientific Director appointment (2025 - Present)"
    }
  ],
  "research": {
    "publications": [
      {
        "title": "From Big Data to Big Impact: Analytics for Teaching and Learning in Higher Education",
        "venue": "Emerald International Journal of Educational Management",
        "year": 2023,
        "doi": "10.1108/IJEM-04-2022-0145",
        "indexed": "Scopus, SCI",
        "evidence": "Emerald IJEM Vol 37, pp. 410-429"
      }
    ],
    "patents": [],
    "research_projects": [],
    "research_domains": ["Innovation", "Entrepreneurship", "Digital Transformation"]
  },
  "screening": {
    "eligibility_status": "eligible",
    "overall_score": 95.0,
    "confidence": 0.94,
    "flags": [],
    "rules_evaluated": [
      {
        "rule_id": "RULE_MIN_DEGREE",
        "name": "Doctoral Degree Requirement",
        "status": "pass",
        "reason": "Candidate holds Ph.D. in Strategy & Innovation",
        "evidence": "Ph.D. in Strategy and Innovation, UNB (2020)",
        "confidence": 0.98,
        "is_mandatory": true,
        "weight": 30
      }
    ]
  },
  "source_evidence": [
    {
      "field": "phd_status",
      "value": "Ph.D.",
      "evidence": "Earned Ph.D. in Strategy and Innovation",
      "source_page": 1,
      "confidence": 0.98
    }
  ]
}
```
