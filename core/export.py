"""Export entries to TXT, Markdown, PDF, JSON."""

import json
from pathlib import Path
from datetime import datetime

from core.database import Database
from core.encryption import EncryptionManager
from utils.formatters import format_date_display, format_duration


class Exporter:
    def __init__(self, db: Database, enc: EncryptionManager):
        self.db = db
        self.enc = enc

    def _decrypt(self, row) -> str:
        if row["content_encrypted"] and self.enc.is_unlocked():
            try:
                return self.enc.decrypt(row["content_encrypted"])
            except Exception:
                return "[Contenu non déchiffrable]"
        return ""

    def export_txt(self, entry_ids: list[int], output_path: Path) -> None:
        lines = []
        for eid in entry_ids:
            row = self.db.get_entry(eid)
            if not row:
                continue
            content = self._decrypt(row)
            title = row["title"] or "Sans titre"
            date_fmt = format_date_display(row["date"])
            lines.append(f"{'='*60}")
            lines.append(f"{title}")
            lines.append(f"{date_fmt} à {row['time'][:5]}")
            lines.append(f"{'='*60}")
            lines.append(content)
            lines.append("")
        output_path.write_text("\n".join(lines), encoding="utf-8")

    def export_markdown(self, entry_ids: list[int], output_path: Path) -> None:
        lines = []
        for eid in entry_ids:
            row = self.db.get_entry(eid)
            if not row:
                continue
            content = self._decrypt(row)
            title = row["title"] or "Sans titre"
            date_fmt = format_date_display(row["date"])
            emoji = row["emoji"] or ""
            tags = self.db.get_entry_tags(eid)
            tag_str = " ".join(f"`{t['name']}`" for t in tags)

            lines.append(f"# {emoji} {title}")
            lines.append(f"**Date:** {date_fmt} à {row['time'][:5]}  ")
            if tag_str:
                lines.append(f"**Tags:** {tag_str}  ")
            lines.append(f"**Durée:** {format_duration(row['duration'])}  ")
            lines.append("")
            lines.append(content)
            lines.append("")
            lines.append("---")
            lines.append("")
        output_path.write_text("\n".join(lines), encoding="utf-8")

    def export_pdf(self, entry_ids: list[int], output_path: Path) -> None:
        try:
            from fpdf import FPDF
        except ImportError:
            raise RuntimeError("fpdf2 not installed. Run: pip install fpdf2")

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)

        for eid in entry_ids:
            row = self.db.get_entry(eid)
            if not row:
                continue
            content = self._decrypt(row)
            title = row["title"] or "Sans titre"
            date_fmt = format_date_display(row["date"])

            pdf.set_font("Helvetica", style="B", size=14)
            pdf.cell(0, 10, title, ln=True)
            pdf.set_font("Helvetica", style="I", size=10)
            pdf.cell(0, 8, f"{date_fmt}  {row['time'][:5]}", ln=True)
            pdf.set_font("Helvetica", size=11)
            pdf.ln(3)
            pdf.multi_cell(0, 7, content)
            pdf.ln(6)
            pdf.set_draw_color(200, 200, 200)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(6)

        pdf.output(str(output_path))

    def export_json(self, entry_ids: list[int], output_path: Path) -> None:
        data = []
        for eid in entry_ids:
            row = self.db.get_entry(eid)
            if not row:
                continue
            content = self._decrypt(row)
            tags = [t["name"] for t in self.db.get_entry_tags(eid)]
            data.append({
                "id": row["id"],
                "date": row["date"],
                "time": row["time"],
                "title": row["title"] or "",
                "content": content,
                "emoji": row["emoji"] or "",
                "tags": tags,
                "duration": row["duration"],
                "word_count": row["word_count"],
                "audio_path": row["audio_path"] or "",
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            })
        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def import_json(self, input_path: Path) -> int:
        """Import entries from a JSON backup. Returns count imported."""
        raw = json.loads(input_path.read_text(encoding="utf-8"))
        imported = 0
        for item in raw:
            content = item.get("content", "")
            encrypted = self.enc.encrypt(content) if content else b""
            eid = self.db.add_entry(
                date=item.get("date", ""),
                time=item.get("time", "00:00:00"),
                content_encrypted=encrypted,
                title=item.get("title", ""),
                audio_path=item.get("audio_path", ""),
                duration=item.get("duration", 0.0),
                word_count=item.get("word_count", 0),
                emoji=item.get("emoji", ""),
            )
            # Re-attach tags
            tag_ids = []
            for tag_name in item.get("tags", []):
                row = self.db.conn.execute(
                    "SELECT id FROM tags WHERE name=?", (tag_name,)
                ).fetchone()
                if row:
                    tag_ids.append(row["id"])
                else:
                    tid = self.db.add_tag(tag_name)
                    tag_ids.append(tid)
            if tag_ids:
                self.db.set_entry_tags(eid, tag_ids)
            imported += 1
        return imported
