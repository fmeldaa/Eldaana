"""
Page "Mon profil" - Eldaana
============================

Page profil complète et autonome pour l'application Eldaana (Streamlit).

Inclut :
- CSS unifié pour cases à cocher et boutons radio (fond violet #7B2FBE, coche blanche)
- Photo de profil ronde
- Vie personnelle (Orientation, Situation amoureuse, ENFANTS, Hobbies, Régime)
- Transports utilisés (cases à cocher)
- Réseaux sociaux (cases à cocher)
- Consentements (cases à cocher)
- Bouton Enregistrer

INTÉGRATION
-----------
Dans onboarding.py, remplace toute l'ancienne page profil par :

    from profile_page import render_profile_page
    render_profile_page(profile=profile_actuel, save_profile_callback=ma_fonction_save)

Adapte `save_profile_callback` à ton mécanisme de sauvegarde existant
(Glide, base de données, fichier JSON, etc.).
"""

import streamlit as st


# ============================================================
#  CSS UNIQUE - À NE PAS DUPLIQUER AILLEURS DANS LE CODE
# ============================================================

PURPLE = "#7B2FBE"

PROFILE_CSS = f"""
<style>
/* CASES À COCHER - état non coché : bordure violette, fond blanc */
[data-baseweb="checkbox"] span:first-child {{
    background-color: white !important;
    border: 2px solid {PURPLE} !important;
    border-radius: 4px !important;
}}

/* CASES À COCHER - état coché : fond violet, bordure violette */
[data-baseweb="checkbox"]:has(input:checked) span:first-child {{
    background-color: {PURPLE} !important;
    border-color: {PURPLE} !important;
}}

/* CASES À COCHER - icône de coche en blanc */
[data-baseweb="checkbox"] svg {{
    fill: white !important;
    stroke: white !important;
}}

/* BOUTONS RADIO - cercle intérieur violet quand sélectionné */
[data-baseweb="radio"] [aria-checked="true"] > div:first-child {{
    background-color: {PURPLE} !important;
    border-color: {PURPLE} !important;
}}

/* PHOTO DE PROFIL - cercle */
.profile-photo-circle {{
    width: 100px;
    height: 100px;
    border-radius: 50%;
    object-fit: cover;
    display: block;
    border: 3px solid {PURPLE};
}}

.profile-photo-placeholder {{
    width: 100px;
    height: 100px;
    border-radius: 50%;
    background: linear-gradient(135deg, #9B7BD4, {PURPLE});
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 48px;
    color: white;
}}
</style>
"""


# ============================================================
#  HELPERS
# ============================================================

def _safe_section(profile: dict, key: str) -> dict:
    """Retourne profile[key] s'il s'agit d'un dict, sinon un dict vide.
    Évite les erreurs quand une clé existe mais vaut None."""
    section = profile.get(key)
    return section if isinstance(section, dict) else {}


# ============================================================
#  RENDU DE LA PAGE
# ============================================================

