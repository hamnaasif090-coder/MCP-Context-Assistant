# 🧠 MCP-Inspired AI Context Retrieval Assistant

A production-ready RAG (Retrieval-Augmented Generation) system with MCP-style architecture.
Upload Markdown docs, index them, and ask AI questions grounded in your knowledge base.

**100% free to run** — uses local embeddings (sentence-transformers) + ChromaDB + Ollama or your own Anthropic key.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                          │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  /documents  │  │   /search    │  │     /qa      │             │
│  │   Upload     │  │  Semantic    │  │  Grounded    │             │
│  │   Index      │  │   Search     │  │  Q&A + Chat  │             │
│  │   Delete     │  │  Tool Call   │  │  Streaming   │             │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │
│         │                 │                  │                      │
│         ▼                 ▼                  ▼                      │
│  ┌──────────────────────────────────────────────────────┐          │
│  │            Retrieval Orchestrator (MCP-style)        │          │
│  │                                                      │          │
│  │  ┌─────────────────┐    ┌──────────────────────┐    │          │
│  │  │ PromptGuardrails│    │   ContextManager     │    │          │
│  │  │  - Injection    │    │  - Token budgeting   │    │          │
│  │  │    detection    │    │  - De-duplication    │    │          │
│  │  │  - Length check │    │  - Source headers    │    │          │
│  │  │  - Blocklist    │    │  - Relevance ranking │    │          │
│  │  └─────────────────┘    └──────────────────────┘    │          │
│  │                                                      │          │
│  │  MCP Tool Definitions:                               │          │
│  │    • retrieve_context   • list_documents             │          │
│  │    • get_memory                                      │          │
│  └──────────────────────────┬───────────────────────────┘          │
│                             │                                       │
│         ┌───────────────────┼──────────────────┐                   │
│         ▼                   ▼                  ▼                   │
│  ┌─────────────┐  ┌──────────────────┐  ┌──────────────┐          │
│  │  VectorStore │  │  EmbeddingService│  │  LLM Service │          │
│  │  (ChromaDB)  │  │ (sentence-transf)│  │  Anthropic / │          │
│  │  Persistent  │  │  all-MiniLM-L6   │  │  Ollama /    │          │
│  │  cosine sim  │  │  FREE local      │  │  Mock        │          │
│  └─────────────┘  └──────────────────┘  └──────────────┘          │
│                                                                     │
│  ┌──────────────────────────────────────────────────────┐          │
│  │                   Memory Manager                     │          │
│  │     Per-session JSON files in /memory/               │          │
│  │     Sliding window · Source citations · Timestamps   │          │
│  └──────────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

### Context Retrieval Flow

```
User Query
    │
    ▼
[PromptGuardrails]──✗──▶ Blocked response
    │ ✓
    ▼
[EmbeddingService]
  Encode query → 384-dim vector (free local model)
    │
    ▼
[VectorStore.query()]
  Cosine similarity search → top-K chunks
    │
    ▼
[ContextManager.build_context()]
  - Rank by score
  - Deduplicate
  - Trim to token budget (3000 tokens default)
  - Add source headers
    │
    ▼
[MemoryManager] → prepend conversation history
    │
    ▼
[LLM.complete()]
  System prompt + context + history + query → Answer
    │
    ▼
[MemoryManager.add()] → persist turn
    │
    ▼
Response with answer + sources + metadata
```

---

## Folder Structure

