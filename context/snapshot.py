"""
context/snapshot.py
Save and inspect context snapshots for debugging and audit purposes.
"""
from __future__ import annotations
import json
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List

CONTEXT_DIR = Path("./context")
CONTEXT_DIR.mkdir(exist_ok=True)


class ContextSnapshot:
    """
    Persists a context retrieval event for debugging and auditing.
    Saves query, hits, context, and answer to /context directory.
    """

    def __init__(
        self,
        query: str,
        hits: List[Dict[str, Any]],
        context: str,
        answer: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        self.snapshot_id = str(uuid.uuid4())[:8]
        self.timestamp = time.time()
        self.query = query
        self.hits = hits
        self.context = context
        self.answer = answer
        self.session_id = session_id

    def save(self) -> str:
        """Save snapshot to /context/. Returns filename."""
        ts = int(self.timestamp)
        filename = f"{ts}_{self.snapshot_id}.json"
        path = CONTEXT_DIR / filename

        data = {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "query": self.query,
            "hit_count": len(self.hits),
            "hits": [
                {
                    "score": h.get("score"),
                    "source": h.get("metadata", {}).get("source"),
                    "section": h.get("metadata", {}).get("section"),
                    "text_preview": h.get("text", "")[:200],
                }
                for h in self.hits
            ],
            "context_length": len(self.context),
            "answer_preview": (self.answer or "")[:500],
        }

        path.write_text(json.dumps(data, indent=2))
        return filename

    @staticmethod
    def list_snapshots(limit: int = 20) -> List[Dict[str, Any]]:
        snapshots = []
        for f in sorted(CONTEXT_DIR.glob("*.json"), reverse=True)[:limit]:
            try:
                data = json.loads(f.read_text())
                snapshots.append({
                    "filename": f.name,
                    "snapshot_id": data.get("snapshot_id"),
                    "timestamp": data.get("timestamp"),
                    "query": data.get("query", "")[:80],
                    "hit_count": data.get("hit_count", 0),
                    "session_id": data.get("session_id"),
                })
            except Exception:
                pass
        return snapshots

    @staticmethod
    def load(filename: str) -> Optional[Dict[str, Any]]:
        path = CONTEXT_DIR / filename
        if not path.exists():
            return None
        return json.loads(path.read_text())

    @staticmethod
    def cleanup(older_than_days: int = 7):
        """Remove snapshots older than N days."""
        cutoff = time.time() - (older_than_days * 86400)
        removed = 0
        for f in CONTEXT_DIR.glob("*.json"):
            try:
                ts = int(f.stem.split("_")[0])
                if ts < cutoff:
                    f.unlink()
                    removed += 1
            except Exception:
                pass
        return removed
