"""
email_agent.py — Agent email Eldaana.
Connexion IMAP (lecture) + SMTP (envoi).
Supports : Gmail, Outlook, Yahoo, OVH, tout provider IMAP standard.
"""

import imaplib
import smtplib
import email as email_lib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from anthropic import Anthropic
import streamlit as st

client = Anthropic()

# Configs IMAP/SMTP des providers courants
PROVIDER_CONFIGS = {
    "gmail": {
        "imap_host": "imap.gmail.com",          "imap_port": 993,
        "smtp_host": "smtp.gmail.com",           "smtp_port": 587,
        "label": "Gmail",                        "emoji": "📬",
        "note": "Activer 'Mot de passe d'application' dans la sécurité Google",
    },
    "outlook": {
        "imap_host": "outlook.office365.com",   "imap_port": 993,
        "smtp_host": "smtp-mail.outlook.com",   "smtp_port": 587,
        "label": "Outlook / Microsoft",         "emoji": "📧",
    },
    "yahoo": {
        "imap_host": "imap.mail.yahoo.com",     "imap_port": 993,
        "smtp_host": "smtp.mail.yahoo.com",     "smtp_port": 587,
        "label": "Yahoo Mail",                  "emoji": "📮",
    },
    "ovh": {
        "imap_host": "ssl0.ovh.net",            "imap_port": 993,
        "smtp_host": "ssl0.ovh.net",            "smtp_port": 465,
        "label": "OVH / Pro",                   "emoji": "🔵",
    },
    "custom": {
        "label": "Autre provider",              "emoji": "⚙️",
    },
}


def fetch_recent_emails(
    profile: dict,
    max_count: int = 10,
    folder: str = "INBOX",
    unread_only: bool = False,
) -> list[dict]:
    """Récupère les emails récents via IMAP."""
    config = profile.get("email_config", {})
    if not config:
        return []

    try:
        mail = imaplib.IMAP4_SSL(config["imap_host"], config.get("imap_port", 993))
        mail.login(config["address"], config["password"])
        mail.select(folder)

        criteria = "UNSEEN" if unread_only else "ALL"
        _, msg_ids = mail.search(None, criteria)
        ids = msg_ids[0].split()[-max_count:]

        emails = []
        for mid in reversed(ids):
            _, data = mail.fetch(mid, "(RFC822)")
            msg = email_lib.message_from_bytes(data[0][1])

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode("utf-8", errors="ignore")
                        break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="ignore")

            emails.append({
                "id":      mid.decode(),
                "from":    msg.get("From", ""),
                "subject": msg.get("Subject", "(Sans objet)"),
                "date":    msg.get("Date", ""),
                "body":    body[:1000],
                "snippet": body[:200],
            })

        mail.logout()
        return emails

    except Exception:
        return []


def summarize_inbox(emails: list[dict]) -> str:
    """Produit un résumé IA de la boîte email."""
    if not emails:
        return "Aucun email à résumer."

    emails_text = "\n\n".join([
        f"De : {e['from']}\nObjet : {e['subject']}\nDate : {e['date']}\n{e['snippet']}"
        for e in emails
    ])

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        system=[{
            "type": "text",
            "text": (
                "Tu es Eldaana, assistante email personnelle.\n"
                "Résume les emails de manière claire et actionnable.\n"
                "Identifie : emails urgents, actions requises, emails informatifs.\n"
                "Sois concise et bienveillante. Réponds en français."
            ),
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content":
            f"Résume ces {len(emails)} emails :\n\n{emails_text}"}]
    )
    return response.content[0].text


def draft_reply(original_email: dict, instruction: str, profile: dict) -> str:
    """Rédige un brouillon de réponse à un email."""
    prenom = profile.get("prenom", "")
    tone   = profile.get("email_tone", "professionnel mais chaleureux")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=(
            f"Tu rédiges des emails pour {prenom}.\n"
            f"Ton : {tone}. Langue : adapter selon l'email original.\n"
            f"Rédige uniquement le corps de l'email, pas l'objet.\n"
            f"Signe avec le prénom {prenom}."
        ),
        messages=[{"role": "user", "content":
            f"Email reçu :\nDe : {original_email.get('from', '')}\n"
            f"Objet : {original_email.get('subject', '')}\n"
            f"{original_email.get('body', '')}\n\n"
            f"Instruction pour la réponse : {instruction}"}]
    )
    return response.content[0].text


def send_email(profile: dict, to: str, subject: str, body: str) -> bool:
    """Envoie un email via SMTP."""
    config = profile.get("email_config", {})
    if not config:
        return False

    try:
        msg = MIMEMultipart()
        msg["From"]    = config["address"]
        msg["To"]      = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(config["smtp_host"], config.get("smtp_port", 587)) as server:
            server.starttls()
            server.login(config["address"], config["password"])
            server.sendmail(config["address"], to, msg.as_string())
        return True
    except Exception:
        return False


def handle_email_intent(intent: dict, message: str, profile: dict) -> dict:
    """Gère une intention email détectée par le router."""
    action = intent.get("action", "")
    uid    = profile.get("user_id", "")

    try:
        from agents.permissions import load_permissions, log_agent_action, PermissionLevel
        perms      = load_permissions(uid)
        email_perm = perms.get("email")
    except Exception:
        email_perm = None

    if "summarize" in action or "read" in action or not action:
        emails  = fetch_recent_emails(profile, max_count=10, unread_only=True)
        summary = summarize_inbox(emails)
        try:
            log_agent_action(uid, "email", "summarize_inbox", f"{len(emails)} emails", "done")
        except Exception:
            pass
        return {
            "type":              "email_summary",
            "content":           summary,
            "emails":            emails,
            "actions_available": ["reply", "archive", "mark_read"],
        }

    elif "draft" in action:
        if email_perm and email_perm.level == PermissionLevel.READ_ONLY:
            return {
                "type":    "permission_upgrade",
                "message": "La rédaction d'emails nécessite le niveau 'Brouillon' dans les permissions.",
            }
        params = intent.get("params", {})
        draft  = draft_reply(
            params.get("original_email", {}),
            params.get("instruction", message),
            profile,
        )
        return {
            "type":                 "email_draft",
            "content":              draft,
            "requires_confirmation": True,
            "confirm_label":        "Envoyer cet email",
            "edit_label":           "Modifier le brouillon",
        }

    return {"type": "error", "message": "Action email non reconnue."}
