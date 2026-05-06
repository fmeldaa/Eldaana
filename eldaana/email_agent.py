"""
email_agent.py — Agent email Gmail pour Eldaana.

Fonctionnalités :
- Connexion OAuth2 Gmail (séparée du login)
- Lecture des emails récents (inbox)
- Détection automatique des emails urgents
- Résumé intelligent par Claude
- Brouillon de réponse assisté
- Injection dans le system prompt
"""

import streamlit as st
import requests as _http
import base64
import json
import re
import time
from datetime import datetime
from storage import db_load, db_save
from translations import t as _t, t_list as _tl

try:
    from streamlit_oauth import OAuth2Component
    _OAUTH_AVAILABLE = True
except ImportError:
    _OAUTH_AVAILABLE = False

# ── Constantes OAuth ──────────────────────────────────────────────────────────
GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GMAIL_BASE       = "https://gmail.googleapis.com/gmail/v1/users/me"

GMAIL_SCOPES = (
    "openid email profile "
    "https://www.googleapis.com/auth/gmail.readonly "
    "https://www.googleapis.com/auth/gmail.send "
    "https://www.googleapis.com/auth/gmail.modify"
)

# Mots-clés pour détecter les emails urgents
URGENT_KEYWORDS = [
    "urgent", "important", "action requise", "action required",
    "rappel", "reminder", "deadline", "échéance", "relance",
    "facture", "impayé", "paiement", "convocation", "litige",
    "annulation", "résiliation", "alerte", "attention", "immédiat",
    "réponse attendue", "convoqué", "huissier", "mise en demeure",
    "overdue", "expiration", "expire", "dernier délai",
]

NEWSLETTER_KEYWORDS = [
    "noreply", "no-reply", "newsletter", "unsubscribe", "désabonner",
    "marketing", "promo", "promotion", "offre", "soldes",
    "notification", "donotreply",
]


# ── Gestion des credentials ───────────────────────────────────────────────────

def _gmail_configured() -> bool:
    """Vérifie que les credentials Gmail sont configurés."""
    try:
        _ = st.secrets["google"]["client_id"]
        _ = st.secrets["google"]["client_secret"]
        return True
    except Exception:
        return False


def _get_redirect_uri() -> str:
    try:
        return st.secrets["google"].get("redirect_uri", "http://localhost:8503")
    except Exception:
        return "http://localhost:8503"


# ── Gestion des tokens ────────────────────────────────────────────────────────

def load_gmail_token(user_id: str) -> dict | None:
    """Charge le token Gmail depuis le profil."""
    profile = db_load(user_id)
    return profile.get("gmail_token") if profile else None


def save_gmail_token(user_id: str, token: dict):
    """Sauvegarde le token Gmail dans le profil."""
    profile = db_load(user_id)
    if profile:
        profile["gmail_token"] = token
        db_save(profile)


def clear_gmail_token(user_id: str):
    """Supprime la connexion Gmail."""
    profile = db_load(user_id)
    if profile:
        profile.pop("gmail_token", None)
        profile.pop("gmail_email", None)
        db_save(profile)


def _refresh_token(user_id: str) -> str | None:
    """Rafraîchit le token d'accès si nécessaire."""
    token = load_gmail_token(user_id)
    if not token:
        return None

    access_token  = token.get("access_token")
    refresh_token = token.get("refresh_token")
    expires_at    = token.get("expires_at", 0)

    # Valide encore (marge de 5 min)
    if access_token and time.time() < (expires_at - 300):
        return access_token

    # Essayer de rafraîchir
    if not refresh_token:
        return access_token  # On tente quand même

    try:
        resp = _http.post(GOOGLE_TOKEN_URL, data={
            "grant_type":    "refresh_token",
            "refresh_token": refresh_token,
            "client_id":     st.secrets["google"]["client_id"],
            "client_secret": st.secrets["google"]["client_secret"],
        }, timeout=10)
        data = resp.json()
        if "access_token" in data:
            token["access_token"] = data["access_token"]
            token["expires_at"]   = time.time() + data.get("expires_in", 3600)
            save_gmail_token(user_id, token)
            return token["access_token"]
    except Exception:
        pass
    return access_token


def _headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


# ── Appels Gmail API ──────────────────────────────────────────────────────────

def _list_messages(access_token: str, max_results: int = 20,
                   label: str = "INBOX", q: str = "") -> list[dict]:
    """Liste les messages Gmail."""
    params = {"maxResults": max_results, "labelIds": label}
    if q:
        params["q"] = q
    try:
        resp = _http.get(
            f"{GMAIL_BASE}/messages",
            headers=_headers(access_token),
            params=params,
            timeout=10,
        )
        return resp.json().get("messages", [])
    except Exception:
        return []


