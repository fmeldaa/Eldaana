"""
social_connect.py — Connexion vie numérique & réseaux sociaux.

Approche : import manuel guidé + questions intelligentes.
Les données enrichissent le profil Eldaana pour une prédiction plus précise.
"""

import streamlit as st
from translations import t as _t, t_list as _tl


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

def _ico(slug: str, color: str | None = None) -> str:
    """Construit une URL Iconify. color = hex sans # (ex: 'FFFC00')."""
    url = f"https://api.iconify.design/{slug}.svg"
    return url if not color else f"{url}?color=%23{color}"

# logos: = couleurs natives  |  simple-icons: = monochrome → couleur forcée via ?color=
RESEAUX_LOGOS = {
    "Instagram":   _ico("logos:instagram-icon"),
    "Facebook":    _ico("logos:facebook"),
    "TikTok":      _ico("logos:tiktok-icon"),
    "Twitter / X": _ico("logos:x"),
    "LinkedIn":    _ico("logos:linkedin-icon"),
    "Snapchat":    _ico("simple-icons:snapchat",  "FFFC00"),
    "WhatsApp":    _ico("logos:whatsapp-icon"),
    "Email":       _ico("logos:google-gmail"),
    "Spotify":     _ico("logos:spotify-icon"),
    "YouTube":     _ico("logos:youtube-icon"),
    "Deezer":      _ico("simple-icons:deezer",    "A238FF"),
    "Shazam":      _ico("simple-icons:shazam",    "0088FF"),
}

NETWORKS_EN = {
    "Instagram": {
        "question": "Paste your Instagram bio or describe what you post (travel, food, fashion, sport…)",
        "placeholder": "e.g. 'Street food enthusiast 🍜 | London | Weekly adventure photos'",
    },
    "LinkedIn": {
        "question": "Paste your LinkedIn headline or describe your professional life",
        "placeholder": "e.g. 'Digital Project Manager | 8 years experience | Open to opportunities'",
    },
    "TikTok": {
        "question": "What type of content do you watch or create on TikTok?",
        "placeholder": "e.g. 'I mostly watch recipes and fitness tips. I sometimes post comedy sketches.'",
    },
    "Twitter / X": {
        "question": "Paste your Twitter bio or describe your favourite topics",
        "placeholder": "e.g. 'Tech, politics, NBA | Strong opinions | 2k followers'",
    },
    "Facebook": {
        "question": "How do you use Facebook? Family, friends, groups?",
        "placeholder": "e.g. 'I follow local community groups and keep up with family news'",
    },
    "Snapchat": {
        "question": "How do you use Snapchat? With whom?",
        "placeholder": "e.g. 'With close friends, daily stories'",
    },
    "WhatsApp": {
        "question": "Describe your main WhatsApp groups and who you communicate with",
        "placeholder": "e.g. 'Family, work group, close friends. I usually reply in the evenings.'",
    },
    "Email": {
        "question": "What is your email usage? Work, personal, newsletters?",
        "placeholder": "e.g. 'Intense work email, personal inbox mostly for orders and tech newsletters'",
    },
    "Spotify": {
        "question": "What music genres, artists or playlists do you listen to most?",
        "placeholder": "e.g. 'R&B, Afrobeats, Drill. Artists: Burna Boy, Drake. I listen mostly on my commute.'",
    },
    "YouTube": {
        "question": "What channels or topics do you follow on YouTube?",
        "placeholder": "e.g. 'Tech reviews, gaming, travel vlogs, documentaries.'",
    },
    "Deezer": {
        "question": "Your music tastes on Deezer — genres, moods, listening moments?",
        "placeholder": "e.g. 'Jazz in the morning, hip-hop in the evening. Chill playlists for work, electronic for sport.'",
    },
    "Shazam": {
        "question": "What style of music do you identify most? In what contexts?",
        "placeholder": "e.g. 'I Shazam mostly at parties or cafés. Lots of Afro and soul.'",
    },
    "Pinterest": {
        "question": "What do you pin on Pinterest?",
        "placeholder": "e.g. 'Interior design, recipes, fashion inspiration.'",
    },
    "BeReal": {
        "question": "How do you use BeReal?",
        "placeholder": "e.g. 'I post daily, mostly at home or at work.'",
    },
}


