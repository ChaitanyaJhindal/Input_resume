import sys
import os
sys.path.insert(0, os.path.abspath("."))
import json
from backend.app.schemas.resume import EmploymentEntry
from backend.app.services.experience_service import ExperienceService

# Employments extracted by Groq for Sushil
raw_employments = [
    {
      "title": "Senior Economist-Policy and Economic Outlook/Economy in Review at Fiscal. Economic and Statistical Division",
      "organization": "GOVERNMENT OF NEW BRUNSWICK",
      "category": "government",
      "start_date": "Nov 2023",
      "end_date": "Present",
      "duration_years": 2.92
    },
    {
      "title": "Acting Scientific Director & Senior Economist-Health Innovation and Policy",
      "organization": "UNIVERSITY OF NEW BRUNSWICK -INSTITUTE OF POPULATION HEALTH",
      "category": "research",
      "start_date": "Sep 2025",
      "end_date": "Present",
      "duration_years": 1.08
    },
    {
      "title": "Departmental Associate",
      "organization": "HARVARD UNIVERSITY (HARVARD T.H. CHAN SCHOOL OF PUBLIC HEALTH)",
      "category": "research",
      "start_date": "Nov 2023",
      "end_date": "Mar 2025",
      "duration_years": 1.33
    },
    {
      "title": "Mitacs Accelerate Research Fellow",
      "organization": "University of New Brunswick",
      "category": "research",
      "start_date": "Feb 2020",
      "end_date": "Jan 2024",
      "duration_years": 3.92
    },
    {
      "title": "Instructor (Undergraduate and master’s Level)",
      "organization": "University of New Brunswick",
      "category": "teaching",
      "start_date": "Feb 2020",
      "end_date": "Jan 2024",
      "duration_years": 3.92
    },
    {
      "title": "Assistant Professor- Strategy and Entrepreneurship",
      "organization": "NMIMS UNIVERSITY",
      "category": "teaching",
      "start_date": "Jan 2018",
      "end_date": "Jan 2020",
      "duration_years": 2.0
    },
    {
      "title": "Assistant Professor-Strategy and Entrepreneurship Area",
      "organization": "SYMBIOSIS INTERNATIONAL UNIVERSITY",
      "category": "teaching",
      "start_date": "Nov 2014",
      "end_date": "Jan 2018",
      "duration_years": 3.17
    },
    {
      "title": "Assistant Professor- Strategy Area",
      "organization": "TOLANI INSTITUTE OF MANAGEMENT STUDIES",
      "category": "teaching",
      "start_date": "Jun 2009",
      "end_date": "Apr 2012",
      "duration_years": 2.83
    }
]

entries = [EmploymentEntry(**e) for e in raw_employments]
exp = ExperienceService.calculate_experience(entries)
print("Sushil Experience Calculation:")
print(f"Teaching Years: {exp.teaching_years}")
print(f"Research Years: {exp.research_years}")
print(f"Industry Years: {exp.industry_years}")
print(f"Total Years: {exp.total_years}")
