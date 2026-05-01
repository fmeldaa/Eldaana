"""
notifications_agent.py — Agent appels manqués, SMS, messages vocaux.

Sources :
1. Android natif (via l'app Android — permissions READ_CALL_LOG, READ_SMS)
2. WhatsApp Business API (notifications + résumés)

Architecture MVP :
- L'app Android envoie les données via l'API de sync (POST /api/sync-notifications)
- Eldaana les reçoit, les analyse et les présente à l'utilisateur
- Les données sont stockées dans st.session_state + Supabase table user_notifications
"""

import json
from anthropic import Anthropic
from datetime import datetime
import streamlit as st

client = Anthropic()


# ── APPELS MANQUÉS ────────────────────────────────────────────────────────────

def analyze_missed_calls(calls: list[dict], profile: dict) -> str:
    """Analyse les appels manqués et produit un résumé actionnable."""
    if not calls:
        return "Aucun appel manqué récent."

    calls_text = "\n".join([
        f"- {c.get('name', c.get('number', '?'))} à {c.get('time', '?')} "
        f"({c.get('duration_missed', 1)} tentative(s))"
        for c in calls
    ])

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=(
            f"Tu es Eldaana. Analyse les appels manqués de {profile.get('prenom', '')} "
            f"et donne des conseils actionnables. Sois concise et bienveillante. "
            f"Réponds en français."
        ),
        messages=[{"role": "user", "content":
            f"Appels manqués :\n{calls_text}\n\n"
            f"Résume et dis-moi qui rappeler en priorité."}]
    )
    return response.content[0].text


# ── SMS ───────────────────────────────────────────────────────────────────────

def analyze_sms(messages: list[dict], profile: dict) -> str:
    """Résume les SMS non lus de manière intelligente."""
    if not messages:
        return "Aucun SMS non lu."

    sms_text = "\n\n".join([
        f"De {m.get('sender', '?')} ({m.get('time', '?')}) :\n{m.get('body', '')[:200]}"
        for m in messages[:10]
    ])

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        system=(
            f"Tu es Eldaana, assistante de {profile.get('prenom', '')}.\n"
            "Résume les SMS non lus. Identifie les urgents, les publicitaires, les importants.\n"
            "Propose des actions concrètes. Sois concise. Réponds en français."
        ),
        messages=[{"role": "user", "content": f"SMS non lus :\n{sms_text}"}]
    )
    return response.content[0].text


# ── MESSAGES VOCAUX ───────────────────────────────────────────────────────────

def transcribe_and_summarize_voicemail(audio_url: str, profile: dict) -> dict:
    """
    Transcrit un message vocal et produit un résumé.
    Phase 1 (MVP) : audio_url → Whisper → résumé Claude.
    """
    try:
        import requests as _http
        from openai import OpenAI

        openai_client = OpenAI()
        audio_data    = _http.get(audio_url, timeout=10).content

        transcription = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=("voicemail.mp3", audio_data, "audio/mpeg"),
            language="fr",
        )
        transcript = transcription.text

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content":
                f"Résume ce message vocal en 2-3 phrases et identifie l'action requise :\n{transcript}"}]
        )

        action_required = any(
            kw in transcript.lower()
            for kw in ["rappelle", "urgent", "dès que possible", "callback", "asap", "rappeler"]
        )

        return {
            "transcript":       transcript,
            "summary":          response.content[0].text,
            "action_required":  action_required,
        }

    except Exception as e:
        return {
            "error":      str(e),
            "transcript": "",
            "summary":    "Impossible de transcrire ce message vocal.",
        }


# ── RÉPONSE SMS ───────────────────────────────────────────────────────────────

def draft_sms_reply(original_sms: dict, instruction: str, profile: dict) -> str:
    """Rédige une réponse SMS courte et naturelle."""
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        system=(
            f"Tu rédiges des SMS pour {profile.get('prenom', '')}. "
            "Sois naturel, concis, maximum 160 caractères."
        ),
        messages=[{"role": "user", "content":
            f"SMS reçu de {original_sms.get('sender', '?')} : '{original_sms.get('body', '')}'\n"
            f"Instruction : {instruction}"}]
    )
    return response.content[0].text


# ── HANDLER PRINCIPAL ─────────────────────────────────────────────────────────

def handle_notifications_intent(intent: dict, message: str, profile: dict) -> dict:
    """Gère une intention notifications."""
    uid       = profile.get("user_id", "")
    action    = intent.get("action", "")
    msg_lower = message.lower()

    try:
        from agents.permissions import log_agent_action
    except Exception:
        log_agent_action = None  # type: ignore

    def _log(act: str, detail: str, status: str):
        if log_agent_action:
            try:
                log_agent_action(uid, "notifications", act, detail, status)
            except Exception:
                pass

    # ── Appels manqués ──
    if any(kw in msg_lower for kw in ["appel", "rappelé", "manqué", "qui a appelé", "called"]):
        calls   = st.session_state.get("missed_calls", [])
        summary = analyze_missed_calls(calls, profile)
        _log("read_missed_calls", f"{len(calls)} appels", "done")
        return {
            "type":    "missed_calls",
            "content": summary,
            "calls":   calls,
            "actions": [{"label": "📞 Rappeler", "action": "call_back"}],
        }

    # ── SMS ──
    elif any(kw in msg_lower for kw in ["sms", "message texte", "texto", "messages"]):
        sms_list = st.session_state.get("unread_sms", [])
        summary  = analyze_sms(sms_list, profile)
        _log("read_sms", f"{len(sms_list)} SMS", "done")
        return {
            "type":     "sms_summary",
            "content":  summary,
            "messages": sms_list,
            "actions":  [{"label": "💬 Répondre", "action": "draft_reply"}],
        }

    # ── Messages vocaux ──
    elif any(kw in msg_lower for kw in ["vocal", "voicemail", "messagerie", "message vocal"]):
        voicemails = st.session_state.get("voicemails", [])
        if voicemails:
            first  = voicemails[0]
            result = transcribe_and_summarize_voicemail(first.get("audio_url", ""), profile)
            _log("read_voicemail", f"1 message de {first.get('sender', '?')}", "done")
            return {
                "type":           "voicemail",
                "content": (
                    f"📭 Message vocal de **{first.get('sender', '?')}** :\n\n"
                    f"*Transcription :* {result.get('transcript', '')}\n\n"
                    f"**Résumé :** {result.get('summary', '')}"
                ),
                "action_required": result.get("action_required", False),
            }
        return {"type": "no_voicemail", "content": "Aucun message vocal en attente."}

    return {"type": "error", "message": "Action notification non reconnue."}
