import streamlit as st
import streamlit.components.v1 as _components_uid
from anthropic import Anthropic
from system_prompt import get_system_prompt, get_voice_mode_suffix
from onboarding import (
    is_onboarding_done,
    show_onboarding,
    show_profile_form,
    load_profile,
    profile_summary,
    logout,
)
from weather import get_weather, build_briefing, build_wakeup_message
from voice import speak, stop, VOICE_OPTIONS, prepare_audio_async, speak_from_prefetched, estimate_speech_duration  # noqa
from voice_input import show_mic_button, show_speaking_indicator, inject_mic_auto_trigger
from social_connect import show_social_connect
from gemini_search import should_search_web, search_web, format_web_results_for_prompt
from shopping import (
    detect_purchases_in_message, add_purchase,
    get_reminders, mark_reminded, format_reminders_for_prompt,
    format_shopping_for_prompt, show_shopping_page,
)
from budget import show_budget_page, format_budget_for_prompt
from humeur import show_humeur_widget, format_humeur_for_prompt
from voyance import show_voyance_page
from dashboard import show_dashboard
from rgpd import show_rgpd_page
from email_agent import show_email_page, format_email_summary_for_prompt
from transport_alerts import (
    check_departure_alert, show_departure_alert_banner,
    show_transport_status_sidebar,
)
from conversation_storage import save_conversation, load_conversation
from stripe_payment import is_premium, create_checkout_url, handle_stripe_return, create_portal_url
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

    /* ── Widget transport sidebar : forcer couleurs visibles ── */
    [data-testid="stSidebar"] .transport-alert p,
    [data-testid="stSidebar"] .transport-ok p {
        color: inherit !important;
    }

    /* ── Checkboxes : couleur violette ── */
    [data-testid="stCheckbox"] svg {
        color: #7B2FBE !important;
        fill: #7B2FBE !important;
    }
    [data-testid="stCheckbox"] p {
        color: #1A0A2E !important;
        font-weight: 500 !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Langue de l'app (définie au premier lancement Android) ───────────────────
if "lang" not in st.session_state:
    st.session_state.lang = st.query_params.get("lang", "fr")

# ── Clé API Anthropic (locale ou Streamlit Cloud) ─────────────────────────────
import os
if "ANTHROPIC_API_KEY" in st.secrets:
    os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]

# ── Constantes ─────────────────────────────────────────────────────────────────
logo_path = Path(__file__).parent / "logo.png"
LOGO = str(logo_path) if logo_path.exists() else "∞"

def _get_user_avatar():
    """Retourne l'URL Cloudinary de la photo de profil, ou None."""
    from cloudinary_storage import get_profile_photo_url
    uid = st.session_state.get("user_id", "")
    return get_profile_photo_url(uid) if uid else None
client = Anthropic()

# ── Restauration de session via ?uid= dans l'URL ─────────────────────────────
# Mécanisme fiable : Python écrit l'uid dans st.query_params (URL du navigateur).
# L'URL ?uid=xxx est mémorisée par le navigateur et l'APK Android (voir MainActivity).
_uid_param = st.query_params.get("uid", "")
if _uid_param and "user_id" not in st.session_state:
    from storage import db_load as _db_load_uid
    _p = _db_load_uid(_uid_param)
    if _p and _p.get("onboarding_complete") and not _p.get("anonymized"):
        st.session_state["user_id"] = _uid_param

# Écrire l'uid dans l'URL dès que la session est active
if "user_id" in st.session_state:
    if st.query_params.get("uid") != st.session_state["user_id"]:
        st.query_params["uid"] = st.session_state["user_id"]

