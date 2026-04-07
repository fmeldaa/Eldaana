"""
voice.py — Voix d'Eldaana.

Mode prioritaire : ElevenLabs (vraie voix humaine, envoûtante)
Mode fallback    : Web Speech Synthesis du navigateur (si pas de clé ElevenLabs)
"""

import re
import json
import base64
import streamlit as st
import streamlit.components.v1 as components


# ── Voix ElevenLabs recommandées (toutes compatibles français) ─────────────────
# Changez VOICE_ID pour choisir une autre voix
# Liste complète : https://elevenlabs.io/voice-library
VOICE_ID = "XB0fDUnXU5powFXDhCwa"   # Charlotte — naturelle, chaleureuse, très humaine

VOICE_SETTINGS = {
    "stability":         0.50,   # moins stable = plus vivante, plus naturelle
    "similarity_boost":  0.80,
    "style":             0.55,   # plus d'expressivité
    "use_speaker_boost": True,
}


# ── Nettoyage du texte ─────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*',     r'\1', text)
    text = re.sub(r'#{1,6}\s+',     '',    text)
    text = re.sub(r'`(.+?)`',       r'\1', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    text = re.sub(r'^[-•*]\s+',     '',    text, flags=re.MULTILINE)
    text = re.sub(r'\n+',           ' ',   text)
    text = re.sub(r'\s+',           ' ',   text).strip()
    # Limite à 500 caractères pour rester dans le quota free
    return text[:500] if len(text) > 500 else text


# ── ElevenLabs ────────────────────────────────────────────────────────────────

def _elevenlabs_configured() -> bool:
    try:
        _ = st.secrets["elevenlabs"]["api_key"]
        return True
    except Exception:
        return False


def _speak_elevenlabs(text: str):
    """Génère l'audio via ElevenLabs et le joue dans le navigateur."""
    try:
        import requests as _http
        api_key = st.secrets["elevenlabs"]["api_key"]
        voice_id = st.secrets["elevenlabs"].get("voice_id", VOICE_ID)

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key":   api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text":           text,
            "model_id":       "eleven_multilingual_v2",
            "voice_settings": VOICE_SETTINGS,
        }
        resp = _http.post(url, json=payload, headers=headers, timeout=15)

        if resp.status_code == 200:
            audio_b64 = base64.b64encode(resp.content).decode("utf-8")
            components.html(f"""
            <script>
            (function() {{
                const audio = new Audio('data:audio/mpeg;base64,{audio_b64}');
                audio.play().catch(e => console.log('Autoplay blocked:', e));
            }})();
            </script>
            """, height=0, scrolling=False)
            return True
    except Exception:
        pass
    return False


# ── Fallback : Web Speech Synthesis ───────────────────────────────────────────

def _speak_browser(text: str):
    """Lecture via l'API du navigateur (fallback si pas ElevenLabs)."""
    preferred_voices = [
        "Microsoft Hortense", "Microsoft Julie",
        "Amélie", "Marie", "Virginie", "Audrey",
        "Google français", "Google French",
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
    """
    Lit le texte à voix haute.
    Utilise ElevenLabs si configuré, sinon le navigateur.
    """
    clean_text = _clean(text)
    if _elevenlabs_configured():
        success = _speak_elevenlabs(clean_text)
        if success:
            return
    _speak_browser(clean_text)


def stop():
    """Arrête la lecture en cours (navigateur uniquement)."""
    components.html(
        "<script>window.speechSynthesis.cancel();</script>",
        height=0, scrolling=False,
    )
