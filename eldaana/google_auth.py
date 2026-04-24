"""
google_auth.py — Connexion Google OAuth pour Eldaana.

Configuration requise dans eldaana/.streamlit/secrets.toml :
    [google]
    client_id     = "VOTRE_CLIENT_ID.apps.googleusercontent.com"
    client_secret = "VOTRE_CLIENT_SECRET"
    redirect_uri  = "http://localhost:8503"
"""

import streamlit as st
import requests as _http

try:
    from streamlit_oauth import OAuth2Component
    _OAUTH_AVAILABLE = True
except ImportError:
    _OAUTH_AVAILABLE = False

GOOGLE_AUTH_URL   = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL  = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_USERINFO   = "https://www.googleapis.com/oauth2/v3/userinfo"


def _credentials_configured() -> bool:
    try:
        _ = st.secrets["google"]["client_id"]
        _ = st.secrets["google"]["client_secret"]
        return True
    except Exception:
        return False


def show_google_button() -> dict | None:
    """
    Affiche le bouton 'Continuer avec Google'.
    Retourne les infos Google de l'utilisateur si connecté, sinon None.
    """
    if not _OAUTH_AVAILABLE:
        st.caption("⚙️ `streamlit-oauth` non installé.")
        return None

    if not _credentials_configured():
        st.caption("⚙️ Credentials Google non configurés — voir `secrets.toml`.")
        return None

    try:
        redirect_uri  = st.secrets["google"].get("redirect_uri", "http://localhost:8503")
        client_id     = st.secrets["google"]["client_id"]
        client_secret = st.secrets["google"]["client_secret"]
    except Exception:
        return None

    oauth2 = OAuth2Component(
        client_id, client_secret,
        GOOGLE_AUTH_URL,
        GOOGLE_TOKEN_URL,
        GOOGLE_TOKEN_URL,
        GOOGLE_REVOKE_URL,
    )

    _GOOGLE_SVG = '''<svg width="18" height="18" viewBox="0 0 48 48" style="vertical-align:middle"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97 2.31-8.16 2.31-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>'''

    # Bouton OAuth caché + bouton custom par-dessus
    st.markdown(f"""
    <style>
    #google-oauth-hidden {{ overflow:hidden; height:0; }}
    </style>
    <div style="width:100%;background:#fff;border:1.5px solid #e5e7eb;
                border-radius:10px;padding:9px 6px;cursor:pointer;
                display:flex;align-items:center;justify-content:center;gap:7px;
                font-size:0.8rem;color:#374151;font-weight:600;font-family:sans-serif;"
         onclick="document.querySelector('#google-oauth-hidden button')?.click()">
        {_GOOGLE_SVG} Google
    </div>
    <div id="google-oauth-hidden">
    """, unsafe_allow_html=True)

    result = oauth2.authorize_button(
        "Google",
        redirect_uri=redirect_uri,
        scope="openid email profile",
        use_container_width=True,
        pkce="S256",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    if result and "token" in result:
        return _fetch_user_info(result["token"].get("access_token", ""))

    return None


def _fetch_user_info(access_token: str) -> dict | None:
    """Récupère le profil Google de l'utilisateur."""
    try:
        resp = _http.get(
            GOOGLE_USERINFO,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5,
        )
        return resp.json()
    except Exception:
        return None


def google_to_profile(google_info: dict) -> dict:
    """
    Convertit les données Google en champs Eldaana.
    Retourne un dict partiel — ville et sexe restent à compléter.
    """
    full_name   = google_info.get("name", "")
    given_name  = google_info.get("given_name", full_name.split()[0] if full_name else "")

    return {
        "prenom":         given_name.strip(),
        "nom":            google_info.get("family_name", ""),
        "google_email":   google_info.get("email", ""),
        "google_picture": google_info.get("picture", ""),
        "google_sub":     google_info.get("sub", ""),
    }
