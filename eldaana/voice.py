"""
voice.py — Voix d'Eldaana.
Priorité : OpenAI TTS (tts-1, démarrage en parallèle du streaming texte)
Fallback  : Web Speech Synthesis navigateur
"""

import re
import io
import concurrent.futures
import streamlit as st
import streamlit.components.v1 as components

# Pool de threads pour lancer TTS en parallèle du streaming
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)


# ── Nettoyage du texte ─────────────────────────────────────────────────────────

OPENAI_TTS_MAX = 4000   # Limite API OpenAI TTS (max 4096)
CHUNK_SIZE     = 3800   # Taille max par chunk pour les très longs textes


def _clean(text: str) -> str:
    """Nettoie le texte pour la synthèse vocale (supprime emojis et Markdown)."""
    emoji_pattern = re.compile(
        "["
        "\U0001F000-\U0001FFFF"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u2600-\u2B55"
        "\u200d\u23cf\u23e9\u231a\ufe0f\u3030"
        "]+", flags=re.UNICODE)
    text = emoji_pattern.sub('', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*',     r'\1', text)
    text = re.sub(r'#{1,6}\s+',     '',    text)
    text = re.sub(r'`(.+?)`',       r'\1', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    text = re.sub(r'^[-•*]\s+',     '',    text, flags=re.MULTILINE)
    text = re.sub(r'\n+',           ' ',   text)
    text = re.sub(r'\s+',           ' ',   text).strip()
    return text  # Plus de limite artificielle ici


def _split_into_chunks(text: str, max_size: int = CHUNK_SIZE) -> list[str]:
    """
    Découpe le texte en morceaux à la frontière de phrases.
    Évite de couper une phrase en plein milieu.
    """
    if len(text) <= max_size:
        return [text]

    chunks = []
    remaining = text
    while len(remaining) > max_size:
        # Chercher la dernière phrase complète avant max_size
        cut = remaining[:max_size]
        # Chercher le dernier point, !, ? ou … avant la limite
        for sep in ['. ', '! ', '? ', '… ', ', ']:
            idx = cut.rfind(sep)
            if idx > max_size // 2:   # au moins à mi-chemin
                cut = remaining[:idx + len(sep)]
                break
        chunks.append(cut.strip())
        remaining = remaining[len(cut):].strip()

    if remaining:
        chunks.append(remaining)
    return chunks


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

def _call_openai_tts(text: str, api_key: str, voice: str) -> bytes | None:
    """Appel HTTP OpenAI TTS — tts-1 pour la rapidité."""
    try:
        import requests as _http
        resp = _http.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            json={
                "model": "tts-1",   # tts-1 = 2x plus rapide que tts-1-hd
                "input": text,
                "voice": voice,
                "speed": 0.95,
            },
            timeout=20,
        )
        if resp.status_code == 200:
            return resp.content
    except Exception:
        pass
    return None


def prepare_audio_async(text: str) -> "concurrent.futures.Future | None":
    """Lance la génération TTS en arrière-plan. Retourne un Future."""
    try:
        api_key = st.secrets["openai"]["api_key"]
        voice   = st.session_state.get("eldaana_voice",
                  st.secrets["openai"].get("voice", "nova"))
        clean   = _clean(text)
        if not clean:
            return None
        return _executor.submit(_call_openai_tts, clean, api_key, voice)
    except Exception:
        return None


def _speak_openai(text: str, precomputed: "concurrent.futures.Future | None" = None) -> bool:
    """
    Joue la voix OpenAI TTS.
    - Texte court (≤ CHUNK_SIZE) : un seul appel, utilise le Future pré-calculé si dispo.
    - Texte long : découpe en morceaux, génère en parallèle, joue tout.
    """
    try:
        api_key = st.secrets["openai"]["api_key"]
        voice   = st.session_state.get("eldaana_voice",
                  st.secrets["openai"].get("voice", "nova"))

        chunks = _split_into_chunks(text)

        if len(chunks) == 1:
            # Texte court — comportement habituel
            audio_bytes = None
            if precomputed is not None:
                try:
                    audio_bytes = precomputed.result(timeout=12)
                except Exception:
                    pass
            if audio_bytes is None:
                audio_bytes = _call_openai_tts(chunks[0], api_key, voice)
            if audio_bytes:
                st.audio(io.BytesIO(audio_bytes), format="audio/mp3", autoplay=True)
                return True

        else:
            # Texte long — générer tous les morceaux en parallèle
            futures = [
                _executor.submit(_call_openai_tts, chunk, api_key, voice)
                for chunk in chunks
            ]
            # Collecter les résultats dans l'ordre
            all_bytes = []
            for f in futures:
                try:
                    b = f.result(timeout=20)
                    if b:
                        all_bytes.append(b)
                except Exception:
                    pass

            if all_bytes:
                # Concaténer tous les MP3 et jouer d'un coup
                combined = b"".join(all_bytes)
                st.audio(io.BytesIO(combined), format="audio/mp3", autoplay=True)
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

def speak(text: str, precomputed=None):
    clean_text = _clean(text)
    if not clean_text:
        return
    if _openai_configured():
        if _speak_openai(clean_text, precomputed=precomputed):
            return
    _speak_browser(clean_text)


def stop():
    components.html(
        "<script>window.speechSynthesis.cancel();</script>",
        height=0, scrolling=False,
    )