def _get_message(access_token: str, msg_id: str) -> dict:
    """Récupère un message complet."""
    try:
        resp = _http.get(
            f"{GMAIL_BASE}/messages/{msg_id}",
            headers=_headers(access_token),
            params={"format": "full"},
            timeout=10,
        )
        return resp.json()
    except Exception:
        return {}


def _get_unread_count(access_token: str) -> int:
    """Retourne le nombre d'emails non lus."""
    try:
        resp = _http.get(
            f"{GMAIL_BASE}/labels/INBOX",
            headers=_headers(access_token),
            timeout=5,
        )
        data = resp.json()
        return data.get("messagesUnread", 0)
    except Exception:
        return 0


def mark_as_read(access_token: str, msg_id: str):
    """Marque un email comme lu."""
    try:
        _http.post(
            f"{GMAIL_BASE}/messages/{msg_id}/modify",
            headers=_headers(access_token),
            json={"removeLabelIds": ["UNREAD"]},
            timeout=5,
        )
    except Exception:
        pass


def send_email(access_token: str, to: str, subject: str, body: str) -> bool:
    """Envoie un email."""
    try:
        message = f"To: {to}\r\nSubject: {subject}\r\n\r\n{body}"
        raw = base64.urlsafe_b64encode(message.encode("utf-8")).decode("utf-8")
        resp = _http.post(
            f"{GMAIL_BASE}/messages/send",
            headers=_headers(access_token),
            json={"raw": raw},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


# ── Parsing des emails ────────────────────────────────────────────────────────

def _extract_header(headers: list, name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _decode_body(data: str) -> str:
    """Décode le body base64url d'un email."""
    if not data:
        return ""
    try:
        decoded = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        # Nettoyer HTML basique
        decoded = re.sub(r"<[^>]+>", " ", decoded)
        decoded = re.sub(r"\s+", " ", decoded).strip()
        return decoded[:1500]  # Limiter la taille
    except Exception:
        return ""


def _extract_text_body(payload: dict) -> str:
    """Extrait le texte du corps d'un email (gère multipart)."""
    mime_type = payload.get("mimeType", "")

    # Corps direct
    if "text" in mime_type:
        data = payload.get("body", {}).get("data", "")
        return _decode_body(data)

    # Multipart : chercher text/plain d'abord, puis text/html
    parts = payload.get("parts", [])
    text_plain = ""
    text_html  = ""

    for part in parts:
        pt = part.get("mimeType", "")
        data = part.get("body", {}).get("data", "")
        if pt == "text/plain":
            text_plain = _decode_body(data)
        elif pt == "text/html":
            text_html = _decode_body(data)
        elif "multipart" in pt:
            # Récursif
            nested = _extract_text_body(part)
            if nested:
                text_plain = nested

    return text_plain or text_html or ""


def parse_email(raw_msg: dict) -> dict:
    """Convertit un message Gmail brut en dict propre."""
    if not raw_msg or "payload" not in raw_msg:
        return {}

    payload = raw_msg["payload"]
    headers = payload.get("headers", [])

    subject = _extract_header(headers, "Subject") or "(Pas de sujet)"
    sender  = _extract_header(headers, "From")
    date    = _extract_header(headers, "Date")
    to      = _extract_header(headers, "To")

    # Extraire l'adresse email propre depuis "Nom <email@exemple.com>"
    email_match = re.search(r"<([^>]+)>", sender)
    sender_email = email_match.group(1) if email_match else sender
    sender_name  = sender.split("<")[0].strip().strip('"') if "<" in sender else sender

    # Corps
    body = _extract_text_body(payload)

    # Labels
    label_ids = raw_msg.get("labelIds", [])
    is_unread = "UNREAD" in label_ids

    # Détecter le type
    sender_lower   = (sender_email + " " + sender_name).lower()
    subject_lower  = subject.lower()
    body_lower     = body.lower()

    is_urgent = any(kw in subject_lower or kw in body_lower for kw in URGENT_KEYWORDS)
    is_newsletter = any(kw in sender_lower or kw in subject_lower for kw in NEWSLETTER_KEYWORDS)

    # Date formatée
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date)
        date_fr = dt.strftime("%d/%m %H:%M")
    except Exception:
        date_fr = date[:16] if date else "—"

    return {
        "id":           raw_msg.get("id", ""),
        "subject":      subject,
        "sender_name":  sender_name or sender_email,
        "sender_email": sender_email,
        "to":           to,
        "date":         date_fr,
        "body":         body,
        "is_unread":    is_unread,
        "is_urgent":    is_urgent,
        "is_newsletter": is_newsletter,
        "snippet":      raw_msg.get("snippet", "")[:120],
    }


def fetch_emails(user_id: str, max_results: int = 15) -> list[dict]:
    """Récupère et parse les N derniers emails."""
    access_token = _refresh_token(user_id)
    if not access_token:
        return []

    raw_list = _list_messages(access_token, max_results=max_results)
    emails   = []
    for m in raw_list:
        raw_msg = _get_message(access_token, m["id"])
        parsed  = parse_email(raw_msg)
        if parsed:
            emails.append(parsed)
    return emails


# ── Résumé Claude ─────────────────────────────────────────────────────────────

def summarize_emails_with_claude(emails: list[dict], prenom: str = "") -> str:
    """
    Utilise Claude pour analyser et résumer les emails importants.
    """
    if not emails:
        return "Aucun email à analyser."

    try:
        from anthropic import Anthropic
        client = Anthropic()

        # Préparer la liste pour Claude
        email_list = []
        for i, e in enumerate(emails[:10], 1):
            email_list.append(
                f"{i}. De : {e['sender_name']} <{e['sender_email']}>\n"
                f"   Sujet : {e['subject']}\n"
                f"   Date : {e['date']}\n"
                f"   Lu : {'Non' if e['is_unread'] else 'Oui'}\n"
                f"   Extrait : {e['snippet']}\n"
            )

        prompt = (
            f"Voici les derniers emails de {prenom or 'l\'utilisateur'} :\n\n"
            + "\n".join(email_list)
            + "\n\nFais un résumé concis en français :\n"
            "1. Les emails URGENTS ou qui nécessitent une action immédiate\n"
            "2. Les emails importants à traiter aujourd'hui\n"
            "3. Ce qui peut attendre\n"
            "Sois direct, bienveillant et pratique. Max 200 mots."
        )

        msg = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

    except Exception as e:
        return f"Impossible de générer le résumé : {e}"


def generate_reply_draft(email: dict, prenom: str = "") -> str:
    """Génère un brouillon de réponse pour un email."""
    try:
        from anthropic import Anthropic
        client = Anthropic()

        prompt = (
            f"Voici un email reçu par {prenom or 'moi'} :\n\n"
            f"De : {email['sender_name']} <{email['sender_email']}>\n"
            f"Sujet : {email['subject']}\n"
            f"Message : {email['body'][:800]}\n\n"
            "Rédige un brouillon de réponse en français, naturel et professionnel. "
            "Adapte le ton (formel/informel) à l'email reçu. "
            "Signe avec le prénom. Ne pas inventer des faits spécifiques. "
            "Max 150 mots."
        )

        msg = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    except Exception as e:
        return f"Impossible de générer le brouillon : {e}"


# ── System prompt ─────────────────────────────────────────────────────────────

def format_email_summary_for_prompt(user_id: str) -> str:
    """Résumé des emails pour injection dans le system prompt."""
    access_token = _refresh_token(user_id)
    if not access_token:
        return ""

    try:
        unread = _get_unread_count(access_token)
        if unread == 0:
            return ""

        # Chercher les urgents non lus
        urgent_list = _list_messages(
            access_token, max_results=5, label="INBOX", q="is:unread"
        )
        urgent_subjects = []
        for m in urgent_list[:5]:
            raw = _get_message(access_token, m["id"])
            parsed = parse_email(raw)
            if parsed.get("is_urgent"):
                urgent_subjects.append(f"• {parsed['subject']} (de {parsed['sender_name']})")

        lines = [f"- Emails non lus : {unread}"]
        if urgent_subjects:
            lines.append("- Emails urgents détectés :")
            lines.extend(urgent_subjects[:3])

        return (
            "\n\n[BOÎTE MAIL]\n"
            + "\n".join(lines)
            + "\nSi pertinent, mentionne les emails importants dans la conversation.\n"
            "[FIN BOÎTE MAIL]"
        )
    except Exception:
        return ""


# ── Interface Streamlit ───────────────────────────────────────────────────────

def show_gmail_connect(user_id: str) -> bool:
    """
    Affiche le bouton de connexion Gmail.
    Retourne True si Gmail est connecté.
    """
    if not _OAUTH_AVAILABLE:
        st.warning("⚙️ `streamlit-oauth` non disponible.")
        return False

    if not _gmail_configured():
        st.warning(
            "⚙️ Credentials Google non configurés.\n\n"
            "Ajoute dans `secrets.toml` :\n"
            "```\n[google]\nclient_id = '...'\nclient_secret = '...'\n"
            "redirect_uri = 'https://ton-app.streamlit.app'\n```"
        )
        return False

    token = load_gmail_token(user_id)
    if token:
        return True  # Déjà connecté

    try:
        oauth2 = OAuth2Component(
            st.secrets["google"]["client_id"],
            st.secrets["google"]["client_secret"],
            GOOGLE_AUTH_URL,
            GOOGLE_TOKEN_URL,
            GOOGLE_TOKEN_URL,
            GOOGLE_REVOKE_URL,
        )

        result = oauth2.authorize_button(
            "📧 Connecter ma boîte Gmail",
            redirect_uri=_get_redirect_uri(),
            scope=GMAIL_SCOPES,
            key="gmail_oauth_btn",
            use_container_width=True,
            extras_params={"access_type": "offline", "prompt": "consent"},
        )

        if result and "token" in result:
            t = result["token"]
            token_data = {
                "access_token":  t.get("access_token"),
                "refresh_token": t.get("refresh_token"),
                "expires_at":    time.time() + t.get("expires_in", 3600),
            }
            # Récupérer l'email Gmail
            try:
                info_resp = _http.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {token_data['access_token']}"},
                    timeout=5,
                )
                email_addr = info_resp.json().get("email", "")
                token_data["gmail_email"] = email_addr
            except Exception:
                pass
            save_gmail_token(user_id, token_data)
            # Sauvegarder l'email dans le profil aussi
            profile = db_load(user_id)
            if profile and token_data.get("gmail_email"):
                profile["gmail_email"] = token_data["gmail_email"]
                db_save(profile)
            st.success("✅ Gmail connecté !")
            st.rerun()
            return True

    except Exception as e:
        st.error(f"Erreur OAuth : {e}")

    return False


