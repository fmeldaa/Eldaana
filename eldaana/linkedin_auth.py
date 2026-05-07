"""
linkedin_auth.py — Connexion LinkedIn OAuth pour Eldaana.
OAuth2 authorization code flow + OpenID Connect — même style que google_auth.py / facebook_auth.py.

Encodage du provider dans le state : "<token>|<platform>|li"
→ google_auth.py ignore les callbacks dont state se termine par "|li"
→ facebook_auth.py ignore les callbacks sans "|fb" (déjà OK)
→ linkedin_auth.py ignore les callbacks sans "|li"
"""

import secrets as _secrets
import urllib.parse
import streamlit as st
import streamlit.components.v1 as _components
import requests as _http

LINKEDIN_AUTH_URL  = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO  = "https://api.linkedin.com/v2/userinfo"

_LINKEDIN_SVG = (
    '<svg width="18" height="18" viewBox="0 0 24 24" style="vertical-align:middle">'
    '<path fill="#0A66C2" d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037'
    '-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046'
    'c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433'
    'a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555'
    'V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24'
    'h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>'
)

_BTN_STYLE = (
    "display:flex;align-items:center;justify-content:center;gap:7px;"
    "width:100%;background:#fff;border:1.5px solid #e5e7eb;"
    "border-radius:10px;padding:9px 6px;cursor:pointer;"
    "font-size:0.85rem;color:#374151;font-weight:600;font-family:sans-serif;"
)


def _credentials_ok() -> bool:
    try:
        cid = st.secrets["linkedin"]["client_id"]
        return bool(cid) and cid not in ("COLLER_ICI_VOTRE_CLIENT_ID", "")
    except Exception:
        return False


def show_linkedin_button() -> dict | None:
    """
    Affiche un bouton LinkedIn stylé.
    Retourne le profil LinkedIn si connecté, sinon None.
    """
    if not _credentials_ok():
        st.markdown(
            f'<div style="{_BTN_STYLE};opacity:0.4;cursor:not-allowed;">'
            f'{_LINKEDIN_SVG} LinkedIn</div>',
            unsafe_allow_html=True,
        )
        return None

    client_id     = st.secrets["linkedin"]["client_id"]
    client_secret = st.secrets["linkedin"]["client_secret"]
    redirect_uri  = st.secrets["linkedin"].get("redirect_uri", "https://app.eldaana.io/")

    # ── Callback OAuth : ?code=... &state=...|li ──────────────────────────────
    code  = st.query_params.get("code",  "")
    state = st.query_params.get("state", "")

    if code and state:
        state_parts = state.split("|", 2)
        # Traiter uniquement si c'est un callback LinkedIn (state se termine par "|li")
        if len(state_parts) >= 3 and state_parts[2] == "li":
            platform = state_parts[1] if len(state_parts) >= 2 else "web"
            token = _exchange_code(code, client_id, client_secret, redirect_uri)
            if token:
                user_info = _fetch_user_info(token.get("access_token", ""))
                st.query_params.clear()
                st.session_state.pop("_li_state", None)
                if platform == "android":
                    st.session_state["_android_oauth"] = True
                return user_info

    # ── Générer bouton LinkedIn ───────────────────────────────────────────────
    _platform = st.query_params.get("platform", "web")

    if "_li_state" not in st.session_state:
        st.session_state["_li_state"] = _secrets.token_urlsafe(16)

    # State = "<token>|<platform>|li" pour identifier le callback LinkedIn
    _state = f"{st.session_state['_li_state']}|{_platform}|li"

    auth_url = LINKEDIN_AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id":     client_id,
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        "scope":         "openid profile email",
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
  {_LINKEDIN_SVG} LinkedIn
</button>
</body></html>"""
    _components.html(_html, height=52)
    return None


def _exchange_code(code: str, client_id: str, client_secret: str,
                   redirect_uri: str) -> dict | None:
    """Échange le code contre un access token."""
    try:
        resp = _http.post(LINKEDIN_TOKEN_URL, data={
            "grant_type":    "authorization_code",
            "code":          code,
            "client_id":     client_id,
            "client_secret": client_secret,
            "redirect_uri":  redirect_uri,
        }, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        try:
            err = resp.json()
            st.error(f"❌ LinkedIn OAuth — {err.get('error', 'Error')}: {err.get('error_description', resp.text[:200])}")
        except Exception:
            st.error(f"❌ LinkedIn OAuth — HTTP {resp.status_code}: {resp.text[:200]}")
        return None
    except Exception as e:
        st.error(f"❌ LinkedIn OAuth — Exception: {e}")
        return None


def _fetch_user_info(access_token: str) -> dict | None:
    """Récupère les infos utilisateur via OpenID Connect."""
    try:
        resp = _http.get(
            LINKEDIN_USERINFO,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


def linkedin_to_profile(li_info: dict) -> dict:
    """Convertit les infos LinkedIn en données de profil Eldaana."""
    full_name  = li_info.get("name", "")
    first_name = li_info.get("given_name",  full_name.split()[0] if full_name else "")
    last_name  = li_info.get("family_name", full_name.split()[-1] if " " in full_name else "")

    return {
        "prenom":       first_name.strip(),
        "nom":          last_name.strip(),
        "li_email":     li_info.get("email", ""),
        "google_email": li_info.get("email", ""),   # partagé pour Stripe
        "li_picture":   li_info.get("picture", ""),
        "li_sub":       li_info.get("sub", ""),
    }
