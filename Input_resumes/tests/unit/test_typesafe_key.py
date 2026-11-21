import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Force load latest .env
load_dotenv(override=True)

from backend.app.core.config import settings
from backend.app.services.jev.jev_client import JevClient
from backend.app.services.jev.jev_schemas import JevDecisionRequest
from backend.app.services.jev.jev_router import jev_router

def test_typesafe():
    print("=" * 60)
    print("  TypeSafe AI / JEV Integration Verification")
    print("=" * 60)
    
    key = os.getenv("TYPESAFE_API_KEY", "")
    print(f"[*] Base URL:    {settings.typesafe_base_url}")
    print(f"[*] JEV Model:   {settings.jev_model}")
    
    if not key or len(key.strip()) == 0:
        print("[!] WARNING: TYPESAFE_API_KEY is currently empty in .env!")
        print("    Please ensure you saved the .env file in your editor (Ctrl+S).")
        print("    Testing local deterministic fallback mechanism...")
    else:
        masked = key[:6] + "..." + key[-4:] if len(key) > 10 else "***"
        print(f"[*] API Key:     {masked} (Length: {len(key)})")

    client = JevClient(api_key=key)
    print(f"[*] Client Configured: {client.is_configured}")

    # Test Task 1: Classify Institution
    print("\n--- Test 1: Classify Institution ---")
    req1 = JevDecisionRequest(
        task="classify_institution",
        context={"institution_name": "Indian Institute of Technology Madras"},
        candidate_options=["IIT", "NIT", "Central University", "Other"]
    )
    resp1 = client.execute_decision(req1)
    print(f"  Decision:   {resp1.decision}")
    print(f"  Confidence: {resp1.confidence}")
    print(f"  Source:     {resp1.source}")
    print(f"  Rationale:  {resp1.rationale}")
    print(f"  Latency:    {resp1.metadata.get('latency_ms', 0):.2f} ms")

    # Test Task 2: Classify Degree
    print("\n--- Test 2: Classify Degree ---")
    req2 = JevDecisionRequest(
        task="classify_degree",
        context={"raw_degree": "Doctor of Philosophy in Computer Science"},
        candidate_options=["PhD / Doctorate", "Postgraduate / Masters", "Undergraduate"]
    )
    resp2 = client.execute_decision(req2)
    print(f"  Decision:   {resp2.decision}")
    print(f"  Confidence: {resp2.confidence}")
    print(f"  Source:     {resp2.source}")
    print(f"  Rationale:  {resp2.rationale}")
    print(f"  Latency:    {resp2.metadata.get('latency_ms', 0):.2f} ms")

    # Test Task 3: Evaluate Screening Condition
    print("\n--- Test 3: Fast Rule Condition Evaluation ---")
    req3 = JevDecisionRequest(
        task="evaluate_rule",
        context={
            "candidate_value": 4.5,
            "operator": ">=",
            "required_value": 2.0
        }
    )
    resp3 = client.execute_decision(req3)
    print(f"  Decision:   {resp3.decision}")
    print(f"  Confidence: {resp3.confidence}")
    print(f"  Source:     {resp3.source}")
    print(f"  Rationale:  {resp3.rationale}")

    assert resp1.decision in ["IIT", "NIT", "Central University", "Other"]
    assert resp2.decision in ["PhD / Doctorate", "Postgraduate / Masters", "Undergraduate"]
    assert str(resp3.decision).lower() in ["true", "pass", "1"]
    print("\n[OK] TypeSafe / JEV fast decision layer verified successfully!")
    print("=" * 60)

if __name__ == "__main__":
    test_typesafe()
