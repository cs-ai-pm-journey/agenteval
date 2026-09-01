import json
import sys

payload = json.loads(sys.stdin.read())
text = payload.get("text", "").lower()

if not text.strip():
    response = {"output": {"category": "abstain"}, "confidence": 0.0}
elif "billing" in text or "payment" in text:
    response = {"output": {"category": "billing"}, "confidence": 0.95}
elif "crash" in text or "bug" in text:
    response = {"output": {"category": "bug"}, "confidence": 0.9}
else:
    response = {"output": {"category": "general"}, "confidence": 0.7}

print(json.dumps(response))