from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class ClassifyRequest(BaseModel):
    text: str


@app.post("/classify")
def classify(payload: ClassifyRequest):
    text = payload.text.lower()
    if not text.strip():
        return {"output": {"category": "abstain"}, "confidence": 0.0}
    if "billing" in text or "payment" in text:
        return {"output": {"category": "billing"}, "confidence": 0.95}
    if "crash" in text or "bug" in text:
        return {"output": {"category": "bug"}, "confidence": 0.9}
    return {"output": {"category": "general"}, "confidence": 0.7}