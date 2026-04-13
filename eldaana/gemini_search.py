"""
gemini_search.py — Recherche web temps réel.

Stratégie :
1. Brave Search API (fiable, 2000 req/mois gratuit) → résultats web
2. Gemini résume les résultats en français
3. Cache 10 min pour éviter les appels redondants
"""

import streamlit as st
import requests
import time

WEB_TRIGGERS = [
    "actualité", "actu", "news", "nouvelles", "info du jour",
    "aujourd'hui", "cette semaine", "ce mois", "en ce moment",
    "événement", "concert", "exposition", "festival", "sortie",
    "spectacle", "cinéma", "film", "série",
    "cherche", "recherche", "trouve", "qu'est-ce que", "c'est quoi",
    "qui est", "où est", "quand est", "comment faire",
    "météo", "prévision", "température",
    "prix", "tarif", "horaire", "ouvert", "fermé",
    "restaurant", "recette", "produit",
    "tendance", "mode", "populaire", "viral",
]

CACHE_TTL = 600  # 10 minutes


def should_search_web(message: str) -> bool:
    msg_lower = message.lower()
    return any(trigger in msg_lower for trigger in WEB_TRIGGERS)


def _serper_search(query: str) -> str | None:
    """Recherche via Serper.dev (Google Search API)."""
    try:
        api_key = st.secrets.get("serper", {}).get("api_key", "")
        if not api_key:
            return None

        r = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "gl": "fr", "hl": "fr", "num": 5},
            timeout=8,
        )
        if r.status_code != 200:
            return None

        data = r.json()
        lines = []

        # Answer box (réponse directe)
        if data.get("answerBox", {}).get("answer"):
            lines.append(f"✦ {data['answerBox']['answer']}")
        elif data.get("answerBox", {}).get("snippet"):
            lines.append(f"✦ {data['answerBox']['snippet']}")

        # Résultats organiques
        for item in data.get("organic", [])[:4]:
            title   = item.get("title", "")
            snippet = item.get("snippet", "")
            if title and snippet:
                lines.append(f"• {title} : {snippet}")

        return "\n".join(lines) if lines else None

    except Exception as e:
        st.session_state["gemini_last_error"] = str(e)
        return None


def _gemini_search(query: str) -> str | None:
    """Recherche via Gemini avec Google Search grounding (fallback)."""
    try:
        from google import genai
        from google.genai import types

        api_key = st.secrets.get("gemini", {}).get("api_key", "")
        if not api_key:
            return None

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"Réponds en français. Résume les infos récentes sur : {query}",
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        return response.text.strip() if response.text else None

    except Exception as e:
        st.session_state["gemini_last_error"] = str(e)
        return None


def search_web(query: str) -> str | None:
    """
    Recherche web avec cache 10 min.
    Essaie Brave en premier, puis Gemini en fallback.
    """
    # Cache
    cache_key = f"web_cache_{query[:50]}"
    cached = st.session_state.get(cache_key)
    if cached and time.time() - cached["ts"] < CACHE_TTL:
        return cached["result"]

    # Serper (Google) en priorité
    result = _serper_search(query)

    # Fallback Gemini si Serper échoue
    if result is None:
        result = _gemini_search(query)

    # Mettre en cache
    if result:
        st.session_state[cache_key] = {"result": result, "ts": time.time()}

    return result


def format_web_results_for_prompt(results: str, query: str) -> str:
    return (
        f"\n\n[INFOS WEB EN TEMPS RÉEL — \"{query}\"]\n"
        f"{results}\n"
        f"[FIN INFOS WEB — intègre ces informations naturellement dans ta réponse "
        f"sans mentionner les sources techniques]"
    )
