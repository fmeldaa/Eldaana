"""
voyance_engine.py — Moteur de prédiction probabiliste d'Eldaana.

Produit 6 scores dimensionnels + une prédiction existentielle (fun/viral).
Utilise Claude Haiku pour le scoring (suffisant + économique).
"""

import json
from anthropic import Anthropic
from datetime import datetime

client = Anthropic()

# ── Prompt système du moteur de scoring ───────────────────────────────────────

SCORING_SYSTEM = """Tu es le moteur prédictif d'Eldaana.
Tu analyses les données d'un utilisateur et tu produis des scores probabilistes entre 0 et 100.
0 = très négatif/risqué. 100 = excellent/positif.

Règles absolues :
- Réponds UNIQUEMENT en JSON valide, sans texte autour, sans markdown
- Sois réaliste : évite les extrêmes (scores entre 15 et 92 en général)
- Chaque score doit être justifié par les données fournies
- Les facteurs doivent être courts (max 8 mots) et en français
- Le conseil_jour doit être concret et actionnable en 1 phrase"""

SCORING_PROMPT_TEMPLATE = """Analyse ces données et produis les scores prédictifs pour aujourd'hui.

DONNÉES DISPONIBLES :
{data_block}

Produis exactement ce JSON (rien d'autre) :
{{
  "score_humeur": <0-100>,
  "score_energie": <0-100>,
  "score_stress": <0-100>,
  "score_budget": <0-100>,
  "score_journee": <0-100>,
  "facteurs_positifs": ["facteur 1", "facteur 2"],
  "facteurs_negatifs": ["facteur 1", "facteur 2"],
  "alerte_principale": "<phrase courte sur le risque principal, ou null>",
  "conseil_jour": "<conseil pratique en 1 phrase>"
}}"""

# ── Prompt système pour la voyance existentielle ───────────────────────────────

EXISTENTIAL_SYSTEM = """Tu es l'oracle d'Eldaana. Tu réponds aux questions existentielles
avec chaleur, humour bienveillant et précision apparente.
Réponds UNIQUEMENT en JSON valide :
{
  "probability": <0-100>,
  "timeframe": "<délai estimé ex: '6 à 18 mois' ou null>",
  "answer": "<réponse chaleureuse et personnalisée, 2 phrases max>",
  "factors": ["facteur lié au profil 1", "facteur 2", "facteur 3"],
  "disclaimer": "<disclaimer court et amusant, 1 phrase>"
}
La probabilité doit sembler réfléchie (pas aléatoire).
Les facteurs doivent être spécifiques au profil fourni."""


# ── Construction du bloc de données ───────────────────────────────────────────

def build_data_block(profile: dict, weather: dict = None,
                     humeur_data: dict = None, budget_data: dict = None,
                     transport_data: dict = None) -> str:
    """Construit le bloc de données texte pour le prompt de scoring."""
    lines = []

    # Profil
    if profile.get("prenom"):
        lines.append(f"Prénom : {profile['prenom']}")
    if profile.get("profession"):
        lines.append(f"Profession : {profile['profession']}")
    if profile.get("ville"):
        lines.append(f"Ville : {profile['ville']}")
    if profile.get("situation_maritale"):
        lines.append(f"Situation : {profile['situation_maritale']}")

    # Humeur
    if humeur_data:
        if humeur_data.get("today") is not None:
            lines.append(f"Humeur aujourd'hui : {humeur_data['today']}/10")
        if humeur_data.get("average_7d") is not None:
            lines.append(f"Moyenne humeur 7 jours : {humeur_data['average_7d']:.1f}/10")
        if humeur_data.get("trend"):
            lines.append(f"Tendance humeur : {humeur_data['trend']}")  # hausse|baisse|stable

    # Météo
    if weather:
        desc = weather.get("description") or weather.get("weather", "")
        temp = weather.get("temp_current") or weather.get("temperature", "")
        if desc or temp:
            lines.append(f"Météo : {desc} {temp}°C".strip())
        t_min = weather.get("temp_min", "")
        t_max = weather.get("temp_max", "")
        if t_min and t_max:
            lines.append(f"Min/Max : {t_min}°C / {t_max}°C")
        rain = weather.get("rain_probability") or weather.get("precipitation", "")
        if rain:
            lines.append(f"Risque pluie : {rain}%")

    # Transport
    if transport_data:
        if transport_data.get("has_alerts"):
            lines.append(f"Transport : PERTURBÉ — {transport_data.get('summary', 'lignes perturbées')}")
        else:
            lines.append("Transport : normal")

    # Budget
    if budget_data:
        if budget_data.get("remaining_pct") is not None:
            lines.append(f"Budget restant ce mois : {budget_data['remaining_pct']:.0f}%")
        if budget_data.get("trend"):
            lines.append(f"Tendance dépenses : {budget_data['trend']}")

    # Contexte temporel
    now = datetime.now()
    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    lines.append(f"Jour : {jours[now.weekday()]} {now.day}")
    lines.append(f"Heure : {now.strftime('%Hh%M')}")

    return "\n".join(lines) if lines else "Données insuffisantes"


