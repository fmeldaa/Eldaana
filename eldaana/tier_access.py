"""
tier_access.py — Gestion centralisée des droits d'accès par tier.

Tiers :
  'free'      → Chat texte, météo, profil, humeur basique, voyance fun
  'essential' → Tout free + voix 120 min, transport, budget, scores prédictifs
  'premium'   → Tout essential + voix illimitée, forecast, facteurs détaillés, Sonnet
"""

import streamlit as st
from stripe_payment import is_premium


# ── Définition des features par tier ──────────────────────────────────────────

FREE_FEATURES = {
    "chat_text",
    "weather",
    "profile",
    "humeur_basic",
    "voyance_fun",          # prédictions existentielles (1/jour)
    "history_7d",
}

ESSENTIAL_FEATURES = FREE_FEATURES | {
    "voice_120min",
    "transport",
    "budget",
    "shopping",
    "email_summary",
    "web_search",
    "humeur_analysis",
    "voyance_daily_scores", # scores humeur/énergie/stress/budget
    "history_90d",
    "memory",
}

PREMIUM_FEATURES = ESSENTIAL_FEATURES | {
    "voice_unlimited",
    "sonnet_model",
    "voyance_forecast_7d",
    "voyance_forecast_30d",
    "voyance_factors_detail",
    "voyance_trends",
    "dashboard_full",
    "beta_access",
}


# ── API publique ───────────────────────────────────────────────────────────────

def get_user_tier(uid: str) -> str:
    """Retourne le tier de l'utilisateur : 'free' | 'essential' | 'premium'."""
    if not uid:
        return "free"
    # Cache en session pour éviter N appels Supabase par page
    cache_key = f"_tier_{uid}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    tier = "essential" if is_premium(uid) else "free"
    # Note : distinguer essential / premium nécessite get_user_plan() dans stripe_payment.py
    # → à affiner quand le plan 29€ sera créé dans Stripe
    st.session_state[cache_key] = tier
    return tier


def can_access(feature: str, uid: str) -> bool:
    """Vérifie si l'utilisateur peut accéder à une fonctionnalité."""
    tier = get_user_tier(uid)
    if tier == "premium":
        return feature in PREMIUM_FEATURES
    elif tier == "essential":
        return feature in ESSENTIAL_FEATURES
    return feature in FREE_FEATURES


def show_upgrade_prompt(feature_label: str, required_tier: str = "essential"):
    """Affiche un bloc d'upgrade quand une feature est verrouillée."""
    price    = "9,99€/mois" if required_tier == "essential" else "29€/mois"
    tier_lbl = "Essentiel" if required_tier == "essential" else "Premium"
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#fdf4ff,#ede9fe);
                border:1.5px solid #c084fc;border-radius:16px;
                padding:1.2rem 1.5rem;text-align:center;margin:1rem 0;">
        <p style="font-size:1.1rem;font-weight:700;color:#7c3aed;margin:0 0 6px 0;">
            🔮 {feature_label}
        </p>
        <p style="color:#6b7280;font-size:0.85rem;margin:0 0 12px 0;">
            Fonctionnalité {tier_lbl} — {price}
        </p>
        <p style="color:#9ca3af;font-size:0.8rem;margin:0;">
            Passe à {tier_lbl} pour débloquer cette fonctionnalité et bien plus.
        </p>
    </div>
    """, unsafe_allow_html=True)
