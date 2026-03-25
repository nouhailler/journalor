# CONTEXT.md — Journalor

> Point de reprise pour les prochaines sessions de développement.
> Mis à jour le : 2026-03-25

---

## Architecture

```
journalor/
├── main.py                  # Point d'entrée, fenêtre login (700×800), lance MainWindow
├── config.json              # Chemin du dossier de données (~/journalor_data par défaut)
├── requirements.txt         # Dépendances Python
├── core/
│   ├── audio_recorder.py    # Enregistrement WAV via sounddevice, silence detection
│   ├── transcription.py     # faster-whisper, callbacks on_progress/on_done/on_error
│   ├── encryption.py        # AES-256-GCM + PBKDF2-HMAC-SHA256 (480 000 iter)
│   ├── database.py          # SQLite3 — entrées, tags, settings
│   ├── export.py            # Export TXT / Markdown / PDF / JSON
│   ├── search.py            # Recherche plein-texte (déchiffrement en mémoire)
│   └── model_downloader.py  # Téléchargement des modèles Whisper depuis HuggingFace
├── gui/
│   ├── main_window.py       # Fenêtre principale, sidebar, navigation, bannière bg
│   ├── login_screen.py      # Écran PIN (setup + login), carte 560×620
│   ├── recorder_widget.py   # Vumètre, timer, pause/stop, panel post-enreg. + MP3
│   ├── editor_widget.py     # Transcription + éditeur texte, tags, emoji, bg mode
│   ├── entry_list.py        # Liste des entrées, recherche, filtre tag
│   ├── stats_view.py        # Streak, totaux, graphique matplotlib 30 jours
│   ├── export_window.py     # Dialogue export (480×360, filedialog parent=self)
│   ├── settings_window.py   # Paramètres (maximisée), modèle Whisper, PIN, logs
│   ├── help_window.py       # Documentation intégrée (maximisée, wraplength dynamique)
│   └── download_dialog.py   # Téléchargement modèle avec barre progression + watchdog
└── utils/
    ├── constants.py         # Constantes UI, catalogue modèles, APP_VERSION
    ├── formatters.py        # Dates, durées, compteur de mots
    ├── validators.py        # Validation PIN
    └── audio_utils.py       # wav_to_mp3() via lameenc (pur Python)
```

**Stack :** Python 3.10+, CustomTkinter (dark theme), sounddevice, faster-whisper (CTranslate2), AES-256-GCM (cryptography), SQLite3, matplotlib, fpdf2, lameenc.

**Données :** `~/journalor_data/` — `journal.db` (SQLite chiffré), `audio/` (WAV ou MP3).

---

## Fonctionnalités implémentées (v1.4.0)

| Code | Fonctionnalité | État |
|------|---------------|------|
| F01/F02 | Enregistrement WAV + vumètre temps réel | ✅ |
| F03/F04 | Auto-stop silence + pause/reprise | ✅ |
| F05 | Sauvegarde copie audio MP3 (lameenc 128 kbps) | ✅ |
| F07–F10 | Transcription faster-whisper + barre progression + countdown | ✅ |
| F11–F14 | Éditeur texte, undo/redo, timestamps, sauvegarde SQLite | ✅ |
| S01–S03 | AES-256-GCM, PBKDF2, écran PIN login | ✅ |
| C01/C05 | Liste entrées chronologique + recherche plein-texte | ✅ |
| O01/O02/O04 | Tags avec couleurs personnalisées | ✅ |
| O05 | Emoji réactions sur les entrées | ✅ |
| O06 | Auto-titre depuis la première phrase | ✅ |
| A01/A02 | Stats : streak, graphique activité 30 jours | ✅ |
| E01–E05 | Export TXT, Markdown, PDF, JSON + import JSON | ✅ |
| I01 | Thème sombre | ✅ |
| I05–I10 | Raccourcis clavier (F5, Ctrl+R/F/E/,, Échap) | ✅ |
| P01–P07 | Fenêtre paramètres complète | ✅ |
| BG01 | Mode transcription arrière-plan + bannière countdown | ✅ |
| DL01 | Téléchargement modèle Whisper avec progression + watchdog | ✅ |
| DOC01 | Documentation intégrée (📖 sidebar) | ✅ |

---

## Tailles de fenêtres actuelles

| Fenêtre | Taille |
|---------|--------|
| Login | 700×800, resizable, carte 560×620 |
| Application principale | 1600×1000 min, **démarre maximisée** |
| Paramètres | **Démarre maximisée** |
| Documentation | **Démarre maximisée**, wraplength dynamique |
| Export | 480×360, resizable en largeur |
| Téléchargement modèle | Fixe (dialog modal) |

---

## Bugs connus / points de vigilance

| Symptôme | Cause | État |
|----------|-------|------|
| `invalid command name …update` dans les logs | CustomTkinter planifie des callbacks après destruction fenêtre lors de la transition login→main | Inoffensif, non corrigeable sans patcher CTK |
| `invalid command name …check_dpi_scaling` | Même cause | Inoffensif |
| Crash `TclError` sur `_progress_bar.set()` | Callback `after(0, ...)` exécuté après navigation rapide hors de l'éditeur | **Corrigé** — `winfo_exists()` ajouté |
| Filedialog export s'ouvrait derrière la fenêtre | Pas de `parent=self` ni `topmost` | **Corrigé** |

---

## Dernier travail effectué (session 2026-03-25)

1. **Sauvegarde MP3 après enregistrement** — panel post-enregistrement avec checkbox "Conserver une copie audio (.mp3)", conversion en thread via `lameenc`, suppression du WAV.
2. **Fix fenêtre export** — taille agrandie, `filedialog` avec `parent=self` + `topmost=True`.
3. **Documentation intégrée** — `gui/help_window.py`, 10 sections, accessible via "📖 Documentation" dans la sidebar.
4. **README.md** — documentation complète avec tableaux, schémas ASCII, flux d'utilisation.
5. **Agrandissement fenêtres** — login 700×800, app maximisée, paramètres maximisés, doc maximisée avec wraplength dynamique.
6. **Correction crash barre de progression** — `winfo_exists()` dans le callback `_on_progress`.

---

## Prochaines pistes possibles

- Lecteur audio intégré pour réécouter l'enregistrement depuis la vue détail
- Export audio groupé (zip des MP3/WAV)
- Synchronisation/backup chiffré vers un dossier distant (rsync, rclone)
- Thème clair en option
- Notifications système à la fin d'une transcription arrière-plan (plyer est déjà installé)
- Verrouillage automatique après inactivité (constante `AUTO_LOCK_DEFAULT = 10` déjà définie)
