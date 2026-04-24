"""
google_auth.py — Connexion Google OAuth pour Eldaana.
OAuth2 manuel (authorization code flow) — bouton stylé comme les autres réseaux sociaux.
"""

import secrets as _secrets
import urllib.parse
import streamlit as st
import requests as _http


GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO  = "https://www.googleapis.com/oauth2/v3/userinfo"

_GOOGLE_SVG = '''<svg width="18" height="18" viewBox="0 0 48 48" style="vertical-align:middle">
<path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0
 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
<path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26
 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
<path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19
C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
<path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97
 2.31-8.16 2.31-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
</svg>'''

_BTN_STYLE = ("display:flex;align-items:center;justify-content:center;gap:7px;"
              "width:100%;background:#fff;border:1.5px solid #e5e7eb;"
              "border-radius:10px;padding:9px 6px;cursor:pointer;"
              "font-size:0.8rem;color:#374151;font-weight:600;"
              "font-family:sans-serif;text-decoration:none;")


def _credentials_ok() -> bool:
    try:
        cid = st.secrets["google"]["client_id"]
        return bool(cid) and cid != "COLLER_ICI_VOTRE_CLIENT_ID"
    except Exception:
        return False


def show_google_button() -> dict | None:
    """
    Affiche un bouton Google stylé (même look que FB/LinkedIn/Twitter).
    Retourne le profil Google si connecté, sinon None.
    """
    if not _credentials_ok():
        st.markdown(
            f'<div style="{_BTN_STYLE};opacity:0.4;cursor:not-allowed;">'
            f'{_GOOGLE_SVG} Google</div>',
            unsafe_allow_html=True,
        )
        return None

    client_id     = st.secrets["google"]["client_id"]
    client_secret = st.secrets["google"]["client_secret"]
    redirect_uri  = st.secrets["google"].get("redirect_uri", "http://localhost:8503")

    # ── Callback OAuth : code dans l'URL ──────────────────────────────────────
    code  = st.query_params.get("code",  "")
    state = st.query_params.get("state", "")

    if code and state:
        token = _exchange_code(code, client_id, client_secret, redirect_uri)
        if token:
            user_info = _fetch_user_info(token.get("access_token", ""))
            st.query_params.clear()
            st.session_state.pop("_google_state", None)
            return user_info

    # ── Générer state CSRF ────────────────────────────────────────────────────
    if "_google_state" not in st.session_state:
        st.session_state["_google_state"] = _secrets.token_urlsafe(16)

    auth_url = GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id":     client_id,
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        "scope":         "openid email profile",
        "state":         st.session_state["_google_state"],
        "access_type":   "online",
        "prompt":        "select_account",
    })

    # ── Bouton stylé (vrai <a href>) ──────────────────────────────────────────
    st.markdown(
        f'<a href="{auth_url}" style="{_BTN_STYLE}">'
        f'{_GOOGLE_SVG} Google</a>',
        unsafe_allow_html=True,
    )
    return None


def _exchange_code(code: str, client_id: str, client_secret: str,
                   redirect_uri: str) -> dict | None:
    try:
        resp = _http.post(GOOGLE_TOKEN_URL, data={
            "code":          code,
            "client_id":     client_id,
            "client_secret": client_secret,
            "redirect_uri":  redirect_uri,
            "grant_type":    "authorization_code",
        }, timeout=10)
        return resp.json() if resp.status_code == 200 else None
    except Exception:
        return None


def _fetch_user_info(access_token: str) -> dict | None:
    try:
        resp = _http.get(GOOGLE_USERINFO,
                         headers={"Authorization": f"Bearer {access_token}"},
                         timeout=5)
        return resp.json()
    except Exception:
        return None


def google_to_profile(google_info: dict) -> dict:
    full_name  = google_info.get("name", "")
    given_name = google_info.get("given_name",
                                 full_name.split()[0] if full_name else "")
    return {
        "prenom":         given_name.strip(),
        "nom":            google_info.get("family_name", ""),
        "google_email":   google_info.get("email", ""),
        "google_picture": google_info.get("picture", ""),
        "google_sub":     google_info.get("sub", ""),
    }
