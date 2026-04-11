import streamlit as st
from anthropic import Anthropic
from system_prompt import get_system_prompt
from onboarding import (
    is_onboarding_done,
    show_onboarding,
    show_profile_form,
    load_profile,
    profile_summary,
    logout,
)
from weather import get_weather, build_briefing
from voice import speak, stop, VOICE_OPTIONS, prepare_audio_async  # noqa
from social_connect import show_social_connect
from pathlib import Path

# ── Configuration de la page ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Eldaana",
    page_icon="C:/Users/fmeld/Autres docs/Documents/These Pro/eldaana/logo.png",
    layout="centered",
)

# ── CSS personnalisé ───────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #fdf4ff 0%, #f0f4ff 50%, #e8f8ff 100%);
    }
    .eldaana-title {
        font-size: 2rem; font-weight: 700;
        background: linear-gradient(135deg, #c084fc, #818cf8, #38bdf8);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .eldaana-subtitle { font-size: 0.85rem; color: #9ca3af; margin: 0; }
    .stChatInput textarea {
        border: 1.5px solid #c084fc !important;
        border-radius: 16px !important;
    }
    .stChatInput textarea:focus {
        border-color: #818cf8 !important;
        box-shadow: 0 0 0 3px rgba(192,132,252,0.15) !important;
    }
    .stButton > button {
        border: 1.5px solid #c084fc; color: #7c3aed;
        border-radius: 20px; background: white; font-size: 0.85rem;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #fdf4ff, #ede9fe);
        border-color: #818cf8;
    }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* ── Champs de formulaire lisibles ── */
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stNumberInput"] input {
        background-color: #ffffff !important;
        color: #1A0A2E !important;
        border: 1.5px solid #c084fc !important;
        border-radius: 10px !important;
    }
    /* Form background blanc */
    [data-testid="stForm"] {
        background-color: #ffffff !important;
        border: 1.5px solid #c084fc !important;
        border-radius: 12px !important;
    }
    [data-testid="stForm"] * {
        background-color: transparent !important;
        color: #1A0A2E !important;
    }
    [data-testid="stForm"] input {
        background-color: #ffffff !important;
        border: 1.5px solid #c084fc !important;
        border-radius: 10px !important;
    }
    /* Selectbox */
    div[data-baseweb="select"] { background: #ffffff !important; }
    div[data-baseweb="select"] > div { background: #ffffff !important; color: #1A0A2E !important; border: 1.5px solid #c084fc !important; border-radius: 10px !important; }
    div[data-baseweb="select"] > div > div { background: #ffffff !important; color: #1A0A2E !important; }
    div[data-baseweb="select"] svg { color: #7c3aed !important; fill: #7c3aed !important; }
    ul[data-baseweb="menu"] { background: #ffffff !important; }
    ul[data-baseweb="menu"] li { background: #ffffff !important; color: #1A0A2E !important; }
    ul[data-baseweb="menu"] li:hover { background: #f3e8ff !important; }
    /* Labels */
    [data-testid="stWidgetLabel"] p,
    .stTextInput label, .stSelectbox label {
        color: #1A0A2E !important;
        font-weight: 500 !important;
    }

    /* ── Sidebar : texte blanc sur fond sombre ── */
    [data-testid="stSidebar"] {
        background-color: #1A0A2E !important;
    }
    [data-testid="stSidebar"] * {
        color: #F0E6FF !important;
    }
    /* Toggle label */
    [data-testid="stSidebar"] [data-testid="stToggle"] p,
    [data-testid="stSidebar"] [data-testid="stToggle"] label,
    [data-testid="stSidebar"] [data-testid="stToggle"] span {
        color: #F0E6FF !important;
    }
    [data-testid="stSidebar"] .stButton > button {
        color: #C9A84C !important;
        border-color: #C9A84C !important;
        background: transparent !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(201,168,76,0.15) !important;
    }
    /* ── Selectbox voix sidebar ── */
    [data-testid="stSidebar"] [data-testid="stSelectbox"],
    [data-testid="stSidebar"] [data-testid="stSelectbox"] > div,
    [data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
    [data-testid="stSidebar"] div[data-baseweb="select"],
    [data-testid="stSidebar"] div[data-baseweb="select"] > div,
    [data-testid="stSidebar"] div[data-baseweb="select"] > div > div {
        background: #1A0A2E !important;
        box-shadow: none !important;
        outline: none !important;
        color: #F0E6FF !important;
    }
    [data-testid="stSidebar"] div[data-baseweb="select"] > div {
        border: 1.5px solid #C9A84C !important;
        border-radius: 20px !important;
    }
    [data-testid="stSidebar"] div[data-baseweb="select"] svg {
        fill: #C9A84C !important;
    }
    [data-testid="stSidebar"] ul[data-baseweb="menu"] {
        background-color: #1A0A2E !important;
        border: 1px solid #C9A84C !important;
    }
    [data-testid="stSidebar"] ul[data-baseweb="menu"] li {
        background-color: #1A0A2E !important;
        color: #F0E6FF !important;
    }
    [data-testid="stSidebar"] ul[data-baseweb="menu"] li:hover {
        background-color: rgba(201,168,76,0.2) !important;
    }

    /* ── Zone de saisie : texte visible ── */
    .stChatInput textarea {
        color: #1A0A2E !important;
        background: white !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Clé API Anthropic (locale ou Streamlit Cloud) ─────────────────────────────
import os
if "ANTHROPIC_API_KEY" in st.secrets:
    os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]

# ── Constantes ─────────────────────────────────────────────────────────────────
logo_path = Path(__file__).parent / "logo.png"
LOGO = str(logo_path) if logo_path.exists() else "∞"
client = Anthropic()

# ── Routing : onboarding si pas encore fait ───────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "onboarding" if not is_onboarding_done() else "chat"

# ── PAGE : ONBOARDING ──────────────────────────────────────────────────────────
if st.session_state.page == "onboarding":
    done = show_onboarding()
    if done:
        st.session_state.page = "chat"
        st.rerun()
    st.stop()

# ── Chargement du profil ───────────────────────────────────────────────────────
profile = load_profile() or {}
prenom  = profile.get("prenom", "")

# ── Météo + timezone : récupérés une seule fois par session ───────────────────
if "weather" not in st.session_state:
    ville = profile.get("ville", "")
    st.session_state.weather = get_weather(ville) if ville else None
    # Stocker le timezone dans le profil pour l'utiliser partout
    if st.session_state.weather and st.session_state.weather.get("timezone"):
        tz = st.session_state.weather["timezone"]
        if profile.get("timezone") != tz:
            profile["timezone"] = tz
            from onboarding import save_profile
            save_profile(profile)

weather = st.session_state.weather

# ── Message d'accueil ──────────────────────────────────────────────────────────
if weather:
    GREETING = build_briefing(weather, profile)
else:
    genre = profile.get("sexe", "").lower() if profile else ""
    accord = "heureuse" if genre == "femme" else "heureux"
    GREETING = f"Bonjour {prenom} — Comment puis-je te rendre {accord} aujourd'hui ?"

# ── PAGE : VIE NUMÉRIQUE ──────────────────────────────────────────────────────
if st.session_state.page == "social":
    col1, col2 = st.columns([1, 6])
    with col1:
        if logo_path.exists():
            st.image(str(logo_path), width=64)
    with col2:
        st.markdown('<p class="eldaana-title">Eldaana</p>', unsafe_allow_html=True)
        st.markdown('<p class="eldaana-subtitle">Ma vie numérique</p>', unsafe_allow_html=True)
    st.divider()
    show_social_connect(profile)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Retour à la conversation"):
        st.session_state.page = "chat"
        st.rerun()
    st.stop()

# ── PAGE : PROFIL (mode de vie) ────────────────────────────────────────────────
if st.session_state.page == "profile":
    col1, col2 = st.columns([1, 6])
    with col1:
        if logo_path.exists():
            st.image(str(logo_path), width=64)
    with col2:
        st.markdown('<p class="eldaana-title">Eldaana</p>', unsafe_allow_html=True)
        st.markdown('<p class="eldaana-subtitle">Compléter mon profil</p>', unsafe_allow_html=True)
    st.divider()
    show_profile_form(profile)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Retour à la conversation"):
        st.session_state.page = "chat"
        st.rerun()
    st.stop()

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    if logo_path.exists():
        st.image(str(logo_path), width=56)
    st.markdown(f"### {prenom}")
    if profile:
        st.markdown(profile_summary(profile))

    # Météo résumée
    if weather:
        st.markdown(
            f"{weather['emoji']} **{weather['city']}** · {weather['temp_current']}°C  \n"
            f"{weather['description']} · max {weather['temp_max']}°"
        )
    st.divider()

    if not profile.get("onboarding_lifestyle_complete"):
        st.info("💡 Plus Eldaana vous connaît, plus elle est précise !")

    if st.button("✏️ Enrichir mon profil", use_container_width=True):
        st.session_state.page = "profile"
        st.rerun()

    if st.button("🌐 Ma vie numérique", use_container_width=True):
        st.session_state.page = "social"
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Toggle voix — sur une seule ligne
    if "voice_on" not in st.session_state:
        st.session_state.voice_on = True

    col_tog, col_lbl = st.columns([1, 3])
    with col_tog:
        voice_on = st.toggle("v", value=st.session_state.voice_on,
                             key="voice_toggle", label_visibility="collapsed")
    with col_lbl:
        lbl = "🔊 Voix activée" if voice_on else "🔇 Désactivée"
        st.markdown(
            f'<p style="color:#F0E6FF;font-size:0.85rem;margin:8px 0 0 0;">{lbl}</p>',
            unsafe_allow_html=True
        )

    if voice_on:
        st.session_state.voice_on = True
    else:
        st.session_state.voice_on = False
        stop()

    # Sélecteur de voix — toujours visible si voix activée
    if voice_on:
        st.markdown(
            '<p style="color:#F0E6FF;font-size:0.82rem;margin:8px 0 4px 0;">'
            '🎙️ Choix de la voix</p>',
            unsafe_allow_html=True
        )
        voice_labels = list(VOICE_OPTIONS.keys())
        saved_voice  = st.session_state.get("eldaana_voice", "nova")
        default_label = next(
            (l for l, v in VOICE_OPTIONS.items() if v == saved_voice),
            voice_labels[0]
        )
        chosen_label = st.selectbox(
            "voix",
            voice_labels,
            index=voice_labels.index(default_label),
            key="voice_selector",
            label_visibility="collapsed",
        )
        st.session_state.eldaana_voice = VOICE_OPTIONS[chosen_label]

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🔄 Nouvelle conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.display_messages = [{"role": "assistant", "content": GREETING}]
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🔀 Changer d'utilisateur", use_container_width=True):
        logout()
        st.session_state.page = "onboarding"
        st.rerun()

# ── PAGE : CHAT ────────────────────────────────────────────────────────────────

# En-tête
col1, col2 = st.columns([1, 6])
with col1:
    if logo_path.exists():
        st.image(str(logo_path), width=72)
with col2:
    st.markdown('<p class="eldaana-title">Eldaana</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="eldaana-subtitle">Ta confidente. Ta présence. Là pour toi.</p>',
        unsafe_allow_html=True,
    )
st.divider()

# État de la conversation
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.display_messages = [{"role": "assistant", "content": GREETING}]

# Affichage de l'historique
for msg in st.session_state.display_messages:
    with st.chat_message(msg["role"], avatar=LOGO if msg["role"] == "assistant" else None):
        st.markdown(msg["content"])

# Zone de saisie
user_input = st.chat_input(f"Écris ton message à Eldaana…")

if user_input:
    st.session_state.display_messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant", avatar=LOGO):
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=get_system_prompt(profile),
            messages=st.session_state.messages,
        ) as stream:
            reply = st.write_stream(stream.text_stream)

    # Dès que le texte est complet → lancer TTS en parallèle immédiatement
    voice_on = st.session_state.get("voice_on", True)
    if voice_on:
        tts_future = prepare_audio_async(reply)
        speak(reply, precomputed=tts_future)

    st.session_state.display_messages.append({"role": "assistant", "content": reply})
    st.session_state.messages.append({"role": "assistant", "content": reply})