def show_social_connect(profile: dict):
    """
    Affiche le formulaire de connexion vie numérique.
    Enrichit le profil avec les données saisies.
    """
    # CSS : alignement vertical des colonnes de la grille réseaux
    st.markdown("""<style>
[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] {
    align-items: center !important;
}
</style>""", unsafe_allow_html=True)

    st.markdown(_t("soc_title"))
    st.caption(_t("soc_subtitle"))

    social = profile.get("social_networks", {})

    try:
        lang = st.session_state.get("lang", "fr")
    except Exception:
        lang = "fr"

    st.markdown(_t("soc_select_networks"))

    # Sélection des réseaux actifs — logo HTML 18×18 + checkbox, grille 4 colonnes
    selected = []
    cols = st.columns(4)
    for i, (name, info) in enumerate(NETWORKS.items()):
        with cols[i % 4]:
            icon_slug = RESEAUX_LOGOS.get(name)
            if icon_slug:
                url = icon_slug  # déjà une URL complète (produite par _ico())
                st.markdown(
                    f'<div style="display:flex;align-items:center;height:32px;">'
                    f'<img src="{url}" width="18" height="18" '
                    f'style="vertical-align:middle;display:inline-block;" />'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                active = st.checkbox(
                    name,
                    value=(name in social),
                    key=f"social_check_{name}",
                )
            else:
                active = st.checkbox(
                    f"{info['emoji']} {name}",
                    value=(name in social),
                    key=f"social_check_{name}",
                )
            if active:
                selected.append(name)

    st.markdown("---")

    # Champs pour chaque réseau sélectionné
    updated_social = {}
    for name in selected:
        info = NETWORKS[name]
        net_info = NETWORKS_EN.get(name, info) if lang == "en" else info
        icon_slug = RESEAUX_LOGOS.get(name)
        if icon_slug:
            url = icon_slug  # déjà une URL complète
            st.markdown(
                f'<img src="{url}" width="18" height="18" '
                f'style="vertical-align:middle;margin-right:6px;">'
                f'<span style="font-size:1.1rem;font-weight:600;color:{info["color"]}">'
                f'{name}</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<span style='font-size:1.1rem;font-weight:600;color:{info['color']}'>"
                f"{info['emoji']} {name}</span>",
                unsafe_allow_html=True,
            )
        val = st.text_area(
            net_info["question"],
            value=social.get(name, {}).get("description", ""),
            placeholder=net_info["placeholder"],
            height=80,
            key=f"social_text_{name}",
            label_visibility="visible",
        )
        updated_social[name] = {"description": val}

    st.markdown("---")

    # Questions sur les habitudes numériques globales
    st.markdown(_t("soc_habits_title"))

    shopping_opts = _tl("soc_shopping_opts")
    saved_shopping = profile.get("online_shopping", "Parfois")
    # Try to find the saved value in current locale opts; fall back to index 1
    try:
        shopping_index = shopping_opts.index(saved_shopping)
    except ValueError:
        shopping_index = 1

    c1, c2 = st.columns(2)
    with c1:
        screen_time = st.select_slider(
            _t("soc_screen_time"),
            options=["< 1h", "1-2h", "2-4h", "4-6h", "6-8h", "> 8h"],
            value=profile.get("screen_time", "2-4h"),
        )
        online_shopping = st.selectbox(
            _t("soc_shopping"),
            shopping_opts,
            index=shopping_index,
        )
    with c2:
        peak_hours = st.multiselect(
            _t("soc_peak"),
            _tl("soc_peak_opts"),
            default=[],
        )
        content_type = st.multiselect(
            _t("soc_content"),
            _tl("soc_content_opts"),
            default=[],
        )

    st.markdown(_t("soc_desc_title"))
    digital_life_desc = st.text_area(
        _t("soc_desc_label"),
        value=profile.get("digital_life_desc", ""),
        placeholder=_t("soc_desc_ph"),
        height=100,
    )

    if st.button(_t("soc_save"), use_container_width=True, type="primary"):
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
        st.success(_t("soc_saved"))
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
