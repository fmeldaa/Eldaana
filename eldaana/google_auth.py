"""
google_auth.py — Connexion Google OAuth pour Eldaana.
OAuth2 manuel (authorization code flow) — bouton stylé comme les autres réseaux sociaux.
"""

import secrets as _secrets
import urllib.parse
import streamlit as st
import streamlit.components.v1 as _components
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
        # Décoder la plateforme encodée dans le state : "<token>|<platform>"
        state_parts = state.split("|", 1)
        platform    = state_parts[1] if len(state_parts) > 1 else "web"

        token = _exchange_code(code, client_id, client_secret, redirect_uri)
        if token:
            user_info = _fetch_user_info(token.get("access_token", ""))
            st.query_params.clear()
            st.session_state.pop("_google_state", None)
            if platform == "android":
                st.session_state["_android_oauth"] = True
            return user_info

    # ── Détecter la plateforme (Android envoie ?platform=android) ─────────────
    _platform = st.query_params.get("platform", "web")

    # ── Générer state CSRF + encoder la plateforme ────────────────────────────
    if "_google_state" not in st.session_state:
        st.session_state["_google_state"] = _secrets.token_urlsafe(16)

    # State = "<token>|<platform>" pour retrouver la plateforme au retour
    _state_with_platform = f"{st.session_state['_google_state']}|{_platform}"

    auth_url = GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id":     client_id,
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        "scope":         "openid email profile",
        "state":         _state_with_platform,
        "access_type":   "online",
        "prompt":        "select_account",
    })

    # ── Bouton Google via st.markdown (unsafe_allow_html) ────────────────────
    # Contrairement à components.html, st.markdown n'a pas de sandbox iframe :
    # un <a href> est traité directement par le navigateur (pas React Router).
    # onclick : si Android bridge → EldaanaNav.openVoice (WebView → Chrome via
    # shouldOverrideUrlLoading) ; sinon le navigateur suit le href normalement.
    # ── components.html : iframe réel, onclick non supprimé par DOMPurify ────────
    # st.markdown supprime les onclick via DOMPurify → rien ne marche.
    # components.html crée un vrai <iframe sandbox="allow-scripts allow-same-origin">
    # → onclick s'exécute normalement.
    #
    # Stratégie :
    #   1. Android  : window.EldaanaAndroid.openUrl(url) — bridge Kotlin confirmé
    #                 (addJavascriptInterface s'applique à TOUS les frames du WebView)
    #   2. PC       : window.parent.location.href = url  — iframe same-origin,
    #                 navigue l'onglet principal vers Google
    #   3. Fallback : window.open(url, '_blank')          — nouvel onglet
    _safe_url = auth_url.replace("'", "\\'").replace('"', "&quot;")
    _html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ background:transparent; }}
button {{
  display:flex; align-items:center; justify-content:center; gap:7px;
  width:100%; background:#fff; border:1.5px solid #e5e7eb;
  border-radius:10px; padding:9px 6px; cursor:pointer;
  font-size:0.85rem; color:#374151; font-weight:600;
  font-family:sans-serif;
}}
button:hover {{ background:#f9fafb; }}
</style>
</head>
<body>
<button onclick="
  var u='{_safe_url}';
  if(window.EldaanaAndroid && window.EldaanaAndroid.openUrl){{
    window.EldaanaAndroid.openUrl(u);
  }} else {{
    try{{ window.parent.location.href=u; }}
    catch(e){{ window.open(u,'_blank'); }}
  }}
">
  {_GOOGLE_SVG} Google
</button>
</body></html>"""
    _components.html(_html, height=52)
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
        if resp.status_code == 200:
            return resp.json()
        # ── Afficher l'erreur Google pour aider au diagnostic ──────────────────
        try:
            err = resp.json()
            desc = err.get("error_description", "")
            code_err = err.get("error", f"HTTP {resp.status_code}")
            st.error(f"❌ Google OAuth — {code_err}: {desc}")
            if code_err == "redirect_uri_mismatch":
                st.caption(f"🔧 redirect_uri utilisé : `{redirect_uri}` — vérifier qu'il est identique dans Google Cloud Console.")
        except Exception:
            st.error(f"❌ Google OAuth — HTTP {resp.status_code}: {resp.text[:200]}")
        return None
    except Exception as e:
        st.error(f"❌ Google OAuth — Exception: {e}")
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
