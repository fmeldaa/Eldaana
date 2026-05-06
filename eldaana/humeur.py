"""
humeur.py — Gestion de l'humeur quotidienne d'Eldaana.

Fonctionnalités :
- Sélecteur d'humeur quotidien
- Suggestions adaptées à l'humeur (musique, activités, blagues)
- Injection dans le system prompt pour personnalisation
"""

import streamlit as st
from datetime import datetime
from storage import db_load, db_save

# ── Libellés d'humeur (clé = emoji + label affiché, valeur = code neutre) ────
HUMEURS = {
    "😴 Fatigué(e)":   "fatigue",
    "😊 Bien":          "bien",
    "🎉 Au top !":      "super",
    "😰 Stressé(e)":   "stress",
    "😢 Pas terrible": "triste",
    "😡 En colère":    "colere",
    "🤒 Pas en forme": "malade",
}

HUMEURS_EN = {
    "😴 Tired":        "fatigue",
    "😊 Good":         "bien",
    "🎉 Amazing!":     "super",
    "😰 Stressed":     "stress",
    "😢 Not great":    "triste",
    "😡 Angry":        "colere",
    "🤒 Unwell":       "malade",
}

# ── Suggestions selon humeur ─────────────────────────────────────────────────
SUGGESTIONS_HUMEUR = {
    "fatigue": {
        "titre":     "Tu as besoin de te recharger 🔋",
        "activites": ["Une courte sieste de 20 min", "Un bain chaud ou une douche relaxante",
                      "Une série légère en mode canapé", "Quelques étirements doux"],
        "musique":   "lofi hip-hop, musique douce, nature sounds",
        "conseil":   "Écoute ton corps. Même une petite pause fait une grande différence.",
    },
    "bien": {
        "titre":     "Belle journée en perspective 🌸",
        "activites": ["Une promenade en plein air", "Appeler un ami proche",
                      "Cuisiner quelque chose de bon", "Avancer sur un projet qui te tient à cœur"],
        "musique":   "pop positive, acoustic, feel-good",
        "conseil":   "Tu es dans un bon état d'esprit. Profite-en pour faire quelque chose que tu aimes.",
    },
    "super": {
        "titre":     "Tu es en feu aujourd'hui ! 🔥",
        "activites": ["Sport intensif ou danse", "Attaquer ce projet que tu remettais à plus tard",
                      "Sortir et explorer quelque chose de nouveau", "Inviter des amis pour une soirée"],
        "musique":   "electro, rap, pop énergique",
        "conseil":   "Ton énergie est contagieuse ! Partage-la avec ceux qui t'entourent.",
    },
    "stress": {
        "titre":     "Respire. Ça va aller. 💜",
        "activites": ["5 minutes de respiration profonde (4-7-8)", "Une courte marche dehors",
                      "Écrire ce qui te stresse sur papier", "Thé chaud + musique douce"],
        "musique":   "méditation, classique doux, ambient",
        "conseil":   "Le stress passe toujours. Un problème à la fois.",
    },
    "triste": {
        "titre":     "Je suis là pour toi 💙",
        "activites": ["Regarder un film ou une série qui te fait sourire",
                      "Appeler quelqu'un qui compte pour toi",
                      "Te préparer ton repas ou dessert préféré",
                      "Une petite sortie en plein air, même courte"],
        "musique":   "R&B doux, pop mélancolique",
        "conseil":   "Ce que tu ressens est valide. Tu n'as pas besoin de faire semblant d'aller bien.",
    },
    "colere": {
        "titre":     "Laisse sortir cette énergie 💪",
        "activites": ["Sport ou boxe (même simulée)", "Écrire une lettre que tu n'enverras jamais",
                      "Un jeu vidéo pour décompresser", "Parler à quelqu'un de confiance"],
        "musique":   "rock, metal, rap puissant",
        "conseil":   "La colère est une émotion normale. L'important c'est comment on la canalise.",
    },
    "malade": {
        "titre":     "Prends soin de toi 🤗",
        "activites": ["Boire beaucoup d'eau et de tisanes", "Se reposer sans culpabiliser",
                      "Un film ou podcast en fond sonore", "Consulter si ça dure plus de 2-3 jours"],
        "musique":   "ambiance calme, podcasts légers",
        "conseil":   "Ton corps a besoin de repos. Les tâches peuvent attendre.",
    },
}

