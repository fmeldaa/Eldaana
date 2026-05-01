"""
shopping_agent.py — Agent courses & shopping Eldaana.

Capacités :
1. Liste de courses intelligente (saisie vocale ou texte)
2. Commande Uber Eats / Deliveroo (deep link + préparation)
3. Carrefour Drive (liste formatée + lien)
4. Amazon / générique (deep link vers recherche)

Architecture : 3 niveaux
  SUGGEST  — Eldaana propose, l'utilisateur commande manuellement
  PREPARE  — Eldaana prépare, l'utilisateur confirme et finalise
  AUTO     — Eldaana commande directement (dans la limite de montant)
"""

import json
from anthropic import Anthropic

client = Anthropic()


# ── LISTE DE COURSES ──────────────────────────────────────────────────────────

def build_shopping_list(request: str, profile: dict) -> dict:
    """
    À partir d'une demande libre, génère une liste de courses structurée.
    Ex : "Je veux faire des pâtes carbonara pour 4 personnes ce soir"
    """
    prenom      = profile.get("prenom", "")
    preferences = profile.get("food_preferences", "aucune restriction alimentaire connue")

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        system=[{
            "type": "text",
            "text": (
                f"Tu es l'agent courses d'Eldaana pour {prenom}.\n"
                f"Préférences alimentaires : {preferences}\n"
                "Génère une liste de courses précise et pratique.\n"
                "Réponds UNIQUEMENT en JSON valide :\n"
                '{"recipe_or_context":"string","items":[{"name":"string","quantity":"string",'
                '"unit":"string","category":"string","estimated_price":0.0}],'
                '"estimated_total":0.0,"store_suggestion":"string","notes":"string"}'
            ),
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": request}]
    )

    try:
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:].strip()
        return json.loads(raw)
    except Exception:
        return {"items": [], "estimated_total": 0}


def format_shopping_list_ui(shopping_list: dict) -> str:
    """Formate la liste de courses pour affichage dans le chat."""
    items   = shopping_list.get("items", [])
    total   = shopping_list.get("estimated_total", 0)
    store   = shopping_list.get("store_suggestion", "")
    notes   = shopping_list.get("notes", "")
    context = shopping_list.get("recipe_or_context", "")

    lines      = [f"🛒 **Liste de courses** — {context}\n"]
    categories: dict = {}
    for item in items:
        cat = item.get("category", "Autre")
        categories.setdefault(cat, []).append(item)

    for cat, cat_items in categories.items():
        lines.append(f"\n**{cat}**")
        for item in cat_items:
            price_str = f" ~{item['estimated_price']:.2f}€" if item.get("estimated_price") else ""
            lines.append(f"• {item.get('quantity','')} {item.get('unit','')} {item['name']}{price_str}")

    if total > 0:
        lines.append(f"\n💰 **Total estimé : {total:.2f}€**")
    if store:
        lines.append(f"🏪 Suggéré : {store}")
    if notes:
        lines.append(f"\n📝 {notes}")

    return "\n".join(lines)


# ── UBER EATS ────────────────────────────────────────────────────────────────

def prepare_ubereats_order(request: str, profile: dict) -> dict:
    """
    Prépare une commande Uber Eats.
    MVP : deep link vers la recherche du restaurant.
    """
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system="Extrais les infos d'une commande livraison. Réponds UNIQUEMENT en JSON.",
        messages=[{"role": "user", "content":
            f"Extrais restaurant, plat, adresse_livraison depuis : '{request}'. "
            f"Ville par défaut : {profile.get('ville', 'Paris')}. "
            f"Adresse par défaut : {profile.get('adresse', '')}. "
            f"Format : {{\"restaurant\":\"...\",\"plat\":\"...\",\"adresse_livraison\":\"...\",\"commentaire\":\"...\"}}"}]
    )

    try:
        raw = response.content[0].text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        order_params = json.loads(raw)
    except Exception:
        order_params = {"restaurant": "", "plat": "", "adresse_livraison": ""}

    restaurant_query = order_params.get("restaurant", "").replace(" ", "+")
    ubereats_link    = f"https://www.ubereats.com/fr/search?q={restaurant_query}"

    plat       = order_params.get("plat", "")
    restaurant = order_params.get("restaurant", "")
    adresse    = order_params.get("adresse_livraison", profile.get("adresse", ""))

    return {
        "type":                 "ubereats",
        "params":               order_params,
        "deep_link":            ubereats_link,
        "requires_confirmation": True,
        "message": (
            f"J'ai trouvé ta demande : **{plat}** chez **{restaurant}**.\n"
            f"Livraison à : {adresse}\n\n"
            f"👆 Je t'ouvre Uber Eats directement sur ce restaurant."
        ),
        "action_button": "🍕 Ouvrir Uber Eats",
        "action_url":    ubereats_link,
    }


