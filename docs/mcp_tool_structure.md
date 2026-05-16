# MCP Tool Calling Structure

This document describes the simulated MCP (Model Context Protocol) tool-calling
architecture implemented in this system.

## Overview

The system exposes a tool dispatcher at `POST /api/v1/search/tool-call` that
accepts a tool name and parameters, executes the tool, and returns structured results.
This mirrors how a real MCP server would expose capabilities to an AI model.

## Available Tools

### `retrieve_context`

Semantically searches the knowledge base and returns ranked, context-ready chunks.

**Request:**
```json
{
  "tool_name": "retrieve_context",
  "parameters": {
    "query": "what is the incident response process",
    "top_k": 5,
    "source_filter": "engineering_standards.md"
  }
}
```

**Response:**
```json
{
  "status": "ok",
  "query": "what is the incident response process",
  "hits": [
    {
      "text": "SEV1: Complete outage — page on-call immediately...",
      "metadata": {
        "source": "engineering_standards.md",
        "section": "Incident Response",
        "chunk_index": 12
      },
      "score": 0.847
    }
  ],
  "context": "## Retrieved Context\n\n[Source: engineering_standards.md ...]",
  "hit_count": 3,
  "token_estimate": 420
}
```

---

### `list_documents`

Lists all sources currently indexed in the vector store.

**Request:**
```json
{
  "tool_name": "list_documents",
  "parameters": {}
}
```

**Response:**
```json
{
  "sources": [
    "engineering_standards.md",
    "onboarding_guide.md",
    "security_policy.md"
  ],
  "total": 247
}
```

---

### `get_memory`

Retrieves conversation history for a given session.

**Request:**
```json
{
  "tool_name": "get_memory",
  "parameters": {
    "session_id": "abc-123-def"
  }
}
```

**Response:**
```json
{
  "sources": [],
  "session_id": "abc-123-def",
  "turns": 4
}
```

---

## Tool Schema (OpenAPI-compatible)

```json
[
  {
    "name": "retrieve_context",
    "description": "Search the knowledge base for documents relevant to a query.",
    "parameters": {
      "type": "object",
      "properties": {
        "query":         { "type": "string",  "description": "The search query" },
        "top_k":         { "type": "integer", "description": "Number of results", "default": 5 },
        "source_filter": { "type": "string",  "description": "Filter by filename" }
      },
      "required": ["query"]
    }
  },
  {
    "name": "list_documents",
    "description": "List all indexed documents in the knowledge base.",
    "parameters": { "type": "object", "properties": {}, "required": [] }
  },
  {
    "name": "get_memory",
    "description": "Retrieve conversation history / memory.",
    "parameters": {
      "type": "object",
      "properties": {
        "session_id": { "type": "string" }
      },
      "required": ["session_id"]
    }
  }
]
```

---

## How It Flows in Practice

```
AI Model / Client
      │
      │  POST /api/v1/search/tool-call
      │  { "tool_name": "retrieve_context", "parameters": { "query": "..." } }
      ▼
RetrievalOrchestrator.tool_dispatch()
      │
      ├─ "retrieve_context" → orchestrator.retrieve(query, top_k, source_filter)
      │       │
      │       ├─ PromptGuardrails.validate(query)
      │       ├─ VectorStore.query(query_embedding, top_k)
      │       └─ ContextManager.build_context(hits)
      │
      ├─ "list_documents"  → VectorStore.list_sources()
      │
      └─ "get_memory"      → MemoryManager.get_session(session_id)

      │
      ▼
  Structured JSON response
  (injected into next LLM prompt)
```

---

## Extending with New Tools

To add a new MCP tool:

1. Add its schema to `MCP_TOOLS` list in `api/retrieval.py`
2. Add a handler branch in `RetrievalOrchestrator.tool_dispatch()`
3. Implement the underlying logic (can call any service)
4. The tool is immediately available at `/api/v1/search/tool-call`

Example — adding a `summarize_document` tool:

```python
# In MCP_TOOLS:
{
    "name": "summarize_document",
    "description": "Return a summary of a specific indexed document.",
    "parameters": {
        "type": "object",
        "properties": {
            "filename": {"type": "string"}
        },
        "required": ["filename"]
    }
}

# In tool_dispatch():
elif tool_name == "summarize_document":
    filename = params.get("filename")
    hits = self._store.query(f"summary of {filename}", top_k=10,
                             where={"source": filename})
    context = self._ctx_mgr.build_context(hits)
    return {"filename": filename, "summary_context": context}
```
