"""
voyance.py — Module "Voyance & Prédictions" d'Eldaana.

Des prédictions fun et probabilistes basées sur le profil.
Toujours présentées comme des estimations ludiques, pas des vérités absolues.
"""

import streamlit as st
import random
from datetime import datetime, timedelta


def _calcul_mariage(profile: dict) -> str:
    """Prédit quand l'utilisateur va se marier (fun)."""
    age     = int(profile.get("age") or 25)
    sit     = profile.get("situation_maritale", "")
    prenom  = profile.get("prenom", "toi")

    if "Marié" in sit or "Pacsé" in sit:
        return f"Tu es déjà marié(e), {prenom} ! Eldaana prédit une belle durée encore devant vous 💑"

    if "En couple" in sit:
        delai = random.randint(1, 4)
        annee = datetime.now().year + delai
        return (
            f"Tu es en couple… les étoiles indiquent **{annee}** comme année prometteuse. "
            f"Statistiquement, les couples qui durent 2+ ans ont 68% de chances de franchir le pas. "
            f"Mais c'est toi qui décides ! 💍"
        )

    if age < 22:
        ans = random.randint(5, 10)
    elif age < 30:
        ans = random.randint(2, 6)
    elif age < 40:
        ans = random.randint(1, 4)
    else:
        ans = random.randint(0, 3)

    annee = datetime.now().year + ans
    return (
        f"D'après ton profil et les statistiques de l'INSEE, "
        f"**{annee}** semble être une année favorable pour toi. "
        f"L'âge moyen du mariage en France est 33 ans pour les femmes, 35 ans pour les hommes. "
        f"Tu as le temps ! 🌸"
    )


def _calcul_carriere(profile: dict) -> str:
    """Prédit un changement de carrière."""
    profession = profile.get("profession", "ton domaine actuel")
    age        = int(profile.get("age") or 30)
    hobbies    = profile.get("hobbies", [])

    if age < 25:
        timing = "dans les 2-3 prochaines années, au moment où tu trouveras ta voie"
    elif age < 35:
        timing = "d'ici 1 à 3 ans, une nouvelle opportunité devrait se présenter"
    else:
        timing = "tu es peut-être à un tournant. Les personnes de ton profil envisagent souvent un pivot dans les 2 ans"

    passion = hobbies[0] if hobbies else "tes passions"
    return (
        f"En tant que **{profession}**, {timing}. "
        f"Les données montrent que les personnes passionnées de **{passion}** "
        f"ont tendance à réorienter leur carrière vers leurs centres d'intérêt. "
        f"💼 Ce n'est pas une certitude — mais si quelque chose te tiraille… écoute-le !"
    )


def _calcul_enfants(profile: dict) -> str:
    """Prédit combien d'enfants l'utilisateur aura."""
    famille = profile.get("famille", {})
    nb_actuel = int(famille.get("nb_enfants") or 0)
    age = int(profile.get("age") or 28)
    sexe = profile.get("sexe", "").lower()

    if age > 45:
        return f"Avec tes {age} ans, la question est surtout celle des petits-enfants maintenant 😄"

    if nb_actuel > 0:
        extra = random.choice([0, 1]) if age < 38 else 0
        total = nb_actuel + extra
        msg = f"Tu en as déjà {nb_actuel}. " + (
            f"Il y a environ 40% de chances que tu en aies {total} au final. Les familles françaises ont en moyenne 1,83 enfants."
            if extra == 1 else
            "Ton foyer semble complet ! Les étoiles confirment."
        )
        return msg

    if age < 30:
        nb = random.choice([1, 2, 2, 3])
        return (
            f"Selon les tendances démographiques françaises et ton profil, "
            f"**{nb} enfant{'s' if nb > 1 else ''}** semble probable pour toi. "
            f"Mais rien n'est gravé dans le marbre — c'est ta vie ! 🍼"
        )
    else:
        nb = random.choice([0, 1, 1, 2])
        return (
            f"À {age} ans, les statistiques indiquent **{nb} enfant{'s' if nb > 1 else ''}** en moyenne "
            f"pour les personnes de ton profil. Mais les surprises arrivent aussi ! 🌟"
        )


