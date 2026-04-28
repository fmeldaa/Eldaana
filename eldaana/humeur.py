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

HUMEURS = {
    "😴 Fatigué(e)":   "fatigue",
    "😊 Bien":          "bien",
    "🎉 Au top !":      "super",
    "😰 Stressé(e)":   "stress",
    "😢 Pas terrible": "triste",
    "😡 En colère":    "colere",
    "🤒 Pas en forme": "malade",
}

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
        "musique":   "R&B doux, pop mélancolique (pour sentir que tu n'es pas seul(e))",
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


def format_humeur_for_prompt(user_id: str) -> str:
    """Retourne l'humeur pour injection dans le system prompt."""
    humeur = load_humeur(user_id)
    if not humeur:
        return ""
    code  = humeur.get("code", "")
    label = humeur.get("label", "")
    sugg  = SUGGESTIONS_HUMEUR.get(code, {})
    conseil = sugg.get("conseil", "")
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
    humeur_actuelle = load_humeur(user_id)
    if humeur_actuelle:
        code  = humeur_actuelle["code"]
        label = humeur_actuelle["label"]
        sugg  = SUGGESTIONS_HUMEUR.get(code, {})

        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #fdf4ff, #f0f4ff);
            border: 1px solid #c084fc;
            border-radius: 16px;
            padding: 1rem 1.2rem;
            margin: 0.5rem 0;
        ">
            <p style="margin:0 0 0.3rem 0;font-weight:600;color:#7c3aed;">
                {sugg.get('titre', 'Humeur du jour')}
            </p>
            <p style="margin:0;font-size:0.9rem;color:#4b5563;">{label}</p>
        </div>
        """, unsafe_allow_html=True)

        if sugg.get("activites"):
            with st.expander("💡 Suggestions pour toi aujourd'hui"):
                for act in sugg["activites"]:
                    st.markdown(f"• {act}")
                if sugg.get("musique"):
                    st.markdown(f"🎵 **Musique** : {sugg['musique']}")

        if st.button("🔄 Changer mon humeur", key="change_humeur"):
            _clear_humeur(user_id)
            st.rerun()
        return code

    else:
        st.markdown("**Comment tu te sens aujourd'hui ?**")
        cols = st.columns(4)
        humeur_list = list(HUMEURS.items())
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
