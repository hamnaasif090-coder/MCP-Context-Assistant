"""
api/routes/context.py
Context inspection, context injection, and snapshot endpoints.
"""
from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.retrieval import get_orchestrator, ContextManager, PromptGuardrails
from context.snapshot import ContextSnapshot
from config import get_settings

router = APIRouter(prefix="/context", tags=["Context"])
settings = get_settings()


class ContextBuildRequest(BaseModel):
    query: str
    top_k: int = Field(5, ge=1, le=20)
    source_filter: Optional[str] = None
    format_for_prompt: bool = True


class GuardrailCheckRequest(BaseModel):
    text: str


@router.post("/build", summary="Retrieve and build context for a query")
async def build_context(req: ContextBuildRequest):
    orch = get_orchestrator()
    result = orch.retrieve(
        query=req.query,
        top_k=req.top_k,
        source_filter=req.source_filter,
    )
    return {
        "query": req.query,
        "context": result["context"] if req.format_for_prompt else result["raw_context"],
        "hits": result["hits"],
        "hit_count": result["hit_count"],
        "token_estimate": result["token_estimate"],
    }


@router.post("/guardrail-check", summary="Check if a query passes guardrails")
async def guardrail_check(req: GuardrailCheckRequest):
    result = PromptGuardrails.validate(req.text)
    return result


@router.get("/context-window-info", summary="Info about context window limits")
async def context_window_info():
    return {
        "max_context_tokens": settings.max_context_tokens,
        "top_k_results": settings.top_k_results,
        "similarity_threshold": settings.similarity_threshold,
        "memory_max_turns": settings.memory_max_turns,
        "embedding_model": settings.embedding_model,
        "llm_model": settings.llm_model,
    }


@router.get("/snapshots", summary="List saved context snapshots")
async def list_snapshots(limit: int = 20):
    return {"snapshots": ContextSnapshot.list_snapshots(limit=limit)}


@router.get("/snapshots/{filename}", summary="Load a specific context snapshot")
async def get_snapshot(filename: str):
    data = ContextSnapshot.load(filename)
    if not data:
        raise HTTPException(404, f"Snapshot '{filename}' not found")
    return data


@router.delete("/snapshots/cleanup", summary="Remove old snapshots")
async def cleanup_snapshots(older_than_days: int = 7):
    removed = ContextSnapshot.cleanup(older_than_days=older_than_days)
    return {"removed": removed, "older_than_days": older_than_days}
