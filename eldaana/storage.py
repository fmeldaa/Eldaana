"""
storage.py — Stockage des profils utilisateurs.

Deux modes automatiques :
  - LOCAL  : fichiers JSON dans user_data/profiles/  (votre machine)
  - CLOUD  : Supabase (app en ligne / Streamlit Cloud)

Détection automatique selon les credentials dans secrets.toml.
Toujours sauvegarde en local EN PLUS du cloud (double sécurité).
"""

import json
import streamlit as st
from pathlib import Path

DATA_DIR     = Path(__file__).parent / "user_data"
PROFILES_DIR = DATA_DIR / "profiles"


# ── Détection du mode ──────────────────────────────────────────────────────────

def _supabase_ok() -> bool:
    try:
        _ = st.secrets["supabase"]["url"]
        _ = st.secrets["supabase"]["key"]
        return True
    except Exception:
        return False


def _get_supabase():
    from supabase import create_client
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["key"],
    )


# ── Stockage local (JSON) ──────────────────────────────────────────────────────

def _local_load(user_id: str) -> dict | None:
    path = PROFILES_DIR / f"{user_id}.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def _local_save(profile: dict):
    user_id = profile.get("user_id")
    if not user_id:
        return
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROFILES_DIR / f"{user_id}.json", "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)


# ── Stockage cloud (Supabase) ──────────────────────────────────────────────────

def _cloud_load(user_id: str) -> dict | None:
    try:
        res = _get_supabase().table("profiles").select("data").eq("user_id", user_id).execute()
        if res.data:
            return res.data[0]["data"]
    except Exception:
        pass
    return None


def _cloud_save(profile: dict):
    try:
        user_id = profile.get("user_id")
        _get_supabase().table("profiles").upsert({
            "user_id": user_id,
            "data":    profile,
        }).execute()
    except Exception:
        pass


# ── Interface publique ─────────────────────────────────────────────────────────

def db_load(user_id: str) -> dict | None:
    """Charge un profil par son ID (cloud en priorité, local en fallback)."""
    if _supabase_ok():
        data = _cloud_load(user_id)
        if data:
            return data
    return _local_load(user_id)


def db_save(profile: dict):
    """Sauvegarde un profil. Toujours en local + cloud si configuré."""
    _local_save(profile)
    if _supabase_ok():
        _cloud_save(profile)
