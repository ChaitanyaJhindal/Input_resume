import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.stdout.reconfigure(encoding='utf-8')
from backend.app.groq.pool import groq_pool

client = groq_pool.key_states[4].client
raw = client.chat.completions.with_raw_response.create(
    model="openai/gpt-oss-20b",
    messages=[{"role": "user", "content": "hi"}]
)
for k, v in raw.headers.items():
    if "ratelimit" in k:
        print(f"{k}: {v}")