def _conseil_repas(profile: dict) -> str:
    """Suggestion de repas pour ce soir."""
    alim  = profile.get("habitudes_alimentaires", "omnivore").lower()
    heure = datetime.now().hour

    repas_omnivore = [
        "Poulet rôti avec légumes de saison", "Pâtes à la bolognaise maison",
        "Saumon grillé avec riz et brocolis", "Omelette aux champignons et salade verte",
        "Curry de poulet avec naan", "Steak haché avec frites au four et salade",
        "Soupe de légumes et tartines", "Pizza maison aux légumes et mozzarella",
        "Quiche lorraine et salade", "Risotto aux champignons",
    ]
    repas_vegeta = [
        "Curry de lentilles et riz basmati", "Gratin de légumes au gruyère",
        "Soupe thaïe aux nouilles et tofu", "Pâtes au pesto et parmesan",
        "Buddha bowl : quinoa, avocat, légumes rôtis", "Frittata aux légumes du frigo",
        "Dal de lentilles corail et chapati", "Salade composée aux œufs durs et feta",
        "Tarte aux légumes et ricotta", "Risotto aux petits pois et menthe",
    ]
    repas_vegan = [
        "Bol de Buddha au quinoa, pois chiches rôtis, tahini",
        "Curry de pois chiches à la noix de coco", "Tacos au jackfruit épicé",
        "Soupe miso aux légumes et tofu soyeux", "Soba noodles sautées aux légumes",
        "Houmous, pita et légumes grillés", "Lentilles vertes à la française",
        "Riz frit aux légumes sauce soja", "Gnocchis à la sauce tomate et basilic",
        "Wraps avocat, haricots noirs, salsa",
    ]

    if "vegan" in alim:
        choix = random.choice(repas_vegan)
    elif "végétar" in alim:
        choix = random.choice(repas_vegeta)
    else:
        choix = random.choice(repas_omnivore)

    moment = "ce soir" if heure >= 14 else "aujourd'hui à midi"
    return f"🍽️ **Eldaana suggère {moment}** : **{choix}**"