# ── Calcul des scores ──────────────────────────────────────────────────────────

def compute_scores(profile: dict, weather: dict = None, humeur_data: dict = None,
                   budget_data: dict = None, transport_data: dict = None) -> dict:
    """
    Calcule les 6 scores prédictifs via Claude Haiku.
    Retourne un dict avec les scores, ou des valeurs par défaut en cas d'erreur.
    """
    data_block = build_data_block(
        profile or {}, weather or {}, humeur_data or {},
        budget_data or {}, transport_data or {}
    )

    prompt = SCORING_PROMPT_TEMPLATE.format(data_block=data_block)

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            system=[{
                "type": "text",
                "text": SCORING_SYSTEM,
                "cache_control": {"type": "ephemeral"}
            }],
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        # Nettoyer les éventuels ```json ... ```
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())

    except Exception as e:
        print(f"[VoyanceEngine] Erreur scoring : {e}")
        return _default_scores()


def _default_scores() -> dict:
    """Scores par défaut en cas d'erreur API."""
    return {
        "score_humeur":    65,
        "score_energie":   60,
        "score_stress":    45,
        "score_budget":    70,
        "score_journee":   62,
        "facteurs_positifs": [],
        "facteurs_negatifs": [],
        "alerte_principale": None,
        "conseil_jour": "Prends soin de toi aujourd'hui. 💜",
    }


# ── Prédiction existentielle (fun / viral) ─────────────────────────────────────

def get_existential_prediction(question: str, profile: dict) -> dict:
    """
    Répond à une question existentielle avec une probabilité et des facteurs.
    Ex : "Quand vais-je me marier ?" → {"probability": 73, "answer": "...", ...}
    """
    prenom    = profile.get("prenom", "toi")
    age       = profile.get("age", "")
    situation = profile.get("situation_maritale", "")
    profession = profile.get("profession", "")
    ville     = profile.get("ville", "")

    context_parts = [f"Prénom : {prenom}"]
    if age:       context_parts.append(f"Âge : {age} ans")
    if situation: context_parts.append(f"Situation : {situation}")
    if profession: context_parts.append(f"Profession : {profession}")
    if ville:     context_parts.append(f"Ville : {ville}")

    context = "\n".join(context_parts)
    prompt  = f"""Profil :\n{context}\n\nQuestion : "{question}"\n\nRéponds en JSON."""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=350,
            system=[{
                "type": "text",
                "text": EXISTENTIAL_SYSTEM,
                "cache_control": {"type": "ephemeral"}
            }],
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())

    except Exception as e:
        print(f"[VoyanceEngine] Erreur existentielle : {e}")
        return {
            "probability": 67,
            "timeframe": None,
            "answer": "Les étoiles s'alignent favorablement pour toi. Continue dans cette direction. ✨",
            "factors": ["Ton énergie positive", "Tes efforts récents", "Le bon moment"],
            "disclaimer": "À titre indicatif, avec une pincée de magie cosmique 🌟",
        }
