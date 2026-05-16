"""
api/routes/search.py
Semantic search and context retrieval endpoints.
"""
from __future__ import annotations
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.retrieval import get_orchestrator, MCP_TOOLS
from logger import logger

router = APIRouter(prefix="/search", tags=["Search & Retrieval"])


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(5, ge=1, le=20)
    source_filter: Optional[str] = None


class ToolCallRequest(BaseModel):
    tool_name: str
    parameters: dict = {}


class SearchHit(BaseModel):
    text: str
    metadata: dict
    score: float


@router.post("/query", summary="Semantic search over indexed documents")
async def semantic_search(req: SearchRequest):
    orchestrator = get_orchestrator()
    result = orchestrator.retrieve(
        query=req.query,
        top_k=req.top_k,
        source_filter=req.source_filter,
    )
    if result["status"] == "blocked":
        raise HTTPException(400, result["reason"])
    return result


@router.post("/tool-call", summary="MCP-style tool dispatch")
async def tool_call(req: ToolCallRequest):
    """
    Simulates MCP tool calling architecture.
    Supported tools: retrieve_context, list_documents
    """
    orchestrator = get_orchestrator()
    result = orchestrator.tool_dispatch(req.tool_name, req.parameters)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.get("/tools", summary="List available MCP tools")
async def list_tools():
    return {"tools": MCP_TOOLS}


@router.get("/similar", summary="Find similar chunks to a text snippet")
async def find_similar(text: str, top_k: int = 5):
    orchestrator = get_orchestrator()
    result = orchestrator.retrieve(query=text, top_k=top_k)
    return {
        "hits": result["hits"],
        "hit_count": result["hit_count"],
    }
