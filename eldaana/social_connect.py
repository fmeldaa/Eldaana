"""
social_connect.py — Connexion vie numérique & réseaux sociaux.

Approche : import manuel guidé + questions intelligentes.
Les données enrichissent le profil Eldaana pour une prédiction plus précise.
"""

import streamlit as st


# ── Réseaux avec leurs icônes et questions guidées ────────────────────────────

NETWORKS = {
    "Instagram": {
        "emoji": "📸",
        "color": "#E1306C",
        "question": "Colle ici ta bio Instagram ou décris ce que tu postes (voyages, food, mode, sport…)",
        "placeholder": "Ex : 'Passionné de street food 🍜 | Paris | Photos de mes aventures hebdo'",
    },
    "LinkedIn": {
        "emoji": "💼",
        "color": "#0077B5",
        "question": "Colle ton titre LinkedIn ou décris ta vie professionnelle",
        "placeholder": "Ex : 'Chef de projet digital chez SNCF | 8 ans d'expérience | Open to opportunities'",
    },
    "TikTok": {
        "emoji": "🎵",
        "color": "#010101",
        "question": "Quel type de contenu tu regardes ou crées sur TikTok ?",
        "placeholder": "Ex : 'Je regarde surtout des recettes et des tips fitness. Je poste parfois des sketchs.'",
    },
    "Twitter / X": {
        "emoji": "🐦",
        "color": "#1DA1F2",
        "question": "Colle ta bio Twitter ou décris tes sujets favoris",
        "placeholder": "Ex : 'Tech, politique, NBA | Opinions tranchées | 2k followers'",
    },
    "Facebook": {
        "emoji": "👥",
        "color": "#1877F2",
        "question": "Comment tu utilises Facebook ? Famille, amis, groupes ?",
        "placeholder": "Ex : 'Je suis dans des groupes de parents, je suis les actualités locales'",
    },
    "Snapchat": {
        "emoji": "👻",
        "color": "#FFFC00",
        "question": "Tu utilises Snap pour quoi ? Avec qui ?",
        "placeholder": "Ex : 'Avec mes proches du lycée, stories quotidiennes'",
    },
    "WhatsApp": {
        "emoji": "💬",
        "color": "#25D366",
        "question": "Décris tes groupes WhatsApp principaux et avec qui tu communiques",
        "placeholder": "Ex : 'Famille, groupe de travail, amis proches. Je réponds en général le soir.'",
    },
    "Email": {
        "emoji": "📧",
        "color": "#7B2FBE",
        "question": "Quel est ton usage de l'email ? Pro, perso, newsletters ?",
        "placeholder": "Ex : 'Email pro intense, boîte perso surtout pour les commandes et newsletters tech'",
    },
    "Spotify": {
        "emoji": "🎧",
        "color": "#1DB954",
        "question": "Quels genres musicaux, artistes ou playlists tu écoutes le plus ?",
        "placeholder": "Ex : 'R&B, afrobeats, drill. Artistes : Burna Boy, Drake, Ninho. J'écoute surtout le soir en rentrant.'",
    },
    "YouTube": {
        "emoji": "▶️",
        "color": "#FF0000",
        "question": "Quel type de contenu tu regardes sur YouTube ?",
        "placeholder": "Ex : 'Documentaires, tech, vlogs, musique. Je regarde beaucoup de rap français et des débats.'",
    },
    "Deezer": {
        "emoji": "🎵",
        "color": "#A238FF",
        "question": "Tes goûts musicaux sur Deezer — genres, humeurs, moments d'écoute ?",
        "placeholder": "Ex : 'Jazz le matin, rap le soir. Playlists chill pour travailler, électro pour le sport.'",
    },
    "Shazam": {
        "emoji": "🔵",
        "color": "#0088FF",
        "question": "Quel style de musique tu identifies souvent ? Dans quels contextes ?",
        "placeholder": "Ex : 'Je Shazam surtout en soirée ou dans les cafés. Beaucoup d'afro et de soul.'",
    },
}