# ── Retour Google OAuth depuis Chrome (APK Android) ─────────────────────────
# Si l'utilisateur vient de se connecter avec Google dans Chrome depuis l'APK,
# on affiche un bouton deep link pour revenir dans l'app avec le uid.
if st.session_state.get("_android_oauth") and st.session_state.get("user_id"):
    _uid_android = st.session_state.get("user_id", "")
    _deep_link   = f"eldaana://?uid={_uid_android}"
    st.markdown(f"""
        <div style="display:flex;flex-direction:column;align-items:center;
                    justify-content:center;min-height:80vh;text-align:center;padding:20px;">
            <div style="font-size:3rem;margin-bottom:16px;">✅</div>
            <p style="font-size:1.2rem;font-weight:700;color:#7c3aed;margin:0 0 8px 0;">
                Connexion Google réussie !
            </p>
            <p style="color:#6b7280;font-size:0.9rem;margin:0 0 28px 0;">
                Retourne maintenant dans l'application Eldaana
            </p>
            <a href="{_deep_link}"
               style="display:inline-block;background:linear-gradient(135deg,#7c3aed,#c084fc);
                      color:#fff;text-decoration:none;padding:16px 32px;
                      border-radius:16px;font-weight:700;font-size:1.05rem;
                      box-shadow:0 4px 20px rgba(124,58,237,0.4);">
                ↩️ Retour dans l'app Eldaana
            </a>
            <p style="color:#9ca3af;font-size:0.75rem;margin-top:16px;">
                Tu peux fermer cet onglet ensuite
            </p>
        </div>
    """, unsafe_allow_html=True)
    del st.session_state["_android_oauth"]
    st.stop()

# ── Retour Stripe (success / cancel) ─────────────────────────────────────────
_uid_now = st.session_state.get("user_id", "")
if st.query_params.get("stripe_success") and _uid_now:
    if handle_stripe_return(_uid_now):
        st.query_params.clear()
        st.query_params["uid"] = _uid_now
        st.success("🎉 Bienvenue dans Eldaana Premium ! Toutes les fonctionnalités sont débloquées.")
        st.balloons()
elif st.query_params.get("stripe_cancel"):
    st.query_params.clear()
    st.query_params["uid"] = _uid_now

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

# ── Détection mode réveil (notification Android → ?wakeup=1) ─────────────────
if st.query_params.get("wakeup") == "1" and st.session_state.get("page") == "chat":
    st.session_state.page = "wakeup"

# ── Injection config Android (alarme réveil) ──────────────────────────────────
# L'app Android lit cet élément caché via JS pour programmer l'alarme quotidienne
heure_reveil = profile.get("heure_reveil", "")
if heure_reveil:
    st.markdown(
        f'<div id="eldaana-config" '
        f'data-wakeup="{heure_reveil}" '
        f'data-prenom="{prenom}" '
        f'style="display:none;position:absolute;width:0;height:0;"></div>',
        unsafe_allow_html=True,
    )

# ── Message d'accueil ──────────────────────────────────────────────────────────
if weather:
    GREETING = build_briefing(weather, profile)
else:
    genre = profile.get("sexe", "").lower() if profile else ""
    accord = "heureuse" if genre == "femme" else "heureux"
    GREETING = f"Bonjour {prenom} — Comment puis-je te rendre {accord} aujourd'hui ?"

# ── PAGE : COURSES ────────────────────────────────────────────────────────────
if st.session_state.page == "shopping":
    col1, col2 = st.columns([1, 6])
    with col1:
        if logo_path.exists():
            st.image(str(logo_path), width=64)
    with col2:
        st.markdown('<p class="eldaana-title">Eldaana</p>', unsafe_allow_html=True)
        st.markdown('<p class="eldaana-subtitle">Mes courses</p>', unsafe_allow_html=True)
    st.divider()
    show_shopping_page(profile)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Retour à la conversation"):
        st.session_state.page = "chat"
        st.rerun()
    st.stop()

# ── PAGE : EMAILS ────────────────────────────────────────────────────────────
if st.session_state.page == "email":
    col1, col2 = st.columns([1, 6])
    with col1:
        if logo_path.exists():
            st.image(str(logo_path), width=64)
    with col2:
        st.markdown('<p class="eldaana-title">Eldaana</p>', unsafe_allow_html=True)
        st.markdown('<p class="eldaana-subtitle">Mes emails</p>', unsafe_allow_html=True)
    st.divider()
    show_email_page(profile)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Retour à la conversation"):
        st.session_state.page = "chat"
        st.rerun()
    st.stop()

