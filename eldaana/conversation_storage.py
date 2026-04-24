"""
conversation_storage.py — Historique de conversation partagé (texte + voix).

Stockage dans Supabase, table `conversations`.
Utilisé par Streamlit ET par le serveur vocal Fly.io (via HTTP REST).
"""

import streamlit as st
from datetime import datetime, timezone

MAX_MESSAGES = 40  # messages conservés (20 échanges)


def _get_supabase():
    from supabase import create_client
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["key"],
    )


def save_conversation(uid: str, messages: list):
    """
    Sauvegarde les N derniers messages dans Supabase.
    messages = liste de {role, content, source?}
    """
    if not uid or not messages:
        return
    try:
        trimmed = messages[-MAX_MESSAGES:]
        _get_supabase().table("conversations").upsert({
            "uid":        uid,
            "messages":   trimmed,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception:
        pass


def load_conversation(uid: str) -> list:
    """
    Charge l'historique depuis Supabase.
    Retourne une liste de messages ou [] si rien.
    """
    if not uid:
        return []
    try:
        res = _get_supabase().table("conversations") \
            .select("messages") \
            .eq("uid", uid) \
            .execute()
        if res.data:
            return res.data[0].get("messages", [])
    except Exception:
        pass
    return []


def append_messages(uid: str, new_messages: list):
    """
    Ajoute des messages à l'historique existant.
    Utile pour le serveur vocal qui ne recharge pas toute la liste.
    """
    if not uid or not new_messages:
        return
    existing = load_conversation(uid)
    merged = existing + new_messages
    save_conversation(uid, merged)