def show_social_connect(profile: dict):
    """
    Affiche le formulaire de connexion vie numérique.
    Enrichit le profil avec les données saisies.
    """
    st.markdown("### 🌐 Ma vie numérique")
    st.caption(
        "Plus Eldaana connaît ta présence en ligne, mieux elle peut anticiper "
        "tes besoins, tes humeurs et tes opportunités. "
        "Partage ce que tu veux — tout reste strictement confidentiel."
    )

    social = profile.get("social_networks", {})

    st.markdown("#### Sélectionne tes réseaux actifs :")

    # Sélection des réseaux actifs avec des checkboxes
    selected = []
    cols = st.columns(4)
    for i, (name, info) in enumerate(NETWORKS.items()):
        with cols[i % 4]:
            active = st.checkbox(
                f"{info['emoji']} {name}",
                value=(name in social),
                key=f"social_check_{name}"
            )
            if active:
                selected.append(name)

    st.markdown("---")

    # Champs pour chaque réseau sélectionné
    updated_social = {}
    for name in selected:
        info = NETWORKS[name]
        st.markdown(
            f"<span style='font-size:1.1rem;font-weight:600;color:{info['color']}'>"
            f"{info['emoji']} {name}</span>",
            unsafe_allow_html=True
        )
        val = st.text_area(
            info["question"],
            value=social.get(name, {}).get("description", ""),
            placeholder=info["placeholder"],
            height=80,
            key=f"social_text_{name}",
            label_visibility="visible",
        )
        updated_social[name] = {"description": val}

    st.markdown("---")

    # Questions sur les habitudes numériques globales
    st.markdown("#### 📊 Tes habitudes numériques")

    c1, c2 = st.columns(2)
    with c1:
        screen_time = st.select_slider(
            "Temps moyen sur les écrans / jour",
            options=["< 1h", "1-2h", "2-4h", "4-6h", "6-8h", "> 8h"],
            value=profile.get("screen_time", "2-4h"),
        )
        online_shopping = st.selectbox(
            "Tu fais tes achats en ligne ?",
            ["Rarement", "Parfois", "Souvent", "Presque toujours"],
            index=["Rarement", "Parfois", "Souvent", "Presque toujours"].index(
                profile.get("online_shopping", "Parfois")
            ),
        )
    with c2:
        peak_hours = st.multiselect(
            "À quelle(s) heure(s) tu es le plus actif en ligne ?",
            ["Matin (6h-9h)", "Journée (9h-12h)", "Après-midi (12h-18h)",
             "Soir (18h-22h)", "Nuit (22h-2h)"],
            default=profile.get("peak_hours", ["Soir (18h-22h)"]),
        )
        content_type = st.multiselect(
            "Quel type de contenu tu consommes ?",
            ["Actualités", "Entertainment / Humour", "Sport", "Musique",
             "Tech / Innovation", "Mode / Beauté", "Cuisine", "Voyages",
             "Politique", "Développement personnel", "Finance"],
            default=profile.get("content_type", []),
        )

    st.markdown("#### 💭 Ta présence en ligne en quelques mots")
    digital_life_desc = st.text_area(
        "Décris librement ta vie numérique — ce qui te passionne, t'énerve, t'inspire en ligne",
        value=profile.get("digital_life_desc", ""),
        placeholder=(
            "Ex : 'Je suis hyperconnecté le soir, je scroll beaucoup Instagram mais ça me stresse. "
            "J'adore les débats Twitter mais je fais attention à ma santé mentale. "
            "LinkedIn c'est pour le boulot, je poste rarement mais je lis beaucoup.'"
        ),
        height=100,
    )

    if st.button("💾 Sauvegarder ma vie numérique", use_container_width=True, type="primary"):
        profile.update({
            "social_networks":   updated_social,
            "screen_time":       screen_time,
            "online_shopping":   online_shopping,
            "peak_hours":        peak_hours,
            "content_type":      content_type,
            "digital_life_desc": digital_life_desc,
            "social_complete":   True,
        })
        from onboarding import save_profile
        save_profile(profile)
        st.success("✅ Vie numérique enregistrée ! Eldaana peut maintenant mieux te connaître.")
        st.rerun()


def format_social_for_prompt(profile: dict) -> str:
    """Formate les données sociales pour le system prompt."""
    lines = []

    social = profile.get("social_networks", {})
    if social:
        lines.append("\n### Présence sur les réseaux sociaux\n")
        for name, data in social.items():
            desc = data.get("description", "").strip()
            if desc:
                info = NETWORKS.get(name, {})
                lines.append(f"- **{info.get('emoji','')} {name}** : {desc}")

    if profile.get("screen_time"):
        lines.append(f"\n- Temps d'écran quotidien : {profile['screen_time']}")

    if profile.get("peak_hours"):
        lines.append(f"- Actif en ligne principalement : {', '.join(profile['peak_hours'])}")

    if profile.get("content_type"):
        lines.append(f"- Contenus consommés : {', '.join(profile['content_type'])}")

    if profile.get("online_shopping"):
        lines.append(f"- Achats en ligne : {profile['online_shopping']}")

    if profile.get("digital_life_desc"):
        lines.append(f"\n**Sa vie numérique en ses mots** :\n{profile['digital_life_desc']}")

    return "\n".join(lines)
