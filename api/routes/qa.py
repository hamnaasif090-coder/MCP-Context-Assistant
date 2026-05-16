"""
api/routes/qa.py
Question-answering and chat endpoints.
"""
from __future__ import annotations
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json

from api.qa_engine import get_qa_engine
from memory.manager import get_memory_manager
from logger import logger

router = APIRouter(prefix="/qa", tags=["Q&A & Chat"])


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = Field(None, description="For memory-aware conversations")
    top_k: int = Field(5, ge=1, le=20)
    source_filter: Optional[str] = None
    use_memory: bool = True
    max_tokens: int = Field(1024, ge=100, le=4096)


class ChatMessage(BaseModel):
    role: str
    content: str


@router.post("/ask", summary="Ask a question, get a grounded answer")
async def ask(req: QuestionRequest):
    engine = get_qa_engine()
    session_id = req.session_id or str(uuid.uuid4())

    result = await engine.answer(
        query=req.question,
        session_id=session_id,
        top_k=req.top_k,
        source_filter=req.source_filter,
        use_memory=req.use_memory,
        max_tokens=req.max_tokens,
    )
    return result


@router.post("/stream", summary="Stream a grounded answer (SSE)")
async def stream_answer(req: QuestionRequest):
    engine = get_qa_engine()
    session_id = req.session_id or str(uuid.uuid4())

    async def event_generator():
        async for chunk in engine.stream_answer(
            query=req.question,
            session_id=session_id,
            top_k=req.top_k,
        ):
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Memory Routes ───────────────────────────────────────────────────────────

@router.get("/sessions", summary="List all conversation sessions")
async def list_sessions():
    mgr = get_memory_manager()
    return {"sessions": mgr.list_sessions()}


@router.get("/sessions/{session_id}", summary="Get conversation history")
async def get_session(session_id: str):
    mgr = get_memory_manager()
    session = mgr.get_session(session_id)
    return {
        "session_id": session_id,
        "history": session.get_full_history(),
        "summary": session.summary(),
    }


@router.delete("/sessions/{session_id}", summary="Clear a conversation session")
async def clear_session(session_id: str):
    mgr = get_memory_manager()
    mgr.delete_session(session_id)
    return {"deleted": session_id}
