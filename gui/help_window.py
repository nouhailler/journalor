"""In-app documentation / help window."""

import customtkinter as ctk
from utils.constants import COLOR_ACCENT, COLOR_TEXT_MUTED, COLOR_SUCCESS, COLOR_WARNING


_SECTIONS = [
    (
        "🎙️  Enregistrement vocal",
        [
            ("Démarrer un enregistrement",
             "Cliquez sur + Enregistrer dans la barre latérale ou appuyez sur F5 / Ctrl+R.\n"
             "Le microphone s'active immédiatement et le niveau sonore s'affiche en temps réel."),
            ("Pause / Reprise",
             "Pendant l'enregistrement, le bouton ⏸ Pause met la capture en pause sans "
             "interrompre le timer. Appuyez sur ▶ Reprendre pour continuer."),
            ("Arrêt automatique",
             "Journalor détecte les silences et arrête l'enregistrement automatiquement "
             "après la durée configurée (par défaut 3 secondes). Vous pouvez modifier ce "
             "seuil dans Paramètres → Enregistrement audio."),
            ("Copie audio MP3",
             "À la fin de chaque enregistrement, vous pouvez cocher « Conserver une copie "
             "audio (.mp3) » pour garder un fichier MP3 compressé de votre voix. "
             "Le WAV temporaire est supprimé ; le MP3 est conservé avec l'entrée."),
        ],
    ),
    (
        "📝  Transcription automatique",
        [
            ("Modèles Whisper",
             "Journalor utilise faster-whisper pour transcrire votre voix. Plusieurs "
             "modèles sont disponibles (Tiny → Large-v3). Le modèle recommandé est "
             "Distil-Large-v3 : excellent en français, 6× plus rapide que Large-v3."),
            ("Premier lancement",
             "Lors de la première utilisation d'un modèle, il est téléchargé (~500 Mo à "
             "~800 Mo selon le modèle). Une barre de progression s'affiche et Journalor "
             "reprend la transcription automatiquement une fois le modèle disponible."),
            ("Mode arrière-plan",
             "Si la transcription est longue, cliquez sur ⏩ Continuer en arrière-plan. "
             "Vous pouvez naviguer dans votre journal pendant ce temps. Une bannière de "
             "progression s'affiche en haut de l'écran et vous prévient quand c'est terminé."),
            ("Langue",
             "La langue de transcription est configurable dans Paramètres. Choisissez "
             "« auto » pour une détection automatique (légèrement plus lente)."),
        ],
    ),
    (
        "✏️  Édition des entrées",
        [
            ("Titre et emoji",
             "Après la transcription, un titre est proposé automatiquement à partir de la "
             "première phrase. Vous pouvez le modifier librement. Choisissez un emoji "
             "dans le menu déroulant pour caractériser l'humeur de l'entrée."),
            ("Éditeur de texte",
             "Le texte transcrit est entièrement éditable. Vous disposez d'un annulation "
             "illimitée (Ctrl+Z) et d'un compteur de mots en bas à droite."),
            ("Tags",
             "Cliquez sur un ou plusieurs tags pour les associer à l'entrée. Les tags "
             "actifs s'affichent en couleur. Vous pouvez créer vos propres tags dans "
             "Paramètres → Tags (via la base de données ou l'interface)."),
            ("Modifier une entrée existante",
             "Depuis la liste du journal, cliquez sur une entrée pour l'ouvrir, puis "
             "cliquez sur ✏️ Modifier pour en éditer le contenu, le titre ou les tags."),
        ],
    ),
    (
        "📋  Journal et recherche",
        [
            ("Liste des entrées",
             "Le panneau Journal affiche toutes vos entrées par ordre chronologique inverse. "
             "Chaque carte montre l'emoji, le titre, la date, la durée et le nombre de mots."),
            ("Recherche plein texte",
             "Tapez dans la barre de recherche (ou appuyez sur Ctrl+F) pour filtrer les "
             "entrées. La recherche porte sur le titre et le contenu (déchiffré en mémoire)."),
            ("Suppression",
             "Ouvrez une entrée et cliquez sur 🗑 Supprimer. Une confirmation est demandée. "
             "La suppression est définitive."),
        ],
    ),
    (
        "🏷️  Tags et organisation",
        [
            ("Tags par défaut",
             "Journalor crée automatiquement 5 tags au premier lancement : Travail, "
             "Personnel, Santé, Idées, Famille — chacun avec une couleur distinctive."),
            ("Filtrage par tag",
             "Dans la liste du journal, cliquez sur un tag pour n'afficher que les entrées "
             "qui lui sont associées."),
            ("Réactions emoji",
             "Chaque entrée peut avoir un emoji de réaction (😊 😢 😤 🙏 🔥 💡 ❤️ 😴 🎉). "
             "Il s'affiche en tête de la carte dans la liste."),
        ],
    ),
    (
        "📊  Statistiques",
        [
            ("Accès",
             "Cliquez sur 📊 Statistiques dans la barre latérale."),
            ("Contenu",
             "La vue affiche : nombre total d'entrées, mots écrits, durée enregistrée, "
             "série de jours consécutifs (streak), et un graphique d'activité sur 30 jours."),
        ],
    ),
    (
        "📤  Export",
        [
            ("Formats disponibles",
             "Journalor exporte vos entrées en :\n"
             "• Texte brut (.txt) — simple et universel\n"
             "• Markdown (.md) — avec titres et mise en forme\n"
             "• PDF (.pdf) — prêt à imprimer\n"
             "• JSON — sauvegarde complète pour réimport"),
            ("Sélection",
             "Si une entrée est sélectionnée dans la liste, seule cette entrée est exportée. "
             "Sinon, toutes les entrées sont exportées. Raccourci : Ctrl+E."),
            ("Réimport JSON",
             "Le format JSON permet de restaurer vos données dans une autre instance de "
             "Journalor (fonctionnalité d'import disponible dans Exporter)."),
        ],
    ),
    (
        "🔒  Sécurité et chiffrement",
        [
            ("Chiffrement AES-256-GCM",
             "Tout le contenu textuel est chiffré avec AES-256-GCM avant d'être stocké "
             "dans la base de données SQLite. Les fichiers audio ne sont pas chiffrés."),
            ("Dérivation de clé PBKDF2",
             "La clé de chiffrement est dérivée de votre PIN avec PBKDF2-HMAC-SHA256 "
             "(480 000 itérations) et un sel aléatoire de 32 octets."),
            ("PIN",
             "Le PIN est demandé à chaque lancement. En cas d'oubli, les données "
             "chiffrées ne sont pas récupérables. Conservez votre PIN précieusement."),
            ("Changer le PIN",
             "Rendez-vous dans Paramètres → Sécurité. Le nouveau PIN re-chiffre "
             "la clé sur la session en cours."),
        ],
    ),
    (
        "⌨️  Raccourcis clavier",
        [
            ("Enregistrer", "F5  ou  Ctrl+R"),
            ("Rechercher", "Ctrl+F"),
            ("Exporter", "Ctrl+E"),
            ("Paramètres", "Ctrl+,"),
            ("Retour à la liste", "Échap"),
        ],
    ),
    (
        "⚙️  Paramètres",
        [
            ("Modèle Whisper", "Choisissez le modèle de transcription selon votre machine. "
             "Distil-Large-v3 est recommandé pour un usage quotidien en français."),
            ("Langue", "Langue de transcription : fr, en, de, es, it, pt, ou auto."),
            ("Silence avant arrêt auto",
             "Durée de silence (0–10 s) après laquelle l'enregistrement s'arrête seul. "
             "Mettez 0 pour désactiver l'arrêt automatique."),
            ("Dossier de sauvegarde",
             "Répertoire où sont stockés la base de données et les fichiers audio. "
             "Par défaut : ~/journalor_data."),
            ("Diagnostics",
             "La section Diagnostics permet d'accéder au fichier de logs et d'afficher "
             "les 50 dernières lignes pour diagnostiquer un problème."),
        ],
    ),
]


class HelpWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Documentation — Journalor")
        self.resizable(True, True)
        self._body_labels: list = []
        self._build()
        self.after(50, lambda: self.attributes("-zoomed", True))
        self.after(150, self.lift)
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event=None):
        """Update wraplength of all body labels when window is resized."""
        w = self.winfo_width()
        if w < 200:
            return
        wrap = max(400, w - 160)
        for lbl in self._body_labels:
            try:
                lbl.configure(wraplength=wrap)
            except Exception:
                pass

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        scroll.grid_columnconfigure(0, weight=1)

        # Header
        ctk.CTkLabel(
            scroll,
            text="📖  Documentation Journalor",
            font=ctk.CTkFont(size=22, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(24, 4))

        ctk.CTkLabel(
            scroll,
            text="Journal vocal personnel — 100% local, chiffré, open source.",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 20))

        row = 2
        for section_title, items in _SECTIONS:
            # Section header
            header_frame = ctk.CTkFrame(scroll, fg_color="#0d1b2a", corner_radius=8)
            header_frame.grid(row=row, column=0, sticky="ew", padx=16, pady=(12, 0))
            header_frame.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                header_frame,
                text=section_title,
                font=ctk.CTkFont(size=15, weight="bold"),
                anchor="w",
            ).grid(row=0, column=0, sticky="w", padx=16, pady=10)
            row += 1

            for item in items:
                if len(item) == 2:
                    subtitle, body = item
                    item_frame = ctk.CTkFrame(scroll, fg_color="transparent")
                    item_frame.grid(row=row, column=0, sticky="ew", padx=24, pady=(8, 0))
                    item_frame.grid_columnconfigure(0, weight=1)

                    ctk.CTkLabel(
                        item_frame,
                        text=subtitle,
                        font=ctk.CTkFont(size=13, weight="bold"),
                        text_color=COLOR_SUCCESS,
                        anchor="w",
                    ).grid(row=0, column=0, sticky="w")

                    body_lbl = ctk.CTkLabel(
                        item_frame,
                        text=body,
                        font=ctk.CTkFont(size=12),
                        text_color="#cccccc",
                        anchor="w",
                        wraplength=1200,
                        justify="left",
                    )
                    body_lbl.grid(row=1, column=0, sticky="w", pady=(2, 0))
                    self._body_labels.append(body_lbl)
                    row += 1

        # Close button
        ctk.CTkButton(
            scroll,
            text="Fermer",
            width=120, height=36,
            fg_color="transparent",
            border_width=1,
            border_color="gray",
            command=self.destroy,
        ).grid(row=row, column=0, pady=(24, 24))