```
mcp-assistant/
├── main.py                    # FastAPI app entrypoint
├── config.py                  # Settings (pydantic-settings)
├── logger.py                  # Loguru structured logging
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── railway.toml               # Railway.app deployment
├── render.yaml                # Render.com deployment
├── Procfile                   # Heroku/Railway
├── .env.example
│
├── api/
│   ├── embeddings.py          # Free local embeddings (sentence-transformers)
│   ├── vector_store.py        # ChromaDB wrapper
│   ├── ingestion.py           # Markdown parser + chunker
│   ├── retrieval.py           # MCP Orchestrator + ContextManager + Guardrails
│   ├── llm.py                 # Anthropic / Ollama / Mock providers
│   ├── qa_engine.py           # Full RAG pipeline
│   └── routes/
│       ├── documents.py       # Upload, index, delete
│       ├── search.py          # Semantic search, tool calls
│       ├── qa.py              # Q&A, streaming, memory
│       └── context.py         # Context inspection
│
├── memory/
│   └── manager.py             # Session memory (JSON persistence)
│
├── prompts/
│   └── templates.py           # System prompts, guardrail definitions
│
├── knowledge_base/            # Your Markdown docs go here
├── sample_docs/               # Pre-loaded example documents
├── vector_store/              # ChromaDB persisted data (auto-created)
├── memory/                    # Session JSON files (auto-created)
├── logs/                      # Log files (auto-created)
├── context/                   # Context snapshots (auto-created)
└── static/
    └── index.html             # Web UI
```

---

## Quick Start

### Option A — Local with Ollama (fully free, no API key)

```bash
# 1. Clone / download the project
cd mcp-assistant

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy env config
cp .env.example .env
# Edit .env: set LLM_PROVIDER=ollama

# 5. Install & start Ollama (https://ollama.com)
ollama pull llama3              # or mistral, phi3, gemma2
ollama serve                    # runs on localhost:11434

# 6. Start the API
uvicorn main:app --reload --port 8000

# 7. Open browser
open http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Option B — With Anthropic Claude

```bash
cp .env.example .env
# Edit .env:
#   LLM_PROVIDER=anthropic
#   ANTHROPIC_API_KEY=sk-ant-...
#   LLM_MODEL=claude-haiku-4-5-20251001   ← cheapest/fastest

uvicorn main:app --reload --port 8000
```

### Option C — Docker Compose (Ollama + App)

```bash
docker-compose up --build
# App: http://localhost:8000
# Ollama: http://localhost:11434

# Pull a model into the Ollama container:
docker exec -it mcp-assistant-ollama-1 ollama pull llama3
```

---

## API Reference

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/documents/upload` | Upload & index a `.md` file |
| `POST` | `/api/v1/documents/bulk-index` | Re-index all `knowledge_base/` docs |
| `GET`  | `/api/v1/documents/list` | List indexed documents |
| `GET`  | `/api/v1/documents/stats` | Index statistics |
| `DELETE` | `/api/v1/documents/{filename}` | Remove document from index |

### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/search/query` | Semantic vector search |
| `POST` | `/api/v1/search/tool-call` | MCP-style tool dispatch |
| `GET`  | `/api/v1/search/tools` | List available MCP tools |
| `GET`  | `/api/v1/search/similar?text=…` | Find similar chunks |

### Q&A

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/qa/ask` | Grounded Q&A with context injection |
| `POST` | `/api/v1/qa/stream` | Streaming answer (SSE) |
| `GET`  | `/api/v1/qa/sessions` | List conversation sessions |
| `GET`  | `/api/v1/qa/sessions/{id}` | Get session history |
| `DELETE` | `/api/v1/qa/sessions/{id}` | Clear session memory |

### Context

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/context/build` | Build context for a query |
| `POST` | `/api/v1/context/guardrail-check` | Test prompt safety |
| `GET`  | `/api/v1/context/context-window-info` | Token budget info |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/health` | Health check + stats |
| `GET`  | `/docs`   | Swagger UI |
| `GET`  | `/redoc`  | ReDoc reference |

### Example Requests

```bash
# Upload a document
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@my_doc.md"

# Semantic search
curl -X POST http://localhost:8000/api/v1/search/query \
  -H "Content-Type: application/json" \
  -d '{"query": "what is the time off policy", "top_k": 5}'

# Ask a question
curl -X POST http://localhost:8000/api/v1/qa/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How many days of PTO do employees get?",
    "session_id": "my-session-123",
    "top_k": 5
  }'

