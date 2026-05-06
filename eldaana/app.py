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
from voice import speak, stop, VOICE_OPTIONS, get_voice_options, prepare_audio_async, speak_from_prefetched, estimate_speech_duration  # noqa
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
try:
    from stripe_payment import handle_stripe_success, upgrade_to_premium
except ImportError:
    def handle_stripe_success(session_id, uid): return False, ""   # type: ignore
    def upgrade_to_premium(uid): return False                       # type: ignore
from pathlib import Path

# ── Configuration de la page ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Eldaana",
    page_icon="logo.png",
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

# ── Langue de l'app (définie au premier lancement Android ou par le toggle) ──
if "lang" not in st.session_state:
    st.session_state.lang = st.query_params.get("lang", "fr")

# ── Système de traduction centralisé ─────────────────────────────────────────
from translations import t as _t

# ── Détection APK Android (platform=android dans l'URL) ──────────────────────
# Mise à jour à chaque rechargement si platform=android est présent dans l'URL
if st.query_params.get("platform") == "android":
    st.session_state.is_android = True
elif "is_android" not in st.session_state:
    st.session_state.is_android = False
_is_android = st.session_state.is_android

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
    _session_id_stripe = st.query_params.get("session_id", "")
    _ok, _plan = handle_stripe_success(_session_id_stripe, _uid_now)
    if not _ok:
        _ok = handle_stripe_return(_uid_now)  # fallback ancien flux
        _plan = "essential"
    if _ok:
        st.query_params.clear()
        st.query_params["uid"] = _uid_now
        if _plan == "premium":
            st.success(_t("stripe_premium_welcome"))
        elif _plan == "essential":
            st.success(_t("stripe_essential_welcome"))
        else:
            st.success(_t("stripe_success"))
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

# ── Restauration de la voix préférée (une seule fois par session) ─────────────
if "eldaana_voice" not in st.session_state:
    _saved_voice = profile.get("preferred_voice", "nova")
    st.session_state.eldaana_voice = _saved_voice

# ── Météo + timezone : récupérés une fois par session, retentative si None ────
ville = profile.get("ville", "")
if "weather" not in st.session_state or (
    st.session_state.weather is None and ville
):
    st.session_state.weather = get_weather(ville, profile) if ville else None
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
    try:
        GREETING = build_briefing(weather, profile)
    except Exception:
        genre = profile.get("sexe", "").lower() if profile else ""
        accord = _t("greeting_f") if genre == "femme" else _t("greeting_m")
        GREETING = _t("greeting_msg").format(prenom=prenom, accord=accord)
else:
    genre = profile.get("sexe", "").lower() if profile else ""
    accord = _t("greeting_f") if genre == "femme" else _t("greeting_m")
    GREETING = _t("greeting_msg").format(prenom=prenom, accord=accord)

# ── PAGE : COURSES ────────────────────────────────────────────────────────────
if st.session_state.page == "shopping":
    col1, col2 = st.columns([1, 6])
    with col1:
        if logo_path.exists():
            st.image(str(logo_path), width=64)
    with col2:
        st.markdown('<p class="eldaana-title">Eldaana</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="eldaana-subtitle">'+_t('page_shopping')+'</p>', unsafe_allow_html=True)
    st.divider()
    show_shopping_page(profile)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(_t("back_to_chat")):
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
        st.markdown(f'<p class="eldaana-subtitle">'+_t('page_email')+'</p>', unsafe_allow_html=True)
    st.divider()
    show_email_page(profile)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(_t("back_to_chat")):
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
        st.markdown(f'<p class="eldaana-subtitle">'+_t('page_budget')+'</p>', unsafe_allow_html=True)
    st.divider()
    show_budget_page(profile)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(_t("back_to_chat")):
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
        st.markdown(f'<p class="eldaana-subtitle">'+_t('page_voyance')+'</p>', unsafe_allow_html=True)
    st.divider()
    show_voyance_page(profile)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(_t("back_to_chat")):
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
        st.markdown(f'<p class="eldaana-subtitle">{_t("page_dashboard")}</p>', unsafe_allow_html=True)
    st.divider()
    show_dashboard(profile, weather)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(_t("back_to_chat")):
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
        st.markdown(f'<p class="eldaana-subtitle">{_t("page_rgpd")}</p>', unsafe_allow_html=True)
    st.divider()
    show_rgpd_page(profile)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(_t("back_to_chat")):
        st.session_state.page = "chat"
        st.rerun()
    st.stop()

