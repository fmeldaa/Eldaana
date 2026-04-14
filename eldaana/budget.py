"""
budget.py — Gestion du budget mensuel d'Eldaana.

Fonctionnalités :
- Budget mensuel défini dans le profil
- Enregistrement des dépenses par catégorie
- Suivi du mois en cours
- Alertes quand on dépasse 80 %
- Résumé pour le system prompt
"""

import streamlit as st
from datetime import datetime
from storage import db_load, db_save

CATEGORIES = [
    "Alimentation", "Logement", "Transport", "Loisirs",
    "Vêtements", "Santé", "Abonnements", "Sorties", "Autre"
]

EMOJIS_CAT = {
    "Alimentation": "🍎", "Logement": "🏠", "Transport": "🚌",
    "Loisirs": "🎮", "Vêtements": "👗", "Santé": "💊",
    "Abonnements": "📱", "Sorties": "🍽️", "Autre": "💸",
}


def load_budget(user_id: str) -> dict:
    profile = db_load(user_id)
    if not profile:
        return {"depenses": [], "budget_mensuel": 0}
    return profile.get("budget_data", {"depenses": [], "budget_mensuel": 0})


def save_budget(user_id: str, budget_data: dict):
    profile = db_load(user_id)
    if profile:
        profile["budget_data"] = budget_data
        db_save(profile)