# ── PAGE : BUDGET ────────────────────────────────────────────────────────────
if st.session_state.page == "budget":
    col1, col2 = st.columns([1, 6])
    with col1:
        if logo_path.exists():
            st.image(str(logo_path), width=64)
    with col2:
        st.markdown('<p class="eldaana-title">Eldaana</p>', unsafe_allow_html=True)
        st.markdown('<p class="eldaana-subtitle">Mon budget</p>', unsafe_allow_html=True)
    st.divider()
    show_budget_page(profile)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Retour à la conversation"):
        st.session_state.page = "chat"
        st.rerun()
    st.stop()

# ── PAGE : VOYANCE ────────────────────────────────────────────────────────────
if st.session_state.page == "voyance":
    col1, col2 = st.columns([1, 6])
    with col1:
        if logo_path.exists():
            st.image(str(logo_path), width=64)
    with col2:
        st.markdown('<p class="eldaana-title">Eldaana</p>', unsafe_allow_html=True)
        st.markdown('<p class="eldaana-subtitle">Mes prédictions</p>', unsafe_allow_html=True)
    st.divider()
    show_voyance_page(profile)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Retour à la conversation"):
        st.session_state.page = "chat"
        st.rerun()
    st.stop()

# ── PAGE : TABLEAU DE BORD ────────────────────────────────────────────────────
if st.session_state.page == "dashboard":
    col1, col2 = st.columns([1, 6])
    with col1:
        if logo_path.exists():
            st.image(str(logo_path), width=64)
    with col2:
        st.markdown('<p class="eldaana-title">Eldaana</p>', unsafe_allow_html=True)
        st.markdown('<p class="eldaana-subtitle">Mon tableau de bord</p>', unsafe_allow_html=True)
    st.divider()
    show_dashboard(profile, weather)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Retour à la conversation"):
        st.session_state.page = "chat"
        st.rerun()
    st.stop()

