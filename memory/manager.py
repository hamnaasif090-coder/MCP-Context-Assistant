"""
memory/manager.py
In-process conversation memory.
Persists to JSON files in /memory directory.
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from config import get_settings
from logger import logger

settings = get_settings()
MEMORY_DIR = Path("./memory")
MEMORY_DIR.mkdir(exist_ok=True)


class ConversationMemory:
    """
    Stores per-session conversation turns.
    Each turn: {role, content, timestamp, context_used}.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._path = MEMORY_DIR / f"{session_id}.json"
        self._turns: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except Exception:
                pass
        return []

    def _save(self):
        self._path.write_text(json.dumps(self._turns, indent=2))

    def add(self, role: str, content: str, context_used: Optional[str] = None):
        self._turns.append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "context_used": context_used,
        })
        # Trim to max turns
        max_turns = settings.memory_max_turns * 2  # user + assistant pairs
        if len(self._turns) > max_turns:
            self._turns = self._turns[-max_turns:]
        self._save()

    def get_messages(self) -> List[Dict[str, str]]:
        """Return as [{role, content}] for LLM API."""
        return [{"role": t["role"], "content": t["content"]} for t in self._turns]

    def get_full_history(self) -> List[Dict[str, Any]]:
        return self._turns.copy()

    def clear(self):
        self._turns = []
        if self._path.exists():
            self._path.unlink()

    def summary(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turns": len(self._turns),
            "created": self._turns[0]["timestamp"] if self._turns else None,
            "last_active": self._turns[-1]["timestamp"] if self._turns else None,
        }


class MemoryManager:
    """Registry of active session memories."""

    def __init__(self):
        self._sessions: Dict[str, ConversationMemory] = {}

    def get_session(self, session_id: str) -> ConversationMemory:
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationMemory(session_id)
        return self._sessions[session_id]

    def list_sessions(self) -> List[Dict[str, Any]]:
        sessions = []
        for path in MEMORY_DIR.glob("*.json"):
            mem = self.get_session(path.stem)
            sessions.append(mem.summary())
        return sessions

    def delete_session(self, session_id: str) -> bool:
        mem = self.get_session(session_id)
        mem.clear()
        self._sessions.pop(session_id, None)
        return True


_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
