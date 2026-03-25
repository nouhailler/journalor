# 🎙️ Journalor

> **Journal vocal personnel — 100 % local, chiffré, open source.**

Journalor vous permet d'enregistrer votre voix, de transcrire automatiquement vos pensées grâce à l'IA Whisper, et de les conserver dans un journal personnel chiffré. Tout fonctionne **hors ligne**, sur votre machine Linux, sans aucune donnée envoyée sur Internet.

---

## ✨ Fonctionnalités

| Catégorie | Ce que Journalor fait |
|---|---|
| 🎤 **Enregistrement** | Capture votre voix depuis le micro, avec vumètre en temps réel |
| ⏸ **Pause / Reprise** | Mettez l'enregistrement en pause sans perdre le fil |
| 🔇 **Arrêt auto** | Détecte les silences et s'arrête automatiquement |
| 🎵 **Export MP3** | Compresse le WAV en MP3 128 kbps pour un archivage léger |
| 📝 **Transcription** | Utilise faster-whisper (Distil-Large-v3 recommandé) |
| ⏩ **Arrière-plan** | Continue à utiliser l'app pendant la transcription |
| 🔒 **Chiffrement** | AES-256-GCM + PBKDF2 — vos mots ne quittent jamais votre disque |
| 🏷️ **Tags colorés** | Organisez vos entrées avec des tags personnalisés |
| 😊 **Réactions emoji** | Associez un emoji à chaque entrée pour marquer votre humeur |
| 🔍 **Recherche** | Recherche plein-texte sur tous vos journaux (déchiffrement en mémoire) |
| 📊 **Statistiques** | Streak de jours consécutifs, graphique d'activité, totaux |
| 📤 **Export** | TXT, Markdown, PDF, JSON (import/export complet) |
| 📖 **Documentation** | Aide intégrée accessible depuis la barre latérale |

---

## 🖥️ Interface

```
┌─────────────────────────────────────────────────────────────┐
│  🎙️ Journalor  │                                            │
│                │   📋 Liste des entrées                      │
│  + Enregistrer │                                            │
│                │  😊 Matinée productive          2026-03-25  │
│  📋 Journal    │  🔥 Session créative             2026-03-24  │
│  📊 Stats      │  💡 Idée de projet               2026-03-23  │
│  ─────────────  │                                            │
│  ⚙️ Paramètres │                                            │
│  📤 Exporter   │                                            │
│  📖 Doc        │                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Installation

### Prérequis

- Python 3.10 ou supérieur
- Linux (testé sur Debian/Ubuntu)
- Microphone fonctionnel

### Étapes

```bash
# 1. Cloner le dépôt
git clone <url-du-repo> journalor
cd journalor

# 2. Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Lancer l'application
python main.py
```

> **Première utilisation :** Journalor vous demandera de créer un PIN. Ce PIN est la seule façon de déchiffrer vos données — conservez-le précieusement.

---

## 🤖 Modèles de transcription

| Modèle | RAM | Vitesse | Qualité | Recommandé ? |
|---|---|---|---|---|
| Tiny | ~390 Mo | ⚡⚡⚡⚡⚡ | ★☆☆☆☆ | Test uniquement |
| Base | ~500 Mo | ⚡⚡⚡⚡ | ★★☆☆☆ | Non |
| Small | ~1 Go | ⚡⚡⚡ | ★★★☆☆ | Machines modestes |
| **Distil-Large-v3** | **~1.5 Go** | **⚡⚡⚡** | **★★★★☆** | **✅ Oui** |
| Medium | ~2.5 Go | ⚡⚡ | ★★★★☆ | Non |
| Large-v2/v3 | ~4.5 Go | ⚡ | ★★★★★ | GPU uniquement |

Le modèle **Distil-Large-v3** est téléchargé automatiquement au premier lancement (~800 Mo). Ensuite, tout fonctionne hors ligne.

---

## ⌨️ Raccourcis clavier

| Raccourci | Action |
|---|---|
| `F5` / `Ctrl+R` | Nouvel enregistrement |
| `Ctrl+F` | Rechercher |
| `Ctrl+E` | Exporter |
| `Ctrl+,` | Paramètres |
| `Échap` | Retour à la liste |

---

## 🔐 Sécurité

```
Voix (WAV/MP3)
      │
      ▼
