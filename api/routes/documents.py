"""
api/routes/documents.py
Document upload and management endpoints.
"""
from __future__ import annotations
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional

from api.ingestion import ingest_markdown, bulk_ingest_directory
from api.vector_store import get_vector_store
from logger import logger

router = APIRouter(prefix="/documents", tags=["Documents"])
KNOWLEDGE_BASE_DIR = Path("./knowledge_base")
KNOWLEDGE_BASE_DIR.mkdir(exist_ok=True)


class DocumentInfo(BaseModel):
    filename: str
    chunks: int
    status: str


@router.post("/upload", summary="Upload a Markdown document and index it")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.endswith(".md"):
        raise HTTPException(400, "Only .md (Markdown) files are supported")

    content = (await file.read()).decode("utf-8")

    # Save to knowledge_base directory
    dest = KNOWLEDGE_BASE_DIR / file.filename
    dest.write_text(content, encoding="utf-8")

    try:
        result = ingest_markdown(content, file.filename)
        logger.info(f"Uploaded & indexed: {file.filename}")
        return result
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(500, f"Indexing failed: {str(e)}")


@router.post("/bulk-index", summary="Re-index all docs in knowledge_base/")
async def bulk_index():
    results = bulk_ingest_directory(KNOWLEDGE_BASE_DIR)
    total = sum(r.get("chunks", 0) for r in results)
    return {"indexed": len(results), "total_chunks": total, "results": results}


@router.get("/list", summary="List all indexed documents")
async def list_documents():
    store = get_vector_store()
    return {
        "documents": store.list_sources(),
        "total_chunks": store.count(),
    }


@router.delete("/{filename}", summary="Delete a document from the index")
async def delete_document(filename: str):
    store = get_vector_store()
    removed = store.delete_by_source(filename)

    # Also remove from disk if present
    disk_path = KNOWLEDGE_BASE_DIR / filename
    if disk_path.exists():
        disk_path.unlink()

    if removed == 0:
        raise HTTPException(404, f"Document '{filename}' not found in index")

    return {"deleted": filename, "chunks_removed": removed}


@router.get("/stats", summary="Vector store statistics")
async def stats():
    store = get_vector_store()
    sources = store.list_sources()
    return {
        "total_chunks": store.count(),
        "total_documents": len(sources),
        "documents": sources,
    }
