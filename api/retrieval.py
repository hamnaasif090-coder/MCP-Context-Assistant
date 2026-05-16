"""
api/retrieval.py
MCP-style Retrieval Orchestrator + Context Manager.

Architecture:
  Query → [RetrievalOrchestrator]
              ├─ VectorStore.query()
              ├─ ContextManager.build_context()
              └─ PromptGuardrails.validate()
"""
from __future__ import annotations
import re
from typing import List, Dict, Any, Optional

import tiktoken

from config import get_settings
from logger import logger
from api.vector_store import get_vector_store

settings = get_settings()

# Token counter (tiktoken is free, no API call)
try:
    _enc = tiktoken.get_encoding("cl100k_base")
    def count_tokens(text: str) -> int:
        return len(_enc.encode(text))
except Exception:
    def count_tokens(text: str) -> int:
        return len(text) // 4   # rough estimate


# ══════════════════════════════════════════════════════════════════════════════
# MCP Tool Definitions (simulated tool-calling schema)
# ══════════════════════════════════════════════════════════════════════════════

MCP_TOOLS = [
    {
        "name": "retrieve_context",
        "description": "Search the knowledge base for documents relevant to a query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
                "top_k": {"type": "integer", "description": "Number of results", "default": 5},
                "source_filter": {"type": "string", "description": "Filter by filename"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_documents",
        "description": "List all indexed documents in the knowledge base.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_memory",
        "description": "Retrieve conversation history / memory.",
        "parameters": {
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# Prompt Guardrails
# ══════════════════════════════════════════════════════════════════════════════

_BLOCKED_PATTERNS = [
    r"ignore (previous|all) instructions",
    r"you are now",
    r"jailbreak",
    r"DAN mode",
    r"<\s*script",
    r"(drop|delete|truncate)\s+(table|database)",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _BLOCKED_PATTERNS]


class PromptGuardrails:
    @staticmethod
    def validate(text: str) -> Dict[str, Any]:
        for pattern in _COMPILED:
            if pattern.search(text):
                return {
                    "safe": False,
                    "reason": f"Blocked pattern detected: {pattern.pattern}",
                }
        if len(text) > 8000:
            return {"safe": False, "reason": "Query exceeds maximum length (8000 chars)"}
        return {"safe": True, "reason": None}


# ══════════════════════════════════════════════════════════════════════════════
# Context Manager
# ══════════════════════════════════════════════════════════════════════════════

class ContextManager:
    """
    Assembles retrieved chunks into a token-budget-aware context string.
    De-duplicates, ranks by score, and trims to MAX_CONTEXT_TOKENS.
    """

    def build_context(
        self,
        hits: List[Dict[str, Any]],
        max_tokens: int = None,
    ) -> str:
        max_tokens = max_tokens or settings.max_context_tokens
        seen = set()
        context_parts: List[str] = []
        used_tokens = 0

        for hit in hits:
            text = hit["text"].strip()
            if text in seen:
                continue
            seen.add(text)

            meta = hit.get("metadata", {})
            source = meta.get("source", "unknown")
            section = meta.get("section", "")
            score = hit.get("score", 0)

            header = f"[Source: {source}"
            if section:
                header += f" | Section: {section}"
            header += f" | Relevance: {score:.2f}]"

            chunk = f"{header}\n{text}"
            chunk_tokens = count_tokens(chunk)

            if used_tokens + chunk_tokens > max_tokens:
                break

            context_parts.append(chunk)
            used_tokens += chunk_tokens

        return "\n\n---\n\n".join(context_parts)

    def format_for_prompt(self, context: str) -> str:
        if not context.strip():
            return "No relevant context found in the knowledge base."
        return (
            "## Retrieved Context\n\n"
            "The following information was retrieved from the knowledge base:\n\n"
            f"{context}\n\n"
            "---\n"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Retrieval Orchestrator
# ══════════════════════════════════════════════════════════════════════════════

class RetrievalOrchestrator:
    """
    Central MCP-style orchestrator.
    Coordinates: guardrails → vector search → context assembly.
    """

    def __init__(self):
        self._store = get_vector_store()
        self._ctx_mgr = ContextManager()
        self._guardrails = PromptGuardrails()

    def retrieve(
        self,
        query: str,
        top_k: int = None,
        source_filter: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        # 1. Guardrails check
        guard = self._guardrails.validate(query)
        if not guard["safe"]:
            logger.warning(f"Query blocked: {guard['reason']}")
            return {
                "status": "blocked",
                "reason": guard["reason"],
                "hits": [],
                "context": "",
            }

        # 2. Vector search
        where = {"source": source_filter} if source_filter else None
        hits = self._store.query(query, top_k=top_k or settings.top_k_results, where=where)
        logger.info(f"Retrieved {len(hits)} chunks for query: {query[:60]}…")

        # 3. Build context
        context = self._ctx_mgr.build_context(hits)
        formatted_context = self._ctx_mgr.format_for_prompt(context)

        return {
            "status": "ok",
            "query": query,
            "hits": hits,
            "context": formatted_context,
            "raw_context": context,
            "hit_count": len(hits),
            "token_estimate": count_tokens(formatted_context),
        }

    def tool_dispatch(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """MCP-style tool dispatcher."""
        if tool_name == "retrieve_context":
            return self.retrieve(**params)
        elif tool_name == "list_documents":
            return {"sources": self._store.list_sources(), "total": self._store.count()}
        else:
            return {"error": f"Unknown tool: {tool_name}"}


_orchestrator: Optional[RetrievalOrchestrator] = None


def get_orchestrator() -> RetrievalOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = RetrievalOrchestrator()
    return _orchestrator
