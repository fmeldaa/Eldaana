"""
translations.py — Système de traduction FR / EN pour Eldaana.

Usage :
    from translations import t
    st.markdown(t("dashboard_hello", prenom="Alice"))
"""

import streamlit as st

# ── Dictionnaire de traductions ───────────────────────────────────────────────
_STRINGS: dict[str, dict[str, str]] = {

    # ── GÉNÉRAL ──────────────────────────────────────────────────────────────
    "fr": {
        "back_to_chat":       "← Retour à la conversation",

        # ── Langue ──────────────────────────────────────────────────────────
        "lang_instruction":   "Tu réponds TOUJOURS en français dans cette session, quelle que soit la langue utilisée par l'utilisateur.",

        # ── Sidebar ─────────────────────────────────────────────────────────
        "scores_title":       "Scores du jour",
        "btn_dashboard":      "🏠 Tableau de bord",
        "btn_profile":        "✏️ Enrichir mon profil",
        "btn_social":         "🌐 Ma vie numérique",
        "btn_emails":         "📧 Mes emails",
        "btn_shopping":       "🛒 Mes courses",
        "btn_budget":         "💰 Mon budget",
        "btn_predictions":    "🔮 Prédictions",
        "btn_privacy":        "🔒 Vie privée",
        "btn_agent":          "🤖 Agent — Permissions",
        "btn_new_conv":       "🔄 Nouvelle conversation",
        "btn_switch_user":    "🔀 Changer d'utilisateur",
        "btn_lang":           "🇬🇧 English",
        "voice_on":           "🔊 Voix activée",
        "voice_off":          "🔇 Désactivée",
        "voice_label":        "🎙️ Choix de la voix",
        "voice_on_label":     "🎙️ Mode vocal ON",
        "voice_off_label":    "🎙️ Mode vocal OFF",

        # ── Greeting ────────────────────────────────────────────────────────
        "greeting_m":         "heureux",
        "greeting_f":         "heureuse",
        "greeting_msg":       "Bonjour {prenom} — Comment puis-je te rendre {accord} aujourd'hui ?",

        # ── Dashboard ───────────────────────────────────────────────────────
        "page_dashboard":     "Mon tableau de bord",
        "page_rgpd":          "Vie privée & RGPD",
        "page_profile":       "Mon profil",
        "page_social":        "Ma vie numérique",
        "page_email":         "Mes emails",
        "page_shopping":      "Mes courses",
        "page_budget":        "Mon budget",
        "page_voyance":       "Prédictions",
        "page_agent":         "Agent — Permissions",

        "dash_hello":         "🏠 Bonjour {prenom} !",
        "dash_weather":       "**☀️ Météo**",
        "dash_weather_tip":   "Ajoute ta ville dans le profil pour voir la météo",
        "dash_mood":          "**😊 Humeur du jour**",
        "dash_mood_empty":    "Non renseignée",
        "dash_budget":        "**💰 Budget du mois**",
        "dash_budget_used":   "Utilisé",
        "dash_budget_left":   "Restant :",
        "dash_budget_spent":  "💸 Dépensé ce mois :",
        "dash_budget_hint":   "Définis un budget mensuel pour le suivi",
        "dash_budget_empty":  "Aucune donnée budget",
        "dash_shopping":      "**🛒 Courses à faire**",
        "dash_shop_empty":    "épuisé",
        "dash_shop_soon":     "dans {n}j",
        "dash_shop_ok":       "✅ Tout est OK !",
        "dash_transport":     "**🚆 Mes transports**",
        "dash_depart_soon":   "⏰ Départ bientôt",
        "dash_at":            "à",
        "dash_lines":         "Lignes :",
        "dash_check_btn":     "🔍 Vérifier les perturbations maintenant",
        "dash_checking":      "Vérification en cours…",
        "dash_alert":         "⚠️ Perturbation détectée sur {lines} !",
        "dash_traffic_ok":    "✅ Trafic normal sur toutes tes lignes !",
        "dash_depart_usual":  "Départ habituel :",
        "dash_suggestion":    "**✨ Suggestion du jour**",
        "dash_activity":      "Activité suggérée",
        "dash_quick":         "**Accès rapide**",
        "dash_btn_emails":    "📧 Emails",
        "dash_btn_shopping":  "🛒 Courses",
        "dash_btn_budget":    "💰 Budget",
        "dash_btn_predict":   "🔮 Prédict.",
        "dash_btn_chat":      "💬 Chat",
        "sugg_morning":       "🌅 Commence ta journée avec 5 min de plein air — ça change tout !",
        "sugg_noon":          "☀️ Prends une vraie pause déjeuner aujourd'hui.",
        "sugg_afternoon":     "💪 Tu as bien avancé. Prends un moment pour toi avant ce soir.",
        "sugg_evening":       "🌙 Prépare-toi à une bonne nuit. Pose ton téléphone 30 min avant de dormir.",

        # ── Dates ───────────────────────────────────────────────────────────
        "days":   ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"],
        "months": ["janvier","février","mars","avril","mai","juin",
                   "juillet","août","septembre","octobre","novembre","décembre"],
    },

    "en": {
        "back_to_chat":       "← Back to conversation",

        # ── Langue ──────────────────────────────────────────────────────────
        "lang_instruction":   "You ALWAYS respond in English in this session, regardless of the language used by the user. Your personality stays the same — warm, direct, predictive — just in English.",

        # ── Sidebar ─────────────────────────────────────────────────────────
        "scores_title":       "Today's scores",
        "btn_dashboard":      "🏠 Dashboard",
        "btn_profile":        "✏️ Enrich my profile",
        "btn_social":         "🌐 My digital life",
        "btn_emails":         "📧 My emails",
        "btn_shopping":       "🛒 My shopping",
        "btn_budget":         "💰 My budget",
        "btn_predictions":    "🔮 Predictions",
        "btn_privacy":        "🔒 Privacy",
        "btn_agent":          "🤖 Agent — Permissions",
        "btn_new_conv":       "🔄 New conversation",
        "btn_switch_user":    "🔀 Switch user",
        "btn_lang":           "🇫🇷 Français",
        "voice_on":           "🔊 Voice enabled",
        "voice_off":          "🔇 Disabled",
        "voice_label":        "🎙️ Choose voice",
        "voice_on_label":     "🎙️ Voice mode ON",
        "voice_off_label":    "🎙️ Voice mode OFF",

        # ── Greeting ────────────────────────────────────────────────────────
        "greeting_m":         "happy",
        "greeting_f":         "happy",
        "greeting_msg":       "Hello {prenom} — How can I make you {accord} today?",

        # ── Dashboard ───────────────────────────────────────────────────────
        "page_dashboard":     "My dashboard",
        "page_rgpd":          "Privacy & GDPR",
        "page_profile":       "My profile",
        "page_social":        "My digital life",
        "page_email":         "My emails",
        "page_shopping":      "My shopping",
        "page_budget":        "My budget",
        "page_voyance":       "Predictions",
        "page_agent":         "Agent — Permissions",

        "dash_hello":         "🏠 Hello {prenom}!",
        "dash_weather":       "**☀️ Weather**",
        "dash_weather_tip":   "Add your city in your profile to see the weather",
        "dash_mood":          "**😊 Today's mood**",
        "dash_mood_empty":    "Not filled in",
        "dash_budget":        "**💰 Monthly budget**",
        "dash_budget_used":   "Used",
        "dash_budget_left":   "Remaining:",
        "dash_budget_spent":  "💸 Spent this month:",
        "dash_budget_hint":   "Set a monthly budget to track spending",
        "dash_budget_empty":  "No budget data",
        "dash_shopping":      "**🛒 Shopping reminders**",
        "dash_shop_empty":    "out of stock",
        "dash_shop_soon":     "in {n}d",
        "dash_shop_ok":       "✅ All good!",
        "dash_transport":     "**🚆 My commute**",
        "dash_depart_soon":   "⏰ Departing soon",
        "dash_at":            "at",
        "dash_lines":         "Lines:",
        "dash_check_btn":     "🔍 Check disruptions now",
        "dash_checking":      "Checking…",
        "dash_alert":         "⚠️ Disruption on {lines}!",
        "dash_traffic_ok":    "✅ Normal traffic on all your lines!",
        "dash_depart_usual":  "Usual departure:",
        "dash_suggestion":    "**✨ Suggestion of the day**",
        "dash_activity":      "Suggested activity",
        "dash_quick":         "**Quick access**",
        "dash_btn_emails":    "📧 Emails",
        "dash_btn_shopping":  "🛒 Shopping",
        "dash_btn_budget":    "💰 Budget",
        "dash_btn_predict":   "🔮 Predict.",
        "dash_btn_chat":      "💬 Chat",
        "sugg_morning":       "🌅 Start your day with 5 min outdoors — it makes all the difference!",
        "sugg_noon":          "☀️ Take a real lunch break today.",
        "sugg_afternoon":     "💪 You've made great progress. Take a moment for yourself before tonight.",
        "sugg_evening":       "🌙 Get ready for a good night. Put your phone down 30 min before bed.",

        # ── Dates ───────────────────────────────────────────────────────────
        "days":   ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],
        "months": ["January","February","March","April","May","June",
                   "July","August","September","October","November","December"],
    },
}


def t(key: str, **kwargs) -> str:
    """Retourne la traduction de `key` dans la langue active (st.session_state.lang).

    Les kwargs sont passés à str.format() pour interpoler des variables.
    Ex : t("dash_hello", prenom="Alice") → "🏠 Bonjour Alice !"
    """
    lang = st.session_state.get("lang", "fr")
    locale = _STRINGS.get(lang, _STRINGS["fr"])
    value  = locale.get(key, _STRINGS["fr"].get(key, key))  # fallback FR → key
    if isinstance(value, str) and kwargs:
        try:
            value = value.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return value


def t_list(key: str) -> list[str]:
    """Retourne une liste traduite (ex : noms de jours ou de mois)."""
    lang   = st.session_state.get("lang", "fr")
    locale = _STRINGS.get(lang, _STRINGS["fr"])
    value  = locale.get(key, _STRINGS["fr"].get(key, []))
    return value if isinstance(value, list) else []
