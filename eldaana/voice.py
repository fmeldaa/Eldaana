"""
voice.py — Voix d'Eldaana.
Priorité : OpenAI TTS (voix shimmer — qualité ChatGPT)
Fallback  : Web Speech Synthesis navigateur
"""

import re
import base64
import io
import streamlit as st
import streamlit.components.v1 as components


# ── Nettoyage du texte ─────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    # Supprime TOUS les emojis
    emoji_pattern = re.compile(
        "["
        "\U0001F000-\U0001FFFF"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u2600-\u2B55"
        "\u200d\u23cf\u23e9\u231a\ufe0f\u3030"
        "]+", flags=re.UNICODE)
    text = emoji_pattern.sub('', text)
    # Supprime le Markdown
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*',     r'\1', text)
    text = re.sub(r'#{1,6}\s+',     '',    text)
    text = re.sub(r'`(.+?)`',       r'\1', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    text = re.sub(r'^[-•*]\s+',     '',    text, flags=re.MULTILINE)
    text = re.sub(r'\n+',           ' ',   text)
    text = re.sub(r'\s+',           ' ',   text).strip()
    return text[:600] if len(text) > 600 else text


# ── OpenAI TTS ────────────────────────────────────────────────────────────────

def _openai_configured() -> bool:
    try:
        _ = st.secrets["openai"]["api_key"]
        return True
    except Exception:
        return False


VOICE_OPTIONS = {
    "Nova — Chaleureuse & naturelle 🌸":     "nova",
    "Shimmer — Douce & apaisante ✨":        "shimmer",
    "Coral — Enjouée & dynamique 🌺":        "coral",
    "Sage — Posée & mature 🍃":              "sage",
    "Fable — Narrative & élégante 📖":       "fable",
}

def _speak_openai(text: str) -> bool:
    """Voix OpenAI TTS — haute qualité, voix choisie par l'utilisateur."""
    try:
        import requests as _http
        api_key = st.secrets["openai"]["api_key"]

        # Priorité : choix du profil > secrets > nova par défaut
        voice = st.session_state.get("eldaana_voice", None)
        if not voice:
            voice = st.secrets["openai"].get("voice", "nova")

        resp = _http.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            json={
                "model": "tts-1-hd",
                "input": text,
                "voice": voice,
                "speed": 0.95,   # légèrement plus lente = plus chaleureuse
            },
            timeout=20,
        )

        if resp.status_code == 200:
            import io
            st.audio(io.BytesIO(resp.content), format="audio/mp3", autoplay=True)
            return True
    except Exception:
        pass
    return False


# ── Fallback : Web Speech Synthesis ───────────────────────────────────────────

def _speak_browser(text: str):
    import json
    preferred_voices = [
        "Microsoft Hortense", "Microsoft Julie",
        "Amélie", "Marie", "Google français", "Google French",
    ]
    voices_json = json.dumps(preferred_voices)
    js = f"""
    <script>
    (function() {{
        window.speechSynthesis.cancel();
        const msg = new SpeechSynthesisUtterance({json.dumps(text)});
        msg.lang = 'fr-FR'; msg.rate = 0.88; msg.pitch = 1.08; msg.volume = 1.0;
        const preferred = {voices_json};
        function go() {{
            const voices = window.speechSynthesis.getVoices();
            let v = null;
            for (const n of preferred) {{ v = voices.find(x => x.name.includes(n)); if (v) break; }}
            if (!v) v = voices.find(x => x.lang && x.lang.startsWith('fr'));
            if (v) msg.voice = v;
            window.speechSynthesis.speak(msg);
        }}
        speechSynthesis.getVoices().length > 0 ? go() : (speechSynthesis.onvoiceschanged = go);
    }})();
    </script>
    """
    components.html(js, height=0, scrolling=False)


# ── Interface publique ─────────────────────────────────────────────────────────

def speak(text: str):
    clean_text = _clean(text)
    if not clean_text:
        return
    if _openai_configured():
        if _speak_openai(clean_text):
            return
    _speak_browser(clean_text)


def stop():
    components.html(
        "<script>window.speechSynthesis.cancel();</script>",
        height=0, scrolling=False,
    )
