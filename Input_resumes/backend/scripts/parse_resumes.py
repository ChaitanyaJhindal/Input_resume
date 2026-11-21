"""
Resume Parser using Groq Vision (qwen/qwen3.8-27b)
Converts PDF pages to images using pypdfium2 and extracts clean Markdown via Groq API.
"""

import os
import sys
import io
import base64
import argparse
import glob
from pathlib import Path
from groq import Groq
import pypdfium2 as pdfium

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_API_KEY = os.environ.get("GROQ_API_KEY", "")
DEFAULT_MODEL = "qwen/qwen3.8-27b"

PROMPT_TEXT = """You are an expert document and resume parser.
Extract all content from this resume page with high fidelity.
Format the output into clean, structured Markdown:
- Use proper markdown headings (# for Candidate Name, ## for Sections like Summary, Experience, Education, Skills, etc.)
- Use bullet points for lists and achievements.
- Extract all dates, company names, job titles, and contact information accurately.
- If there are tables or columns, convert them into readable markdown tables or bulleted lists.
- Do NOT add conversational preamble or concluding remarks; return only the extracted Markdown content.
"""

def pdf_page_to_base64_jpeg(page, scale=2.0):
    """Render a PDF page to a base64 encoded JPEG string."""
    image = page.render(scale=scale).to_pil()
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def parse_single_resume(client, pdf_path, output_dir="parsed_resumes", model=DEFAULT_MODEL):
    pdf_path = Path(pdf_path)
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n[>] Processing: {pdf_path.name}")
    
    pdf = pdfium.PdfDocument(str(pdf_path))
    num_pages = len(pdf)
    print(f"    Total Pages: {num_pages}")
    
    extracted_pages = []
    
    for page_idx in range(num_pages):
        page = pdf[page_idx]
        b64_img = pdf_page_to_base64_jpeg(page)
        
        print(f"    --> Parsing page {page_idx + 1}/{num_pages} via Groq ({model})...")
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT_TEXT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64_img}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.2,
            max_completion_tokens=2048,
            top_p=0.95,
        )
        
        page_md = completion.choices[0].message.content.strip()
        extracted_pages.append(f"<!-- Page {page_idx + 1} -->\n{page_md}")
        
    full_markdown = "\n\n---\n\n".join(extracted_pages)
    out_file = Path(output_dir) / f"{pdf_path.stem}_full.md"
    out_file.write_text(full_markdown, encoding="utf-8")
    print(f"[✓] Saved Markdown to: {out_file}")
    return out_file

def parse_directory(client, input_dir=".", output_dir="parsed_resumes", model=DEFAULT_MODEL):
    pdf_files = [f for f in glob.glob(os.path.join(input_dir, "*.pdf")) if not f.endswith(".md")]
    print(f"[+] Found {len(pdf_files)} PDF resume(s) in {input_dir}")
    
    for idx, pdf in enumerate(pdf_files, 1):
        print(f"\n[{idx}/{len(pdf_files)}] Starting {os.path.basename(pdf)}...")
        try:
            parse_single_resume(client, pdf, output_dir=output_dir, model=model)
        except Exception as e:
            print(f"[!] Error processing {pdf}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse resumes using Groq Vision (qwen/qwen3.8-27b)")
    parser.add_argument("--input", "-i", type=str, default=None, help="Path to a PDF resume or folder")
    parser.add_argument("--output", "-o", type=str, default="parsed_resumes", help="Output directory")
    parser.add_argument("--model", "-m", type=str, default=DEFAULT_MODEL, help="Groq vision model")
    parser.add_argument("--api-key", "-k", type=str, default=DEFAULT_API_KEY, help="Groq API key")
    args = parser.parse_args()

    client = Groq(api_key=args.api_key)

    if args.input:
        if os.path.isdir(args.input):
            parse_directory(client, input_dir=args.input, output_dir=args.output, model=args.model)
        else:
            parse_single_resume(client, args.input, output_dir=args.output, model=args.model)
    else:
        parse_directory(client, input_dir=".", output_dir=args.output, model=args.model)
