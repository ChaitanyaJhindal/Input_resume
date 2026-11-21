import sys
import os
sys.path.insert(0, os.path.abspath("."))
from backend.app.groq.extractor import groq_extractor

test_truncated = '''
{
  "name": "Sushil Chaurasia",
  "employment": [
    {
      "title": "Instructor",
      "organization": "University of New Brunswick",
      "category": "teaching",
      "start_date": "Feb 2020",
      "end_date": "Jan 2024",
      "duration_years": 4.0
    }
  ],
  "publications": [
    {
      "title": "Paper 1",
      "evidence": "truncated here...
'''

parsed = groq_extractor._robust_json_parse(test_truncated)
print("Parsed result:", parsed)
