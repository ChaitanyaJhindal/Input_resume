import sys, os
sys.path.insert(0, os.path.abspath("."))
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