SUGGESTIONS_HUMEUR_EN = {
    "fatigue": {
        "titre":     "You need to recharge 🔋",
        "activites": ["A short 20-min nap", "A warm bath or relaxing shower",
                      "A light series in couch mode", "Some gentle stretches"],
        "musique":   "lofi hip-hop, soft music, nature sounds",
        "conseil":   "Listen to your body. Even a short break makes a big difference.",
    },
    "bien": {
        "titre":     "A beautiful day ahead 🌸",
        "activites": ["An outdoor walk", "Call a close friend",
                      "Cook something delicious", "Make progress on a project you care about"],
        "musique":   "positive pop, acoustic, feel-good",
        "conseil":   "You're in a great headspace. Use it to do something you love.",
    },
    "super": {
        "titre":     "You're on fire today! 🔥",
        "activites": ["Intense workout or dancing", "Tackle that project you've been putting off",
                      "Go out and explore something new", "Invite friends over for a night out"],
        "musique":   "electro, rap, energetic pop",
        "conseil":   "Your energy is contagious! Share it with the people around you.",
    },
    "stress": {
        "titre":     "Breathe. It'll be okay. 💜",
        "activites": ["5 minutes of deep breathing (4-7-8)", "A short walk outside",
                      "Write down what's stressing you", "Hot tea + soft music"],
        "musique":   "meditation, gentle classical, ambient",
        "conseil":   "Stress always passes. One problem at a time.",
    },
    "triste": {
        "titre":     "I'm here for you 💙",
        "activites": ["Watch a film or series that makes you smile",
                      "Call someone who matters to you",
                      "Prepare your favourite meal or dessert",
                      "A short trip outside, even a brief one"],
        "musique":   "soft R&B, melancholic pop",
        "conseil":   "What you feel is valid. You don't need to pretend to be okay.",
    },
    "colere": {
        "titre":     "Release that energy 💪",
        "activites": ["Sport or boxing (even shadowboxing)", "Write a letter you'll never send",
                      "A video game to decompress", "Talk to someone you trust"],
        "musique":   "rock, metal, powerful rap",
        "conseil":   "Anger is a normal emotion. What matters is how you channel it.",
    },
    "malade": {
        "titre":     "Take care of yourself 🤗",
        "activites": ["Drink plenty of water and herbal tea", "Rest without guilt",
                      "A film or podcast in the background", "See a doctor if it lasts more than 2-3 days"],
        "musique":   "calm atmosphere, light podcasts",
        "conseil":   "Your body needs rest. Tasks can wait.",
    },
}


def load_humeur(user_id: str) -> dict:
    """Charge l'humeur du jour."""
    profile = db_load(user_id)
    if not profile:
        return {}
    today = datetime.now().strftime("%Y-%m-%d")
    humeur_data = profile.get("humeur_data", {})
    # Retourner seulement si c'est aujourd'hui
    if humeur_data.get("date") == today:
        return humeur_data
    return {}


def save_humeur(user_id: str, code: str, label: str):
    """Sauvegarde l'humeur du jour."""
    profile = db_load(user_id)
    if profile:
        profile["humeur_data"] = {
            "date":  datetime.now().strftime("%Y-%m-%d"),
            "code":  code,
            "label": label,
        }
        db_save(profile)


