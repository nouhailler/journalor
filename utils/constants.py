"""Shared constants for the Journalor application."""

APP_NAME = "Journalor"
APP_VERSION = "1.1.0"

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION = 0.1  # seconds per chunk
MAX_RECORDING_MINUTES = 30

# Silence detection
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION_DEFAULT = 3.0  # seconds

# Whisper / Distil-Whisper model catalogue
# key = model_id passé à faster-whisper
MODEL_CATALOG: dict[str, dict] = {
    "tiny": {
        "display": "Tiny",
        "ram": "~390 Mo",
        "speed": 5,   # barres sur 5
        "quality": 1,
        "pros": [
            "Quasi-instantané, même sur CPU lent",
            "RAM minimale (~390 Mo)",
            "Utile pour tester l'installation",
        ],
        "cons": [
            "Nombreuses erreurs en français",
            "Mauvaise gestion des accents et de la ponctuation",
            "À éviter pour un usage quotidien",
        ],
        "note": "",
    },
    "base": {
        "display": "Base",
        "ram": "~500 Mo",
        "speed": 4,
        "quality": 2,
        "pros": [
            "Rapide sur CPU modeste",
            "RAM très faible (~500 Mo)",
            "Convenable pour du vocabulaire courant",
        ],
        "cons": [
            "Approximatif sur les mots techniques ou rares",
            "Erreurs fréquentes sur les noms propres",
        ],
        "note": "",
    },
    "small": {
        "display": "Small",
        "ram": "~1 Go",
        "speed": 3,
        "quality": 3,
        "pros": [
            "Bonne précision pour le français courant",
            "Vitesse correcte (≈ 1-2× durée audio sur CPU)",
            "RAM raisonnable (~1 Go)",
        ],
        "cons": [
            "Peut rater les termes très spécialisés",
            "2-3× plus lent que Base",
        ],
        "note": "Bon choix d'entrée de gamme.",
    },
    "distil-whisper/distil-large-v3": {
        "display": "Distil-Large-v3  ⭐ Recommandé",
        "ram": "~1.5 Go",
        "speed": 3,
        "quality": 4,
        "pros": [
            "Précision quasi équivalente à Large-v3",
            "6× plus rapide que Large-v3",
            "Excellent en français : accents, ponctuation, noms propres",
            "Meilleur rapport vitesse / qualité disponible",
        ],
        "cons": [
            "Premier lancement : téléchargement ~800 Mo",
            "~1.5 Go RAM nécessaires",
        ],
        "note": "Idéal pour un usage quotidien en français.",
    },
    "medium": {
        "display": "Medium",
        "ram": "~2.5 Go",
        "speed": 2,
        "quality": 4,
        "pros": [
            "Très bonne précision générale",
            "Gère bien les accents et les termes spécialisés",
        ],
        "cons": [
            "Lent sur CPU (3-4× la durée de l'audio)",
            "2.5 Go RAM requis",
        ],
        "note": "",
    },
    "large-v2": {
        "display": "Large-v2",
        "ram": "~4.5 Go",
        "speed": 1,
        "quality": 5,
        "pros": [
            "Excellente précision toutes langues",
            "Gère parfaitement les termes techniques",
        ],
        "cons": [
            "Très lent sur CPU",
            "4.5 Go RAM minimum — GPU fortement recommandé",
        ],
        "note": "",
    },
    "large-v3": {
        "display": "Large-v3",
        "ram": "~4.5 Go",
        "speed": 1,
        "quality": 5,
        "pros": [
            "Meilleure précision disponible toutes langues",
            "Français irréprochable",
        ],
        "cons": [
            "Peut prendre plusieurs minutes par enregistrement sur CPU",
            "4.5 Go RAM minimum — GPU fortement recommandé",
        ],
        "note": "Réservé aux machines avec GPU.",
    },
}

WHISPER_MODELS = list(MODEL_CATALOG.keys())   # pour la rétrocompatibilité
WHISPER_DEFAULT = "distil-whisper/distil-large-v3"

# Security
PBKDF2_ITERATIONS = 480000
SALT_SIZE = 32

# UI colors (dark theme)
COLOR_BG = "#1a1a2e"
COLOR_SURFACE = "#16213e"
COLOR_SURFACE2 = "#0f3460"
COLOR_ACCENT = "#e94560"
COLOR_ACCENT_HOVER = "#c73652"
COLOR_TEXT = "#eaeaea"
COLOR_TEXT_MUTED = "#888888"
COLOR_SUCCESS = "#2ecc71"
COLOR_WARNING = "#f39c12"
COLOR_ERROR = "#e74c3c"
COLOR_RECORD = "#e74c3c"
COLOR_RECORD_ACTIVE = "#ff6b6b"

# Geometry
WINDOW_MIN_W = 1400
WINDOW_MIN_H = 900
WINDOW_DEFAULT_W = 1600
WINDOW_DEFAULT_H = 1000

# Inactivity lock (minutes)
AUTO_LOCK_DEFAULT = 10

# Default tags
DEFAULT_TAGS = [
    ("Travail", "#3498db"),
    ("Personnel", "#2ecc71"),
    ("Santé", "#e74c3c"),
    ("Idées", "#f39c12"),
    ("Famille", "#9b59b6"),
]
