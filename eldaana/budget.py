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
from translations import t as _t, t_list as _tl

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
    mois_nom = _tl("months")[datetime.now().month - 1]

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


def get_budget_stats(user_id: str) -> dict:
    """
    Retourne les stats de budget pour le moteur de scoring voyance.
    Format compatible avec voyance_engine.build_data_block().
    """
    summary = get_current_month_total(user_id)
    if summary["budget_mensuel"] == 0 and summary["total"] == 0:
        return {}

    pct_used = summary["pourcentage"]
    remaining_pct = max(0.0, 100.0 - pct_used)

    # Tendance dépenses : basée sur la moitié du mois
    from datetime import datetime as _dt
    day_of_month = _dt.now().day
    days_in_month = 30  # approximation
    expected_pct = (day_of_month / days_in_month) * 100
    if pct_used > expected_pct + 10:
        trend = "en hausse (dépasse le rythme prévu)"
    elif pct_used < expected_pct - 10:
        trend = "en baisse (bien en dessous du budget prévu)"
    else:
        trend = "stable"

    result = {
        "remaining_pct": remaining_pct,
        "trend": trend,
    }
    return result


def show_budget_page(profile: dict):
    """Page de gestion du budget dans Streamlit."""
    user_id = profile.get("user_id", "")
    budget_data = load_budget(user_id)
    summary = get_current_month_total(user_id)

    # Category translation helpers
    cats_display = _tl("bud_categories")
    cats_fr = ["Alimentation","Logement","Transport","Loisirs","Vêtements","Santé","Abonnements","Sorties","Autre"]

    def _cat_to_fr(display: str) -> str:
        """Map display category name back to French canonical for storage."""
        try:
            idx = cats_display.index(display)
            return cats_fr[idx]
        except (ValueError, IndexError):
            return display

    def _cat_to_display(fr_name: str) -> str:
        """Map French canonical category name to display name."""
        try:
            idx = cats_fr.index(fr_name)
            return cats_display[idx]
        except (ValueError, IndexError):
            return fr_name

    mois_nom = _tl("months")[datetime.now().month - 1]

    st.markdown(_t("bud_title"))
    st.caption(_t("bud_subtitle", mois=mois_nom, year=datetime.now().year))

    # ── Budget mensuel ──────────────────────────────────────────────────────────
    budget_mensuel = float(budget_data.get("budget_mensuel") or profile.get("budget_mensuel") or 0)

    with st.form("set_budget_form"):
        new_budget = st.number_input(
            _t("bud_input_label"),
            min_value=0.0, max_value=50000.0,
            value=budget_mensuel, step=50.0,
            help=_t("bud_input_help")
        )
        if st.form_submit_button(_t("bud_save_btn"), use_container_width=True):
            budget_data["budget_mensuel"] = float(new_budget)
            save_budget(user_id, budget_data)
            st.success(_t("bud_saved", n=int(new_budget)))
            st.rerun()

    st.divider()

    # ── Résumé du mois ──────────────────────────────────────────────────────────
    if summary["budget_mensuel"] > 0 or summary["total"] > 0:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(_t("bud_spent"), f"{summary['total']:.0f} €")
        with col2:
            restant_label = f"{summary['restant']:.0f} €" if summary["budget_mensuel"] > 0 else "—"
            st.metric(_t("bud_remaining"), restant_label)
        with col3:
            pct = f"{summary['pourcentage']:.0f}%" if summary["budget_mensuel"] > 0 else "—"
            st.metric(_t("bud_used"), pct)

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
                st.warning(_t("bud_alert", pct=f"{summary['pourcentage']:.0f}"))

        # Dépenses par catégorie
        if summary["by_cat"]:
            st.markdown(_t("bud_by_cat"))
            for cat, montant in sorted(summary["by_cat"].items(), key=lambda x: x[1], reverse=True):
                emoji = EMOJIS_CAT.get(cat, "💸")
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.markdown(f"{emoji} {_cat_to_display(cat)}")
                with col_b:
                    st.markdown(f"**{montant:.0f} €**")

    st.divider()

    # ── Ajouter une dépense ──────────────────────────────────────────────────────
    st.markdown(_t("bud_add_title"))
    with st.form("add_expense_form"):
        c1, c2 = st.columns(2)
        with c1:
            montant = st.number_input(_t("bud_amount"), min_value=0.01, max_value=10000.0, value=10.0, step=0.5)
        with c2:
            categorie = st.selectbox(_t("bud_category"), cats_display)
        description = st.text_input(_t("bud_desc"), placeholder=_t("bud_desc_ph"))
        if st.form_submit_button(_t("bud_record_btn"), use_container_width=True):
            add_expense(user_id, montant, _cat_to_fr(categorie), description)
            st.success(_t("bud_recorded", n=montant, cat=categorie))
            st.rerun()

    st.divider()

    # ── Historique du mois ──────────────────────────────────────────────────────
    if summary["depenses"]:
        st.markdown(_t("bud_history"))
        for dep in reversed(summary["depenses"]):
            emoji = EMOJIS_CAT.get(dep["categorie"], "💸")
            desc  = f" — {dep['description']}" if dep.get("description") else ""
            col1, col2, col3 = st.columns([3, 1, 0.5])
            with col1:
                st.markdown(f"{emoji} **{_cat_to_display(dep['categorie'])}**{desc}")
                st.caption(dep["date"])
            with col2:
                st.markdown(f"**{dep['montant']:.2f} €**")
            with col3:
                if st.button("🗑️", key=f"del_dep_{dep['id']}", help=_t("bud_delete_tip")):
                    delete_expense(user_id, dep["id"])
                    st.rerun()
    else:
        st.info(_t("bud_no_expenses"))