# ── CARREFOUR DRIVE ───────────────────────────────────────────────────────────

def prepare_carrefour_drive(shopping_list: dict, profile: dict) -> dict:
    """
    Prépare une commande Carrefour Drive.
    MVP : liste formatée + lien Drive.
    """
    ville         = profile.get("ville", "Paris").split()[0]
    carrefour_link = f"https://www.carrefour.fr/drive/{ville.lower()}"

    items_text = "\n".join([
        f"- {item.get('quantity','')} {item.get('unit','')} {item['name']}"
        for item in shopping_list.get("items", [])
    ])
    nb    = len(shopping_list.get("items", []))
    total = shopping_list.get("estimated_total", 0)

    return {
        "type":                 "carrefour_drive",
        "shopping_list":        shopping_list,
        "deep_link":            carrefour_link,
        "requires_confirmation": True,
        "message": (
            f"Ta liste est prête ({nb} articles, ~{total:.2f}€).\n\n"
            f"Je vais t'ouvrir le Carrefour Drive de {ville}. "
            f"Tu pourras ajouter les articles au panier.\n\n"
            f"📋 **Ta liste :**\n{items_text}"
        ),
        "action_button": "🛒 Ouvrir Carrefour Drive",
        "action_url":    carrefour_link,
    }


# ── AMAZON ────────────────────────────────────────────────────────────────────

def prepare_amazon_order(item_request: str, profile: dict) -> dict:
    """
    Prépare une commande Amazon.
    MVP : lien de recherche avec les mots-clés extraits.
    """
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        system='Extrais les mots-clés de recherche. Réponds en JSON : {"keywords":"string","category":"string"}',
        messages=[{"role": "user", "content": item_request}]
    )

    try:
        raw      = response.content[0].text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        params   = json.loads(raw)
        keywords = params.get("keywords", item_request)
    except Exception:
        keywords = item_request

    amazon_link = f"https://www.amazon.fr/s?k={keywords.replace(' ', '+')}"

    return {
        "type":                 "amazon",
        "keywords":             keywords,
        "deep_link":            amazon_link,
        "requires_confirmation": True,
        "message": (
            f"J'ai préparé ta recherche Amazon pour : **{keywords}**.\n"
            f"Je t'ouvre les résultats directement."
        ),
        "action_button": "📦 Chercher sur Amazon",
        "action_url":    amazon_link,
    }


# ── HANDLER PRINCIPAL ─────────────────────────────────────────────────────────

def handle_shopping_intent(intent: dict, message: str, profile: dict) -> dict:
    """Route vers le bon sous-agent shopping."""
    uid      = profile.get("user_id", "")
    action   = intent.get("action", "")
    msg_lower = message.lower()

    if any(kw in msg_lower for kw in [
        "uber eats", "deliveroo", "just eat", "pizza",
        "livraison", "commander à manger", "commande à manger",
    ]):
        result = prepare_ubereats_order(message, profile)

    elif any(kw in msg_lower for kw in [
        "carrefour", "drive", "supermarché", "épicerie", "faire les courses",
    ]):
        shopping_list = build_shopping_list(message, profile)
        result        = prepare_carrefour_drive(shopping_list, profile)

    elif any(kw in msg_lower for kw in [
        "amazon", "commander sur", "acheter", "article",
    ]):
        result = prepare_amazon_order(message, profile)

    else:
        # Par défaut : liste de courses
        shopping_list = build_shopping_list(message, profile)
        formatted     = format_shopping_list_ui(shopping_list)
        result = {
            "type":          "shopping_list",
            "content":       formatted,
            "shopping_list": shopping_list,
            "actions": [
                {"label": "🛒 Commander sur Carrefour Drive", "action": "carrefour_drive"},
                {"label": "📦 Chercher sur Amazon",          "action": "amazon"},
                {"label": "📋 Copier la liste",              "action": "copy"},
            ],
        }

    try:
        from agents.permissions import log_agent_action
        log_agent_action(uid, "shopping", action, message[:100], "pending_confirm")
    except Exception:
        pass

    return result
