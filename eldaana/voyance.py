"""
voyance.py — Module "Voyance & Prédictions" d'Eldaana.

Des prédictions fun et probabilistes basées sur le profil.
Toujours présentées comme des estimations ludiques, pas des vérités absolues.
"""

import streamlit as st
import random
from datetime import datetime, date
from translations import t as _t, t_list as _tl


def _lang() -> str:
    try:
        import streamlit as _st
        return _st.session_state.get("lang", "fr")
    except Exception:
        return "fr"


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
    lang   = _lang()

    if "Marié" in sit or "Pacsé" in sit or "Married" in sit or "Civil" in sit:
        if lang == "en":
            return f"You're already married, {prenom}! Eldaana predicts many more beautiful years ahead 💑"
        return f"Tu es déjà marié(e), {prenom} ! Eldaana prédit une belle durée encore devant vous 💑"

    if "En couple" in sit or "In a relationship" in sit:
        delai = random.randint(1, 4)
        annee = datetime.now().year + delai
        if lang == "en":
            return (
                f"You're in a relationship… the stars point to **{annee}** as a promising year. "
                f"Statistically, couples lasting 2+ years have a 68% chance of taking the next step. "
                f"But it's your choice! 💍"
            )
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

    if lang == "en":
        return (
            f"Based on your profile and demographic statistics, "
            f"**{annee}** looks like a favourable year for you. "
            f"The average marriage age in the UK is 32 for women and 34 for men. "
            f"You have time! 🌸"
        )
    return (
        f"D'après ton profil et les statistiques de l'INSEE, "
        f"**{annee}** semble être une année favorable pour toi. "
        f"L'âge moyen du mariage en France est 33 ans pour les femmes, 35 ans pour les hommes. "
        f"Tu as le temps ! 🌸"
    )


def _calcul_carriere(profile: dict) -> str:
    profession = profile.get("profession", "ton domaine actuel" if _lang() == "fr" else "your current field")
    age        = int(profile.get("age") or 30)
    hobbies    = profile.get("hobbies", [])
    lang       = _lang()

    if lang == "en":
        if age < 25:   timing = "in the next 2-3 years, as you find your path"
        elif age < 35: timing = "within 1-3 years, a new opportunity should arise"
        else:          timing = "you may be at a turning point. People with your profile often consider a pivot within 2 years"
        passion = hobbies[0] if hobbies else "your passions"
        return (
            f"As a **{profession}**, {timing}. "
            f"Data shows that people passionate about **{passion}** tend to steer their career towards their interests. "
            f"💼 No certainties — but if something is pulling at you… listen to it!"
        )

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
    lang      = _lang()

    if lang == "en":
        if age > 45:
            return f"At {age}, the question is more about grandchildren now 😄"
        if nb_actuel > 0:
            extra = random.choice([0, 1]) if age < 38 else 0
            total = nb_actuel + extra
            if extra == 1:
                return (f"You already have {nb_actuel}. "
                        f"There's roughly a 40% chance you'll have {total} in total. "
                        f"Average family size in the UK is 1.89 children.")
            return f"You already have {nb_actuel}. Your family seems complete! The stars confirm."
        if age < 30: nb = random.choice([1, 2, 2, 3])
        else:        nb = random.choice([0, 1, 1, 2])
        return (
            f"Based on demographic trends and your profile, "
            f"**{nb} child{'ren' if nb > 1 else ''}** seems likely for you. "
            f"But nothing is set in stone — it's your life! 🍼"
        )

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
    lang  = _lang()

    if lang == "en":
        repas_omnivore_en = [
            "Roast chicken with seasonal vegetables", "Homemade spaghetti bolognese",
            "Grilled salmon with rice and broccoli", "Mushroom omelette and green salad",
            "Chicken curry with naan", "Beef burger with oven fries and salad",
            "Vegetable soup and toast", "Quiche and salad", "Mushroom risotto",
        ]
        repas_vegeta_en = [
            "Lentil curry and basmati rice", "Vegetable gratin with cheese",
            "Pasta with pesto and parmesan", "Buddha bowl: quinoa, avocado, roasted vegetables",
            "Red lentil dal and chapati", "Vegetable and ricotta tart",
        ]
        repas_vegan_en = [
            "Buddha bowl: quinoa, roasted chickpeas, tahini",
            "Coconut chickpea curry", "Miso soup with vegetables and silken tofu",
            "French green lentils", "Avocado, black bean and salsa wraps",
        ]
        if "vegan" in alim:     choix = random.choice(repas_vegan_en)
        elif "végétar" in alim or "vegetar" in alim: choix = random.choice(repas_vegeta_en)
        else:                   choix = random.choice(repas_omnivore_en)
        moment = _t("voy_meal_moment_dinner") if heure >= 14 else _t("voy_meal_moment_lunch")
        return f"🍽️ **Eldaana suggests {moment}**: **{choix}**"

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
    moment = _t("voy_meal_moment_dinner") if heure >= 14 else _t("voy_meal_moment_lunch")
    return f"🍽️ **Eldaana suggère {moment}** : **{choix}**"