# ── PAGE : RGPD ───────────────────────────────────────────────────────────────
if st.session_state.page == "rgpd":
    col1, col2 = st.columns([1, 6])
    with col1:
        if logo_path.exists():
            st.image(str(logo_path), width=64)
    with col2:
        st.markdown('<p class="eldaana-title">Eldaana</p>', unsafe_allow_html=True)
        st.markdown('<p class="eldaana-subtitle">Vie privée & RGPD</p>', unsafe_allow_html=True)
    st.divider()
    show_rgpd_page(profile)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Retour à la conversation"):
        st.session_state.page = "chat"
        st.rerun()
    st.stop()

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

    # Statut transport en temps réel
    show_transport_status_sidebar(profile, weather)

    st.divider()

    # ── Statut Premium ────────────────────────────────────────────────────────
    _uid_sb  = st.session_state.get("user_id", "")
    _premium = is_premium(_uid_sb)
    if _premium:
        st.markdown(
            '<div style="background:linear-gradient(135deg,#7c3aed,#c084fc);'
            'color:#fff;border-radius:10px;padding:7px 10px;text-align:center;'
            'font-size:0.8rem;font-weight:700;margin-bottom:6px;">✨ Premium actif</div>',
            unsafe_allow_html=True,
        )
        _portal_url = create_portal_url(
            _uid_sb,
            f"https://app.eldaana.io/?uid={_uid_sb}"
        )
        if _portal_url:
            st.markdown(
                f'<a href="{_portal_url}" style="display:block;text-align:center;'
                f'color:#9ca3af;font-size:0.72rem;margin-bottom:8px;">Gérer mon abonnement</a>',
                unsafe_allow_html=True,
            )
    else:
        _app_url = f"https://app.eldaana.io/?uid={_uid_sb}"
        _checkout_url = create_checkout_url(
            _uid_sb,
            profile.get("google_email", ""),
            _app_url,
        )
        if _checkout_url:
            st.markdown(
                f'<a href="{_checkout_url}" style="display:block;background:linear-gradient(135deg,#f59e0b,#f97316);'
                f'color:#fff;font-weight:700;font-size:0.82rem;text-decoration:none;'
                f'text-align:center;border-radius:10px;padding:9px 8px;margin-bottom:8px;">'
                f'⭐ Passer Premium — 9,99€/mois</a>',
                unsafe_allow_html=True,
            )

    if not profile.get("onboarding_lifestyle_complete"):
        st.info("💡 Plus Eldaana vous connaît, plus elle est précise !")

    if st.button("🏠 Tableau de bord", use_container_width=True):
        st.session_state.page = "dashboard"
        st.rerun()

    if st.button("✏️ Enrichir mon profil", use_container_width=True):
        st.session_state.page = "profile"
        st.rerun()

    if st.button("🌐 Ma vie numérique", use_container_width=True):
        st.session_state.page = "social"
        st.rerun()

    if st.button("📧 Mes emails", use_container_width=True):
        st.session_state.page = "email"
        st.rerun()

    if st.button("🛒 Mes courses", use_container_width=True):
        st.session_state.page = "shopping"
        st.rerun()

    if st.button("💰 Mon budget", use_container_width=True):
        st.session_state.page = "budget"
        st.rerun()

    if st.button("🔮 Prédictions", use_container_width=True):
        st.session_state.page = "voyance"
        st.rerun()

    if st.button("🔒 Vie privée", use_container_width=True):
        st.session_state.page = "rgpd"
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Mode conversation vocale ──────────────────────────────────────────────
    if "voice_mode" not in st.session_state:
        st.session_state.voice_mode = False

    col_tog2, col_lbl2 = st.columns([1, 3])
    with col_tog2:
        voice_mode = st.toggle("vm", value=st.session_state.voice_mode,
                               key="voice_mode_toggle", label_visibility="collapsed")
    with col_lbl2:
        lbl2 = "🎙️ Mode vocal ON" if voice_mode else "🎙️ Mode vocal OFF"
        st.markdown(
            f'<p style="color:#C9A84C;font-size:0.85rem;font-weight:600;margin:8px 0 0 0;">{lbl2}</p>',
            unsafe_allow_html=True
        )
    st.session_state.voice_mode = voice_mode

    if voice_mode:
        _voice_base = st.secrets.get("VOICE_SERVER_URL", "https://eldaana-voice.fly.dev")
        _uid        = st.session_state.get("user_id", "")
        _url_voice  = f"{_voice_base}/?uid={_uid}"
        _app_url    = f"https://app.eldaana.io/?uid={_uid}"

        if is_premium(_uid):
            # ── Premium → lien vers Eldaana Voice (components.html pour Android) ──
            _v = _url_voice.replace("'", "%27").replace('"', "%22")
            _components_uid.html(f"""<!DOCTYPE html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:transparent;}}
a{{display:block;background:linear-gradient(135deg,#7c3aed,#c084fc);
   color:#fff;font-weight:700;font-size:0.9rem;text-decoration:none;
   text-align:center;border-radius:14px;padding:11px 8px;margin:8px 0 2px 0;
   box-shadow:0 0 16px rgba(192,132,252,0.4);}}
p{{color:#9ca3af;font-size:0.75rem;text-align:center;margin:4px 0 0 0;}}
</style></head><body>
<a href="{_url_voice}" onclick="var u='{_v}';
  if(window.EldaanaNav){{window.EldaanaNav.openVoice(u);return false;}}
  try{{window.top.location.href=u;return false;}}catch(e){{}}
  window.location.href=u;return false;">🎙️ Ouvrir Eldaana Voice →</a>
<p>Conversation vocale temps réel · Premium</p>
</body></html>""", height=70)
        else:
            # ── Non-premium → Stripe Checkout (components.html pour Android) ──────
            _checkout = create_checkout_url(_uid, profile.get("google_email", ""), _app_url)
            _dest     = _checkout or _app_url
            _d = _dest.replace("'", "%27").replace('"', "%22")
            _components_uid.html(f"""<!DOCTYPE html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:transparent;}}
a{{display:block;background:linear-gradient(135deg,#f59e0b,#f97316);
   color:#fff;font-weight:700;font-size:0.9rem;text-decoration:none;
   text-align:center;border-radius:14px;padding:11px 8px;margin:8px 0 2px 0;
   box-shadow:0 0 16px rgba(251,146,60,0.4);}}
p{{color:#9ca3af;font-size:0.75rem;text-align:center;margin:4px 0 0 0;}}
</style></head><body>
<a href="{_dest}" onclick="var u='{_d}';
  if(window.EldaanaNav){{window.EldaanaNav.openVoice(u);return false;}}
  try{{window.top.location.href=u;return false;}}catch(e){{}}
  window.location.href=u;return false;">🔒 Débloquer Eldaana Voice</a>
<p>Fonctionnalité Premium · 9,99€/mois</p>
</body></html>""", height=70)

    # ── Toggle TTS seul ───────────────────────────────────────────────────────
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
    if voice_on or voice_mode:
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
        # Effacer le localStorage (window.parent car iframe Streamlit)
        _components_uid.html("""
        <script>
        (function() {
            try {
                var store = window.parent ? window.parent.localStorage : localStorage;
                store.removeItem('eldaana_uid');
            } catch(e) {}
        })();
        </script>
        """, height=1)
        st.session_state.page = "onboarding"
        st.rerun()