def add_expense(user_id: str, montant: float, categorie: str, description: str = "") -> dict:
    """Enregistre une dépense."""
    budget_data = load_budget(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")

    expense = {
        "id":          datetime.now().strftime("%Y%m%d%H%M%S"),
        "date":        today,
        "month":       month,
        "montant":     round(float(montant), 2),
        "categorie":   categorie,
        "description": description.strip(),
    }
    budget_data["depenses"].append(expense)
    save_budget(user_id, budget_data)
    return expense


def get_current_month_total(user_id: str) -> dict:
    """Retourne les totaux du mois en cours."""
    budget_data = load_budget(user_id)
    month = datetime.now().strftime("%Y-%m")
    depenses_mois = [d for d in budget_data["depenses"] if d.get("month") == month]

    total = sum(d["montant"] for d in depenses_mois)
    by_cat = {}
    for d in depenses_mois:
        cat = d["categorie"]
        by_cat[cat] = by_cat.get(cat, 0) + d["montant"]

    budget_mensuel = float(budget_data.get("budget_mensuel") or 0)
    pourcentage = (total / budget_mensuel * 100) if budget_mensuel > 0 else 0
    restant = max(0, budget_mensuel - total)

    return {
        "total":          round(total, 2),
        "budget_mensuel": budget_mensuel,
        "restant":        round(restant, 2),
        "pourcentage":    round(pourcentage, 1),
        "by_cat":         {k: round(v, 2) for k, v in by_cat.items()},
        "depenses":       depenses_mois,
        "alerte":         pourcentage >= 80,
    }


def delete_expense(user_id: str, expense_id: str):
    """Supprime une dépense."""
    budget_data = load_budget(user_id)
    budget_data["depenses"] = [d for d in budget_data["depenses"] if d.get("id") != expense_id]
    save_budget(user_id, budget_data)


def format_budget_for_prompt(user_id: str) -> str:
    """Résumé budget pour injection dans le system prompt."""
    summary = get_current_month_total(user_id)
    if summary["budget_mensuel"] == 0 and summary["total"] == 0:
        return ""

    lines = []
    mois_fr = ["janvier","février","mars","avril","mai","juin",
               "juillet","août","septembre","octobre","novembre","décembre"]
    mois_nom = mois_fr[datetime.now().month - 1]

    if summary["budget_mensuel"] > 0:
        lines.append(f"- Budget {mois_nom} : {summary['budget_mensuel']} €")
        lines.append(f"- Dépensé : {summary['total']} € ({summary['pourcentage']}%)")
        lines.append(f"- Restant : {summary['restant']} €")
        if summary["alerte"]:
            lines.append(f"⚠️ ALERTE : budget utilisé à {summary['pourcentage']}% !")
    else:
        lines.append(f"- Dépenses {mois_nom} : {summary['total']} €")

    if summary["by_cat"]:
        top = sorted(summary["by_cat"].items(), key=lambda x: x[1], reverse=True)[:3]
        lines.append("- Top dépenses : " + ", ".join(f"{c} {v}€" for c, v in top))

    return (
        "\n\n[BUDGET]\n"
        + "\n".join(lines)
        + "\n[FIN BUDGET]"
    )


def show_budget_page(profile: dict):
    """Page de gestion du budget dans Streamlit."""
    user_id = profile.get("user_id", "")
    budget_data = load_budget(user_id)
    summary = get_current_month_total(user_id)

    mois_fr = ["janvier","février","mars","avril","mai","juin",
               "juillet","août","septembre","octobre","novembre","décembre"]
    mois_nom = mois_fr[datetime.now().month - 1]

    st.markdown("### 💰 Mon budget")
    st.caption(f"Suivi de tes dépenses — {mois_nom} {datetime.now().year}")

    # ── Budget mensuel ──────────────────────────────────────────────────────────
    budget_mensuel = float(budget_data.get("budget_mensuel") or profile.get("budget_mensuel") or 0)

    with st.form("set_budget_form"):
        new_budget = st.number_input(
            "💳 Budget mensuel (€)",
            min_value=0.0, max_value=50000.0,
            value=budget_mensuel, step=50.0,
            help="Ton budget disponible ce mois-ci"
        )
        if st.form_submit_button("💾 Enregistrer le budget", use_container_width=True):
            budget_data["budget_mensuel"] = float(new_budget)
            save_budget(user_id, budget_data)
            st.success(f"✅ Budget fixé à {new_budget:.0f} €")
            st.rerun()

    st.divider()

    # ── Résumé du mois ──────────────────────────────────────────────────────────
    if summary["budget_mensuel"] > 0 or summary["total"] > 0:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💸 Dépensé", f"{summary['total']:.0f} €")
        with col2:
            restant_label = f"{summary['restant']:.0f} €" if summary["budget_mensuel"] > 0 else "—"
            st.metric("💚 Restant", restant_label)
        with col3:
            pct = f"{summary['pourcentage']:.0f}%" if summary["budget_mensuel"] > 0 else "—"
            st.metric("📊 Utilisé", pct)

        if summary["budget_mensuel"] > 0:
            pct_val = min(summary["pourcentage"] / 100, 1.0)
            bar_color = "#22c55e" if pct_val < 0.6 else "#f59e0b" if pct_val < 0.8 else "#ef4444"
            st.markdown(f"""
            <div style="background:#e5e7eb;border-radius:8px;height:12px;margin:0.5rem 0 1rem 0;">
                <div style="background:{bar_color};width:{min(summary['pourcentage'],100):.0f}%;
                            height:100%;border-radius:8px;transition:width 0.3s;"></div>
            </div>
            """, unsafe_allow_html=True)

            if summary["alerte"]:
                st.warning(f"⚠️ Attention — tu as utilisé **{summary['pourcentage']:.0f}%** de ton budget !")

        # Dépenses par catégorie
        if summary["by_cat"]:
            st.markdown("**Répartition par catégorie**")
            for cat, montant in sorted(summary["by_cat"].items(), key=lambda x: x[1], reverse=True):
                emoji = EMOJIS_CAT.get(cat, "💸")
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.markdown(f"{emoji} {cat}")
                with col_b:
                    st.markdown(f"**{montant:.0f} €**")

    st.divider()

    # ── Ajouter une dépense ──────────────────────────────────────────────────────
    st.markdown("**➕ Ajouter une dépense**")
    with st.form("add_expense_form"):
        c1, c2 = st.columns(2)
        with c1:
            montant = st.number_input("Montant (€)", min_value=0.01, max_value=10000.0, value=10.0, step=0.5)
        with c2:
            categorie = st.selectbox("Catégorie", CATEGORIES)
        description = st.text_input("Description *(optionnel)*", placeholder="Ex : Courses Carrefour")
        if st.form_submit_button("✅ Enregistrer", use_container_width=True):
            add_expense(user_id, montant, categorie, description)
            st.success(f"✅ Dépense de **{montant:.2f} €** enregistrée ({categorie})")
            st.rerun()

    st.divider()

    # ── Historique du mois ──────────────────────────────────────────────────────
    if summary["depenses"]:
        st.markdown("**📋 Historique du mois**")
        for dep in reversed(summary["depenses"]):
            emoji = EMOJIS_CAT.get(dep["categorie"], "💸")
            desc  = f" — {dep['description']}" if dep.get("description") else ""
            col1, col2, col3 = st.columns([3, 1, 0.5])
            with col1:
                st.markdown(f"{emoji} **{dep['categorie']}**{desc}")
                st.caption(dep["date"])
            with col2:
                st.markdown(f"**{dep['montant']:.2f} €**")
            with col3:
                if st.button("🗑️", key=f"del_dep_{dep['id']}", help="Supprimer"):
                    delete_expense(user_id, dep["id"])
                    st.rerun()
    else:
        st.info("Aucune dépense ce mois-ci. Commence à les enregistrer !")