def _prediction_vacances(profile: dict) -> str:
    budget_mensuel = float(profile.get("budget_mensuel") or 0)
    hobbies = profile.get("hobbies", [])
    lang    = _lang()

    if lang == "en":
        seasons_en = ["spring", "summer", "autumn", "winter"]
        saison = seasons_en[(datetime.now().month - 1) // 3]
        dests_budget_moyen = [
            ("Portugal 🇵🇹", "culture, gastronomy, beaches", "flight + hotel ~£350"),
            ("Spain 🇪🇸", "sunshine, tapas, flamenco", "flight + hotel ~£300"),
            ("Morocco 🇲🇦", "change of scenery, flavours, desert", "flight + riad ~£260"),
            ("Italy 🇮🇹", "history, art, gastronomy", "flight + hotel ~£380"),
        ]
        dests_budget_plus = [
            ("Greece 🇬🇷", "paradise islands, history", "flight + hotel ~£520"),
            ("Japan 🇯🇵", "unique culture, gastronomy", "flight + hotel ~£1100"),
            ("Canada 🇨🇦", "nature, wide open spaces", "flight + hotel ~£900"),
        ]
        dests_nature = [
            ("Iceland 🇮🇸", "northern lights, geysers", "flight + hotel ~£700"),
            ("Scottish Highlands 🏴󠁧󠁢󠁳󠁣󠁴󠁿", "wild coastlines, whisky", "car + B&B ~£180"),
        ]
        hobby_str = " ".join(hobbies).lower()
        if "nature" in hobby_str or "hiking" in hobby_str or "randonnée" in hobby_str:
            pool = dests_nature
        elif budget_mensuel > 2000:
            pool = dests_budget_plus
        else:
            pool = dests_budget_moyen
        dest, desc, tarif = random.choice(pool)
        return (
            f"🌍 For your next holiday, the stars point to **{dest}**!\n"
            f"*{desc}* — {tarif}.\nBased on your tastes and the upcoming **{saison}** season."
        )

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

    st.markdown(_t("voy_title"))
    st.caption(_t("voy_subtitle"))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — Scores du jour (Essentiel+)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown(_t("voy_scores_title"))

    if not can_access("voyance_daily_scores", uid):
        show_upgrade_prompt(_t("voy_scores_feature"), "essential")
    else:
        # Cache : ne calculer qu'une fois par jour
        cache_key = f"scores_{uid}_{date.today().isoformat()}"
        if cache_key not in st.session_state:
            if st.button(_t("voy_compute"), use_container_width=True,
                         key="btn_compute_scores"):
                from voyance_engine import compute_scores
                weather = st.session_state.get("weather") or {}
                with st.spinner(_t("voy_computing")):
                    st.session_state[cache_key] = compute_scores(
                        profile=profile,
                        weather=weather,
                        lang=_lang(),
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
                    {_t("voy_score_label")}
                </p>
            </div>
            """, unsafe_allow_html=True)

            # 4 scores détaillés
            col1, col2 = st.columns(2)
            with col1:
                _show_score_bar(_t("voy_mood"),   scores.get("score_humeur",  65), "😊")
                _show_score_bar(_t("voy_energy"), scores.get("score_energie", 60), "⚡")
            with col2:
                _show_score_bar(_t("voy_stress"), scores.get("score_stress",  50), "🧘")
                _show_score_bar(_t("voy_budget"), scores.get("score_budget",  70), "💰")

            # Conseil du jour
            if conseil := scores.get("conseil_jour"):
                st.info(_t("voy_counsel", conseil=conseil))

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
                        st.markdown(_t("voy_positive"))
                        for f in pos: st.markdown(f"• {f}")
                    with col_neg:
                        st.markdown(_t("voy_vigilance"))
                        for f in neg: st.markdown(f"• {f}")
            else:
                show_upgrade_prompt(_t("voy_factors_feature"), "premium")

            # Recalculer
            if st.button(_t("voy_recalc"), key="btn_recompute"):
                st.session_state.pop(cache_key, None)
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — Question existentielle IA (tous les tiers)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown(_t("voy_ask_title"))
    st.markdown(_t("voy_ask_sub"))

    # Exemples rapides
    examples = _tl("voy_examples")
    cols = st.columns(2)
    for i, ex in enumerate(examples):
        with cols[i % 2]:
            if st.button(ex, key=f"ex_{i}", use_container_width=True):
                st.session_state["voyance_question"] = ex
                st.session_state["voyance_input"] = ex   # met à jour le widget texte
                st.rerun()

    question = st.text_input(
        _t("voy_input_label"),
        value=st.session_state.get("voyance_question", ""),
        placeholder=_t("voy_input_ph"),
        key="voyance_input",
    )

    if question and st.button(_t("voy_calc_btn"), type="primary",
                               use_container_width=True, key="btn_predict"):
        from voyance_engine import get_existential_prediction
        with st.spinner(_t("voy_consulting")):
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
            st.markdown(_t("voy_factors"))
            for f in factors:
                st.markdown(f"• {f}")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — Prédictions fun (tous les tiers)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown(_t("voy_fun_title"))

    # Repas
    st.markdown(_t("voy_meal_title"))
    if st.button(_t("voy_meal_btn"), use_container_width=True, key="btn_repas"):
        st.session_state["repas_suggestion"] = _conseil_repas(profile)
    if "repas_suggestion" in st.session_state:
        st.success(st.session_state["repas_suggestion"])
        if st.button(_t("voy_other_idea"), key="autre_repas"):
            st.session_state["repas_suggestion"] = _conseil_repas(profile)
            st.rerun()

    # Vacances
    st.markdown(_t("voy_vac_title"))
    if st.button(_t("voy_vac_btn"), use_container_width=True, key="btn_vac"):
        st.session_state["vacances_pred"] = _prediction_vacances(profile)
    if "vacances_pred" in st.session_state:
        st.info(st.session_state["vacances_pred"])

    # Mariage
    st.markdown(_t("voy_mar_title"))
    if st.button(_t("voy_mar_btn"), use_container_width=True, key="btn_mar"):
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
    st.markdown(_t("voy_car_title"))
    if st.button(_t("voy_car_btn"), use_container_width=True, key="btn_carr"):
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
    st.markdown(_t("voy_child_title"))
    if st.button(_t("voy_child_btn"), use_container_width=True, key="btn_enf"):
        st.session_state["enfants_pred"] = _calcul_enfants(profile)
    if "enfants_pred" in st.session_state:
        st.info(f"👶 {st.session_state['enfants_pred']}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.caption(_t("voy_disclaimer"))