# ── PAGE : AGENT PERMISSIONS (Premium) ───────────────────────────────────────
if st.session_state.page == "agent_permissions":
    col1, col2 = st.columns([1, 6])
    with col1:
        if logo_path.exists():
            st.image(str(logo_path), width=64)
    with col2:
        st.markdown('<p class="eldaana-title">Eldaana</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="eldaana-subtitle">'+_t('page_agent')+'</p>', unsafe_allow_html=True)
    st.divider()
    try:
        from agents.permissions import show_permissions_settings
        show_permissions_settings(profile)
    except Exception as _e:
        st.error(_t("error_agent_load", e=_e))
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(_t("back_to_chat")):
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
        st.markdown(f'<p class="eldaana-subtitle">'+_t('page_social')+'</p>', unsafe_allow_html=True)
    st.divider()
    show_social_connect(profile)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(_t("back_to_chat")):
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
        st.markdown(f'<p class="eldaana-subtitle">'+_t('page_profile')+'</p>', unsafe_allow_html=True)
    st.divider()
    show_profile_form(profile)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(_t("back_to_chat")):
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
        from weather import get_weather_desc as _get_wdesc, _c_to_f as _ctof
        _lang_sb = st.session_state.get("lang", "fr")
        _wdesc_sb = _get_wdesc(weather.get("weathercode", 0), _lang_sb)
        if _lang_sb == "en":
            _temp_sb = f"{_ctof(weather['temp_current'])}°F"
            _tmax_sb = f"max {_ctof(weather['temp_max'])}°F"
        else:
            _temp_sb = f"{weather['temp_current']}°C"
            _tmax_sb = f"max {weather['temp_max']}°"
        st.markdown(
            f"{weather['emoji']} **{weather['city']}** · {_temp_sb}  \n"
            f"{_wdesc_sb} · {_tmax_sb}"
        )

    # Statut transport en temps réel
    show_transport_status_sidebar(profile, weather)

    # ── Widget scores journaliers compact (Essentiel+) ────────────────────────
    _uid_scores = st.session_state.get("user_id", "")
    try:
        from tier_access import can_access as _can_access
        _scores_allowed = _can_access("voyance_daily_scores", _uid_scores)
    except Exception:
        _scores_allowed = False
    if _scores_allowed:
        from datetime import date as _date
        _score_cache_key = f"scores_{_uid_scores}_{_date.today().isoformat()}"
        if _score_cache_key not in st.session_state:
            try:
                from voyance_engine import compute_scores as _compute_scores
                from humeur import get_humeur_stats as _get_humeur_stats
                from budget import get_budget_stats as _get_budget_stats
                from transport_alerts import get_transport_summary as _get_transport_summary
                st.session_state[_score_cache_key] = _compute_scores(
                    profile        = profile or {},
                    weather        = weather  or {},
                    humeur_data    = _get_humeur_stats(_uid_scores),
                    budget_data    = _get_budget_stats(_uid_scores),
                    transport_data = _get_transport_summary(profile or {}, weather or {}),
                )
            except Exception:
                pass  # scores non disponibles, on skip le widget
        _sc = st.session_state[_score_cache_key]
        # Couleur d'un score (vert / jaune / rouge)
        def _sc_color(s):
            if s >= 70: return "#22c55e"
            if s >= 45: return "#f59e0b"
            return "#ef4444"

        _s_hum = _sc.get("score_humeur",  _sc.get("score_journee", 60))
        _s_ene = _sc.get("score_energie", 60)
        _s_str = _sc.get("score_stress",  60)
        _s_bud = _sc.get("score_budget",  70)
        st.markdown(f"""
        <div style="background:rgba(124,58,237,0.07);border:1px solid rgba(192,132,252,0.3);
                    border-radius:12px;padding:0.55rem 0.7rem;margin:0.4rem 0;">
            <p style="margin:0 0 5px 0;font-size:0.72rem;color:#a78bfa;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;">
                {_t("scores_title")}
            </p>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;">
                <span style="font-size:0.75rem;color:#e9d5ff;">😊 <b style="color:{_sc_color(_s_hum)}">{_s_hum}</b></span>
                <span style="font-size:0.75rem;color:#e9d5ff;">⚡ <b style="color:{_sc_color(_s_ene)}">{_s_ene}</b></span>
                <span style="font-size:0.75rem;color:#e9d5ff;">😰 <b style="color:{_sc_color(100 - _s_str)}">{_s_str}</b></span>
                <span style="font-size:0.75rem;color:#e9d5ff;">💰 <b style="color:{_sc_color(_s_bud)}">{_s_bud}</b></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── Statut Premium ────────────────────────────────────────────────────────
    _uid_sb  = st.session_state.get("user_id", "")
    _premium = is_premium(_uid_sb)
    # Tier complet (free / essential / premium) pour gating des features
    try:
        from tier_access import get_user_tier as _get_tier
        _tier_sb = _get_tier(_uid_sb)
    except Exception:
        _tier_sb = "essential" if _premium else "free"

    if _tier_sb == "premium":
        _badge_label = "✨ Premium actif" if _tier_sb == "premium" else "⭐ Essentiel actif"
        _badge_color = "linear-gradient(135deg,#7c3aed,#c084fc)" if _tier_sb == "premium" \
                       else "linear-gradient(135deg,#f59e0b,#f97316)"
        st.markdown(
            f'<div style="background:{_badge_color};'
            f'color:#fff;border-radius:10px;padding:7px 10px;text-align:center;'
            f'font-size:0.8rem;font-weight:700;margin-bottom:6px;">{_badge_label}</div>',
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
    elif _tier_sb == "essential":
        # Essentiel → propose Premium
        _app_url = f"https://app.eldaana.io/?uid={_uid_sb}"
        try:
            from stripe_payment import create_checkout_url_premium as _checkout_prem
            _prem_url = _checkout_prem(_uid_sb, profile.get("google_email", ""), _app_url)
        except Exception:
            _prem_url = None
        if _prem_url:
            _safe_prem_ess = _prem_url.replace("'", "\\'")
            st.markdown(
                f'<a href="{_prem_url}" '
                f'onclick="if(window.EldaanaNav){{window.EldaanaNav.openVoice(\'{_safe_prem_ess}\');return false;}}"'
                f' style="display:block;background:linear-gradient(135deg,#7c3aed,#c084fc);'
                f'color:#fff;font-weight:700;font-size:0.82rem;text-decoration:none;'
                f'text-align:center;border-radius:14px;padding:9px 8px;margin-bottom:8px;">'
                f'{_t("stripe_upgrade_prem_btn")}</a>',
                unsafe_allow_html=True,
            )
    else:
        # Free → deux boutons côte à côte : Essentiel + Premium
        _app_url = f"https://app.eldaana.io/?uid={_uid_sb}"
        _email_sb = profile.get("google_email", "")
        _checkout_ess = create_checkout_url(_uid_sb, _email_sb, _app_url)
        try:
            from stripe_payment import create_checkout_url_premium as _checkout_prem_fn
            _checkout_prem = _checkout_prem_fn(_uid_sb, _email_sb, _app_url)
        except Exception:
            _checkout_prem = None

        if _checkout_ess or _checkout_prem:
            # ── components.html : évite l'interception React de st.markdown ──
            # target="_top" = navigue la frame Streamlit (PC)
            # EldaanaNav.openVoice = charge dans le WebView Android
            import streamlit.components.v1 as _cmp_stripe
            _safe_ess  = (_checkout_ess  or "").replace("'", "%27")
            _safe_prem = (_checkout_prem or "").replace("'", "%27")
            # onclick : Android → EldaanaNav (charge dans WebView, shouldOverride l'envoie dans Chrome)
            #          PC      → window.open (autorisé par sandbox allow-popups de components.html)
            _onclick_ess  = (f"if(window.EldaanaNav){{window.EldaanaNav.openVoice('{_safe_ess}');return false;}}"
                             f"window.open('{_safe_ess}','_blank');return false;")
            _onclick_prem = (f"if(window.EldaanaNav){{window.EldaanaNav.openVoice('{_safe_prem}');return false;}}"
                             f"window.open('{_safe_prem}','_blank');return false;")
            _btn_ess = (
                f'<a href="{_checkout_ess}" onclick="{_onclick_ess}" '
                f'style="display:flex;align-items:center;justify-content:center;flex:1;'
                f'background:linear-gradient(135deg,#f59e0b,#f97316);'
                f'color:#fff;font-weight:700;font-size:0.78rem;text-decoration:none;'
                f'border-radius:14px;padding:9px 6px;text-align:center;line-height:1.3;">'
                f'{_t("stripe_ess_btn_html")}</a>'
            ) if _checkout_ess else '<div style="flex:1"></div>'
            _btn_prem = (
                f'<a href="{_checkout_prem}" onclick="{_onclick_prem}" '
                f'style="display:flex;align-items:center;justify-content:center;flex:1;'
                f'background:linear-gradient(135deg,#7c3aed,#c084fc);'
                f'color:#fff;font-weight:700;font-size:0.78rem;text-decoration:none;'
                f'border-radius:14px;padding:9px 6px;text-align:center;line-height:1.3;">'
                f'{_t("stripe_prem_btn_html")}</a>'
            ) if _checkout_prem else '<div style="flex:1"></div>'
            _cmp_stripe.html(
                f'<html><head><meta charset="utf-8">'
                f'<style>*{{margin:0;padding:0;box-sizing:border-box;}}body{{background:transparent;}}'
                f'</style></head><body>'
                f'<div style="display:flex;gap:8px;">'
                f'{_btn_ess}{_btn_prem}</div>'
                f'</body></html>',
                height=72,
            )

    if not profile.get("onboarding_lifestyle_complete") and _tier_sb == "free":
        st.info(_t("sidebar_enrich_info"))

    if st.button(_t("btn_dashboard"), use_container_width=True):
        st.session_state.page = "dashboard"
        st.rerun()

    if st.button(_t("btn_profile"), use_container_width=True):
        st.session_state.page = "profile"
        st.rerun()

    if st.button(_t("btn_social"), use_container_width=True):
        st.session_state.page = "social"
        st.rerun()

    if st.button(_t("btn_emails"), use_container_width=True):
        st.session_state.page = "email"
        st.rerun()

    if st.button(_t("btn_shopping"), use_container_width=True):
        st.session_state.page = "shopping"
        st.rerun()

    if st.button(_t("btn_budget"), use_container_width=True):
        st.session_state.page = "budget"
        st.rerun()

    if st.button(_t("btn_predictions"), use_container_width=True):
        st.session_state.page = "voyance"
        st.rerun()

    if st.button(_t("btn_privacy"), use_container_width=True):
        st.session_state.page = "rgpd"
        st.rerun()

    # Agent — Premium uniquement
    if _tier_sb == "premium":
        if st.button(_t("btn_agent"), use_container_width=True):
            st.session_state.page = "agent_permissions"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Mode conversation vocale — Premium uniquement ─────────────────────────
    if "voice_mode" not in st.session_state:
        st.session_state.voice_mode = False

    if _tier_sb == "premium":
        col_tog2, col_lbl2 = st.columns([1, 3])
        with col_tog2:
            voice_mode = st.toggle("vm", value=st.session_state.voice_mode,
                                   key="voice_mode_toggle", label_visibility="collapsed")
        with col_lbl2:
            lbl2 = _t("voice_on_label") if voice_mode else _t("voice_off_label")
            st.markdown(
                f'<p style="color:#C9A84C;font-size:0.85rem;font-weight:600;margin:8px 0 0 0;">{lbl2}</p>',
                unsafe_allow_html=True
            )
        st.session_state.voice_mode = voice_mode
    else:
        voice_mode = False
        st.session_state.voice_mode = False
        if _tier_sb == "essential":
            # Cadenas visible pour Essentiel — invite à Premium
            st.markdown(
                f'<div style="opacity:.55;padding:6px 0 2px 0;font-size:0.83rem;color:#9ca3af;">'
                f'{_t("voice_premium_lock")}</div>',
                unsafe_allow_html=True
            )

    if voice_mode:
        import urllib.parse as _uparse
        _voice_base    = st.secrets.get("VOICE_SERVER_URL", "https://eldaana-voice.fly.dev")
        _uid           = st.session_state.get("user_id", "")
        _current_voice = st.session_state.get("eldaana_voice", "nova")
        _app_url       = f"https://app.eldaana.io/?uid={_uid}"
        # ?back= : "Revenir" sur la page Voice revient à la conversation
        # Android : EldaanaNav.goBack() est utilisé en priorité (bridge WebView)
        # PC      : window.location.href = back_url
        _back = _uparse.quote(_app_url, safe="")
        _url_voice     = f"{_voice_base}/?uid={_uid}&voice={_current_voice}&back={_back}"

        if is_premium(_uid):
            # ── Premium → bouton Eldaana Voice ───────────────────────────────────
            _BTN_STYLE_VOICE = (
                "display:block;background:linear-gradient(135deg,#7c3aed,#c084fc);"
                "color:#fff;font-weight:700;font-size:0.9rem;text-decoration:none;"
                "text-align:center;border-radius:14px;padding:11px 8px;margin:8px 0 2px 0;"
                "box-shadow:0 0 16px rgba(192,132,252,0.4);"
            )
            if _is_android:
                # APK : EldaanaAndroid.openVoice() — bridge fiable (même-origine)
                _v = _url_voice.replace("'", "%27").replace('"', "%22")
                _components_uid.html(f"""<!DOCTYPE html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>*{{margin:0;padding:0;box-sizing:border-box;}}body{{background:transparent;}}
a{{display:block;background:linear-gradient(135deg,#7c3aed,#c084fc);
color:#fff;font-weight:700;font-size:0.9rem;text-decoration:none;
text-align:center;border-radius:14px;padding:11px 8px;margin:8px 0 2px 0;
box-shadow:0 0 16px rgba(192,132,252,0.4);}}
</style></head><body>
<a href="{_url_voice}" onclick="
  var u='{_v}';
  var b=null;
  try{{b=window.EldaanaAndroid;}}catch(e){{}}
  if(!b)try{{b=window.parent.EldaanaAndroid;}}catch(e){{}}
  if(!b)try{{b=window.top.EldaanaAndroid;}}catch(e){{}}
  if(b){{b.openVoice(u);return false;}}
  window.location.href=u;return false;">{_t("voice_open_btn")}</a>
</body></html>""", height=54)
            else:
                # PC/navigateur : lien simple qui s'ouvre dans un nouvel onglet
                st.markdown(
                    f'<a href="{_url_voice}" target="_blank" style="{_BTN_STYLE_VOICE}">'
                    f'{_t("voice_open_btn")}</a>'
                    f'<p style="color:#9ca3af;font-size:0.75rem;text-align:center;margin:4px 0 0 0;">'
                    f'{_t("voice_open_caption")}</p>',
                    unsafe_allow_html=True,
                )
        else:
            # ── Non-premium → Stripe Checkout ────────────────────────────────────
            _checkout = create_checkout_url(_uid, profile.get("google_email", ""), _app_url)
            _dest     = _checkout or _app_url
            _BTN_STYLE_STRIPE = (
                "display:block;background:linear-gradient(135deg,#f59e0b,#f97316);"
                "color:#fff;font-weight:700;font-size:0.9rem;text-decoration:none;"
                "text-align:center;border-radius:14px;padding:11px 8px;margin:8px 0 2px 0;"
                "box-shadow:0 0 16px rgba(251,146,60,0.4);"
            )
            if _is_android:
                # APK : EldaanaAndroid.openVoice()
                _d = _dest.replace("'", "%27").replace('"', "%22")
                _components_uid.html(f"""<!DOCTYPE html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>*{{margin:0;padding:0;box-sizing:border-box;}}body{{background:transparent;}}
a{{display:block;background:linear-gradient(135deg,#f59e0b,#f97316);
color:#fff;font-weight:700;font-size:0.9rem;text-decoration:none;
text-align:center;border-radius:14px;padding:11px 8px;margin:8px 0 2px 0;
box-shadow:0 0 16px rgba(251,146,60,0.4);}}
</style></head><body>
<a href="{_dest}" onclick="
  var u='{_d}';
  var b=null;
  try{{b=window.EldaanaAndroid;}}catch(e){{}}
  if(!b)try{{b=window.parent.EldaanaAndroid;}}catch(e){{}}
  if(!b)try{{b=window.top.EldaanaAndroid;}}catch(e){{}}
  if(b){{b.openVoice(u);return false;}}
  window.location.href=u;return false;">{_t("voice_unlock_btn")}</a>
</body></html>""", height=54)
            else:
                # PC/navigateur : lien simple nouvel onglet
                st.markdown(
                    f'<a href="{_dest}" target="_blank" style="{_BTN_STYLE_STRIPE}">'
                    f'{_t("voice_unlock_btn")}</a>'
                    f'<p style="color:#9ca3af;font-size:0.75rem;text-align:center;margin:4px 0 0 0;">'
                    f'{_t("voice_unlock_caption")}</p>',
                    unsafe_allow_html=True,
                )

    # ── Toggle TTS + sélecteur voix — Essentiel+ uniquement ─────────────────
    if "voice_on" not in st.session_state:
        st.session_state.voice_on = False

    if _tier_sb in ("essential", "premium"):
        col_tog, col_lbl = st.columns([1, 3])
        with col_tog:
            voice_on = st.toggle("v", value=st.session_state.voice_on,
                                 key="voice_toggle", label_visibility="collapsed")
        with col_lbl:
            lbl = _t("voice_on") if voice_on else _t("voice_off")
            st.markdown(
                f'<p style="color:#F0E6FF;font-size:0.85rem;margin:8px 0 0 0;">{lbl}</p>',
                unsafe_allow_html=True
            )
        if voice_on:
            st.session_state.voice_on = True
        else:
            st.session_state.voice_on = False
            stop()

        # Sélecteur de voix filtré par tier
        if voice_on or voice_mode:
            st.markdown(
                f'<p style="color:#F0E6FF;font-size:0.82rem;margin:8px 0 4px 0;">'
                f'{_t("voice_label")}</p>',
                unsafe_allow_html=True
            )
            _voice_opts   = get_voice_options(_tier_sb, st.session_state.get("lang", "fr"))
            voice_labels  = list(_voice_opts.keys())
            saved_voice   = st.session_state.get("eldaana_voice", "nova")
            default_label = next(
                (l for l, v in _voice_opts.items() if v == saved_voice),
                voice_labels[0] if voice_labels else ""
            )
            if voice_labels:
                chosen_label = st.selectbox(
                    "voix",
                    voice_labels,
                    index=voice_labels.index(default_label) if default_label in voice_labels else 0,
                    key="voice_selector",
                    label_visibility="collapsed",
                )
                _chosen_voice = _voice_opts[chosen_label]
                if _chosen_voice != st.session_state.get("eldaana_voice"):
                    st.session_state.eldaana_voice = _chosen_voice
                    if profile.get("preferred_voice") != _chosen_voice:
                        profile["preferred_voice"] = _chosen_voice
                        from onboarding import save_profile as _save_profile
                        _save_profile(profile)
                else:
                    st.session_state.eldaana_voice = _chosen_voice
    else:
        # Gratuit : voix désactivée, TTS caché
        voice_on = False
        st.session_state.voice_on = False

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button(_t("btn_new_conv"), use_container_width=True):
        st.session_state.messages = []
        st.session_state.display_messages = [{"role": "assistant", "content": GREETING}]
        st.rerun()

    # ── Bascule de langue FR ↔ EN ─────────────────────────────────────────────
    if st.button(_t("btn_lang"), use_container_width=True):
        st.session_state.lang = "en" if st.session_state.get("lang", "fr") == "fr" else "fr"
        # Réinitialiser le greeting pour qu'il soit régénéré dans la nouvelle langue
        st.session_state.pop("display_messages", None)
        st.session_state.pop("messages", None)
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button(_t("btn_switch_user"), use_container_width=True):
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
        st.markdown('<p class="eldaana-title">'+_t("wakeup_title")+'</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="eldaana-subtitle">'+_t("wakeup_subtitle")+'</p>',
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
                {weather['description']} {_t('wakeup_in')} {weather['city']}
            </p>
            <p style="color:#9ca3af;font-size:0.85rem;margin:0;">
                Min {weather['temp_min']}° · Max {weather['temp_max']}°
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        genre = profile.get("sexe", "").lower()
        ready_key = "wakeup_ready_f" if genre == "femme" else "wakeup_ready_m"
        wakeup_txt = _t("wakeup_rise", prenom=prenom) + " " + _t(ready_key)

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
        if st.button(_t("wakeup_replay"), use_container_width=True):
            speak(wakeup_txt)
    with col_b:
        if st.button(_t("wakeup_start_day"), use_container_width=True, type="primary"):
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
        f'<p class="eldaana-subtitle">{_t("chat_subtitle")}</p>',
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
    if st.button(_t("refresh_transport"), key="refresh_transport"):
        st.session_state.transport_alert_checked = False
        st.session_state.departure_alert = None
        st.rerun()

# ── Humeur du jour (widget compact en haut du chat) ───────────────────────────
user_id_chat = profile.get("user_id", "")
with st.expander(_t("humeur_expander"), expanded=False):
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
    # Mode vocal ON → saisie texte disponible
    user_input = st.chat_input(_t("chat_input_ph"))

else:
    _tier_for_mic = st.session_state.get("_tier_cached", "free")
    if not _is_android and _tier_for_mic in ("essential", "premium"):
        # ── PC Essentiel/Premium : WebRTC natif (fonctionne dans Chrome) ──
        _mic_transcript = show_mic_button(key=f"mic_{st.session_state.voice_turn}")
        if _mic_transcript:
            user_input = _mic_transcript
            st.session_state.voice_turn += 1

    # ── Saisie texte classique ────────────────────────────────────────────
    _text_input = st.chat_input(_t("chat_input_ph"))
    if _text_input:
        user_input = _text_input

# ── Garde anti-doublon : évite de traiter deux fois le même message ──────────
# (peut arriver si l'injection JS déclenche 2 événements 'input' sur Android)
if user_input:
    _last_msgs = st.session_state.get("messages", [])
    if (_last_msgs
            and _last_msgs[-1].get("role") == "user"
            and _last_msgs[-1].get("content") == user_input):
        user_input = None   # déjà traité dans le run précédent

# ── Helper : affichage d'une réponse agent dans le chat ──────────────────────
def render_agent_response(agent_result: dict):
    """Affiche la réponse d'un agent avec ses boutons d'action."""
    result_type = agent_result.get("type", "")
    content     = agent_result.get("content", "")

    if content:
        st.markdown(content)

    # Permission manquante → lien vers les paramètres
    if result_type == "permission_required":
        if st.button("⚙️ Configurer les permissions agent", key="btn_agent_perms"):
            st.session_state.page = "agent_permissions"
            st.rerun()
        return

    # Confirmation (email draft, etc.)
    if agent_result.get("requires_confirmation"):
        c1, c2 = st.columns(2)
        with c1:
            confirm_label = agent_result.get("confirm_label", "Confirmer")
            if st.button(f"✅ {confirm_label}", use_container_width=True, type="primary",
                         key="agent_confirm"):
                st.session_state.pending_agent_confirm = agent_result
                st.rerun()
        with c2:
            edit_label = agent_result.get("edit_label", "Modifier")
            if st.button(f"✏️ {edit_label}", use_container_width=True, key="agent_edit"):
                st.session_state.editing_agent = agent_result

    # Deep link (shopping)
    action_url = agent_result.get("action_url")
    if action_url:
        action_label = agent_result.get("action_button", "Ouvrir")
        st.markdown(
            f'<a href="{action_url}" target="_blank" '
            f'style="display:inline-block;background:#7c3aed;color:#fff;'
            f'padding:10px 20px;border-radius:10px;text-decoration:none;'
            f'font-weight:700;margin-top:8px;">{action_label} ↗</a>',
            unsafe_allow_html=True,
        )

    # Boutons d'actions multiples
    for i, action_item in enumerate(agent_result.get("actions", [])):
        if st.button(action_item["label"], key=f"agent_action_{i}_{action_item['action']}"):
            st.session_state.pending_agent_action = action_item["action"]


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

    # ── Agent routing (Premium uniquement) ───────────────────────────────────
    _tier_for_agent = st.session_state.get("_tier_cached", "free")
    _agent_handled  = False
    if _tier_for_agent == "premium":
        try:
            from agents.agent_router import detect_intent, route_to_agent
            _intent = detect_intent(user_input)
            if _intent.get("is_agent_request") and _intent.get("confidence", 0) >= 0.7:
                _agent_result = route_to_agent(_intent, user_input, profile)
                if _agent_result is not None:
                    with st.chat_message("assistant", avatar=LOGO):
                        render_agent_response(_agent_result)
                    # Sauvegarder dans l'historique
                    _agent_text = _agent_result.get("content") or _agent_result.get("message", "")
                    if _agent_text:
                        st.session_state.display_messages.append(
                            {"role": "assistant", "content": _agent_text}
                        )
                        st.session_state.messages.append(
                            {"role": "assistant", "content": _agent_text}
                        )
                        save_conversation(profile.get("user_id", ""), st.session_state.messages)
                    _agent_handled = True
        except Exception:
            pass  # Fallback silencieux vers le chat Claude normal

    # ── Claude streaming (seulement si l'agent n'a pas traité la requête) ──────
    if not _agent_handled:

        # ── Construction du prompt système enrichi ────────────────────────────
        system_prompt = get_system_prompt(profile, lang=st.session_state.get("lang", "fr"))

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

        # ── Recherche web si nécessaire ───────────────────────────────────────
        if not _voice_mode and should_search_web(user_input):
            with st.spinner("🔍 Recherche web en cours..."):
                web_results = search_web(user_input)
            if web_results:
                system_prompt += format_web_results_for_prompt(web_results, user_input)
                st.toast("✅ Infos web récupérées", icon="🌐")
            else:
                err = st.session_state.get("gemini_last_error", "inconnu")
                st.toast(f"⚠️ Recherche : {err[:80]}", icon="⚠️")

        # ── Rappels courses dans le contexte ──────────────────────────────────
        reminders = get_reminders(user_id)
        if reminders:
            system_prompt += format_reminders_for_prompt(reminders)
            for r in reminders:
                mark_reminded(user_id, r["name"])

        # ── Suivi courses général ─────────────────────────────────────────────
        system_prompt += format_shopping_for_prompt(user_id)

        # ── Modèle : routing par tier (free→Haiku, essential→Sonnet, premium→Opus)
        _tier_chat = st.session_state.get("_tier_cached", "free")
        _model_map = {
            "free":      ("claude-haiku-4-5-20251001", 768),
            "essential": ("claude-sonnet-4-6",          1024),
            "premium":   ("claude-opus-4-6",            2048),
        }
        if _voice_mode:
            _model, _max_tokens = "claude-haiku-4-5-20251001", 350
        else:
            _model, _max_tokens = _model_map.get(_tier_chat, _model_map["free"])

        # ── HARD LIMITS — vérification avant tout envoi à Claude ────────────────
        try:
            from crisis_response import (
                detect_hard_limit, log_hard_limit_event, BLOCK_SESSION_MESSAGE,
                detect_crisis_level_fast, detect_crisis_level_ai,
                get_crisis_resources, get_crisis_system_prompt,
                format_crisis_card_ui, log_crisis_event,
            )
            _hard_limit = detect_hard_limit(user_input)
        except Exception:
            _hard_limit = "ok"

        if _hard_limit == "block_session":
            # Contenu pédocriminel → refus immédiat, pas d'envoi à Claude
            try:
                log_hard_limit_event(user_id, "block_session", user_input)
            except Exception:
                pass
            with st.chat_message("assistant", avatar=LOGO):
                st.markdown(BLOCK_SESSION_MESSAGE)
            st.session_state.messages.append({
                "role": "assistant", "content": BLOCK_SESSION_MESSAGE
            })
            st.stop()

        # ── Détection de crise avant envoi à Claude ───────────────────────────
        try:
            _crisis_level = detect_crisis_level_fast(user_input)
            # Analyse contextuelle toutes les 5 interactions si pas de mot-clé
            if _crisis_level == 0 and len(st.session_state.messages) > 4:
                if len(st.session_state.messages) % 5 == 0:
                    _crisis_level = detect_crisis_level_ai(
                        user_input, st.session_state.messages
                    )
            if _crisis_level >= 2:
                log_crisis_event(user_id, _crisis_level, user_input)
            # Injecter les instructions de crise EN TÊTE du system prompt
            _crisis_instructions = get_crisis_system_prompt(_crisis_level, profile)
            if _crisis_instructions:
                system_prompt = _crisis_instructions + "\n\n---\n\n" + system_prompt

            # soft_refuse : log + HARD_LIMITS déjà en tête du prompt (system_prompt.py)
            if _hard_limit == "soft_refuse":
                try:
                    log_hard_limit_event(user_id, "soft_refuse", user_input)
                except Exception:
                    pass
        except Exception:
            _crisis_level = 0

        # Afficher la carte d'aide si niveau 2 ou 3
        if _crisis_level >= 2:
            try:
                _crisis_resources = get_crisis_resources(profile)
                _crisis_html = format_crisis_card_ui(_crisis_level, _crisis_resources)
                st.markdown(_crisis_html, unsafe_allow_html=True)
            except Exception:
                pass

        # ── Streaming avec pré-génération TTS phrase par phrase ───────────────
        with st.chat_message("assistant", avatar=LOGO):
            reply_placeholder = st.empty()
            full_reply   = ""
            sent_buffer  = ""
            tts_futures  = []

            with client.messages.stream(
                model=_model,
                max_tokens=_max_tokens,
                system=[{"type": "text", "text": system_prompt,
                         "cache_control": {"type": "ephemeral"}}],
                messages=st.session_state.messages,
            ) as stream:
                for chunk in stream.text_stream:
                    full_reply  += chunk
                    sent_buffer += chunk
                    reply_placeholder.markdown(full_reply + "▌")

                    if _voice_on:
                        for sep in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
                            idx = sent_buffer.find(sep)
                            if idx > 15:
                                sentence    = sent_buffer[:idx + 1].strip()
                                sent_buffer = sent_buffer[idx + len(sep):]
                                f = prepare_audio_async(sentence)
                                if f:
                                    tts_futures.append(f)
                                break

            reply_placeholder.markdown(full_reply)

            if sent_buffer.strip() and _voice_on:
                f = prepare_audio_async(sent_buffer.strip())
                if f:
                    tts_futures.append(f)

        # ── Lecture audio ─────────────────────────────────────────────────────
        if _voice_on:
            if tts_futures:
                speak_from_prefetched(tts_futures, fallback_text=full_reply)
            else:
                tts_future = prepare_audio_async(full_reply)
                speak(full_reply, precomputed=tts_future)

        st.session_state.display_messages.append({"role": "assistant", "content": full_reply})
        st.session_state.messages.append({"role": "assistant", "content": full_reply})

        # ── Sauvegarde de l'historique dans Supabase ──────────────────────────
        save_conversation(profile.get("user_id", ""), st.session_state.messages)

# ── Bouton micro Android — Essentiel+ uniquement ──────────────────────────────
_tier_main = st.session_state.get("_tier_cached", "free")
try:
    from tier_access import get_user_tier as _get_tier_main
    _tier_main = _get_tier_main(st.session_state.get("user_id", ""))
    st.session_state["_tier_cached"] = _tier_main
except Exception:
    pass

if _is_android and not _voice_mode and _tier_main in ("essential", "premium"):
    _components_uid.html("""<!DOCTYPE html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{background:transparent;display:flex;justify-content:center;}
button{
  width:100%;padding:14px 8px;
  background:#fff;border:1.5px solid #e5e7eb;border-radius:12px;
  font-size:1rem;color:#374151;cursor:pointer;
  font-family:-apple-system,sans-serif;
  display:flex;align-items:center;justify-content:center;gap:8px;
}
button:active{background:#f3f4f6;}
</style></head><body>
<button onclick="
  var b=null;
  try{b=window.EldaanaAndroid;}catch(e){}
  if(!b)try{b=window.parent.EldaanaAndroid;}catch(e){}
  if(!b)try{b=window.top.EldaanaAndroid;}catch(e){}
  if(b){b.startNativeMic();}
">🎤 Appuyer et parler</button>
</body></html>""", height=56)
