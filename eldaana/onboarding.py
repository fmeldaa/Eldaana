"""
onboarding.py — Gestion des profils multi-utilisateurs + wizard d'onboarding.

Chaque utilisateur a son propre profil identifié par :
  - son Google ID (google_sub) s'il se connecte avec Google
  - un UUID généré automatiquement sinon
"""

import streamlit as st
import json
import uuid
from pathlib import Path
from google_auth import show_google_button, google_to_profile
from facebook_auth import show_facebook_button, facebook_to_profile
from storage import db_load, db_save
from cloudinary_storage import upload_profile_photo, get_profile_photo_url, invalidate_photo_cache
from translations import t as _t, t_list as _tl

# ── Configuration des pays supportés ─────────────────────────────────────────
COUNTRY_CONFIG = {
    "🇫🇷 France": {
        "code": "FR", "locale": "fr-FR", "currency": "EUR",
        "unit_temp": "C", "unit_speed": "km/h",
        "transport_provider": "navitia_idf",
        "traffic_provider": "tomtom",
        "weather_lang": "fr",
        "emergency_number": "15",
        "crisis_line": "3114",
    },
    "🇧🇪 Belgique": {
        "code": "BE", "locale": "fr-BE", "currency": "EUR",
        "unit_temp": "C", "unit_speed": "km/h",
        "transport_provider": "generic",
        "traffic_provider": "tomtom",
        "weather_lang": "fr",
        "emergency_number": "112",
        "crisis_line": "0800 32 123",
    },
    "🇨🇭 Suisse": {
        "code": "CH", "locale": "fr-CH", "currency": "CHF",
        "unit_temp": "C", "unit_speed": "km/h",
        "transport_provider": "generic",
        "traffic_provider": "tomtom",
        "weather_lang": "fr",
        "emergency_number": "144",
        "crisis_line": "143",
    },
    "🇬🇧 Grande-Bretagne": {
        "code": "GB", "locale": "en-GB", "currency": "GBP",
        "unit_temp": "C", "unit_speed": "mph",
        "transport_provider": "tfl",
        "traffic_provider": "tomtom",
        "weather_lang": "en",
        "emergency_number": "999",
        "crisis_line": "116 123",
    },
    "🇨🇦 Canada": {
        "code": "CA", "locale": "fr-CA", "currency": "CAD",
        "unit_temp": "C", "unit_speed": "km/h",
        "transport_provider": "generic",
        "traffic_provider": "tomtom",
        "weather_lang": "fr",
        "emergency_number": "911",
        "crisis_line": "1-866-APPELLE",
    },
    "🇺🇸 USA": {
        "code": "US", "locale": "en-US", "currency": "USD",
        "unit_temp": "F", "unit_speed": "mph",
        "transport_provider": "generic",
        "traffic_provider": "tomtom",
        "weather_lang": "en",
        "emergency_number": "911",
        "crisis_line": "988",
    },
    "🇨🇩 RDC": {
        "code": "CD", "locale": "fr-CD", "currency": "USD",
        "unit_temp": "C", "unit_speed": "km/h",
        "transport_provider": "generic",
        "traffic_provider": "tomtom",
        "weather_lang": "fr",
        "emergency_number": "112",
        "crisis_line": None,
    },
    "🇬🇦 Gabon": {
        "code": "GA", "locale": "fr-GA", "currency": "XAF",
        "unit_temp": "C", "unit_speed": "km/h",
        "transport_provider": "generic",
        "traffic_provider": "tomtom",
        "weather_lang": "fr",
        "emergency_number": "1730",
        "crisis_line": None,
    },
}

DATA_DIR          = Path(__file__).parent / "user_data"
PROFILES_DIR      = DATA_DIR / "profiles"
CURRENT_USER_FILE = DATA_DIR / "current_user.json"
WARDROBE_DIR      = DATA_DIR / "wardrobe"
PHOTOS_DIR        = DATA_DIR / "photos"
LOGO_PATH         = Path(__file__).parent / "logo.png"


# ── Gestion des identifiants utilisateur ──────────────────────────────────────