def show_email_page(profile: dict):
    """Page principale de l'agent email."""
    user_id = profile.get("user_id", "")
    prenom  = profile.get("prenom", "")

    st.markdown(_t("email_title"))
    st.caption(_t("email_subtitle"))

    # ── Connexion Gmail ──────────────────────────────────────────────────────
    token = load_gmail_token(user_id)

    if not token:
        st.info(_t("email_connect_info"))
        connected = show_gmail_connect(user_id)
        if not connected:
            return
        token = load_gmail_token(user_id)

    # Adresse connectée
    gmail_email = token.get("gmail_email") or profile.get("gmail_email", "")
    col_a, col_b = st.columns([4, 1])
    with col_a:
        st.success(_t("email_connected", email=gmail_email))
    with col_b:
        if st.button(_t("email_disconnect"), key="gmail_disconnect"):
            clear_gmail_token(user_id)
            st.rerun()
            return

    st.divider()

    # ── Chargement des emails ────────────────────────────────────────────────
    access_token = _refresh_token(user_id)
    if not access_token:
        st.error(_t("email_expired"))
        clear_gmail_token(user_id)
        st.rerun()
        return

    # Nombre de non-lus
    unread_count = _get_unread_count(access_token)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(_t("email_unread"), unread_count)

    # ── Résumé IA ────────────────────────────────────────────────────────────
    st.markdown(_t("email_ai_title"))
    if st.button(_t("email_summarize"), use_container_width=True, type="primary"):
        with st.spinner(_t("email_loading")):
            emails = fetch_emails(user_id, max_results=15)
        if emails:
            with st.spinner(_t("email_analysing")):
                summary = summarize_emails_with_claude(emails, prenom)
            st.session_state["email_summary"]  = summary
            st.session_state["email_list"]     = emails
        else:
            st.warning(_t("email_no_emails"))

    if "email_summary" in st.session_state:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#fdf4ff,#f0f4ff);
                    border:1.5px solid #c084fc;border-radius:16px;
                    padding:1.2rem;margin:0.5rem 0;">
            <p style="margin:0;color:#374151;line-height:1.6;">
                {st.session_state['email_summary'].replace(chr(10), '<br>')}
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── Liste des emails ─────────────────────────────────────────────────────
    if "email_list" not in st.session_state:
        if st.button(_t("email_see_recent"), use_container_width=True):
            with st.spinner(_t("email_loading2")):
                st.session_state["email_list"] = fetch_emails(user_id, max_results=15)
            st.rerun()
    else:
        emails = st.session_state["email_list"]
        if not emails:
            st.info(_t("email_none"))
            return

        # Filtres
        filter_opts = _tl("email_filters")
        filtre = st.radio(
            _t("email_filter_label"),
            filter_opts,
            horizontal=True,
            key="email_filter",
        )
        filtre_idx = filter_opts.index(filtre) if filtre in filter_opts else 0

        filtered = emails
        if filtre_idx == 1:
            filtered = [e for e in emails if e["is_urgent"]]
        elif filtre_idx == 2:
            filtered = [e for e in emails if e["is_unread"]]
        elif filtre_idx == 3:
            filtered = [e for e in emails if e["is_newsletter"]]

        if not filtered:
            st.info(_t("email_none_category"))
        else:
            st.markdown(f"**{len(filtered)} email{'s' if len(filtered) > 1 else ''}**")
            for email in filtered:
                _show_email_card(email, user_id, prenom, access_token)

        if st.button(_t("email_refresh"), use_container_width=True):
            del st.session_state["email_list"]
            if "email_summary" in st.session_state:
                del st.session_state["email_summary"]
            st.rerun()


