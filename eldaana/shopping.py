"""
shopping.py — Gestion intelligente des courses d'Eldaana.

Fonctionnalités :
- Enregistrement des achats avec date
- Estimation automatique de la date de rachat selon le type de produit
- Rappels intelligents quand un produit est bientôt épuisé
- Historique des achats
"""

import streamlit as st
import json
from datetime import datetime, timedelta
from pathlib import Path
from storage import db_load, db_save

# ── Durées moyennes en jours par catégorie ────────────────────────────────────
DUREES_DEFAUT = {
    # Alimentaire frais
    "lait":          7,   "yaourt":       7,   "fromage":      10,
    "beurre":        14,  "œuf":          14,  "oeufs":        14,
    "pain":          3,   "légume":       5,   "légumes":      5,
    "fruit":         5,   "fruits":       5,   "viande":       5,
    "poisson":       5,   "jambon":       7,   "crème":        7,

    # Alimentaire sec
    "pâtes":         60,  "riz":          60,  "farine":       60,
    "sucre":         60,  "café":         21,  "thé":          30,
    "huile":         45,  "sel":          90,  "poivre":       90,
    "céréales":      21,  "biscuit":      14,  "biscuits":     14,
    "chocolat":      14,  "conserve":     90,  "sauce":        30,

    # Boissons
    "eau":           14,  "jus":          14,  "soda":         14,
    "bière":         21,  "vin":          30,

    # Hygiène / Beauté
    "shampoing":     30,  "gel douche":   30,  "savon":        21,
    "dentifrice":    45,  "déodorant":    30,  "rasoir":       14,
    "crème visage":  45,  "parfum":       90,  "coton":        30,

    # Entretien maison
    "liquide vaisselle": 21, "lessive":   21,  "éponge":       14,
    "sac poubelle":  30,  "papier toilette": 21, "essuie-tout": 14,

    # Divers
    "médicament":    30,  "pile":         180, "ampoule":      365,
}

SEUIL_RAPPEL_JOURS = 2  # Rappel X jours avant épuisement estimé


def _get_duree(nom: str) -> int:
    """Retourne la durée estimée en jours pour un produit."""
    nom_lower = nom.lower()
    for key, duree in DUREES_DEFAUT.items():
        if key in nom_lower:
            return duree
    return 14  # défaut : 2 semaines


def load_shopping(user_id: str) -> dict:
    """Charge la liste de courses depuis le profil."""
    profile = db_load(user_id)
    if not profile:
        return {"items": [], "history": []}
    return profile.get("shopping", {"items": [], "history": []})


def save_shopping(user_id: str, shopping: dict):
    """Sauvegarde la liste de courses dans le profil."""
    profile = db_load(user_id)
    if profile:
        profile["shopping"] = shopping
        db_save(profile)


def add_purchase(user_id: str, items: list[str], date: str = None) -> list[dict]:
    """
    Enregistre un ou plusieurs achats.
    items : liste de noms de produits
    Retourne la liste des articles ajoutés.
    """
    shopping = load_shopping(user_id)
    today    = date or datetime.now().strftime("%Y-%m-%d")
    added    = []

    for nom in items:
        nom = nom.strip().lower()
        if not nom:
            continue

        duree       = _get_duree(nom)
        restock_date = (datetime.now() + timedelta(days=duree)).strftime("%Y-%m-%d")

        # Mettre à jour si déjà existant, sinon ajouter
        existing = next((i for i in shopping["items"] if i["name"] == nom), None)
        if existing:
            existing["last_bought"]  = today
            existing["restock_date"] = restock_date
            existing["reminded"]     = False
        else:
            item = {
                "name":         nom,
                "last_bought":  today,
                "restock_date": restock_date,
                "frequency_days": duree,
                "reminded":     False,
            }
            shopping["items"].append(item)

        # Historique
        shopping["history"].append({"name": nom, "date": today})
        added.append({"name": nom, "restock_date": restock_date, "days": duree})

    save_shopping(user_id, shopping)
    return added


def get_reminders(user_id: str) -> list[dict]:
    """
    Retourne les produits à racheter bientôt (dans les X prochains jours).
    """
    shopping = load_shopping(user_id)
    today    = datetime.now().date()
    reminders = []

    for item in shopping["items"]:
        if item.get("reminded"):
            continue
        restock = datetime.strptime(item["restock_date"], "%Y-%m-%d").date()
        days_left = (restock - today).days

        if days_left <= SEUIL_RAPPEL_JOURS:
            reminders.append({
                "name":      item["name"],
                "days_left": days_left,
                "overdue":   days_left < 0,
            })

    return reminders


def mark_reminded(user_id: str, item_name: str):
    """Marque un article comme ayant été rappelé."""
    shopping = load_shopping(user_id)
    for item in shopping["items"]:
        if item["name"] == item_name:
            item["reminded"] = True
    save_shopping(user_id, shopping)