def _read_current_user_id() -> str | None:
    """
    NE PAS UTILISER en production multi-utilisateurs.
    current_user.json est partagé côté serveur — chaque utilisateur
    doit être identifié uniquement via st.session_state.
    Conservé uniquement pour la migration locale.
    """
    return None  # Désactivé — session uniquement


def _write_current_user_id(user_id: str):
    """No-op en production. Ne pas écrire de fichier partagé côté serveur."""
    pass  # Désactivé


def get_active_user_id() -> str | None:
    """Retourne l'ID de l'utilisateur actif — SESSION UNIQUEMENT.
    Chaque onglet / appareil a sa propre session Streamlit indépendante."""
    return st.session_state.get("user_id")


def _profile_path(user_id: str) -> Path:
    return PROFILES_DIR / f"{user_id}.json"


# ── Profil I/O ─────────────────────────────────────────────────────────────────

def load_profile() -> dict | None:
    """Charge le profil de l'utilisateur actif."""
    user_id = get_active_user_id()
    if not user_id:
        return None
    return db_load(user_id)


def load_profile_by_google_sub(google_sub: str) -> dict | None:
    """Charge un profil à partir d'un Google ID (pour reconnexion)."""
    return db_load(google_sub)


def save_profile(profile: dict):
    """Sauvegarde le profil et met à jour l'utilisateur actif."""
    user_id = profile.get("user_id") or get_active_user_id()
    if not user_id:
        user_id = str(uuid.uuid4())
        profile["user_id"] = user_id

    db_save(profile)
    st.session_state["user_id"] = user_id


def is_onboarding_done() -> bool:
    p = load_profile()
    return p is not None and p.get("onboarding_complete", False)


def logout():
    """Déconnecte l'utilisateur actif (nettoie la session uniquement)."""
    for key in ["user_id", "social_prefill", "google_prefill", "messages", "display_messages",
                "weather", "transport_alert_checked", "departure_alert",
                "email_list", "email_summary"]:
        st.session_state.pop(key, None)


# ── Résumé sidebar ─────────────────────────────────────────────────────────────

def profile_summary(profile: dict) -> str:
    from translations import t_list as _tl_ps
    lines = []
    if profile.get("ville"):
        lines.append(f"📍 {profile['ville']}")
    if profile.get("sexe"):
        _GENDER_FR  = ["Femme", "Homme", "Non-binaire", "Préfère ne pas préciser"]
        _gender_idx = _GENDER_FR.index(profile["sexe"]) if profile["sexe"] in _GENDER_FR else -1
        _gender_opts_display = _tl_ps("pf_gender_opts")
        _gender_display = (
            _gender_opts_display[_gender_idx]
            if 0 <= _gender_idx < len(_gender_opts_display)
            else profile["sexe"]
        )
        lines.append(f"· {_gender_display}")
    if profile.get("profession"):
        lines.append(f"· {profile['profession']}")
    hobbies = profile.get("hobbies", [])
    if hobbies:
        lines.append("♥ " + ", ".join(hobbies[:3]))
    return "  ".join(lines)


# ── Sync photo depuis réseau social ──────────────────────────────────────────

def _sync_social_photo(uid: str, photo_url: str):
    """
    Télécharge la photo de profil du réseau social et l'uploade sur Cloudinary.
    Ne fait rien si une photo existe déjà ou si l'URL est vide.
    """
    if not uid or not photo_url:
        return
    # Ne pas écraser une photo déjà uploadée manuellement
    existing = get_profile_photo_url(uid)
    if existing:
        return
    try:
        import requests as _req
        resp = _req.get(photo_url, timeout=10)
        if resp.status_code == 200:
            upload_profile_photo(resp.content, uid)
            invalidate_photo_cache(uid)
    except Exception:
        pass


# ── Migration profil ancien format ────────────────────────────────────────────

def _migrate_legacy():
    """Désactivée — migration one-shot uniquement en local, jamais en production multi-users."""
    pass


# ── Onboarding Wizard ──────────────────────────────────────────────────────────