Transcription Whisper (locale, hors ligne)
      │
      ▼
Texte brut
      │
      ▼ PBKDF2-HMAC-SHA256 (480 000 itérations) + sel aléatoire 32 octets
      │
      ▼
Clé AES-256
      │
      ▼ AES-256-GCM (chiffrement authentifié)
      │
      ▼
SQLite (~/journalor_data/journal.db)
```

- Aucune donnée n'est envoyée sur Internet
- Le contenu textuel est chiffré avant d'être écrit sur le disque
- Les fichiers audio ne sont pas chiffrés (stockés dans `~/journalor_data/audio/`)
- Sans le PIN correct, les données chiffrées sont illisibles

---

## 📁 Structure du projet

```
journalor/
├── main.py                  # Point d'entrée
├── requirements.txt
├── core/
│   ├── audio_recorder.py    # Enregistrement WAV (sounddevice)
│   ├── transcription.py     # Transcription Whisper (faster-whisper)
│   ├── encryption.py        # AES-256-GCM + PBKDF2
│   ├── database.py          # SQLite3
│   ├── export.py            # TXT / MD / PDF / JSON
│   ├── search.py            # Recherche plein-texte
│   └── model_downloader.py  # Téléchargement des modèles Whisper
├── gui/
│   ├── main_window.py       # Fenêtre principale + sidebar
│   ├── login_screen.py      # Écran PIN
│   ├── recorder_widget.py   # Widget d'enregistrement + MP3
│   ├── editor_widget.py     # Éditeur de transcription
│   ├── entry_list.py        # Liste du journal
│   ├── stats_view.py        # Vue statistiques
│   ├── export_window.py     # Fenêtre d'export
│   ├── settings_window.py   # Fenêtre de paramètres
│   ├── help_window.py       # Documentation intégrée
│   └── download_dialog.py   # Dialogue de téléchargement de modèle
└── utils/
    ├── constants.py         # Constantes et catalogue de modèles
    ├── formatters.py        # Formatage de dates, durées, mots
    ├── validators.py        # Validation du PIN
    └── audio_utils.py       # Conversion WAV → MP3
```

---

## 📦 Dépendances principales

| Bibliothèque | Rôle |
|---|---|
| `customtkinter` | Interface graphique moderne (dark theme) |
| `sounddevice` | Capture audio depuis le microphone |
| `faster-whisper` | Transcription vocale IA (modèles CTranslate2) |
| `cryptography` | AES-256-GCM, PBKDF2 |
| `lameenc` | Encodage MP3 pur Python |
| `matplotlib` | Graphique d'activité dans les statistiques |
| `fpdf2` | Génération PDF à l'export |
| `numpy` / `scipy` | Traitement du signal audio |

---

## 🗺️ Flux d'utilisation typique

```
Ouvrir Journalor
      │
      ▼ (saisir PIN)
Liste du journal
      │
      ├─ + Enregistrer ─────────────────────────────┐
      │                                              │
      │   ┌─ Enregistrement vocal ─────────────────┐ │
      │   │  Vumètre • Timer • Pause • Arrêt      │ │
      │   │  ↳ Arrêt auto sur silence             │ │
      │   │  ↳ Option : Garder une copie MP3      │ │
      │   └──────────────────────────────────────┘ │
      │                                              │
      │   ┌─ Transcription ────────────────────────┐ │
      │   │  Barre de progression • Countdown     │ │
      │   │  Option : Mode arrière-plan           │ │
      │   └──────────────────────────────────────┘ │
      │                                              │
      │   ┌─ Éditeur ──────────────────────────────┐ │
      │   │  Texte transcrit • Titre • Emoji      │ │
      │   │  Tags • Compteur de mots              │ │
      │   │  💾 Sauvegarder                       │ │
      │   └──────────────────────────────────────┘ │
      │◄─────────────────────────────────────────────┘
      │
      ├─ 🔍 Rechercher dans le journal
      ├─ 📊 Consulter les statistiques
      └─ 📤 Exporter (TXT / MD / PDF / JSON)
```

---

## 📄 Licence

MIT — libre d'utilisation, de modification et de distribution.