# ── PAGE : RÉVEIL ─────────────────────────────────────────────────────────────
if st.session_state.page == "wakeup":
    col1, col2 = st.columns([1, 6])
    with col1:
        if logo_path.exists():
            st.image(str(logo_path), width=72)
    with col2:
        st.markdown('<p class="eldaana-title">Bonjour ☀️</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="eldaana-subtitle">C\'est l\'heure de commencer ta journée</p>',
            unsafe_allow_html=True,
        )
    st.divider()

    # Construction du message de réveil
    if weather:
        wakeup_txt = build_wakeup_message(weather, profile)
        # Carte météo visuelle
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #fdf4ff 0%, #e8f8ff 100%);
            border: 1.5px solid #c084fc;
            border-radius: 20px;
            padding: 2rem 1.5rem;
            text-align: center;
            margin: 0.5rem 0 1.5rem 0;
        ">
            <p style="font-size:3.5rem;margin:0 0 0.5rem 0;">{weather['emoji']}</p>
            <p style="font-size:1.6rem;font-weight:700;color:#7c3aed;margin:0 0 0.25rem 0;">
                {weather['temp_current']}°C
            </p>
            <p style="color:#6b7280;margin:0 0 0.25rem 0;">
                {weather['description']} à {weather['city']}
            </p>
            <p style="color:#9ca3af;font-size:0.85rem;margin:0;">
                Min {weather['temp_min']}° · Max {weather['temp_max']}°
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        genre = profile.get("sexe", "").lower()
        accord = "prête" if genre == "femme" else "prêt"
        wakeup_txt = (
            f"Bonjour {prenom} ! C'est l'heure de se lever. "
            f"Tu es {accord} pour une belle journée ?"
        )

    # Message positif
    st.markdown(f"""
    <p style="
        text-align:center;
        font-size:1.05rem;
        color:#4b5563;
        font-style:italic;
        margin: 0 0 1.5rem 0;
        padding: 0 1rem;
    ">{wakeup_txt.split(". ")[-2] if ". " in wakeup_txt else ""}</p>
    """, unsafe_allow_html=True)

    # TTS automatique au premier chargement
    if st.session_state.get("voice_on", True) and not st.session_state.get("wakeup_spoken"):
        tts_future = prepare_audio_async(wakeup_txt)
        speak(wakeup_txt, precomputed=tts_future)
        st.session_state.wakeup_spoken = True

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔊 Réécouter", use_container_width=True):
            speak(wakeup_txt)
    with col_b:
        if st.button("💜 Commencer ma journée", use_container_width=True, type="primary"):
            st.session_state.page = "chat"
            st.session_state.wakeup_spoken = False
            st.query_params.clear()
            st.rerun()
    st.stop()

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

