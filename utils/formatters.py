"""Date/text formatting utilities."""

from datetime import datetime


def format_date_display(date_str: str) -> str:
    """Convert YYYY-MM-DD to 'Lundi 25 mars 2026'."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        months = [
            "janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre"
        ]
        return f"{days[dt.weekday()]} {dt.day} {months[dt.month - 1]} {dt.year}"
    except ValueError:
        return date_str


def format_time_display(time_str: str) -> str:
    """Convert HH:MM:SS to HH:MM."""
    try:
        return time_str[:5]
    except Exception:
        return time_str


def format_duration(seconds: float) -> str:
    """Format seconds as MM:SS or HH:MM:SS."""
    if seconds is None:
        return "0:00"
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_word_count(count: int) -> str:
    """Format word count with label."""
    if count is None:
        return "0 mot"
    return f"{count} mot{'s' if count > 1 else ''}"


def truncate_text(text: str, max_len: int = 120) -> str:
    """Truncate text with ellipsis."""
    if not text:
        return ""
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len - 1] + "…"


def count_words(text: str) -> int:
    """Count words in a text string."""
    if not text:
        return 0
    return len(text.split())


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def now_time_str() -> str:
    return datetime.now().strftime("%H:%M:%S")


def now_datetime_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