def render_profile_page(profile: dict, save_profile_callback) -> None:
    """
    Affiche la page 'Mon profil' complète.

    Args:
        profile: dict contenant le profil utilisateur (peut être vide)
        save_profile_callback: fonction(dict) -> None appelée à l'enregistrement
    """
    # Injection du CSS - une seule fois, en haut de page
    st.markdown(PROFILE_CSS, unsafe_allow_html=True)

    # Lecture sécurisée des sous-sections
    famille = _safe_section(profile, "famille")
    vie_perso = _safe_section(profile, "vie_personnelle")
    transports = _safe_section(profile, "transports")
    reseaux = _safe_section(profile, "reseaux_sociaux")
    consentements = _safe_section(profile, "consentements")

    # --------------------------------------------------------
    # EN-TÊTE
    # --------------------------------------------------------
    st.markdown("## ✏️ Mon profil")
    st.caption("Plus Eldaana vous connaît, plus ses prédictions sont précises.")
    st.write("")

    # --------------------------------------------------------
    # PHOTO DE PROFIL
    # --------------------------------------------------------
    col_photo, col_upload = st.columns([1, 3])

    with col_photo:
        photo_url = profile.get("photo_url")
        if photo_url:
            st.markdown(
                f'<img src="{photo_url}" class="profile-photo-circle" />',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="profile-photo-placeholder">👤</div>',
                unsafe_allow_html=True,
            )

    with col_upload:
        st.markdown("📷 **Photo de profil**")
        photo_file = st.file_uploader(
            "Upload",
            type=["jpg", "jpeg", "png"],
            label_visibility="collapsed",
            key="photo_upload",
        )

    st.divider()

    # --------------------------------------------------------
    # VIE PERSONNELLE
    # --------------------------------------------------------
    st.markdown("### Vie personnelle")

    # Orientation sexuelle
    orientations = [
        "Hétérosexuel(le)",
        "Homosexuel(le)",
        "Bisexuel(le)",
        "Autre",
        "Préfère ne pas dire",
    ]
    orientation_default = vie_perso.get("orientation", orientations[0])
    orientation = st.selectbox(
        "Orientation sexuelle",
        orientations,
        index=orientations.index(orientation_default)
        if orientation_default in orientations
        else 0,
        key="orientation",
    )

    # Situation amoureuse
    situations = [
        "Célibataire",
        "En couple",
        "Marié(e)",
        "Pacsé(e)",
        "Divorcé(e)",
        "Veuf / Veuve",
    ]
    situation_default = vie_perso.get("situation_amoureuse", situations[0])
    situation = st.selectbox(
        "Situation amoureuse",
        situations,
        index=situations.index(situation_default)
        if situation_default in situations
        else 0,
        key="situation",
    )

    # ----- ENFANTS (entre Situation amoureuse et Hobbies) -----
    a_enfants_default = bool(famille.get("a_enfants", False))
    a_enfants = st.checkbox(
        "J'ai des enfants",
        value=a_enfants_default,
        key="a_enfants",
    )

    nombre_enfants = 0
    if a_enfants:
        # Le champ apparaît dynamiquement dès que la case est cochée
        # (fonctionne car on n'utilise PAS st.form)
        nb_default = int(famille.get("nombre_enfants", 1) or 1)
        if nb_default < 1:
            nb_default = 1
        nombre_enfants = st.number_input(
            "Nombre d'enfants",
            min_value=1,
            max_value=20,
            value=nb_default,
            step=1,
            key="nombre_enfants",
        )
    # ----- /ENFANTS -----

    # Hobbies
    hobbies = st.text_area(
        "Hobbies / Centres d'intérêt",
        value=vie_perso.get("hobbies", ""),
        placeholder="Ex : Lecture, sport, cuisine, voyages…",
        key="hobbies",
    )

    # Régime alimentaire
    regimes = [
        "Omnivore",
        "Végétarien(ne)",
        "Végan(e)",
        "Pescétarien(ne)",
        "Halal",
        "Casher",
        "Sans gluten",
        "Autre",
    ]
    regime_default = vie_perso.get("regime", regimes[0])
    regime = st.selectbox(
        "Régime alimentaire",
        regimes,
        index=regimes.index(regime_default)
        if regime_default in regimes
        else 0,
        key="regime",
    )

    st.divider()

    # --------------------------------------------------------
    # TRANSPORTS UTILISÉS
    # --------------------------------------------------------
    st.markdown("### Transports utilisés")

    transport_options = [
        ("voiture", "Voiture"),
        ("transport_commun", "Transport en commun"),
        ("velo", "Vélo"),
        ("a_pied", "À pied"),
        ("moto", "Moto / Scooter"),
        ("teletravail", "Télétravail"),
        ("mixte", "Mixte"),
    ]

    transports_selectionnes = {}
    for key, label in transport_options:
        transports_selectionnes[key] = st.checkbox(
            label,
            value=bool(transports.get(key, False)),
            key=f"transport_{key}",
        )

    st.divider()

    # --------------------------------------------------------
    # RÉSEAUX SOCIAUX
    # --------------------------------------------------------
    st.markdown("### Réseaux sociaux utilisés")

    reseaux_options = [
        ("instagram", "Instagram"),
        ("facebook", "Facebook"),
        ("tiktok", "TikTok"),
        ("linkedin", "LinkedIn"),
        ("twitter", "X / Twitter"),
        ("whatsapp", "WhatsApp"),
        ("youtube", "YouTube"),
    ]

    reseaux_selectionnes = {}
    for key, label in reseaux_options:
        reseaux_selectionnes[key] = st.checkbox(
            label,
            value=bool(reseaux.get(key, False)),
            key=f"reseau_{key}",
        )

    st.divider()

    # --------------------------------------------------------
    # CONSENTEMENTS
    # --------------------------------------------------------
    st.markdown("### Consentements")

    consent_notifications = st.checkbox(
        "J'accepte de recevoir des notifications WhatsApp",
        value=bool(consentements.get("notifications_whatsapp", False)),
        key="consent_notif",
    )
    consent_donnees = st.checkbox(
        "J'autorise Eldaana à utiliser mes données pour personnaliser ses prédictions",
        value=bool(consentements.get("utilisation_donnees", False)),
        key="consent_data",
    )
    consent_marketing = st.checkbox(
        "J'accepte de recevoir des communications marketing de Eldaa Group",
        value=bool(consentements.get("marketing", False)),
        key="consent_mkt",
    )

    st.divider()

    # --------------------------------------------------------
    # BOUTON ENREGISTRER
    # --------------------------------------------------------
    if st.button(
        "💾 Enregistrer mon profil",
        type="primary",
        use_container_width=True,
    ):
        new_profile = dict(profile)  # copie pour ne pas muter l'original

        new_profile["vie_personnelle"] = {
            "orientation": orientation,
            "situation_amoureuse": situation,
            "hobbies": hobbies,
            "regime": regime,
        }
        new_profile["famille"] = {
            "a_enfants": a_enfants,
            "nombre_enfants": nombre_enfants if a_enfants else 0,
        }
        new_profile["transports"] = transports_selectionnes
        new_profile["reseaux_sociaux"] = reseaux_selectionnes
        new_profile["consentements"] = {
            "notifications_whatsapp": consent_notifications,
            "utilisation_donnees": consent_donnees,
            "marketing": consent_marketing,
        }

        if photo_file is not None:
            # À adapter selon ton mécanisme de stockage
            # (Cloudinary, S3, fichier local, base64, etc.)
            new_profile["photo_file_pending"] = photo_file

        try:
            save_profile_callback(new_profile)
            st.success("✅ Profil enregistré avec succès !")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Erreur lors de l'enregistrement : {e}")


# ============================================================
#  EXEMPLE D'UTILISATION (à supprimer en intégration)
# ============================================================

if __name__ == "__main__":
    # Exemple de profil pour tester la page en local
    if "profile" not in st.session_state:
        st.session_state.profile = {}

    def save_profile(new_profile: dict) -> None:
        st.session_state.profile = new_profile

    render_profile_page(
        profile=st.session_state.profile,
        save_profile_callback=save_profile,
    )
