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

    result = oauth2.authorize_button(
        "🔵  Continuer avec Google",
        redirect_uri=redirect_uri,
        scope="openid email profile",
        use_container_width=True,
        pkce="S256",
    )

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
