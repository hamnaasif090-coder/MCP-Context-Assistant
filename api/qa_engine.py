"""
api/qa_engine.py
Grounded Question-Answering engine.
Flow: query → retrieve → inject context → LLM → answer
"""
from __future__ import annotations
from typing import Dict, Any, Optional, List

from config import get_settings
from logger import logger
from api.retrieval import get_orchestrator
from api.llm import get_llm
from memory.manager import get_memory_manager
from prompts.templates import (
    SYSTEM_PROMPT,
    CHAT_SYSTEM_PROMPT,
    NO_CONTEXT_RESPONSE,
    CONTEXT_INJECTION_TEMPLATE,
)

settings = get_settings()


class QAEngine:
    """
    Orchestrates the full RAG pipeline:
    1. Retrieve context
    2. Inject into prompt
    3. Optionally include memory
    4. Call LLM
    5. Store to memory
    """

    def __init__(self):
        self._orchestrator = get_orchestrator()
        self._llm = get_llm()
        self._memory = get_memory_manager()

    async def answer(
        self,
        query: str,
        session_id: Optional[str] = None,
        top_k: int = None,
        source_filter: Optional[str] = None,
        use_memory: bool = True,
        max_tokens: int = 1024,
    ) -> Dict[str, Any]:

        # 1. Retrieve context
        retrieval = self._orchestrator.retrieve(
            query=query,
            top_k=top_k or settings.top_k_results,
            source_filter=source_filter,
        )

        if retrieval["status"] == "blocked":
            return {
                "answer": f"⛔ Query blocked: {retrieval['reason']}",
                "sources": [],
                "context_used": False,
                "session_id": session_id,
            }

        context = retrieval["context"]
        hits = retrieval["hits"]

        # 2. Build messages
        messages: List[Dict[str, str]] = []

        # Add memory history
        if use_memory and session_id:
            session = self._memory.get_session(session_id)
            history_msgs = session.get_messages()
            messages.extend(history_msgs)

        # Build the user message with injected context
        if hits:
            user_content = CONTEXT_INJECTION_TEMPLATE.format(
                context=retrieval["raw_context"],
                history="(see conversation above)" if messages else "No prior history.",
                question=query,
            )
            system = CHAT_SYSTEM_PROMPT
        else:
            user_content = query
            system = (
                CHAT_SYSTEM_PROMPT
                + "\n\nNote: No relevant context was found in the knowledge base for this query."
            )

        messages.append({"role": "user", "content": user_content})

        # 3. Call LLM
        try:
            answer_text = await self._llm.complete(
                messages=messages,
                system=system,
                max_tokens=max_tokens,
            )
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            answer_text = f"LLM error: {str(e)}"

        # 4. Store to memory
        if use_memory and session_id:
            session = self._memory.get_session(session_id)
            session.add("user", query)
            session.add("assistant", answer_text, context_used=retrieval["raw_context"][:200])

        # 5. Format sources
        sources = list({h["metadata"].get("source", "unknown") for h in hits})

        return {
            "answer": answer_text,
            "sources": sources,
            "hit_count": len(hits),
            "context_used": bool(hits),
            "token_estimate": retrieval["token_estimate"],
            "session_id": session_id,
        }

    async def stream_answer(
        self,
        query: str,
        session_id: Optional[str] = None,
        top_k: int = None,
    ):
        """Async generator for streaming responses."""
        retrieval = self._orchestrator.retrieve(query=query, top_k=top_k)

        if retrieval["status"] == "blocked":
            yield {"type": "error", "content": f"Query blocked: {retrieval['reason']}"}
            return

        hits = retrieval["hits"]
        messages = []

        if session_id:
            session = self._memory.get_session(session_id)
            messages.extend(session.get_messages())

        if hits:
            user_content = CONTEXT_INJECTION_TEMPLATE.format(
                context=retrieval["raw_context"],
                history="(see above)" if messages else "None",
                question=query,
            )
        else:
            user_content = query

        messages.append({"role": "user", "content": user_content})

        full_response = ""
        async for chunk in self._llm.stream(messages=messages, system=CHAT_SYSTEM_PROMPT):
            full_response += chunk
            yield {"type": "token", "content": chunk}

        sources = list({h["metadata"].get("source", "unknown") for h in hits})
        yield {"type": "done", "sources": sources, "hit_count": len(hits)}

        if session_id:
            session = self._memory.get_session(session_id)
            session.add("user", query)
            session.add("assistant", full_response)


_engine: QAEngine = None


def get_qa_engine() -> QAEngine:
    global _engine
    if _engine is None:
        _engine = QAEngine()
    return _engine