# MCP Tool call
curl -X POST http://localhost:8000/api/v1/search/tool-call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "retrieve_context", "parameters": {"query": "security requirements"}}'
```

---

## Free Deployment Options

### 1. Railway.app (Recommended — easiest)

```bash
# Install Railway CLI
npm install -g @railway/cli

railway login
railway init
railway up

# Set env vars in Railway dashboard:
# ANTHROPIC_API_KEY=sk-ant-...  (or use Ollama add-on)
# LLM_PROVIDER=anthropic
```

**Free tier**: 500 hours/month, 512 MB RAM, custom domain.
URL: `https://your-app.railway.app`

---

### 2. Render.com

1. Push code to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your repo
4. Render auto-detects `render.yaml`
5. Add `ANTHROPIC_API_KEY` in Environment tab
6. Deploy

**Free tier**: 750 hours/month, spins down after 15min inactivity.

---

### 3. Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

fly auth login
fly launch        # auto-detects Dockerfile
fly secrets set ANTHROPIC_API_KEY=sk-ant-...
fly deploy
```

**Free tier**: 3 shared VMs, 256 MB RAM each, 3 GB storage.

---

### 4. Hugging Face Spaces (Gradio/Docker)

1. Create a new Space → Docker SDK
2. Upload all files
3. Add `ANTHROPIC_API_KEY` in Space secrets
4. HF Spaces runs the Dockerfile automatically

**Free tier**: Always-on CPU spaces, GPU available for paid.

---

### 5. Google Cloud Run (free tier)

```bash
gcloud builds submit --tag gcr.io/PROJECT/mcp-assistant
gcloud run deploy mcp-assistant \
  --image gcr.io/PROJECT/mcp-assistant \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars ANTHROPIC_API_KEY=sk-ant-...
```

**Free tier**: 2M requests/month, 360K CPU-seconds.

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `anthropic` | `anthropic` or `ollama` |
| `LLM_MODEL` | `claude-haiku-4-5-20251001` | Model name |
| `ANTHROPIC_API_KEY` | – | Your Anthropic key |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Free local model (80 MB) |
| `TOP_K_RESULTS` | `5` | Chunks retrieved per query |
| `SIMILARITY_THRESHOLD` | `0.3` | Min cosine similarity |
| `MAX_CONTEXT_TOKENS` | `3000` | Token budget for context |
| `MEMORY_MAX_TURNS` | `10` | Conversation turns to keep |

---

## Adding Your Own Documents

Drop any `.md` file in `knowledge_base/` then:

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/documents/bulk-index

# Or via CLI (if you add docs while server is stopped)
python -c "
from api.ingestion import bulk_ingest_directory
from pathlib import Path
bulk_ingest_directory(Path('./knowledge_base'))
"
```

Frontmatter is supported and indexed as metadata:

```markdown
---
title: My Document
category: Engineering
author: Alice
---

# Content starts here...
```

---

## MCP Tool Calling

The system simulates MCP-style tool calling. You can dispatch tools via API:

```json
POST /api/v1/search/tool-call
{
  "tool_name": "retrieve_context",
  "parameters": {
    "query": "what is the incident response process",
    "top_k": 3,
    "source_filter": "engineering_standards.md"
  }
}
```

Available tools:
- `retrieve_context` — semantic search + context assembly
- `list_documents` — list all indexed sources
- `get_memory` — retrieve session history

---

## Tech Stack (all free/open source)

| Component | Technology | Cost |
|-----------|-----------|------|
| API Framework | FastAPI + Uvicorn | Free |
| Vector DB | ChromaDB (in-process) | Free |
| Embeddings | sentence-transformers (local) | Free |
| LLM (option A) | Ollama + llama3/mistral | Free |
| LLM (option B) | Anthropic Claude | Pay per token |
| Memory | JSON files | Free |
| Logging | Loguru | Free |
| Deployment | Railway / Render / Fly.io | Free tier |

---

## License

MIT — free to use, modify, and deploy.
