#!/usr/bin/env python3
"""Journalor — Journal vocal personnel.
Point d'entrée de l'application.
"""

import sys
import logging
from pathlib import Path

# ── Configure logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("journalor")

# ── Resolve data directory ─────────────────────────────────────────────────────
def get_data_dir() -> Path:
    """Return the data directory, creating it if needed."""
    import json
    cfg_path = Path(__file__).parent / "config.json"
    default_dir = Path.home() / "journalor_data"

    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            d = Path(cfg.get("data_dir", default_dir))
        except Exception:
            d = default_dir
    else:
        d = default_dir
        cfg_path.write_text(json.dumps({"data_dir": str(d)}, indent=2))

    d.mkdir(parents=True, exist_ok=True)
    return d


def main():
    import customtkinter as ctk

    data_dir = get_data_dir()
    log.info("Data directory: %s", data_dir)

    # ── Database + encryption ──────────────────────────────────────────────────
    from core.database import Database
    from core.encryption import EncryptionManager

    db = Database(data_dir / "journal.db")
    enc = EncryptionManager()

    # ── CustomTkinter appearance ───────────────────────────────────────────────
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    # ── Root window (holds login + main) ──────────────────────────────────────
    root = ctk.CTk()
    root.title("Journalor")
    root.geometry("460x560")
    root.resizable(False, False)

    def launch_main(password: str):
        """Called after successful login."""
        root.destroy()

        # Update data_dir from settings if changed
        saved_dir = db.get_setting("save_dir")
        effective_dir = Path(saved_dir) if saved_dir else data_dir
        effective_dir.mkdir(parents=True, exist_ok=True)

        from gui.main_window import MainWindow
        app = MainWindow(db=db, enc=enc, data_dir=effective_dir)
        app.mainloop()

    # ── Login screen ───────────────────────────────────────────────────────────
    from gui.login_screen import LoginScreen

    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)

    login = LoginScreen(root, db=db, enc=enc, on_success=launch_main)
    login.grid(row=0, column=0, sticky="nsew")

    root.mainloop()


if __name__ == "__main__":
    main()