def _prediction_vacances(profile: dict) -> str:
    """Suggère une destination vacances."""
    budget_mensuel = float(profile.get("budget_mensuel") or 0)
    hobbies = profile.get("hobbies", [])
    saison  = ["printemps", "été", "automne", "hiver"][(datetime.now().month - 1) // 3]

    dests_budget_moyen = [
        ("Portugal 🇵🇹", "culture, gastronomie, plage", "vol + hôtel ~400€"),
        ("Espagne 🇪🇸",  "soleil, tapas, flamenco",    "vol + hôtel ~350€"),
        ("Maroc 🇲🇦",    "dépaysement, saveurs, désert", "vol + riad ~300€"),
        ("Italie 🇮🇹",   "histoire, art, gastronomie", "vol + hôtel ~450€"),
    ]
    dests_budget_plus = [
        ("Grèce 🇬🇷",    "îles paradisiaques, histoire", "vol + hôtel ~600€"),
        ("Japon 🇯🇵",    "culture unique, gastronomie",   "vol + hôtel ~1200€"),
        ("Canada 🇨🇦",   "nature, grands espaces",        "vol + hôtel ~1000€"),
    ]
    dests_nature = [
        ("Islande 🇮🇸",  "aurores boréales, geysers",    "vol + hôtel ~800€"),
        ("Nouvelle-Zélande 🇳🇿", "nature sauvage",       "vol + hôtel ~1500€"),
        ("Bretagne 🏴",  "côtes sauvages, crêpes",        "voiture + gîte ~200€"),
    ]

    hobby_str = " ".join(hobbies).lower()
    if "nature" in hobby_str or "randonnée" in hobby_str or "camping" in hobby_str:
        pool = dests_nature
    elif budget_mensuel > 2000:
        pool = dests_budget_plus
    else:
        pool = dests_budget_moyen

    dest, desc, tarif = random.choice(pool)
    return (
        f"🌍 Pour tes prochaines vacances, les étoiles pointent vers **{dest}** !\n"
        f"*{desc}* — {tarif}.\n"
        f"Basé sur tes goûts et la saison **{saison}** qui arrive."
    )


def _fun_question(profile: dict, question: str) -> str:
    """Réponse générique fun pour les questions de voyance."""
    prenom = profile.get("prenom", "toi")
    reponses = [
        f"Les astres sont un peu brumeux aujourd'hui, mais je sens quelque chose de positif pour **{prenom}** dans les semaines à venir 🌟",
        f"Ma boule de cristal indique... suspense... que tu es sur la bonne voie ! Continue comme ça 🔮",
        f"D'après mon algorithme mystique (et quelques données statistiques), je dirais : **bientôt** ✨",
        f"L'univers conspire en ta faveur, **{prenom}**. Les signes sont là — il faut juste les voir 🌙",
    ]
    return random.choice(reponses)


def show_voyance_page(profile: dict):
    """Page 'Voyance' dans Streamlit."""
    prenom = profile.get("prenom", "")

    st.markdown("### 🔮 Prédictions & Voyance")
    st.caption("Des estimations fun basées sur ton profil — pas des vérités absolues ! 😄")

    st.info(
        "✨ **Eldaana est une IA, pas une vraie voyante** — mais en croisant les données de ton profil "
        "avec des statistiques réelles, elle peut te donner des projections probabilistes. "
        "Prends ça comme un jeu !"
    )

    # ── Suggestion repas ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🍽️ Que manger ?")
    if st.button("✨ Suggère-moi un repas", use_container_width=True):
        st.session_state["repas_suggestion"] = _conseil_repas(profile)
    if "repas_suggestion" in st.session_state:
        st.success(st.session_state["repas_suggestion"])
        if st.button("🔄 Autre idée", key="autre_repas"):
            st.session_state["repas_suggestion"] = _conseil_repas(profile)
            st.rerun()

    # ── Vacances ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### ✈️ Où partir en vacances ?")
    if st.button("🌍 Quelle est ma destination idéale ?", use_container_width=True):
        st.session_state["vacances_pred"] = _prediction_vacances(profile)
    if "vacances_pred" in st.session_state:
        st.info(st.session_state["vacances_pred"])

    # ── Mariage ─────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 💍 Quand vais-je me marier ?")
    if st.button("💫 Révèle-moi mon avenir amoureux", use_container_width=True):
        st.session_state["mariage_pred"] = _calcul_mariage(profile)
    if "mariage_pred" in st.session_state:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#fdf4ff,#fce7f3);
                    border:1.5px solid #f9a8d4;border-radius:16px;
                    padding:1rem 1.2rem;margin:0.5rem 0;">
            <p style="margin:0;color:#7c3aed;">🔮 {st.session_state['mariage_pred']}</p>
        </div>
        """, unsafe_allow_html=True)

    # ── Carrière ─────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 💼 Vais-je changer de travail ?")
    if st.button("🚀 Lis mon avenir professionnel", use_container_width=True):
        st.session_state["carriere_pred"] = _calcul_carriere(profile)
    if "carriere_pred" in st.session_state:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#eff6ff,#f0fdf4);
                    border:1.5px solid #86efac;border-radius:16px;
                    padding:1rem 1.2rem;margin:0.5rem 0;">
            <p style="margin:0;color:#374151;">💼 {st.session_state['carriere_pred']}</p>
        </div>
        """, unsafe_allow_html=True)

    # ── Enfants ─────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 👶 Combien d'enfants aurai-je ?")
    if st.button("🍼 Prédit ma famille idéale", use_container_width=True):
        st.session_state["enfants_pred"] = _calcul_enfants(profile)
    if "enfants_pred" in st.session_state:
        st.info(f"👶 {st.session_state['enfants_pred']}")

    # ── Question libre ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### ❓ Pose ta propre question")
    q = st.text_input("Ta question à Eldaana :", placeholder="Ex: Vais-je être riche ? Quand trouverai-je l'amour ?")
    if st.button("🔮 Consulter les étoiles", use_container_width=True) and q.strip():
        st.session_state["question_libre"] = _fun_question(profile, q)
    if "question_libre" in st.session_state:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#1A0A2E,#2D1045);
                    border-radius:16px;padding:1rem 1.2rem;margin:0.5rem 0;">
            <p style="margin:0;color:#F0E6FF;font-style:italic;">
                🔮 {st.session_state['question_libre']}
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("⚠️ Ces prédictions sont basées sur des statistiques et des probabilités — jamais des certitudes. Eldaana ne remplace pas ta propre intuition.")
