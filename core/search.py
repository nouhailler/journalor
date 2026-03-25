"""Full-text search over decrypted entries."""

from core.encryption import EncryptionManager
from core.database import Database


class SearchEngine:
    """Decrypts entries in memory for full-text search."""

    def __init__(self, db: Database, enc: EncryptionManager):
        self.db = db
        self.enc = enc

    def search(self, query: str, max_results: int = 100) -> list[dict]:
        """Search query across title and decrypted content."""
        query_lower = query.lower().strip()
        if not query_lower:
            return []

        entries = self.db.list_entries(limit=500)
        results = []

        for row in entries:
            title = (row["title"] or "").lower()
            # Try to decrypt content for full-text search
            content = ""
            if row["content_encrypted"] and self.enc.is_unlocked():
                try:
                    content = self.enc.decrypt(row["content_encrypted"]).lower()
                except Exception:
                    pass

            if query_lower in title or query_lower in content:
                # Build snippet
                snippet = ""
                if query_lower in content:
                    idx = content.find(query_lower)
                    start = max(0, idx - 60)
                    end = min(len(content), idx + len(query_lower) + 60)
                    snippet = "…" + content[start:end] + "…"
                results.append({
                    "id": row["id"],
                    "date": row["date"],
                    "time": row["time"],
                    "title": row["title"] or "",
                    "snippet": snippet,
                    "word_count": row["word_count"],
                    "emoji": row["emoji"] or "",
                })
                if len(results) >= max_results:
                    break

        return results
