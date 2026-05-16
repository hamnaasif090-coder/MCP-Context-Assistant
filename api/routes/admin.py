"""
api/routes/admin.py
Admin and system management endpoints.
"""
from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from config import get_settings
from api.vector_store import get_vector_store
from context.snapshot import ContextSnapshot
from memory.manager import get_memory_manager
from logger import logger

router = APIRouter(prefix="/admin", tags=["Admin"])
settings = get_settings()


def _require_key(x_api_key: Optional[str] = Header(None)):
    if settings.internal_api_key and x_api_key != settings.internal_api_key:
        raise HTTPException(403, "Invalid or missing X-API-Key header")


@router.post("/reindex", summary="Wipe and re-index all knowledge_base/ documents")
async def reindex(x_api_key: Optional[str] = Header(None)):
    _require_key(x_api_key)
    from api.ingestion import bulk_ingest_directory
    from pathlib import Path

    store = get_vector_store()
    # Clear all existing chunks
    for source in store.list_sources():
        store.delete_by_source(source)

    results = bulk_ingest_directory(Path("./knowledge_base"))
    sample_results = bulk_ingest_directory(Path("./sample_docs"))
    all_results = results + sample_results

    return {
        "reindexed": len([r for r in all_results if r.get("status") == "indexed"]),
        "total_chunks": store.count(),
        "results": all_results,
    }


@router.delete("/vector-store/reset", summary="Wipe entire vector store")
async def reset_vector_store(x_api_key: Optional[str] = Header(None)):
    _require_key(x_api_key)
    store = get_vector_store()
    sources = store.list_sources()
    for src in sources:
        store.delete_by_source(src)
    logger.warning("Vector store wiped by admin")
    return {"wiped": True, "documents_removed": len(sources)}


@router.get("/system-info", summary="Full system diagnostics")
async def system_info(x_api_key: Optional[str] = Header(None)):
    _require_key(x_api_key)
    import sys
    import platform
    from pathlib import Path

    store = get_vector_store()
    mem_mgr = get_memory_manager()

    return {
        "app": {"name": settings.app_name, "version": settings.app_version},
        "python": sys.version,
        "platform": platform.system(),
        "llm": {"provider": settings.llm_provider, "model": settings.llm_model},
        "embeddings": settings.embedding_model,
        "vector_store": {
            "chunks": store.count(),
            "documents": len(store.list_sources()),
            "persist_dir": settings.chroma_persist_dir,
        },
        "sessions": len(mem_mgr.list_sessions()),
        "snapshots": len(ContextSnapshot.list_snapshots(100)),
        "disk": {
            "knowledge_base": str(sum(f.stat().st_size for f in Path("./knowledge_base").glob("**/*.md")) if Path("./knowledge_base").exists() else 0),
        },
    }


@router.post("/cleanup", summary="Clean up old logs, snapshots, and memory")
async def cleanup(older_than_days: int = 7, x_api_key: Optional[str] = Header(None)):
    _require_key(x_api_key)
    snaps_removed = ContextSnapshot.cleanup(older_than_days)
    return {
        "snapshots_removed": snaps_removed,
        "older_than_days": older_than_days,
    }
