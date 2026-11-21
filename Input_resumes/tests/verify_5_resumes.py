import os
import sys
import time
import json
import httpx
from pathlib import Path
import pypdfium2 as pdfium

BASE_URL = "http://127.0.0.1:8000"

RESUMES_TO_TEST = [
    "Dr Tushar Sharma Profile for Placement Department.pdf",
    "HanqingZhao_Curriculum-vitae.pdf.pdf",
    "John-Sarfo-CV-4-1.pdf.pdf",
    "Sourabh_Aggarwal_AOM-Resume_2026.pdf.pdf",
    "farhan khan CV.pdf"
]

def main():
    print("=" * 80)
    print("  FACULTYSCREEN — 5 RESUME UPLOAD & EXTRACTION ACCURACY VERIFICATION")
    print("=" * 80)

    client = httpx.Client(timeout=60.0)

    # 1. Check Backend Health
    try:
        r = client.get(f"{BASE_URL}/health")
        print(f"[*] Backend Health Check: {r.status_code} -> {r.json()}")
    except Exception as e:
        print(f"[!] Failed to reach backend at {BASE_URL}: {e}")
        sys.exit(1)

    # 2. Clean Database for Honest Verification
    print("\n[*] Clearing database for clean-slate verification...")
    r = client.delete(f"{BASE_URL}/api/candidates/clear-all")
    print(f"    Clear response: {r.json()}")

    results = []

    for idx, filename in enumerate(RESUMES_TO_TEST, 1):
        file_path = Path(filename)
        if not file_path.exists():
            print(f"[!] Error: File {filename} not found!")
            continue

        print(f"\n[{idx}/5] -------------------------------------------------------------")
        print(f"[*] Uploading: {filename} ({file_path.stat().st_size} bytes)...")

        # Read sample raw text from PDF for ground truth comparison
        pdf_sample_text = ""
        try:
            doc = pdfium.PdfDocument(str(file_path))
            for p in range(min(len(doc), 3)):
                pdf_sample_text += doc[p].get_textpage().get_text_range() + "\n"
            doc.close()
        except Exception as e:
            pdf_sample_text = f"Error reading PDF: {e}"

        # Upload resume to API endpoint
        t0 = time.time()
        with open(file_path, "rb") as f:
            upload_resp = client.post(
                f"{BASE_URL}/api/resumes/upload",
                files={"file": (file_path.name, f, "application/pdf")}
            )
        elapsed = time.time() - t0

        print(f"    Status: {upload_resp.status_code} | Latency: {elapsed:.2f}s")
        if upload_resp.status_code != 200:
            print(f"    [!] Upload Failed: {upload_resp.text}")
            continue

        upload_data = upload_resp.json()
        candidate_id = upload_data.get("candidate_id")
        print(f"    Assigned Candidate ID: {candidate_id}")

        # Fetch full candidate profile from API
        cand_resp = client.get(f"{BASE_URL}/api/candidates/{candidate_id}")
        if cand_resp.status_code != 200:
            print(f"    [!] Could not fetch candidate profile: {cand_resp.text}")
            continue

        profile = cand_resp.json()

        # Extract parsed details
        name = profile.get("name")
        email = profile.get("email")
        phone = profile.get("phone")
        designation = profile.get("current_designation")
        highest_deg = profile.get("highest_degree")
        highest_inst = profile.get("highest_institution")
        tier = profile.get("institution_tier")
        teaching_yrs = profile.get("teaching_years", 0.0)
        research_yrs = profile.get("research_years", 0.0)
        pub_count = profile.get("publications_count", 0)
        eligibility = profile.get("eligibility_status")
        score = profile.get("overall_score")
        confidence = profile.get("confidence")
        
        # Ground Truth Verification
        # Check if the extracted name or email actually exists in the ground truth PDF text
        name_in_pdf = name.lower() in pdf_sample_text.lower() if name else False
        email_in_pdf = email.lower() in pdf_sample_text.lower() if email else False

        # Sample evidence quote
        sample_evidence = ""
        if profile.get("education"):
            sample_evidence = profile["education"][0].get("evidence", "")

        results.append({
            "filename": filename,
            "candidate_id": candidate_id,
            "name": name,
            "email": email,
            "phone": phone,
            "current_designation": designation,
            "highest_degree": highest_deg,
            "institution": highest_inst,
            "tier": tier,
            "teaching_years": teaching_yrs,
            "research_years": research_yrs,
            "publications_count": pub_count,
            "eligibility": eligibility,
            "score": score,
            "confidence": confidence,
            "name_verified_in_pdf": name_in_pdf,
            "email_verified_in_pdf": email_in_pdf,
            "sample_evidence": sample_evidence,
            "latency": elapsed
        })

        print(f"    Name:              {name} (Verified in PDF: {name_in_pdf})")
        print(f"    Email:             {email} (Verified in PDF: {email_in_pdf})")
        print(f"    Phone:             {phone}")
        print(f"    Designation:       {designation}")
        print(f"    Highest Degree:    {highest_deg}")
        print(f"    Institution:       {highest_inst} [{tier}]")
        print(f"    Experience:        Teaching: {teaching_yrs} yrs | Research: {research_yrs} yrs")
        print(f"    Publications:      {pub_count}")
        print(f"    Eligibility:       {eligibility} (Score: {score}%, Confidence: {confidence})")
        print(f"    Sample Evidence:   \"{sample_evidence[:90]}...\"")

    print("\n" + "=" * 80)
    print("  SUMMARY OF ACCURACY FOR ALL 5 RESUMES")
    print("=" * 80)
    print(f"{'Candidate Name':<22} | {'Degree':<20} | {'Institution':<22} | {'Exp(T/R)':<10} | {'Pubs':<5} | {'Status':<12}")
    print("-" * 105)
    for r in results:
        exp_str = f"{r['teaching_years']:.1f}y / {r['research_years']:.1f}y"
        print(f"{r['name'][:22]:<22} | {str(r['highest_degree'])[:20]:<20} | {str(r['institution'])[:22]:<22} | {exp_str:<10} | {r['publications_count']:<5} | {r['eligibility']:<12}")

    print("\n[*] All 5 resumes tested. Checking total candidates in database...")
    all_cands = client.get(f"{BASE_URL}/api/candidates").json()
    print(f"[*] Database now contains {all_cands.get('total')} live candidates.")

if __name__ == "__main__":
    main()