def get_humeur_stats(user_id: str) -> dict:
    """
    Retourne les stats d'humeur pour le moteur de scoring voyance.
    Format compatible avec voyance_engine.build_data_block().
    """
    profile = db_load(user_id)
    if not profile:
        return {}

    today   = datetime.now().strftime("%Y-%m-%d")
    humeur_data = profile.get("humeur_data", {})

    # Humeur du jour (convertie en score 1-10)
    score_map = {
        "super":   9,
        "bien":    7,
        "fatigue": 5,
        "stress":  4,
        "triste":  3,
        "colere":  3,
        "malade":  3,
    }
    today_score = None
    if humeur_data.get("date") == today:
        today_score = score_map.get(humeur_data.get("code"), 5)

    # Historique des 7 derniers jours dans humeur_history
    history = profile.get("humeur_history", [])  # [{date, code, label}, ...]
    recent  = [h for h in history if h.get("date", "") >= (
        datetime.now().strftime("%Y-%m-") + "01"  # approximation : même mois
    )][-7:]

    scores_7d = [score_map.get(h.get("code"), 5) for h in recent]
    avg_7d    = sum(scores_7d) / len(scores_7d) if scores_7d else None

    # Tendance : compare le score d'aujourd'hui à la moyenne
    trend = None
    if today_score is not None and avg_7d is not None:
        diff = today_score - avg_7d
        if diff > 1:
            trend = "hausse"
        elif diff < -1:
            trend = "baisse"
        else:
            trend = "stable"

    result = {}
    if today_score is not None:
        result["today"] = today_score
    if avg_7d is not None:
        result["average_7d"] = avg_7d
    if trend:
        result["trend"] = trend
    return result


def _get_lang() -> str:
    """Retourne la langue active depuis la session Streamlit."""
    try:
        return st.session_state.get("lang", "fr")
    except Exception:
        return "fr"


def _sugg_dict(code: str) -> dict:
    """Retourne les suggestions dans la langue active."""
    lang = _get_lang()
    bank = SUGGESTIONS_HUMEUR_EN if lang == "en" else SUGGESTIONS_HUMEUR
    return bank.get(code, {})


def format_humeur_for_prompt(user_id: str) -> str:
    """Retourne l'humeur pour injection dans le system prompt (bilingue)."""
    humeur = load_humeur(user_id)
    if not humeur:
        return ""
    lang    = _get_lang()
    code    = humeur.get("code", "")
    label   = humeur.get("label", "")
    sugg    = _sugg_dict(code)
    conseil = sugg.get("conseil", "")
    if lang == "en":
        return (
            f"\n\n[TODAY'S MOOD]\n"
            f"The user feels: {label}\n"
            f"Adapt your tone accordingly. {conseil}\n"
            f"[END MOOD]"
        )
    return (
        f"\n\n[HUMEUR DU JOUR]\n"
        f"L'utilisateur se sent : {label}\n"
        f"Adapte ton ton en conséquence. {conseil}\n"
        f"[FIN HUMEUR]"
    )


def show_humeur_widget(user_id: str) -> str | None:
    """
    Affiche le sélecteur d'humeur dans l'interface.
    Retourne le code humeur sélectionné ou None.
    """
    from translations import t as _t_h
    lang = _get_lang()

    humeur_actuelle = load_humeur(user_id)
    if humeur_actuelle:
        code  = humeur_actuelle["code"]
        label = humeur_actuelle["label"]
        sugg  = _sugg_dict(code)

        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #fdf4ff, #f0f4ff);
            border: 1px solid #c084fc;
            border-radius: 16px;
            padding: 1rem 1.2rem;
            margin: 0.5rem 0;
        ">
            <p style="margin:0 0 0.3rem 0;font-weight:600;color:#7c3aed;">
                {sugg.get('titre', _t_h('humeur_label'))}
            </p>
            <p style="margin:0;font-size:0.9rem;color:#4b5563;">{label}</p>
        </div>
        """, unsafe_allow_html=True)

        if sugg.get("activites"):
            with st.expander(_t_h("humeur_suggestions")):
                for act in sugg["activites"]:
                    st.markdown(f"• {act}")
                if sugg.get("musique"):
                    st.markdown(f"🎵 **{_t_h('humeur_music')}** : {sugg['musique']}")

        if st.button(_t_h("humeur_change"), key="change_humeur"):
            _clear_humeur(user_id)
            st.rerun()
        return code

    else:
        st.markdown(_t_h("humeur_today"))
        humeur_map = HUMEURS_EN if lang == "en" else HUMEURS
        cols = st.columns(4)
        humeur_list = list(humeur_map.items())
        for i, (label, code) in enumerate(humeur_list):
            col = cols[i % 4]
            with col:
                if st.button(label, key=f"humeur_{code}", use_container_width=True):
                    save_humeur(user_id, code, label)
                    st.rerun()
        return None


def _clear_humeur(user_id: str):
    """Efface l'humeur du jour."""
    profile = db_load(user_id)
    if profile:
        profile["humeur_data"] = {}
        db_save(profile)
