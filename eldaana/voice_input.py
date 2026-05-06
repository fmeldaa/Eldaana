"""
voice_input.py — Saisie vocale pour Eldaana.
Utilise streamlit-mic-recorder pour capturer l'audio,
puis OpenAI Whisper pour la transcription en français.
Fallback : Web Speech API navigateur (sans API key).
"""

import io
import streamlit as st
import streamlit.components.v1 as components
from translations import t as _t_vi


# ── Artefacts courants de Whisper sur silence / bruit ────────────────────────

_WHISPER_ARTIFACTS = {
    "", ".", "..", "...", "…", "merci.", "merci", "ok.", "ok",
    "sous-titres réalisés para la communauté d'amara.org",
    "sous-titres réalisés par la communauté d'amara.org",
    "sous-titres", "fin.", "bonjour.", "voilà.",
}


def _transcribe_whisper(audio_bytes: bytes) -> str | None:
    """Transcrit audio WAV → texte via OpenAI Whisper API."""
    # Audio trop court = silence probable (< ~0.3s)
    if len(audio_bytes) < 4000:
        return None
    try:
        import requests
        api_key = st.secrets["openai"]["api_key"]
        resp = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": ("audio.wav", io.BytesIO(audio_bytes), "audio/wav")},
            data={"model": "whisper-1", "language": "fr"},
            timeout=20,
        )
        if resp.status_code == 200:
            text = resp.json().get("text", "").strip()
            if text.lower() in _WHISPER_ARTIFACTS:
                return None
            return text
    except KeyError:
        st.error("⚠️ Clé OpenAI manquante dans les secrets Streamlit.", icon="🔑")
    except Exception:
        pass
    return None


# ── Interface micro principale ────────────────────────────────────────────────

def show_mic_button(key: str = "mic_eldaana") -> str | None:
    """
    Affiche le bouton micro (streamlit-mic-recorder + Whisper).
    Retourne le texte transcrit ou None si rien capturé.
    """
    try:
        from streamlit_mic_recorder import mic_recorder
    except ImportError:
        st.warning("📦 Package `streamlit-mic-recorder` manquant — redéployez l'app.", icon="⚠️")
        return None

    audio = mic_recorder(
        start_prompt=_t_vi("mic_start_btn"),
        stop_prompt=_t_vi("mic_stop_btn"),
        just_once=True,
        use_container_width=True,
        key=key,
    )

    if not audio or not audio.get("bytes"):
        return None

    audio_bytes = audio["bytes"]

    # Trop court → ne pas appeler Whisper
    if len(audio_bytes) < 4000:
        st.caption("🎤 Enregistrement trop court — maintiens le bouton plus longtemps.")
        return None

    with st.spinner("🎧 Transcription en cours…"):
        transcript = _transcribe_whisper(audio_bytes)

    if transcript:
        # Afficher le texte reconnu en petit
        st.markdown(
            f'<p style="font-size:0.82rem;color:#a78bfa;font-style:italic;'
            f'margin:0.2rem 0 0.5rem 0;">🎤 « {transcript} »</p>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("🎤 Rien capturé — réessaie en parlant plus fort ou plus longtemps.")

    return transcript


# ── Indicateur visuel "Eldaana parle…" ───────────────────────────────────────

def show_speaking_indicator():
    """Affiche l'animation pendant que la TTS joue."""
    st.markdown("""
    <div style="
        display:flex; align-items:center; gap:10px;
        background:rgba(167,139,250,0.12);
        border:1px solid #c084fc;
        border-radius:16px;
        padding:0.6rem 1rem;
        margin:0.5rem 0;
    ">
        <div style="display:flex; gap:4px; align-items:center;">
            <div style="width:6px;height:6px;border-radius:50%;background:#c084fc;
                        animation:pulse 1s ease-in-out infinite;"></div>
            <div style="width:6px;height:6px;border-radius:50%;background:#c084fc;
                        animation:pulse 1s ease-in-out 0.2s infinite;"></div>
            <div style="width:6px;height:6px;border-radius:50%;background:#c084fc;
                        animation:pulse 1s ease-in-out 0.4s infinite;"></div>
        </div>
        <span style="color:#a78bfa;font-size:0.88rem;font-style:italic;">
            Eldaana parle…
        </span>
    </div>
    <style>
    @keyframes pulse {
        0%, 100% { opacity: 0.3; transform: scale(0.8); }
        50%       { opacity: 1;   transform: scale(1.2); }
    }
    </style>
    """, unsafe_allow_html=True)


# ── Auto-activation micro après TTS (JS timer) ────────────────────────────────

def inject_mic_auto_trigger(estimated_duration_s: float, mic_btn_label: str | None = None):
    """
    Injecte un script JS qui clique automatiquement sur le bouton micro
    après la fin estimée du TTS (basé sur la durée audio).
    """
    if mic_btn_label is None:
        mic_btn_label = _t_vi("mic_start_btn")
    delay_ms = int(estimated_duration_s * 1000) + 800  # +0.8s de marge
    js = f"""
    <script>
    (function() {{
        setTimeout(function() {{
            // Chercher le bouton mic dans tous les iframes Streamlit
            function findAndClick(doc) {{
                var buttons = doc.querySelectorAll('button');
                for (var b of buttons) {{
                    if (b.innerText && b.innerText.includes('{mic_btn_label}')) {{
                        b.click();
                        return true;
                    }}
                }}
                return false;
            }}
            // Parent d'abord
            if (!findAndClick(window.parent.document)) {{
                // Puis tous les iframes du parent
                var frames = window.parent.document.querySelectorAll('iframe');
                for (var f of frames) {{
                    try {{ if (findAndClick(f.contentDocument)) break; }} catch(e) {{}}
                }}
            }}
        }}, {delay_ms});
    }})();
    </script>
    """
    components.html(js, height=0, scrolling=False)
