"""
gemini_search.py — Recherche web temps réel via Gemini 2.0 Flash + Google Search.
"""

import streamlit as st

# Mots-clés qui déclenchent une recherche web
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


def should_search_web(message: str) -> bool:
    msg_lower = message.lower()
    return any(trigger in msg_lower for trigger in WEB_TRIGGERS)


def search_web(query: str) -> str | None:
    """
    Interroge Gemini 2.0 Flash avec Google Search grounding.
    Retourne un résumé des résultats web, ou None si erreur.
    """
    try:
        from google import genai
        from google.genai import types

        api_key = st.secrets.get("gemini", {}).get("api_key", "")
        if not api_key:
            return None

        client = genai.Client(api_key=api_key)

        prompt = (
            f"Réponds uniquement en français. "
            f"Fais une recherche web et donne un résumé factuel et concis "
            f"(maximum 8 lignes) des informations les plus récentes sur : {query}. "
            f"Inclus les faits importants et si pertinent les sources."
        )

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )

        text = response.text.strip() if response.text else None
        return text

    except Exception as e:
        st.session_state["gemini_last_error"] = str(e)
        return None


def format_web_results_for_prompt(results: str, query: str) -> str:
    return (
        f"\n\n[INFOS WEB EN TEMPS RÉEL pour \"{query}\" — source : Google via Gemini]\n"
        f"{results}\n"
        f"[FIN INFOS WEB — intègre naturellement ces informations dans ta réponse "
        f"sans mentionner Gemini, présente-les comme tes propres connaissances actualisées]"
    )