# ── BANNIÈRE TRANSPORT URGENTE (avant tout le reste) ─────────────────────────
# Vérifier si on est proche du départ ET qu'il y a une perturbation
# (une seule vérif par session pour ne pas spammer l'API)
if "transport_alert_checked" not in st.session_state:
    st.session_state.transport_alert_checked = True
    st.session_state.departure_alert = check_departure_alert(profile, weather)

if st.session_state.get("departure_alert"):
    show_departure_alert_banner(st.session_state.departure_alert)
    if st.button("🔄 Vérifier à nouveau", key="refresh_transport"):
        st.session_state.transport_alert_checked = False
        st.session_state.departure_alert = None
        st.rerun()

# ── Humeur du jour (widget compact en haut du chat) ───────────────────────────
user_id_chat = profile.get("user_id", "")
with st.expander("😊 Comment tu te sens aujourd'hui ?", expanded=False):
    show_humeur_widget(user_id_chat)

# État de la conversation — chargement depuis Supabase si première visite
if "messages" not in st.session_state:
    _uid_chat = profile.get("user_id", "")
    _history  = load_conversation(_uid_chat) if _uid_chat else []
    if _history:
        st.session_state.messages         = _history
        st.session_state.display_messages = _history
    else:
        st.session_state.messages         = []
        st.session_state.display_messages = [{"role": "assistant", "content": GREETING}]

# Affichage de l'historique
_user_avatar = _get_user_avatar()
for msg in st.session_state.display_messages:
    _avatar = LOGO if msg["role"] == "assistant" else _user_avatar
    with st.chat_message(msg["role"], avatar=_avatar):
        st.markdown(msg["content"])

# ── Saisie : micro (mode vocal) + texte ──────────────────────────────────────
_voice_mode = st.session_state.get("voice_mode", False)
_voice_on   = st.session_state.get("voice_on", True)

# Initialiser le compteur de tour pour le micro (recrée le composant à chaque tour)
if "voice_turn" not in st.session_state:
    st.session_state.voice_turn = 0

user_input = None

if _voice_mode:
    # Mode vocal ON → EldaanaVoice, saisie texte toujours disponible
    user_input = st.chat_input("💬 Écris ton message à Eldaana…")

else:
    # ── Saisie texte classique ────────────────────────────────────────────
    user_input = st.chat_input(f"Écris ton message à Eldaana…")

