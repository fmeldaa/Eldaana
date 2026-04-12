"""
gemini_search.py — Recherche web temps réel via Gemini.

Utilisé quand l'utilisateur pose une question sur :
- L'actualité récente
- Des événements / sorties / concerts
- Des infos qui changent (prix, horaires, météo future...)
- Tout ce qui nécessite des données fraîches

Gemini retourne un résumé avec ses sources, qu'on injecte
dans le contexte Claude pour une réponse enrichie.
"""

import streamlit as st
import re

# Mots-clés qui déclenchent une recherche web
WEB_TRIGGERS = [
    # Actualité
    "actualité", "actu", "news", "dernières nouvelles", "info du jour",
    "aujourd'hui", "cette semaine", "ce mois",
    # Événements
    "événement", "concert", "exposition", "festival", "sortie",
    "spectacle", "cinéma", "film", "série",
    # Recherche explicite
    "cherche", "recherche", "trouve", "qu'est-ce que", "c'est quoi",
    "qui est", "où est", "quand est", "comment faire",
    # Infos pratiques
    "météo", "température", "prévision",
    "prix", "tarif", "horaire", "ouvert", "fermé",
    "restaurant", "recette", "produit",
    # Tendances
    "tendance", "mode", "populaire", "viral", "trending",
]


def should_search_web(message: str) -> bool:
    """Détermine si la question nécessite une recherche web."""
    msg_lower = message.lower()
    return any(trigger in msg_lower for trigger in WEB_TRIGGERS)


def search_web(query: str) -> str | None:
    """
    Interroge Gemini avec Google Search grounding.
    Retourne un résumé des résultats web, ou None si erreur.
    """
    try:
        import google.generativeai as genai

        api_key = st.secrets.get("gemini", {}).get("api_key", "")
        if not api_key:
            return None

        genai.configure(api_key=api_key)

        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            tools="google_search",
        )

        prompt = (
            f"Réponds en français. Fais une recherche web sur : {query}\n"
            f"Donne un résumé factuel et concis (5-8 lignes max) avec les informations "
            f"les plus récentes et pertinentes. Mentionne les sources si important."
        )

        response = model.generate_content(prompt)
        text = response.text.strip()
        return text if text else None

    except Exception:
        return None


def format_web_results_for_prompt(results: str, query: str) -> str:
    """Formate les résultats web pour injection dans le contexte Claude."""
    return (
        f"\n\n[RECHERCHE WEB — résultats en temps réel pour : \"{query}\"]\n"
        f"{results}\n"
        f"[FIN RECHERCHE WEB — utilise ces infos pour enrichir ta réponse de façon naturelle]"
    )
