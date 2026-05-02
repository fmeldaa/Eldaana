"""
perplexity_search.py — Recherche temps réel via Perplexity Sonar.

Utilisé comme fallback transport pour les pays sans API dédiée (BE, CH, GB, CA…).
Perplexity Sonar effectue une recherche web live et synthétise les résultats.

Clé API dans st.secrets["perplexity"]["api_key"]  (ou env PERPLEXITY_API_KEY).
"""

import json
import os
import requests
import streamlit as st
from datetime import datetime


_API_URL = "https://api.perplexity.ai/chat/completions"
_MODEL   = "sonar"   # sonar = rapide + web-search temps réel ; sonar-pro = plus détaillé


def _get_key() -> str | None:
    """Récupère la clé Perplexity depuis les secrets Streamlit ou l'env."""
    try:
        return st.secrets["perplexity"]["api_key"]
    except Exception:
        return os.getenv("PERPLEXITY_API_KEY", "")


# ── Fonction principale ───────────────────────────────────────────────────────

def search_realtime(query: str, locale: str = "fr") -> str:
    """
    Recherche web temps réel via Perplexity Sonar.
    Retourne le texte brut de la réponse, ou "" en cas d'erreur.
    """
    api_key = _get_key()
    if not api_key:
        return ""
    try:
        resp = requests.post(
            _API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            json={
                "model": _MODEL,
                "messages": [
                    {
                        "role":    "system",
                        "content": (
                            f"Tu es un assistant spécialisé dans les transports. "
                            f"Réponds toujours en {locale}. "
                            "Sois précis, factuel et concis."
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                "max_tokens":         600,
                "temperature":        0.1,   # factuel, peu créatif
                "search_recency_filter": "day",   # résultats du jour uniquement
            },
            timeout=12,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[Perplexity] Erreur: {e}")
    return ""


# ── Transport disruptions ─────────────────────────────────────────────────────

_DISRUPTION_PROMPT = """\
Cherche les perturbations de transports en commun à {ville} aujourd'hui ({date}).
Lignes qui m'intéressent : {lines}.

Réponds UNIQUEMENT avec un tableau JSON valide (pas de texte autour), dans ce format exact :
[
  {{
    "ligne": "Nom exact de la ligne",
    "severite": "majeur" ou "mineur",
    "bloquant": true ou false,
    "titre": "Titre court de la perturbation",
    "message": "Description en 1-2 phrases",
    "alternatives": ["Alternative 1", "Alternative 2"]
  }}
]

Si aucune perturbation actuellement : réponds []
Si information indisponible : réponds []
Ne jamais inventer de perturbations."""


def search_transport_disruptions(
    city: str,
    lines: list[str],
    locale: str = "fr",
) -> list[dict]:
    """
    Retourne la liste des perturbations TC pour {city} sur les {lines} données.
    Format de sortie identique aux disruptions Navitia :
      {"line", "severity", "blocking", "title", "message", "period", "alternatives_info"}
    """
    if not city or not lines:
        return []

    api_key = _get_key()
    if not api_key:
        print("[Perplexity] Clé API manquante — transport Perplexity désactivé")
        return []

    today = datetime.now().strftime("%d/%m/%Y")
    lines_str = ", ".join(lines[:8])   # limiter à 8 lignes max dans le prompt

    query = _DISRUPTION_PROMPT.format(
        ville=city,
        date=today,
        lines=lines_str,
    )

    raw = search_realtime(query, locale=locale)
    if not raw:
        return []

    # ── Parser le JSON retourné par Perplexity ────────────────────────────────
    try:
        # Extraire le premier [...] du texte (Perplexity peut ajouter du texte)
        start = raw.find("[")
        end   = raw.rfind("]") + 1
        if start == -1 or end == 0:
            return []
        parsed = json.loads(raw[start:end])
        if not isinstance(parsed, list):
            return []
    except json.JSONDecodeError:
        print(f"[Perplexity] JSON invalide: {raw[:200]}")
        return []

    # ── Normaliser vers le format interne Eldaana ─────────────────────────────
    disruptions = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        ligne    = item.get("ligne", "")
        if not ligne:
            continue

        severity = item.get("severite", "mineur").lower()
        blocking = bool(item.get("bloquant", severity == "majeur"))
        alts     = item.get("alternatives", [])

        disruptions.append({
            "line":     ligne,
            "severity": severity,
            "blocking": blocking,
            "title":    item.get("titre", f"Perturbation {ligne}"),
            "message":  item.get("message", ""),
            "period":   "Aujourd'hui",
            "source":   "perplexity",
            "alternatives_info": {
                "temps_extra_min": 20 if blocking else 10,
                "conseil": f"Perturbation sur {ligne} — consultez les infos trafic en temps réel.",
                "alternatives": [{"ligne": a, "note": ""} for a in alts],
            },
        })

    print(f"[Perplexity] {len(disruptions)} perturbation(s) trouvée(s) à {city}")
    return disruptions


# ── Recherche générique (utilisée ailleurs dans l'app) ────────────────────────

def search_web_question(question: str, locale: str = "fr") -> str:
    """
    Recherche web générique — répond à une question factuelle en temps réel.
    Retourne une réponse textuelle courte, ou "" si indisponible.
    """
    return search_realtime(question, locale=locale)
