"""
FastAPI entrypoint for the offline Phase 1 chatbot.

    uvicorn phase1_pilot.app.main:app      from the repository root
"""

from fastapi import FastAPI, Query

from phase1_pilot.app.router import QueryRouter
from phase1_pilot.app.utils import log_event

router = QueryRouter()
app = FastAPI(title="Multi-Intent AI Chatbot Assistant - Phase 1 (Offline)")


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Chatbot is online"}


@app.post("/query")
def handle_query(user_query: str = Query(..., description="User's question")):
    intent, response = router.handle_query(user_query)
    log_event("INTENT", intent)
    return {"intent": intent, "response": response}
