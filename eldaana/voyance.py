"""
voyance.py — Module "Voyance & Prédictions" d'Eldaana.

Des prédictions fun et probabilistes basées sur le profil.
Toujours présentées comme des estimations ludiques, pas des vérités absolues.
"""

import streamlit as st
import random
from datetime import datetime, date


# ── Helpers d'affichage ────────────────────────────────────────────────────────

def _score_color(score: int) -> str:
    if score >= 70: return "#3B6D11"
    if score >= 45: return "#BA7517"
    return "#A32D2D"


def _show_score_bar(label: str, score: int, icon: str = ""):
    color = _score_color(score)
    st.markdown(f"""
    <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
                border-radius:12px;padding:10px 14px;margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
            <span style="font-size:0.85rem;color:#9ca3af;">{icon} {label}</span>
            <span style="font-size:1.2rem;font-weight:700;color:{color};">{score}</span>
        </div>
        <div style="height:6px;background:#374151;border-radius:3px;overflow:hidden;">
            <div style="width:{score}%;height:100%;background:{color};border-radius:3px;
                        transition:width 0.5s ease;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Prédictions statiques (fun) ───────────────────────────────────────────────

def _calcul_mariage(profile: dict) -> str:
    age    = int(profile.get("age") or 25)
    sit    = profile.get("situation_maritale", "")
    prenom = profile.get("prenom", "toi")

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
    if age < 22:   ans = random.randint(5, 10)
    elif age < 30: ans = random.randint(2, 6)
    elif age < 40: ans = random.randint(1, 4)
    else:          ans = random.randint(0, 3)
    annee = datetime.now().year + ans
    return (
        f"D'après ton profil et les statistiques de l'INSEE, "
        f"**{annee}** semble être une année favorable pour toi. "
        f"L'âge moyen du mariage en France est 33 ans pour les femmes, 35 ans pour les hommes. "
        f"Tu as le temps ! 🌸"
    )


def _calcul_carriere(profile: dict) -> str:
    profession = profile.get("profession", "ton domaine actuel")
    age        = int(profile.get("age") or 30)
    hobbies    = profile.get("hobbies", [])
    if age < 25:   timing = "dans les 2-3 prochaines années, au moment où tu trouveras ta voie"
    elif age < 35: timing = "d'ici 1 à 3 ans, une nouvelle opportunité devrait se présenter"
    else:          timing = "tu es peut-être à un tournant. Les personnes de ton profil envisagent souvent un pivot dans les 2 ans"
    passion = hobbies[0] if hobbies else "tes passions"
    return (
        f"En tant que **{profession}**, {timing}. "
        f"Les données montrent que les personnes passionnées de **{passion}** "
        f"ont tendance à réorienter leur carrière vers leurs centres d'intérêt. "
        f"💼 Ce n'est pas une certitude — mais si quelque chose te tiraille… écoute-le !"
    )


def _calcul_enfants(profile: dict) -> str:
    famille   = profile.get("famille", {})
    nb_actuel = int(famille.get("nb_enfants") or 0)
    age       = int(profile.get("age") or 28)
    if age > 45:
        return f"Avec tes {age} ans, la question est surtout celle des petits-enfants maintenant 😄"
    if nb_actuel > 0:
        extra = random.choice([0, 1]) if age < 38 else 0
        total = nb_actuel + extra
        return (f"Tu en as déjà {nb_actuel}. " + (
            f"Il y a environ 40% de chances que tu en aies {total} au final. Les familles françaises ont en moyenne 1,83 enfants."
            if extra == 1 else "Ton foyer semble complet ! Les étoiles confirment."))
    if age < 30: nb = random.choice([1, 2, 2, 3])
    else:        nb = random.choice([0, 1, 1, 2])
    return (
        f"Selon les tendances démographiques françaises et ton profil, "
        f"**{nb} enfant{'s' if nb > 1 else ''}** semble probable pour toi. "
        f"Mais rien n'est gravé dans le marbre — c'est ta vie ! 🍼"
    )


def _conseil_repas(profile: dict) -> str:
    alim  = profile.get("habitudes_alimentaires", "omnivore").lower()
    heure = datetime.now().hour
    repas_omnivore = [
        "Poulet rôti avec légumes de saison", "Pâtes à la bolognaise maison",
        "Saumon grillé avec riz et brocolis", "Omelette aux champignons et salade verte",
        "Curry de poulet avec naan", "Steak haché avec frites au four et salade",
        "Soupe de légumes et tartines", "Quiche lorraine et salade", "Risotto aux champignons",
    ]
    repas_vegeta = [
        "Curry de lentilles et riz basmati", "Gratin de légumes au gruyère",
        "Pâtes au pesto et parmesan", "Buddha bowl : quinoa, avocat, légumes rôtis",
        "Dal de lentilles corail et chapati", "Tarte aux légumes et ricotta",
    ]
    repas_vegan = [
        "Bol de Buddha au quinoa, pois chiches rôtis, tahini",
        "Curry de pois chiches à la noix de coco", "Soupe miso aux légumes et tofu soyeux",
        "Lentilles vertes à la française", "Wraps avocat, haricots noirs, salsa",
    ]
    if "vegan" in alim:       choix = random.choice(repas_vegan)
    elif "végétar" in alim:   choix = random.choice(repas_vegeta)
    else:                     choix = random.choice(repas_omnivore)
    moment = "ce soir" if heure >= 14 else "aujourd'hui à midi"
    return f"🍽️ **Eldaana suggère {moment}** : **{choix}**"


def _prediction_vacances(profile: dict) -> str:
    budget_mensuel = float(profile.get("budget_mensuel") or 0)
    hobbies = profile.get("hobbies", [])
    saison  = ["printemps", "été", "automne", "hiver"][(datetime.now().month - 1) // 3]
    dests_budget_moyen = [
        ("Portugal 🇵🇹", "culture, gastronomie, plage", "vol + hôtel ~400€"),
        ("Espagne 🇪🇸", "soleil, tapas, flamenco", "vol + hôtel ~350€"),
        ("Maroc 🇲🇦", "dépaysement, saveurs, désert", "vol + riad ~300€"),
        ("Italie 🇮🇹", "histoire, art, gastronomie", "vol + hôtel ~450€"),
    ]
    dests_budget_plus = [
        ("Grèce 🇬🇷", "îles paradisiaques, histoire", "vol + hôtel ~600€"),
        ("Japon 🇯🇵", "culture unique, gastronomie", "vol + hôtel ~1200€"),
        ("Canada 🇨🇦", "nature, grands espaces", "vol + hôtel ~1000€"),
    ]
    dests_nature = [
        ("Islande 🇮🇸", "aurores boréales, geysers", "vol + hôtel ~800€"),
        ("Bretagne 🏴", "côtes sauvages, crêpes", "voiture + gîte ~200€"),
    ]
    hobby_str = " ".join(hobbies).lower()
    if "nature" in hobby_str or "randonnée" in hobby_str:   pool = dests_nature
    elif budget_mensuel > 2000:                              pool = dests_budget_plus
    else:                                                    pool = dests_budget_moyen
    dest, desc, tarif = random.choice(pool)
    return (
        f"🌍 Pour tes prochaines vacances, les étoiles pointent vers **{dest}** !\n"
        f"*{desc}* — {tarif}.\nBasé sur tes goûts et la saison **{saison}** qui arrive."
    )


# ── Page principale ────────────────────────────────────────────────────────────

def show_voyance_page(profile: dict):
    """Page Voyance enrichie : scores prédictifs + prédictions existentielles IA + fun."""
    from tier_access import can_access, show_upgrade_prompt

    prenom = profile.get("prenom", "")
    uid    = profile.get("user_id", "")

    st.markdown("### 🔮 Voyance & Prédictions")
    st.caption("Prédictions probabilistes basées sur ton profil et tes données.")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — Scores du jour (Essentiel+)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("#### 📊 Tes scores du jour")

    if not can_access("voyance_daily_scores", uid):
        show_upgrade_prompt("Scores prédictifs quotidiens (humeur, énergie, stress, budget)", "essential")
    else:
        # Cache : ne calculer qu'une fois par jour
        cache_key = f"scores_{uid}_{date.today().isoformat()}"
        if cache_key not in st.session_state:
            if st.button("🔮 Calculer mes scores du jour", use_container_width=True,
                         key="btn_compute_scores"):
                from voyance_engine import compute_scores
                weather = st.session_state.get("weather") or {}
                with st.spinner("Eldaana analyse tes données..."):
                    st.session_state[cache_key] = compute_scores(
                        profile=profile,
                        weather=weather,
                    )
                st.rerun()
        else:
            scores     = st.session_state[cache_key]
            score_jour = scores.get("score_journee", 65)
            color_jour = _score_color(score_jour)

            # Score global
            st.markdown(f"""
            <div style="text-align:center;padding:0.8rem 0 1rem 0;">
                <p style="font-size:3rem;font-weight:800;color:{color_jour};margin:0;
                           line-height:1;">{score_jour}</p>
                <p style="color:#9ca3af;font-size:0.85rem;margin:4px 0 0 0;">
                    Score de ta journée · sur 100
                </p>
            </div>
            """, unsafe_allow_html=True)

            # 4 scores détaillés
            col1, col2 = st.columns(2)
            with col1:
                _show_score_bar("Humeur",  scores.get("score_humeur",  65), "😊")
                _show_score_bar("Énergie", scores.get("score_energie", 60), "⚡")
            with col2:
                _show_score_bar("Stress",  scores.get("score_stress",  50), "🧘")
                _show_score_bar("Budget",  scores.get("score_budget",  70), "💰")

            # Conseil du jour
            if conseil := scores.get("conseil_jour"):
                st.info(f"💡 **Conseil d'Eldaana :** {conseil}")

            # Alerte principale
            if alerte := scores.get("alerte_principale"):
                st.warning(f"⚠️ {alerte}")

            # Facteurs détaillés (Premium)
            if can_access("voyance_factors_detail", uid):
                pos = scores.get("facteurs_positifs", [])
                neg = scores.get("facteurs_negatifs", [])
                if pos or neg:
                    st.markdown("---")
                    col_pos, col_neg = st.columns(2)
                    with col_pos:
                        st.markdown("**✅ Points positifs**")
                        for f in pos: st.markdown(f"• {f}")
                    with col_neg:
                        st.markdown("**⚠️ Points de vigilance**")
                        for f in neg: st.markdown(f"• {f}")
            else:
                show_upgrade_prompt("Facteurs détaillés & forecast 7 jours", "premium")

            # Recalculer
            if st.button("🔄 Recalculer", key="btn_recompute"):
                st.session_state.pop(cache_key, None)
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — Question existentielle IA (tous les tiers)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("#### 🔮 Pose ta question à Eldaana")
    st.markdown("*Mariage, carrière, avenir… Eldaana calcule ta probabilité.*")

    # Exemples rapides
    examples = [
        "Quand vais-je trouver l'amour ?",
        "Vais-je changer de travail cette année ?",
        "Vais-je déménager bientôt ?",
        "Est-ce que mon projet va réussir ?",
    ]
    cols = st.columns(2)
    for i, ex in enumerate(examples):
        with cols[i % 2]:
            if st.button(ex, key=f"ex_{i}", use_container_width=True):
                st.session_state["voyance_question"] = ex
                st.session_state["voyance_input"] = ex   # met à jour le widget texte
                st.rerun()

    question = st.text_input(
        "Ou pose ta propre question :",
        value=st.session_state.get("voyance_question", ""),
        placeholder="Quand vais-je… ? Est-ce que… ?",
        key="voyance_input",
    )

    if question and st.button("🔮 Calculer ma prédiction", type="primary",
                               use_container_width=True, key="btn_predict"):
        from voyance_engine import get_existential_prediction
        with st.spinner("Eldaana consulte les astres… (et les données 😉)"):
            result = get_existential_prediction(question, profile)
        st.session_state["voyance_result"] = result
        st.session_state["voyance_question"] = question

    if result := st.session_state.get("voyance_result"):
        prob  = result.get("probability", 50)
        color = _score_color(prob)
        tf    = result.get("timeframe") or ""
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#fdf4ff,#ede9fe);
                    border:1.5px solid #c084fc;border-radius:20px;
                    padding:1.5rem;text-align:center;margin:1rem 0;">
            <p style="font-size:3rem;font-weight:800;color:{color};margin:0;">{prob}%</p>
            {"<p style='font-size:0.85rem;color:#7c3aed;font-weight:600;margin:4px 0;'>" + tf + "</p>" if tf else ""}
            <p style="color:#374151;font-size:0.95rem;margin:0.8rem 0 0.5rem 0;">
                {result.get('answer', '')}
            </p>
            <p style="color:#9ca3af;font-size:0.75rem;font-style:italic;margin:0;">
                {result.get('disclaimer', '')}
            </p>
        </div>
        """, unsafe_allow_html=True)
        factors = result.get("factors", [])
        if factors:
            st.markdown("**Facteurs pris en compte :**")
            for f in factors:
                st.markdown(f"• {f}")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — Prédictions fun (tous les tiers)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("#### ✨ Prédictions du moment")

    # Repas
    st.markdown("**🍽️ Que manger ?**")
    if st.button("✨ Suggère-moi un repas", use_container_width=True, key="btn_repas"):
        st.session_state["repas_suggestion"] = _conseil_repas(profile)
    if "repas_suggestion" in st.session_state:
        st.success(st.session_state["repas_suggestion"])
        if st.button("🔄 Autre idée", key="autre_repas"):
            st.session_state["repas_suggestion"] = _conseil_repas(profile)
            st.rerun()

    # Vacances
    st.markdown("**✈️ Où partir en vacances ?**")
    if st.button("🌍 Quelle est ma destination idéale ?", use_container_width=True, key="btn_vac"):
        st.session_state["vacances_pred"] = _prediction_vacances(profile)
    if "vacances_pred" in st.session_state:
        st.info(st.session_state["vacances_pred"])

    # Mariage
    st.markdown("**💍 Quand vais-je me marier ?**")
    if st.button("💫 Révèle-moi mon avenir amoureux", use_container_width=True, key="btn_mar"):
        st.session_state["mariage_pred"] = _calcul_mariage(profile)
    if "mariage_pred" in st.session_state:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#fdf4ff,#fce7f3);
                    border:1.5px solid #f9a8d4;border-radius:16px;
                    padding:1rem 1.2rem;margin:0.5rem 0;">
            <p style="margin:0;color:#7c3aed;">🔮 {st.session_state['mariage_pred']}</p>
        </div>
        """, unsafe_allow_html=True)

    # Carrière
    st.markdown("**💼 Vais-je changer de travail ?**")
    if st.button("🚀 Lis mon avenir professionnel", use_container_width=True, key="btn_carr"):
        st.session_state["carriere_pred"] = _calcul_carriere(profile)
    if "carriere_pred" in st.session_state:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#eff6ff,#f0fdf4);
                    border:1.5px solid #86efac;border-radius:16px;
                    padding:1rem 1.2rem;margin:0.5rem 0;">
            <p style="margin:0;color:#374151;">💼 {st.session_state['carriere_pred']}</p>
        </div>
        """, unsafe_allow_html=True)

    # Enfants
    st.markdown("**👶 Combien d'enfants aurai-je ?**")
    if st.button("🍼 Prédit ma famille idéale", use_container_width=True, key="btn_enf"):
        st.session_state["enfants_pred"] = _calcul_enfants(profile)
    if "enfants_pred" in st.session_state:
        st.info(f"👶 {st.session_state['enfants_pred']}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("⚠️ Ces prédictions sont basées sur des statistiques et des probabilités — jamais des certitudes.")
