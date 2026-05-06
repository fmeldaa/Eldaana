"""
facebook_auth.py — Connexion Facebook OAuth pour Eldaana.
OAuth2 authorization code flow — même style que google_auth.py.

Encodage du provider dans le state : "<token>|<platform>|fb"
→ google_auth.py ignore les callbacks dont state se termine par "|fb"
→ facebook_auth.py ignore les callbacks sans ce suffixe
"""

import secrets as _secrets
import urllib.parse
import streamlit as st
import streamlit.components.v1 as _components
import requests as _http

FACEBOOK_AUTH_URL  = "https://www.facebook.com/v19.0/dialog/oauth"
FACEBOOK_TOKEN_URL = "https://graph.facebook.com/v19.0/oauth/access_token"
FACEBOOK_USERINFO  = "https://graph.facebook.com/me"

_FACEBOOK_SVG = (
    '<svg width="18" height="18" viewBox="0 0 24 24" style="vertical-align:middle">'
    '<path fill="#1877F2" d="M24 12.073C24 5.404 18.627 0 12 0S0 5.404 0 12.073'
    'C0 18.1 4.388 23.094 10.125 24v-8.437H7.078v-3.49h3.047V9.41'
    'c0-3.025 1.792-4.697 4.533-4.697 1.312 0 2.686.235 2.686.235v2.97'
    'h-1.513c-1.491 0-1.956.93-1.956 1.886v2.269h3.328l-.532 3.49'
    'h-2.796V24C19.612 23.094 24 18.1 24 12.073z"/></svg>'
)

_BTN_STYLE = (
    "display:flex;align-items:center;justify-content:center;gap:7px;"
    "width:100%;background:#fff;border:1.5px solid #e5e7eb;"
    "border-radius:10px;padding:9px 6px;cursor:pointer;"
    "font-size:0.85rem;color:#374151;font-weight:600;font-family:sans-serif;"
)


def _credentials_ok() -> bool:
    try:
        app_id = st.secrets["facebook"]["app_id"]
        return bool(app_id) and app_id not in ("COLLER_ICI_VOTRE_APP_ID", "")
    except Exception:
        return False


def show_facebook_button() -> dict | None:
    """
    Affiche un bouton Facebook stylé.
    Retourne le profil Facebook si connecté, sinon None.
    """
    if not _credentials_ok():
        st.markdown(
            f'<div style="{_BTN_STYLE};opacity:0.4;cursor:not-allowed;">'
            f'{_FACEBOOK_SVG} Facebook</div>',
            unsafe_allow_html=True,
        )
        return None

    app_id       = st.secrets["facebook"]["app_id"]
    app_secret   = st.secrets["facebook"]["app_secret"]
    redirect_uri = st.secrets["facebook"].get("redirect_uri", "https://app.eldaana.io/")

    # ── Callback OAuth : ?code=... &state=...|fb ──────────────────────────────
    code  = st.query_params.get("code",  "")
    state = st.query_params.get("state", "")

    if code and state:
        state_parts = state.split("|", 2)
        # Traiter uniquement si c'est un callback Facebook (state se termine par "|fb")
        if len(state_parts) >= 3 and state_parts[2] == "fb":
            platform = state_parts[1] if len(state_parts) >= 2 else "web"
            token = _exchange_code(code, app_id, app_secret, redirect_uri)
            if token:
                user_info = _fetch_user_info(token.get("access_token", ""))
                st.query_params.clear()
                st.session_state.pop("_fb_state", None)
                if platform == "android":
                    st.session_state["_android_oauth"] = True
                return user_info

    # ── Générer bouton Facebook ───────────────────────────────────────────────
    _platform = st.query_params.get("platform", "web")

    if "_fb_state" not in st.session_state:
        st.session_state["_fb_state"] = _secrets.token_urlsafe(16)

    # State = "<token>|<platform>|fb" pour identifier le callback Facebook
    _state = f"{st.session_state['_fb_state']}|{_platform}|fb"

    auth_url = FACEBOOK_AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id":     app_id,
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        "scope":         "email,public_profile",
        "state":         _state,
    })

    # ── components.html : iframe réel, onclick non supprimé par DOMPurify ────
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
  {_FACEBOOK_SVG} Facebook
</button>
</body></html>"""
    _components.html(_html, height=52)
    return None


def _exchange_code(code: str, app_id: str, app_secret: str,
                   redirect_uri: str) -> dict | None:
    """Échange le code contre un access token."""
    try:
        resp = _http.get(FACEBOOK_TOKEN_URL, params={
            "client_id":     app_id,
            "client_secret": app_secret,
            "redirect_uri":  redirect_uri,
            "code":          code,
        }, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        try:
            err = resp.json().get("error", {})
            st.error(f"❌ Facebook OAuth — {err.get('type', 'Error')}: {err.get('message', resp.text[:200])}")
        except Exception:
            st.error(f"❌ Facebook OAuth — HTTP {resp.status_code}: {resp.text[:200]}")
        return None
    except Exception as e:
        st.error(f"❌ Facebook OAuth — Exception: {e}")
        return None


def _fetch_user_info(access_token: str) -> dict | None:
    """Récupère les infos utilisateur via Graph API."""
    try:
        resp = _http.get(
            FACEBOOK_USERINFO,
            params={
                "fields":       "id,name,first_name,last_name,email,picture.type(large)",
                "access_token": access_token,
            },
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


def facebook_to_profile(fb_info: dict) -> dict:
    """Convertit les infos Facebook en données de profil Eldaana."""
    full_name  = fb_info.get("name", "")
    first_name = fb_info.get("first_name", full_name.split()[0] if full_name else "")
    last_name  = fb_info.get("last_name",  full_name.split()[-1] if " " in full_name else "")

    # La photo est imbriquée dans picture.data.url
    picture_url = ""
    pic_data = fb_info.get("picture", {})
    if isinstance(pic_data, dict):
        picture_url = pic_data.get("data", {}).get("url", "")

    return {
        "prenom":       first_name.strip(),
        "nom":          last_name.strip(),
        "fb_email":     fb_info.get("email", ""),
        "fb_picture":   picture_url,
        "fb_id":        fb_info.get("id", ""),
        # google_email reste vide pour distinguer les comptes Facebook
        "google_email": fb_info.get("email", ""),  # partagé pour Stripe
    }
