"""
voice.py — Voix d'Eldaana via Web Speech Synthesis API (navigateur)
Voix féminine, douce, calme et posée en français.
"""

import re
import json
import streamlit.components.v1 as components


# ── Nettoyage du texte pour la parole ─────────────────────────────────────────

def _clean(text: str) -> str:
    """Supprime le formatage Markdown pour une lecture naturelle."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)       # gras
    text = re.sub(r'\*(.+?)\*',     r'\1', text)        # italique
    text = re.sub(r'#{1,6}\s+',     '',    text)        # titres
    text = re.sub(r'`(.+?)`',       r'\1', text)        # code inline
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)     # liens
    text = re.sub(r'^[-•*]\s+',     '',    text, flags=re.MULTILINE)  # listes
    text = re.sub(r'\n+',           ' ',   text)        # sauts de ligne
    text = re.sub(r'\s+',           ' ',   text).strip()
    return text


# ── Lecture vocale ─────────────────────────────────────────────────────────────

def speak(text: str):
    """
    Lit le texte à voix haute avec une voix féminine française douce et posée.
    Utilise l'API Web Speech Synthesis du navigateur — gratuit, sans clé API.
    """
    clean_text = _clean(text)

    # Voix françaises féminines prioritaires (Windows / macOS / Chrome)
    preferred_voices = [
        "Microsoft Hortense",   # Windows — très naturelle
        "Microsoft Julie",      # Windows
        "Amélie",               # macOS
        "Marie",                # macOS
        "Virginie",             # macOS
        "Audrey",               # macOS
        "Pauline",              # macOS
        "Google français",      # Chrome
        "Google French",        # Chrome anglophone
        "Helena",               # macOS/iOS
        "Elsa",                 # Windows
    ]

    voices_json = json.dumps(preferred_voices)

    js = f"""
    <script>
    (function() {{
        // Annule toute parole en cours
        window.speechSynthesis.cancel();

        const msg = new SpeechSynthesisUtterance({json.dumps(clean_text)});
        msg.lang   = 'fr-FR';
        msg.rate   = 0.88;   // légèrement plus lent — calme et posé
        msg.pitch  = 1.08;   // légèrement plus aigu — féminin
        msg.volume = 1.0;

        const preferred = {voices_json};

        function selectVoice() {{
            const voices = window.speechSynthesis.getVoices();
            let chosen = null;

            // Cherche une voix préférée
            for (const name of preferred) {{
                chosen = voices.find(v => v.name.includes(name));
                if (chosen) break;
            }}
            // Repli : n'importe quelle voix française
            if (!chosen) chosen = voices.find(v => v.lang && v.lang.startsWith('fr'));

            if (chosen) msg.voice = chosen;
            window.speechSynthesis.speak(msg);
        }}

        // Les voix peuvent ne pas être chargées immédiatement
        const voices = window.speechSynthesis.getVoices();
        if (voices.length > 0) {{
            selectVoice();
        }} else {{
            window.speechSynthesis.onvoiceschanged = selectVoice;
        }}
    }})();
    </script>
    """
    components.html(js, height=0, scrolling=False)


def stop():
    """Arrête la lecture en cours."""
    components.html(
        "<script>window.speechSynthesis.cancel();</script>",
        height=0,
        scrolling=False,
    )