def _show_email_card(email: dict, user_id: str, prenom: str, access_token: str):
    """Affiche une carte email avec actions."""
    # Couleurs selon le type
    if email["is_urgent"]:
        border_color = "#ef4444"
        badge = _t("email_badge_urgent")
    elif email["is_unread"]:
        border_color = "#c084fc"
        badge = _t("email_badge_unread")
    elif email["is_newsletter"]:
        border_color = "#e5e7eb"
        badge = _t("email_badge_news")
    else:
        border_color = "#e5e7eb"
        badge = ""

    bold = "font-weight:700;" if email["is_unread"] else ""

    with st.expander(
        f"{'🔴 ' if email['is_urgent'] else '📧 '}"
        f"**{email['subject'][:60]}** — {email['sender_name']} · {email['date']}",
        expanded=email["is_urgent"],
    ):
        st.markdown(f"""
        <div style="border-left:3px solid {border_color};padding:0.5rem 0.8rem;
                    margin-bottom:0.5rem;border-radius:0 8px 8px 0;">
            <p style="margin:0 0 0.2rem;font-size:0.85rem;color:#6b7280;">
                <b>{_t('email_from')}</b> {email['sender_name']} &lt;{email['sender_email']}&gt;
                {'&nbsp;&nbsp;<span style="background:#ef4444;color:white;padding:1px 6px;border-radius:8px;font-size:0.75rem;">' + badge + '</span>' if badge else ''}
            </p>
            <p style="margin:0 0 0.5rem;font-size:0.85rem;color:#6b7280;">
                <b>{_t('email_date')}</b> {email['date']}
            </p>
        </div>
        """, unsafe_allow_html=True)

        if email["body"]:
            st.text_area(
                _t("email_content"),
                value=email["body"][:800],
                height=150,
                key=f"body_{email['id']}",
                disabled=True,
                label_visibility="collapsed",
            )
        else:
            st.caption(email["snippet"])

        # Actions
        col1, col2, col3 = st.columns(3)

        with col1:
            if email["is_unread"]:
                if st.button(_t("email_mark_read"), key=f"read_{email['id']}", use_container_width=True):
                    mark_as_read(access_token, email["id"])
                    st.toast(_t("email_marked_read"))
                    if "email_list" in st.session_state:
                        for e in st.session_state["email_list"]:
                            if e["id"] == email["id"]:
                                e["is_unread"] = False
                    st.rerun()

        with col2:
            if st.button(_t("email_draft_btn"), key=f"reply_{email['id']}", use_container_width=True):
                with st.spinner(_t("email_drafting")):
                    draft = generate_reply_draft(email, prenom)
                st.session_state[f"draft_{email['id']}"] = draft

        with col3:
            pass  # Espace pour futures actions

        # Afficher le brouillon si généré
        if f"draft_{email['id']}" in st.session_state:
            draft_text = st.session_state[f"draft_{email['id']}"]
            st.markdown(_t("email_draft_title"))
            edited_draft = st.text_area(
                _t("email_draft_edit"),
                value=draft_text,
                height=150,
                key=f"edit_draft_{email['id']}",
            )
            col_send, col_cancel = st.columns(2)
            with col_send:
                if st.button(_t("email_send"), key=f"send_{email['id']}", type="primary", use_container_width=True):
                    subject_reply = (
                        f"Re: {email['subject']}"
                        if not email["subject"].startswith("Re:") else email["subject"]
                    )
                    success = send_email(access_token, email["sender_email"], subject_reply, edited_draft)
                    if success:
                        st.success(_t("email_sent"))
                        del st.session_state[f"draft_{email['id']}"]
                        st.rerun()
                    else:
                        st.error(_t("email_send_error"))
            with col_cancel:
                if st.button(_t("email_cancel"), key=f"cancel_{email['id']}", use_container_width=True):
                    del st.session_state[f"draft_{email['id']}"]
                    st.rerun()
