"""SQLite database management for Journalor."""

import sqlite3
import base64
from pathlib import Path
from datetime import datetime

from utils.constants import DEFAULT_TAGS
from utils.formatters import now_datetime_str


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = self._connect()
        return self._conn

    def _init_db(self) -> None:
        c = self.conn
        c.executescript("""
            CREATE TABLE IF NOT EXISTS entries (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                date            TEXT NOT NULL,
                time            TEXT NOT NULL,
                title           TEXT,
                content_encrypted BLOB,
                audio_path      TEXT,
                duration        REAL DEFAULT 0,
                word_count      INTEGER DEFAULT 0,
                emoji           TEXT DEFAULT '',
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tags (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                name  TEXT UNIQUE NOT NULL,
                color TEXT NOT NULL DEFAULT '#888888'
            );

            CREATE TABLE IF NOT EXISTS entry_tags (
                entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
                tag_id   INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                PRIMARY KEY (entry_id, tag_id)
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(date);
        """)
        c.commit()
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        for name, color in DEFAULT_TAGS:
            self.conn.execute(
                "INSERT OR IGNORE INTO tags (name, color) VALUES (?, ?)", (name, color)
            )
        self.conn.commit()

    # ── Settings ──────────────────────────────────────────────────────────────

    def get_setting(self, key: str, default=None) -> str | None:
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
        )
        self.conn.commit()

    # ── Entries ───────────────────────────────────────────────────────────────

    def add_entry(
        self,
        date: str,
        time: str,
        content_encrypted: bytes,
        title: str = "",
        audio_path: str = "",
        duration: float = 0.0,
        word_count: int = 0,
        emoji: str = "",
    ) -> int:
        now = now_datetime_str()
        cur = self.conn.execute(
            """INSERT INTO entries
               (date, time, title, content_encrypted, audio_path, duration,
                word_count, emoji, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (date, time, title, content_encrypted, audio_path, duration,
             word_count, emoji, now, now),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_entry(
        self,
        entry_id: int,
        content_encrypted: bytes,
        title: str = "",
        word_count: int = 0,
        emoji: str = "",
    ) -> None:
        self.conn.execute(
            """UPDATE entries
               SET content_encrypted=?, title=?, word_count=?, emoji=?, updated_at=?
               WHERE id=?""",
            (content_encrypted, title, word_count, emoji, now_datetime_str(), entry_id),
        )
        self.conn.commit()

    def delete_entry(self, entry_id: int) -> None:
        self.conn.execute("DELETE FROM entries WHERE id=?", (entry_id,))
        self.conn.commit()

    def get_entry(self, entry_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM entries WHERE id=?", (entry_id,)
        ).fetchone()

    def list_entries(self, limit: int = 200, offset: int = 0) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM entries ORDER BY date DESC, time DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()

    def entries_for_date(self, date: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM entries WHERE date=? ORDER BY time DESC", (date,)
        ).fetchall()

    def dates_with_entries(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT date FROM entries ORDER BY date"
        ).fetchall()
        return [r["date"] for r in rows]

    # ── Tags ──────────────────────────────────────────────────────────────────

    def list_tags(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM tags ORDER BY name").fetchall()

    def add_tag(self, name: str, color: str = "#888888") -> int:
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO tags (name, color) VALUES (?, ?)", (name, color)
        )
        self.conn.commit()
        return cur.lastrowid

    def set_entry_tags(self, entry_id: int, tag_ids: list[int]) -> None:
        self.conn.execute("DELETE FROM entry_tags WHERE entry_id=?", (entry_id,))
        for tid in tag_ids:
            self.conn.execute(
                "INSERT OR IGNORE INTO entry_tags (entry_id, tag_id) VALUES (?, ?)",
                (entry_id, tid),
            )
        self.conn.commit()

    def get_entry_tags(self, entry_id: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            """SELECT t.* FROM tags t
               JOIN entry_tags et ON et.tag_id = t.id
               WHERE et.entry_id = ?""",
            (entry_id,),
        ).fetchall()

    # ── Search (plaintext word_count + title) ─────────────────────────────────

    def search_entries(self, query: str) -> list[sqlite3.Row]:
        """Basic search on title field (content is encrypted)."""
        like = f"%{query}%"
        return self.conn.execute(
            """SELECT * FROM entries
               WHERE title LIKE ?
               ORDER BY date DESC, time DESC""",
            (like,),
        ).fetchall()

    # ── Stats ─────────────────────────────────────────────────────────────────

    def count_entries(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) as c FROM entries").fetchone()
        return row["c"]

    def total_words(self) -> int:
        row = self.conn.execute("SELECT SUM(word_count) as s FROM entries").fetchone()
        return row["s"] or 0

    def total_duration(self) -> float:
        row = self.conn.execute("SELECT SUM(duration) as s FROM entries").fetchone()
        return row["s"] or 0.0

    def weekly_counts(self, weeks: int = 12) -> list[dict]:
        """Returns entry count per week for the last N weeks."""
        rows = self.conn.execute(
            """SELECT strftime('%Y-%W', date) as week, COUNT(*) as count
               FROM entries
               GROUP BY week
               ORDER BY week DESC
               LIMIT ?""",
            (weeks,),
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
