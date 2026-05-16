"""
main.py – FastAPI application entrypoint
MCP-Inspired AI Context Retrieval Assistant
"""
import sys
import time
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

# Ensure parent directory is in path
sys.path.insert(0, str(Path(__file__).parent))

from config import get_settings
from logger import logger
from api.routes import documents, search, qa, context, admin

settings = get_settings()


# ── Startup / Shutdown ──────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 Starting {settings.app_name} v{settings.app_version}")

    # Ensure directories exist
    for d in ["knowledge_base", "memory", "context", "logs", "vector_store", "prompts"]:
        Path(d).mkdir(exist_ok=True)

    # Auto-index sample docs on first run
    from api.ingestion import bulk_ingest_directory
    from api.vector_store import get_vector_store
    store = get_vector_store()
    if store.count() == 0:
        sample_dir = Path("./sample_docs")
        kb_dir = Path("./knowledge_base")
        if sample_dir.exists():
            results = bulk_ingest_directory(sample_dir)
            logger.info(f"Auto-indexed {len(results)} sample documents")
        if kb_dir.exists():
            results = bulk_ingest_directory(kb_dir)
            logger.info(f"Auto-indexed {len(results)} knowledge base documents")

    logger.info(f"✅ {settings.app_name} ready")
    yield
    logger.info("👋 Shutting down")


# ── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "MCP-Inspired AI Context Retrieval Assistant. "
        "Upload docs, semantic search, context injection, grounded Q&A."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request timing middleware ───────────────────────────────────────────────
@app.middleware("http")
async def add_timing(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = round((time.time() - start) * 1000, 1)
    response.headers["X-Process-Time-Ms"] = str(elapsed)
    return response


# ── Routes ──────────────────────────────────────────────────────────────────
app.include_router(documents.router, prefix="/api/v1")
app.include_router(search.router,    prefix="/api/v1")
app.include_router(qa.router,        prefix="/api/v1")
app.include_router(context.router,   prefix="/api/v1")
app.include_router(admin.router,     prefix="/api/v1")

# Serve the web UI at /ui
static_dir = Path("./static")
if static_dir.exists():
    app.mount("/ui", StaticFiles(directory="static", html=True), name="static")


# ── Health & Root ───────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    from api.vector_store import get_vector_store
    store = get_vector_store()
    docs = len(store.list_sources())
    chunks = store.count()
    return f"""
<!DOCTYPE html>
<html>
<head>
  <title>{settings.app_name}</title>
  <style>
    body {{ font-family: 'Segoe UI', sans-serif; max-width: 800px; margin: 60px auto; padding: 20px; background: #0f0f1a; color: #e2e8f0; }}
    h1 {{ color: #7c3aed; font-size: 2em; }}
    .badge {{ display: inline-block; background: #1e1b4b; color: #a5b4fc; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; margin: 4px; }}
    .card {{ background: #1a1a2e; border: 1px solid #2d2d5e; border-radius: 12px; padding: 20px; margin: 16px 0; }}
    a {{ color: #818cf8; text-decoration: none; }} a:hover {{ color: #a5b4fc; }}
    code {{ background: #0d0d1a; padding: 2px 6px; border-radius: 4px; color: #34d399; }}
    .stat {{ font-size: 2em; font-weight: bold; color: #7c3aed; }}
  </style>
</head>
<body>
  <h1>🧠 {settings.app_name}</h1>
  <p>MCP-Inspired AI Context Retrieval Assistant — v{settings.app_version}</p>

  <div class="card">
    <div style="display:flex;gap:40px">
      <div><div class="stat">{docs}</div><div>Documents</div></div>
      <div><div class="stat">{chunks}</div><div>Chunks Indexed</div></div>
    </div>
  </div>

  <div class="card">
    <h3>Quick Links</h3>
    <a href="/docs">📖 Interactive API Docs (Swagger)</a><br><br>
    <a href="/redoc">📚 ReDoc API Reference</a><br><br>
    <a href="/health">💚 Health Check</a>
  </div>

  <div class="card">
    <h3>Key Endpoints</h3>
    <code>POST /api/v1/documents/upload</code> – Upload a Markdown doc<br><br>
    <code>POST /api/v1/search/query</code> – Semantic search<br><br>
    <code>POST /api/v1/qa/ask</code> – Grounded Q&A<br><br>
    <code>POST /api/v1/qa/stream</code> – Streaming answers<br><br>
    <code>POST /api/v1/search/tool-call</code> – MCP tool dispatch
  </div>

  <span class="badge">FastAPI</span>
  <span class="badge">ChromaDB</span>
  <span class="badge">Sentence-Transformers</span>
  <span class="badge">Free to deploy</span>
</body>
</html>
"""


@app.get("/health", tags=["Health"])
async def health():
    from api.vector_store import get_vector_store
    store = get_vector_store()
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "embedding_model": settings.embedding_model,
        "indexed_chunks": store.count(),
        "indexed_documents": len(store.list_sources()),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.debug)