# ── Traitement du message ─────────────────────────────────────────────────────
if user_input:
    st.session_state.display_messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user", avatar=_user_avatar):
        st.markdown(user_input)

    # ── Détection automatique d'achats ───────────────────────────────────────
    user_id   = profile.get("user_id", "")
    purchases = detect_purchases_in_message(user_input)
    if purchases:
        added = add_purchase(user_id, purchases)
        if added:
            noms = ", ".join(a["name"] for a in added)
            st.toast(f"🛒 Achat enregistré : {noms}", icon="✅")

    # ── Construction du prompt système enrichi ────────────────────────────────
    system_prompt = get_system_prompt(profile)

    # Mode vocal : réponses courtes + sans markdown
    if _voice_mode:
        system_prompt += get_voice_mode_suffix()

    # Humeur du jour
    system_prompt += format_humeur_for_prompt(user_id)

    # Budget
    system_prompt += format_budget_for_prompt(user_id)

    # Emails (résumé non-lus/urgents si Gmail connecté)
    system_prompt += format_email_summary_for_prompt(user_id)

    # Alertes transport (si perturbation sur les lignes de l'utilisateur)
    dep_alert = st.session_state.get("departure_alert")
    if dep_alert and dep_alert.get("tc_alerts"):
        from transport_alerts import format_departure_alert_message
        alert_txt = format_departure_alert_message(dep_alert)
        if alert_txt:
            system_prompt += (
                f"\n\n[ALERTE TRANSPORT DÉPART]\n{alert_txt}\n"
                "Mentionne cette alerte de manière proactive si l'utilisateur parle de son trajet ou de son départ.\n"
                "[FIN ALERTE TRANSPORT]"
            )

    # ── Recherche web si nécessaire (désactivée en mode vocal pour la rapidité) ──
    if not _voice_mode and should_search_web(user_input):
        with st.spinner("🔍 Recherche web en cours..."):
            web_results = search_web(user_input)
        if web_results:
            system_prompt += format_web_results_for_prompt(web_results, user_input)
            st.toast("✅ Infos web récupérées", icon="🌐")
        else:
            err = st.session_state.get("gemini_last_error", "inconnu")
            st.toast(f"⚠️ Recherche : {err[:80]}", icon="⚠️")

    # ── Rappels courses dans le contexte ─────────────────────────────────────
    reminders = get_reminders(user_id)
    if reminders:
        system_prompt += format_reminders_for_prompt(reminders)
        for r in reminders:
            mark_reminded(user_id, r["name"])

    # ── Suivi courses général ─────────────────────────────────────────────────
    system_prompt += format_shopping_for_prompt(user_id)

    # ── Modèle : Haiku (rapide) en mode vocal, Opus sinon ────────────────────
    _model      = "claude-haiku-4-5-20251001" if _voice_mode else "claude-opus-4-6"
    _max_tokens = 350 if _voice_mode else 1024

    # ── Streaming avec pré-génération TTS phrase par phrase ──────────────────
    with st.chat_message("assistant", avatar=LOGO):
        reply_placeholder = st.empty()
        full_reply   = ""
        sent_buffer  = ""     # tampon pour détecter les fins de phrase
        tts_futures  = []     # futures des TTS pré-générées

        with client.messages.stream(
            model=_model,
            max_tokens=_max_tokens,
            system=system_prompt,
            messages=st.session_state.messages,
        ) as stream:
            for chunk in stream.text_stream:
                full_reply  += chunk
                sent_buffer += chunk
                reply_placeholder.markdown(full_reply + "▌")

                # Dès qu'une phrase est complète → lancer la TTS en background
                if _voice_on:
                    for sep in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
                        idx = sent_buffer.find(sep)
                        if idx > 15:   # au moins 15 chars = phrase significative
                            sentence   = sent_buffer[:idx + 1].strip()
                            sent_buffer = sent_buffer[idx + len(sep):]
                            f = prepare_audio_async(sentence)
                            if f:
                                tts_futures.append(f)
                            break

        reply_placeholder.markdown(full_reply)

        # Ajouter le reste du tampon (dernière phrase sans ponctuation finale)
        if sent_buffer.strip() and _voice_on:
            f = prepare_audio_async(sent_buffer.strip())
            if f:
                tts_futures.append(f)

    # ── Lecture audio : depuis les futures pré-générés ────────────────────────
    if _voice_on:
        if tts_futures:
            speak_from_prefetched(tts_futures, fallback_text=full_reply)
        else:
            # Texte très court → pas eu le temps de pré-générer → générer maintenant
            tts_future = prepare_audio_async(full_reply)
            speak(full_reply, precomputed=tts_future)


    st.session_state.display_messages.append({"role": "assistant", "content": full_reply})
    st.session_state.messages.append({"role": "assistant", "content": full_reply})

    # ── Sauvegarde de l'historique dans Supabase ──────────────────────────────
    save_conversation(profile.get("user_id", ""), st.session_state.messages)