def show_onboarding() -> bool:
    """
    Affiche le wizard d'onboarding.
    Retourne True quand le profil est créé/chargé et qu'on peut entrer dans l'app.
    """
    # Migration silencieuse si ancien format
    _migrate_legacy()

    # Logo + titre
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=80)
    with col_title:
        st.markdown(f"""
        <p style="font-size:1.7rem;font-weight:700;
                  background:linear-gradient(135deg,#c084fc,#818cf8,#38bdf8);
                  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                  margin:14px 0 2px 0;">
            {_t("ob_welcome")}
        </p>
        <p style="color:#9ca3af;font-size:0.88rem;margin:0;">
            {_t("ob_tagline")}
        </p>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f'<p style="text-align:center;color:#6b7280;font-size:0.85rem;margin:0 0 10px 0;">'
        f'{_t("ob_continue_with")}</p>',
        unsafe_allow_html=True,
    )

    # ── SVG logos ─────────────────────────────────────────────────────────────
    _LOGO_GOOGLE = '''<svg width="18" height="18" viewBox="0 0 48 48" style="vertical-align:middle"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97 2.31-8.16 2.31-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>'''
    _LOGO_FACEBOOK = '''<svg width="18" height="18" viewBox="0 0 24 24" style="vertical-align:middle"><path fill="#1877F2" d="M24 12.073C24 5.404 18.627 0 12 0S0 5.404 0 12.073C0 18.1 4.388 23.094 10.125 24v-8.437H7.078v-3.49h3.047V9.41c0-3.025 1.792-4.697 4.533-4.697 1.312 0 2.686.235 2.686.235v2.97h-1.513c-1.491 0-1.956.93-1.956 1.886v2.269h3.328l-.532 3.49h-2.796V24C19.612 23.094 24 18.1 24 12.073z"/></svg>'''
    _LOGO_LINKEDIN = '''<svg width="18" height="18" viewBox="0 0 24 24" style="vertical-align:middle"><path fill="#0A66C2" d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>'''
    _LOGO_X = '''<svg width="18" height="18" viewBox="0 0 24 24" style="vertical-align:middle"><path fill="#000" d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.747l7.73-8.835L1.254 2.25H8.08l4.253 5.622zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>'''

    _btn = ("width:100%;background:#fff;border:1.5px solid #e5e7eb;"
            "border-radius:10px;padding:9px 6px;cursor:pointer;"
            "display:flex;align-items:center;justify-content:center;gap:7px;"
            "font-size:0.8rem;color:#374151;font-weight:600;font-family:sans-serif;")

    # ── 4 boutons sur une ligne ───────────────────────────────────────────────
    col_g, col_fb, col_li, col_x = st.columns(4)
    with col_g:
        google_info = show_google_button()
    with col_fb:
        facebook_info = show_facebook_button()
    with col_li:
        st.markdown(f'<button onclick="alert(\'LinkedIn — bientôt disponible !\')" style="{_btn}">'
                    f'{_LOGO_LINKEDIN} LinkedIn</button>', unsafe_allow_html=True)
    with col_x:
        st.markdown(f'<button onclick="alert(\'X — bientôt disponible !\')" style="{_btn}">'
                    f'{_LOGO_X} Twitter</button>', unsafe_allow_html=True)

    # ── Callback Google ───────────────────────────────────────────────────────
    if google_info:
        google_sub = google_info.get("sub", "")
        existing = load_profile_by_google_sub(google_sub)
        if existing and existing.get("onboarding_complete"):
            st.session_state["user_id"] = google_sub
            _sync_social_photo(google_sub, google_info.get("picture", ""))
            return True
        prefill_data = google_to_profile(google_info)
        _sync_social_photo(google_sub, google_info.get("picture", ""))
        st.session_state["social_prefill"] = prefill_data
        st.rerun()

    # ── Callback Facebook ─────────────────────────────────────────────────────
    if facebook_info:
        fb_id = facebook_info.get("id", "")
        existing = db_load(fb_id) if fb_id else None
        if existing and existing.get("onboarding_complete"):
            st.session_state["user_id"] = fb_id
            prefill_fb = facebook_to_profile(facebook_info)
            _sync_social_photo(fb_id, prefill_fb.get("fb_picture", ""))
            return True
        prefill_data = facebook_to_profile(facebook_info)
        _sync_social_photo(fb_id, prefill_data.get("fb_picture", ""))
        st.session_state["social_prefill"] = prefill_data
        st.rerun()

    # ── Formulaire ─────────────────────────────────────────────────────────────
    prefill      = st.session_state.get("social_prefill", {})
    from_social  = bool(prefill)
    from_fb      = from_social and bool(prefill.get("fb_id"))

    if from_social:
        if from_fb:
            st.success(_t("ob_fb_ok", prenom=prefill.get('prenom', '')))
        else:
            st.success(_t("ob_google_ok", prenom=prefill.get('prenom', '')))
        st.markdown(_t("ob_form_google"))
    else:
        st.markdown(
            f'<div style="text-align:center;color:#9ca3af;font-size:0.82rem;'
            f'margin:8px 0;">{_t("ob_or")}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(_t("ob_form_title"))

    # Canonical FR gender list for storage (always stored in French for data consistency)
    _GENDER_OPTS_FR = ["Femme", "Homme", "Non-binaire", "Préfère ne pas préciser"]

    if not from_social:
        prenom = st.text_input(_t("ob_first_name"), placeholder=_t("ob_first_name_ph"))
    else:
        prenom = prefill.get("prenom", "")

    ville = st.text_input(
        _t("ob_city"),
        placeholder=_t("ob_city_ph"),
        help=_t("ob_city_help"),
    )

    country_label = st.selectbox(
        _t("ob_country"),
        options=list(COUNTRY_CONFIG.keys()),
        index=0,
        key="onboarding_country",
    )

    gender_opts_display = _tl("ob_gender_opts")
    sexe_display = st.radio(
        _t("ob_gender"),
        gender_opts_display,
        horizontal=True,
        index=0,
    )
    # Map display value back to canonical French for storage
    _sexe_idx = gender_opts_display.index(sexe_display) if sexe_display in gender_opts_display else 0
    sexe = _GENDER_OPTS_FR[_sexe_idx]

    submitted = st.button(_t("ob_submit"), use_container_width=True, type="primary")

    if submitted:
        errors = []
        if not str(prenom).strip():
            errors.append(_t("ob_err_name"))
        if not ville.strip():
            errors.append(_t("ob_err_city"))
        if errors:
            for e in errors:
                st.error(e)
        else:
            # Détermine l'ID : Google sub, Facebook ID, ou nouvel UUID
            user_id = (prefill.get("google_sub")
                       or prefill.get("fb_id")
                       or str(uuid.uuid4()))

            _country_cfg = COUNTRY_CONFIG.get(country_label, COUNTRY_CONFIG["🇫🇷 France"])
            profile = {
                "user_id":        user_id,
                "prenom":         str(prenom).strip(),
                "sexe":           sexe,
                "ville":          ville.strip(),
                "nom":            prefill.get("nom", ""),
                "google_email":   prefill.get("google_email", ""),
                "google_picture": prefill.get("google_picture", ""),
                "google_sub":     prefill.get("google_sub", ""),
                "fb_id":          prefill.get("fb_id", ""),
                "fb_email":       prefill.get("fb_email", ""),
                "fb_picture":     prefill.get("fb_picture", ""),
                # Localisation
                "country":             _country_cfg["code"],
                "country_label":       country_label,
                "locale":              _country_cfg["locale"],
                "currency":            _country_cfg["currency"],
                "unit_temp":           _country_cfg["unit_temp"],
                "unit_speed":          _country_cfg["unit_speed"],
                "transport_provider":  _country_cfg["transport_provider"],
                "crisis_line":         _country_cfg["crisis_line"],
                "emergency_number":    _country_cfg["emergency_number"],
                # Champs enrichis — complétés plus tard
                "age":                    None,
                "poids":                  None,
                "taille":                 None,
                "budget_mensuel":         0,
                "profession":             "",
                "orientation_sexuelle":   "",
                "situation_maritale":     "",
                "famille":                {"a_enfants": None, "nb_enfants": 0},
                "hobbies":                [],
                "habitudes_alimentaires": "",
                "transport":              "",
                "garde_robe":             {"description": "", "photos": []},
                "consents":               {"profil": True, "claude": True, "suggestions": True},
                "onboarding_complete":         True,
                "onboarding_lifestyle_complete": False,
            }
            save_profile(profile)
            st.session_state.pop("social_prefill", None)
            st.session_state.pop("google_prefill", None)  # compat ancien code
            return True

    return False


# ── Formulaire profil enrichi ──────────────────────────────────────────────────

def show_profile_form(profile: dict):
    st.markdown(_t("pf_title"))
    st.caption(_t("pf_subtitle"))

    # Canonical FR lists for storage (data compatibility with existing profiles)
    _GENDER_OPTS_FR  = ["Femme", "Homme", "Non-binaire", "Préfère ne pas préciser"]
    _ORIENT_OPTS_FR  = ["Hétérosexuel(le)", "Homosexuel(le)", "Bisexuel(le)", "Autre", "Préfère ne pas préciser"]
    _SIT_OPTS_FR     = ["Célibataire", "En couple", "Marié(e) / Pacsé(e)", "Divorcé(e)", "Veuf/Veuve", "C'est compliqué"]
    _ALIM_OPTS_FR    = ["Omnivore", "Végétarien(ne)", "Vegan", "Pescétarien(ne)", "Sans gluten", "Halal", "Casher", "Autre"]
    _TRANSP_OPTS_FR  = ["Voiture", "Transport en commun", "Vélo", "À pied", "Moto / Scooter", "Télétravail", "Mixte"]

    # Translated display lists
    sexe_opts_display   = _tl("pf_gender_opts")
    orient_opts_display = _tl("pf_orient_opts")
    sit_opts_display    = _tl("pf_sit_opts")
    alim_opts_display   = _tl("pf_alim_opts")
    transp_opts_display = _tl("pf_transp_opts")

    def _idx_fr(fr_list, display_list, stored_val, default=0):
        """Find index in FR list for a stored value, then return same index for display list."""
        idx = fr_list.index(stored_val) if stored_val in fr_list else default
        return idx

    def _idx_display(display_list, val, default=0):
        return display_list.index(val) if val in display_list else default

    # ── Photo de profil (hors formulaire pour mise à jour immédiate) ─────────────
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    uid = get_active_user_id() or ""
    photo_path = PHOTOS_DIR / f"{uid}.jpg" if uid else None
    col_ph1, col_ph2 = st.columns([1, 3])
    with col_ph1:
        photo_url = get_profile_photo_url(uid) if uid else None
        if photo_url:
            st.image(photo_url, width=90)
        else:
            st.markdown(
                '<div style="width:90px;height:90px;border-radius:50%;'
                'background:linear-gradient(135deg,#C084FC,#818CF8);'
                'display:flex;align-items:center;justify-content:center;'
                'font-size:36px;">👤</div>', unsafe_allow_html=True
            )
    with col_ph2:
        uploaded = st.file_uploader(_t("pf_photo"), type=["jpg","jpeg","png"],
                                    key="profile_photo_upload")
        if uploaded and uid:
            url = upload_profile_photo(uploaded.getbuffer(), uid)
            if url:
                invalidate_photo_cache(uid)
                st.success(_t("pf_photo_ok"))
                st.rerun()

    with st.form("profile_form"):
        st.markdown(_t("pf_identity"))
        c1, c2 = st.columns(2)
        with c1:
            prenom = st.text_input(_t("pf_prenom"), value=profile.get("prenom", ""))
            ville  = st.text_input(_t("pf_ville"),  value=profile.get("ville",  ""))
            age    = st.number_input(_t("pf_age"), min_value=11, max_value=120,
                                     value=max(11, int(profile.get("age") or 11)))
            _ddn_str = profile.get("date_naissance", "")
            date_naissance = st.text_input(
                _t("pf_ddn"),
                value=_ddn_str,
                placeholder=_t("pf_ddn_ph"),
                help=_t("pf_ddn_help"),
            )
            poids  = st.number_input(_t("pf_poids"), min_value=0, max_value=700,
                                     value=int(profile.get("poids") or 0),
                                     help=_t("pf_poids_help"))
            taille = st.number_input(_t("pf_taille"), min_value=0, max_value=300,
                                     value=int(profile.get("taille") or 0),
                                     help=_t("pf_taille_help"))
        with c2:
            _sexe_stored = profile.get("sexe", "")
            _sexe_idx = _idx_fr(_GENDER_OPTS_FR, sexe_opts_display, _sexe_stored)
            sexe_display = st.selectbox(_t("pf_sexe"), sexe_opts_display, index=_sexe_idx)
            sexe_sel_idx = _idx_display(sexe_opts_display, sexe_display)
            sexe = _GENDER_OPTS_FR[sexe_sel_idx] if sexe_sel_idx < len(_GENDER_OPTS_FR) else _sexe_stored

            profession = st.text_input(_t("pf_profession"), value=profile.get("profession", ""),
                                       placeholder=_t("pf_profession_ph"))
            budget_mensuel = st.number_input(
                _t("pf_budget"),
                min_value=0, max_value=50000,
                value=int(profile.get("budget_mensuel") or 0),
                step=50,
                help=_t("pf_budget_help"),
            )

        st.markdown(_t("pf_personal"))
        _orient_stored = profile.get("orientation_sexuelle", "")
        _orient_idx = _idx_fr(_ORIENT_OPTS_FR, orient_opts_display, _orient_stored)
        orient_display = st.selectbox(_t("pf_orientation"), orient_opts_display, index=_orient_idx)
        orient_sel_idx = _idx_display(orient_opts_display, orient_display)
        orientation = _ORIENT_OPTS_FR[orient_sel_idx] if orient_sel_idx < len(_ORIENT_OPTS_FR) else _orient_stored

        _sit_stored = profile.get("situation_maritale", "")
        _sit_idx = _idx_fr(_SIT_OPTS_FR, sit_opts_display, _sit_stored)
        sit_display = st.selectbox(_t("pf_situation"), sit_opts_display, index=_sit_idx)
        sit_sel_idx = _idx_display(sit_opts_display, sit_display)
        situation = _SIT_OPTS_FR[sit_sel_idx] if sit_sel_idx < len(_SIT_OPTS_FR) else _sit_stored

        fam = profile.get("famille", {})
        st.markdown(_t("pf_children"))
        a_enfants_val = "Oui" if fam.get("a_enfants") else "Non"
        col_enf1, col_enf2 = st.columns(2)
        with col_enf1:
            enf_non = st.checkbox(_t("pf_children_no"), value=(a_enfants_val == "Non"), key="enf_non")
        with col_enf2:
            enf_oui = st.checkbox(_t("pf_children_yes"), value=(a_enfants_val == "Oui"), key="enf_oui")
        a_enfants = "Oui" if enf_oui else "Non"
        nb_enfants = st.number_input(
            _t("pf_nb_children"),
            min_value=0, max_value=20,
            value=int(fam.get("nb_enfants") or 0),
        )
        hobbies = st.text_area(_t("pf_hobbies"),
                               value=", ".join(profile.get("hobbies", [])),
                               placeholder=_t("pf_hobbies_ph"))

        st.markdown(_t("pf_lifestyle"))
        c3, c4 = st.columns(2)
        with c3:
            _alim_stored = profile.get("habitudes_alimentaires", "")
            _alim_idx = _idx_fr(_ALIM_OPTS_FR, alim_opts_display, _alim_stored)
            alim_display = st.selectbox(_t("pf_diet"), alim_opts_display, index=_alim_idx)
            alim_sel_idx = _idx_display(alim_opts_display, alim_display)
            alim = _ALIM_OPTS_FR[alim_sel_idx] if alim_sel_idx < len(_ALIM_OPTS_FR) else _alim_stored
        with c4:
            st.markdown(_t("pf_transport"))
            saved_transport = profile.get("transport", "")
            # saved_transport stores FR canonical values; match against FR list
            saved_list = [s.strip() for s in saved_transport.split(",")] if saved_transport else []
            transport_checks = {
                fr_val: st.checkbox(disp_val, value=(fr_val in saved_list), key=f"tr_{fr_val}")
                for fr_val, disp_val in zip(_TRANSP_OPTS_FR, transp_opts_display)
            }
            transport = ", ".join([fr_val for fr_val, checked in transport_checks.items() if checked])

        # ── Détail transport pour les alertes ──
        st.markdown(_t("pf_transport_lines_section"))
        transport_info = profile.get("transport_detail", {})
        all_lines = [
            "RER A", "RER B", "RER C", "RER D", "RER E",
            "Métro 1", "Métro 2", "Métro 3", "Métro 4", "Métro 5",
            "Métro 6", "Métro 7", "Métro 8", "Métro 9", "Métro 10",
            "Métro 11", "Métro 12", "Métro 13", "Métro 14",
            "Transilien H", "Transilien J", "Transilien K", "Transilien L",
            "Transilien N", "Transilien P", "Transilien R", "Transilien U",
            "TGV", "Intercités", "TER", "Autre ligne",
        ]
        tc_lines = st.multiselect(
            _t("pf_lines_label"),
            all_lines,
            default=transport_info.get("lines", []),
            placeholder=_t("pf_lines_ph"),
        )
        c5, c6 = st.columns(2)
        with c5:
            depart_heure = st.text_input(
                _t("pf_depart_label"),
                value=transport_info.get("depart_heure", ""),
                placeholder="Ex : 08:00",
            )
        with c6:
            has_car = st.checkbox(
                _t("pf_has_car"),
                value=transport_info.get("has_car", False),
                key="has_car"
            )
        trajet_desc = st.text_input(
            _t("pf_trajet_label"),
            value=transport_info.get("trajet_desc", ""),
            placeholder=_t("pf_trajet_ph"),
        )

        # ── Réveil ──
        st.markdown(_t("pf_wakeup_section"))
        heure_reveil = st.text_input(
            _t("pf_wakeup_label"),
            value=profile.get("heure_reveil", ""),
            placeholder=_t("pf_wakeup_ph"),
            help=_t("pf_wakeup_help"),
        )

        st.markdown(_t("pf_wardrobe_section"))
        gdr = profile.get("garde_robe", {})
        if not isinstance(gdr, dict):
            gdr = {"description": "", "photos": []}
        garde_desc = st.text_area(_t("pf_wardrobe_style_label"), value=gdr.get("description", ""),
                                  placeholder=_t("pf_wardrobe_style_ph"))
        photos = st.file_uploader(_t("pf_wardrobe_photos"), type=["jpg", "jpeg", "png"],
                                  accept_multiple_files=True)

        saved = st.form_submit_button(_t("pf_save"), use_container_width=True)

    if saved:
        saved_photos = list(gdr.get("photos", []))
        if photos:
            WARDROBE_DIR.mkdir(parents=True, exist_ok=True)
            for p in photos:
                dest = WARDROBE_DIR / p.name
                with open(dest, "wb") as f:
                    f.write(p.getbuffer())
                if p.name not in saved_photos:
                    saved_photos.append(p.name)

        profile.update({
            "prenom":         prenom.strip(),
            "ville":          ville.strip(),
            "age":            int(age) if age else None,
            "date_naissance": date_naissance.strip(),
            "poids":          int(poids) if poids else None,
            "taille":         int(taille) if taille else None,
            "budget_mensuel": int(budget_mensuel) if budget_mensuel else 0,
            "sexe":           sexe,
            "profession":     profession.strip(),
            "orientation_sexuelle": orientation,
            "situation_maritale":   situation,
            "famille":   {"a_enfants": a_enfants == "Oui",
                          "nb_enfants": int(nb_enfants) if a_enfants == "Oui" else 0},
            "hobbies":   [h.strip() for h in hobbies.split(",") if h.strip()],
            "habitudes_alimentaires": alim,
            "transport": transport,
            "transport_detail": {
                "lines":        tc_lines,
                "depart_heure": depart_heure.strip(),
                "has_car":      has_car,
                "trajet_desc":  trajet_desc.strip(),
            },
            "garde_robe": {"description": garde_desc, "photos": saved_photos},
            "heure_reveil": heure_reveil.strip(),
            "onboarding_lifestyle_complete": True,
        })
        save_profile(profile)
        st.success(_t("pf_saved"))
        st.rerun()