def format_reminders_for_prompt(reminders: list[dict]) -> str:
    """Formate les rappels pour injection dans le system prompt."""
    if not reminders:
        return ""

    lines = []
    for r in reminders:
        if r["overdue"]:
            lines.append(f"• {r['name'].capitalize()} — épuisé depuis {abs(r['days_left'])} jour(s)")
        elif r["days_left"] == 0:
            lines.append(f"• {r['name'].capitalize()} — normalement épuisé aujourd'hui")
        else:
            lines.append(f"• {r['name'].capitalize()} — encore ~{r['days_left']} jour(s)")

    return (
        "\n\n[RAPPELS COURSES]\n"
        "Ces produits sont bientôt ou déjà épuisés selon les habitudes d'achat :\n"
        + "\n".join(lines)
        + "\nMentionne-les naturellement dans la conversation si pertinent, "
          "et propose de les ajouter à une liste de courses.\n[FIN RAPPELS COURSES]"
    )


def format_shopping_for_prompt(user_id: str) -> str:
    """Résumé des courses pour le system prompt."""
    shopping = load_shopping(user_id)
    items    = shopping.get("items", [])
    if not items:
        return ""

    today   = datetime.now().date()
    lines   = []
    for item in sorted(items, key=lambda x: x["restock_date"])[:10]:
        restock   = datetime.strptime(item["restock_date"], "%Y-%m-%d").date()
        days_left = (restock - today).days
        status    = f"dans {days_left}j" if days_left > 0 else "épuisé"
        lines.append(f"• {item['name'].capitalize()} (à racheter : {status})")

    return (
        "\n\n[SUIVI COURSES]\n"
        + "\n".join(lines)
        + "\n[FIN SUIVI COURSES]"
    )


def detect_purchases_in_message(message: str) -> list[str]:
    """
    Détecte si l'utilisateur mentionne un achat dans son message.
    Retourne la liste des produits achetés détectés.
    """
    triggers = [
        "j'ai acheté", "j'ai pris", "j'ai fait les courses",
        "j'ai récupéré", "j'viens d'acheter", "je viens d'acheter",
        "on a acheté", "on a pris", "j'ai commandé",
    ]
    msg_lower = message.lower()
    if not any(t in msg_lower for t in triggers):
        return []

    # Extraction basique des produits (après le trigger)
    products = []
    for trigger in triggers:
        if trigger in msg_lower:
            rest = msg_lower.split(trigger, 1)[1]
            # Nettoyer et séparer
            rest = rest.strip(" .,!?")
            # Séparer par virgule, "et", "du", "de la", "des", "un", "une"
            import re
            parts = re.split(r",|\bet\b|\bdu\b|\bde la\b|\bdes\b|\bun\b|\bune\b", rest)
            for p in parts:
                p = p.strip(" .,!?")
                if 2 < len(p) < 40:
                    products.append(p)
            break

    return products[:10]  # max 10 produits détectés


def show_shopping_page(profile: dict):
    """Page de gestion des courses dans Streamlit."""
    user_id  = profile.get("user_id", "")
    shopping = load_shopping(user_id)
    items    = shopping.get("items", [])
    today    = datetime.now().date()

    st.markdown("### 🛒 Mes courses")
    st.caption("Eldaana suit tes achats et te rappelle quand racheter.")

    # ── Ajouter un achat manuellement ──
    with st.form("add_purchase_form"):
        st.markdown("**Ajouter un achat**")
        new_items = st.text_input(
            "Produit(s) achetés",
            placeholder="Ex : lait, shampoing, pâtes…",
        )
        submitted = st.form_submit_button("✅ Enregistrer l'achat", use_container_width=True)

    if submitted and new_items.strip():
        products = [p.strip() for p in new_items.split(",") if p.strip()]
        added    = add_purchase(user_id, products)
        for a in added:
            restock = datetime.strptime(a["restock_date"], "%Y-%m-%d").date()
            days    = (restock - today).days
            st.success(f"✅ **{a['name'].capitalize()}** — à racheter dans ~{days} jours")
        st.rerun()

    st.divider()

    # ── Liste des produits ──
    if not items:
        st.info("Aucun produit enregistré. Dis à Eldaana ce que tu as acheté !")
        return

    # Trier par date de rachat
    items_sorted = sorted(items, key=lambda x: x["restock_date"])

    st.markdown("**Suivi des produits**")
    for item in items_sorted:
        restock   = datetime.strptime(item["restock_date"], "%Y-%m-%d").date()
        days_left = (restock - today).days

        if days_left < 0:
            emoji, color = "🔴", "#fee2e2"
            status = f"Épuisé depuis {abs(days_left)}j"
        elif days_left == 0:
            emoji, color = "🟠", "#fff7ed"
            status = "À racheter aujourd'hui"
        elif days_left <= 3:
            emoji, color = "🟡", "#fefce8"
            status = f"Dans {days_left} jour(s)"
        else:
            emoji, color = "🟢", "#f0fdf4"
            status = f"Dans {days_left} jours"

        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            st.markdown(f"{emoji} **{item['name'].capitalize()}**")
        with col2:
            st.caption(status)
        with col3:
            if st.button("🗑️", key=f"del_{item['name']}", help="Supprimer"):
                shopping["items"] = [i for i in shopping["items"] if i["name"] != item["name"]]
                save_shopping(user_id, shopping)
                st.rerun()
