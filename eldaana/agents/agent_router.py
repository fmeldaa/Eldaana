"""
agent_router.py — Détection d'intention et routage vers les agents.

Intercepte les messages AVANT l'appel Claude principal.
Si une intention agent est détectée, route vers l'agent approprié.
Sinon, retourne None pour laisser passer au chat normal.
"""

import json
from anthropic import Anthropic

client = Anthropic()

INTENT_SYSTEM = """Tu es un classificateur d'intentions pour Eldaana.
Analyse le message utilisateur et détermine si c'est une demande d'action agent.
Réponds UNIQUEMENT en JSON valide, sans markdown, sans explication.

Catégories d'agents disponibles :
- email : lire emails, résumer, rédiger, envoyer
- shopping : liste de courses, commander, Uber Eats, Carrefour Drive, Amazon
- notifications : appels manqués, SMS, messages vocaux, WhatsApp

Format de réponse :
{
  "is_agent_request": true/false,
  "agent": "email" | "shopping" | "notifications" | null,
  "action": "string décrivant l'action précise",
  "params": {},
  "confidence": 0.0
}

Exemples :
- "Résume mes emails du matin" → email, action: summarize_inbox, confidence: 0.95
- "Commande une pizza Hut sur Uber Eats" → shopping, action: order_ubereats, confidence: 0.92
- "Qui m'a appelé ce matin ?" → notifications, action: read_missed_calls, confidence: 0.90
- "Fais une liste de courses pour des spaghetti" → shopping, action: build_shopping_list, confidence: 0.88
- "Comment tu vas ?" → is_agent_request: false, agent: null, confidence: 0.05
- "Quel temps fait-il ?" → is_agent_request: false, agent: null, confidence: 0.02
"""


def detect_intent(message: str) -> dict:
    """Détecte si le message est une demande d'action agent."""
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=INTENT_SYSTEM,
            messages=[{"role": "user", "content": message}]
        )
        raw = response.content[0].text.strip()
        # Nettoyer les blocs markdown éventuels
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:].strip()
        return json.loads(raw)
    except Exception:
        return {"is_agent_request": False, "agent": None, "confidence": 0.0}


def route_to_agent(intent: dict, message: str, profile: dict) -> dict | None:
    """
    Route vers le bon agent si l'intention est détectée avec confiance suffisante.
    Retourne la réponse de l'agent ou None pour laisser passer au chat normal.
    """
    if not intent.get("is_agent_request") or intent.get("confidence", 0) < 0.7:
        return None

    agent_name = intent.get("agent")
    uid        = profile.get("user_id", "")

    # Vérifier les permissions
    try:
        from agents.permissions import has_permission, load_permissions
        perms = load_permissions(uid)
        perm  = perms.get(agent_name)
    except Exception:
        perm = None

    if not perm or not perm.enabled:
        return {
            "type":    "permission_required",
            "agent":   agent_name,
            "message": (
                f"Pour que je puisse **{intent.get('action', 'faire ça')}**, "
                f"j'ai besoin de ton autorisation. "
                f"Tu peux l'activer dans **Paramètres → Agent → {agent_name.capitalize() if agent_name else ''}**."
            ),
        }

    # Router vers l'agent concerné
    try:
        if agent_name == "email":
            from agents.email_agent import handle_email_intent
            return handle_email_intent(intent, message, profile)

        elif agent_name == "shopping":
            from agents.shopping_agent import handle_shopping_intent
            return handle_shopping_intent(intent, message, profile)

        elif agent_name == "notifications":
            from agents.notifications_agent import handle_notifications_intent
            return handle_notifications_intent(intent, message, profile)

    except Exception as e:
        return {
            "type":    "error",
            "message": f"L'agent {agent_name} a rencontré une erreur. Je reste disponible par chat.",
        }

    return None
