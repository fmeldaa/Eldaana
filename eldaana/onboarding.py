"""
onboarding.py — Gestion des profils multi-utilisateurs + wizard d'onboarding.

Chaque utilisateur a son propre profil identifié par :
  - son Google ID (google_sub) s'il se connecte avec Google
  - un UUID généré automatiquement sinon
"""

import streamlit as st
import json
import uuid
from pathlib import Path
from google_auth import show_google_button, google_to_profile
from storage import db_load, db_save

DATA_DIR          = Path(__file__).parent / "user_data"
PROFILES_DIR      = DATA_DIR / "profiles"
CURRENT_USER_FILE = DATA_DIR / "current_user.json"
WARDROBE_DIR      = DATA_DIR / "wardrobe"
PHOTOS_DIR        = DATA_DIR / "photos"
LOGO_PATH         = Path(__file__).parent / "logo.png"


# ── Gestion des identifiants utilisateur ──────────────────────────────────────

def _read_current_user_id() -> str | None:
    """
    NE PAS UTILISER en production multi-utilisateurs.
    current_user.json est partagé côté serveur — chaque utilisateur
    doit être identifié uniquement via st.session_state.
    Conservé uniquement pour la migration locale.
    """
    return None  # Désactivé — session uniquement


def _write_current_user_id(user_id: str):
    """No-op en production. Ne pas écrire de fichier partagé côté serveur."""
    pass  # Désactivé


def get_active_user_id() -> str | None:
    """Retourne l'ID de l'utilisateur actif — SESSION UNIQUEMENT.
    Chaque onglet / appareil a sa propre session Streamlit indépendante."""
    return st.session_state.get("user_id")


def _profile_path(user_id: str) -> Path:
    return PROFILES_DIR / f"{user_id}.json"


# ── Profil I/O ─────────────────────────────────────────────────────────────────

def load_profile() -> dict | None:
    """Charge le profil de l'utilisateur actif."""
    user_id = get_active_user_id()
    if not user_id:
        return None
    return db_load(user_id)


def load_profile_by_google_sub(google_sub: str) -> dict | None:
    """Charge un profil à partir d'un Google ID (pour reconnexion)."""
    return db_load(google_sub)


def save_profile(profile: dict):
    """Sauvegarde le profil et met à jour l'utilisateur actif."""
    user_id = profile.get("user_id") or get_active_user_id()
    if not user_id:
        user_id = str(uuid.uuid4())
        profile["user_id"] = user_id

    db_save(profile)
    st.session_state["user_id"] = user_id


def is_onboarding_done() -> bool:
    p = load_profile()
    return p is not None and p.get("onboarding_complete", False)


def logout():
    """Déconnecte l'utilisateur actif (nettoie la session uniquement)."""
    for key in ["user_id", "google_prefill", "messages", "display_messages",
                "weather", "transport_alert_checked", "departure_alert",
                "email_list", "email_summary"]:
        st.session_state.pop(key, None)


# ── Résumé sidebar ─────────────────────────────────────────────────────────────

def profile_summary(profile: dict) -> str:
    lines = []
    if profile.get("ville"):
        lines.append(f"📍 {profile['ville']}")
    if profile.get("sexe"):
        lines.append(f"· {profile['sexe']}")
    if profile.get("profession"):
        lines.append(f"· {profile['profession']}")
    if profile.get("situation_maritale"):
        lines.append(f"· {profile['situation_maritale']}")
    hobbies = profile.get("hobbies", [])
    if hobbies:
        lines.append("♥ " + ", ".join(hobbies[:3]))
    return "  ".join(lines)


# ── Migration profil ancien format ────────────────────────────────────────────

def _migrate_legacy():
    """Désactivée — migration one-shot uniquement en local, jamais en production multi-users."""
    pass


# ── Onboarding Wizard ──────────────────────────────────────────────────────────

def show_onboarding() -> bool:
    """
    Affiche le wizard d'onboarding.
    Retourne True quand le profil est créé/chargé et qu'on peut entrer dans l'app.
    """
    # Migration silencieuse si ancien format
    _migrate_legacy()

    # Logo + titre
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=80)
    with col_title:
        st.markdown("""
        <p style="font-size:1.7rem;font-weight:700;
                  background:linear-gradient(135deg,#c084fc,#818cf8,#38bdf8);
                  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                  margin:14px 0 2px 0;">
            Bienvenue sur Eldaana
        </p>
        <p style="color:#9ca3af;font-size:0.88rem;margin:0;">
            Votre assistante IA bienveillante &amp; prédictive 🌸
        </p>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Bouton Google ──────────────────────────────────────────────────────────
    google_info = show_google_button()

    if google_info:
        google_sub = google_info.get("sub", "")

        # Utilisateur déjà connu ? → connexion directe
        existing = load_profile_by_google_sub(google_sub)
        if existing and existing.get("onboarding_complete"):
            st.session_state["user_id"] = google_sub
            return True

        # Nouvel utilisateur Google → pré-remplissage
        st.session_state["google_prefill"] = google_to_profile(google_info)
        st.rerun()

    # ── Formulaire ─────────────────────────────────────────────────────────────
    prefill    = st.session_state.get("google_prefill", {})
    from_google = bool(prefill)

    if from_google:
        st.success(f"✅ Connecté avec Google — bonjour **{prefill.get('prenom', '')}** !")
        st.markdown("##### Deux dernières infos :")
    else:
        st.markdown(
            '<div style="text-align:center;color:#9ca3af;font-size:0.82rem;'
            'margin:8px 0;">— ou —</div>',
            unsafe_allow_html=True,
        )
        st.markdown("##### Juste 3 infos pour commencer :")

    if not from_google:
        prenom = st.text_input("Votre prénom *", placeholder="Comment vous appelez-vous ?")
    else:
        prenom = prefill.get("prenom", "")

    ville = st.text_input(
        "Votre ville *",
        placeholder="Ex : Paris, Lyon, Dakar, Montréal…",
        help="Pour la météo et les suggestions du jour",
    )

    sexe = st.radio(
        "Vous êtes *",
        ["Femme", "Homme", "Non-binaire", "Préfère ne pas préciser"],
        horizontal=True,
        index=0,
    )

    submitted = st.button("C'est parti avec Eldaana ✨", use_container_width=True, type="primary")

    if submitted:
        errors = []
        if not str(prenom).strip():
            errors.append("Votre prénom est requis.")
        if not ville.strip():
            errors.append("Votre ville est requise.")
        if errors:
            for e in errors:
                st.error(e)
        else:
            # Détermine l'ID : Google sub ou nouvel UUID
            user_id = prefill.get("google_sub") or str(uuid.uuid4())

            profile = {
                "user_id":        user_id,
                "prenom":         str(prenom).strip(),
                "sexe":           sexe,
                "ville":          ville.strip(),
                "nom":            prefill.get("nom", ""),
                "google_email":   prefill.get("google_email", ""),
                "google_picture": prefill.get("google_picture", ""),
                "google_sub":     prefill.get("google_sub", ""),
                # Champs enrichis — complétés plus tard
                "age":                    None,
                "poids":                  None,
                "taille":                 None,
                "budget_mensuel":         0,
                "profession":             "",
                "orientation_sexuelle":   "",
                "situation_maritale":     "",
                "famille":                {"a_enfants": None, "nb_enfants": 0},
                "hobbies":                [],
                "habitudes_alimentaires": "",
                "transport":              "",
                "garde_robe":             {"description": "", "photos": []},
                "consents":               {"profil": True, "claude": True, "suggestions": True},
                "onboarding_complete":         True,
                "onboarding_lifestyle_complete": False,
            }
            save_profile(profile)
            st.session_state.pop("google_prefill", None)
            return True

    return False


# ── Formulaire profil enrichi ──────────────────────────────────────────────────

def show_profile_form(profile: dict):
    st.markdown("### ✏️ Mon profil")
    st.caption("Plus Eldaana vous connaît, plus ses prédictions sont précises.")

    sexe_opts   = ["Femme", "Homme", "Non-binaire", "Préfère ne pas préciser"]
    orient_opts = ["Hétérosexuel(le)", "Homosexuel(le)", "Bisexuel(le)", "Autre", "Préfère ne pas préciser"]
    sit_opts    = ["Célibataire", "En couple", "Marié(e) / Pacsé(e)", "Divorcé(e)", "Veuf/Veuve", "C'est compliqué"]
    alim_opts   = ["Omnivore", "Végétarien(ne)", "Vegan", "Pescétarien(ne)", "Sans gluten", "Halal", "Casher", "Autre"]
    transp_opts = ["Voiture", "Transport en commun", "Vélo", "À pied", "Moto / Scooter", "Télétravail", "Mixte"]

    def _idx(lst, val, default=0):
        return lst.index(val) if val in lst else default

    # ── Photo de profil (hors formulaire pour mise à jour immédiate) ─────────────
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    uid = get_active_user_id() or ""
    photo_path = PHOTOS_DIR / f"{uid}.jpg" if uid else None
    col_ph1, col_ph2 = st.columns([1, 3])
    with col_ph1:
        if photo_path and photo_path.exists():
            st.image(str(photo_path), width=90)
        else:
            st.markdown(
                '<div style="width:90px;height:90px;border-radius:50%;'
                'background:linear-gradient(135deg,#C084FC,#818CF8);'
                'display:flex;align-items:center;justify-content:center;'
                'font-size:36px;">👤</div>', unsafe_allow_html=True
            )
    with col_ph2:
        uploaded = st.file_uploader("📷 Photo de profil", type=["jpg","jpeg","png"],
                                    key="profile_photo_upload")
        if uploaded and photo_path:
            with open(photo_path, "wb") as f:
                f.write(uploaded.getbuffer())
            st.success("Photo mise à jour !")
            st.rerun()

    with st.form("profile_form"):
        st.markdown("**Identité**")
        c1, c2 = st.columns(2)
        with c1:
            prenom = st.text_input("Prénom",  value=profile.get("prenom", ""))
            ville  = st.text_input("Ville",   value=profile.get("ville",  ""))
            age    = st.number_input("Âge", min_value=11, max_value=120,
                                     value=max(11, int(profile.get("age") or 11)))
            poids  = st.number_input("Poids (kg) *(optionnel)*", min_value=0, max_value=300,
                                     value=int(profile.get("poids") or 0),
                                     help="Utilisé pour des suggestions santé/alimentation personnalisées")
            taille = st.number_input("Taille (cm) *(optionnel)*", min_value=0, max_value=250,
                                     value=int(profile.get("taille") or 0),
                                     help="Utilisé pour des suggestions de tenue vestimentaire")
        with c2:
            sexe       = st.selectbox("Sexe", sexe_opts, index=_idx(sexe_opts, profile.get("sexe", "")))
            profession = st.text_input("Profession", value=profile.get("profession", ""),
                                       placeholder="Ex : Infirmière, Étudiant…")
            budget_mensuel = st.number_input(
                "Budget mensuel (€) *(optionnel)*",
                min_value=0, max_value=50000,
                value=int(profile.get("budget_mensuel") or 0),
                step=50,
                help="Ton budget disponible chaque mois — pour les alertes et prédictions",
            )

        st.markdown("**Vie personnelle**")
        orientation = st.selectbox("Orientation sexuelle", orient_opts,
                                   index=_idx(orient_opts, profile.get("orientation_sexuelle", "")))
        situation   = st.selectbox("Situation amoureuse", sit_opts,
                                   index=_idx(sit_opts, profile.get("situation_maritale", "")))
        fam = profile.get("famille", {})
        st.markdown("**Enfants ?**")
        a_enfants_val = "Oui" if fam.get("a_enfants") else "Non"
        col_enf1, col_enf2 = st.columns(2)
        with col_enf1:
            enf_non = st.checkbox("Non", value=(a_enfants_val == "Non"), key="enf_non")
        with col_enf2:
            enf_oui = st.checkbox("Oui", value=(a_enfants_val == "Oui"), key="enf_oui")
        a_enfants = "Oui" if enf_oui else "Non"
        nb_enfants = st.number_input(
            "Nombre d'enfants",
            min_value=0, max_value=20,
            value=int(fam.get("nb_enfants") or 0),
        )
        hobbies = st.text_area("Hobbies / Centres d'intérêt",
                               value=", ".join(profile.get("hobbies", [])),
                               placeholder="Ex : Lecture, sport, cuisine, voyages…")

        st.markdown("**Mode de vie**")
        c3, c4 = st.columns(2)
        with c3:
            alim = st.selectbox("Régime alimentaire", alim_opts,
                                index=_idx(alim_opts, profile.get("habitudes_alimentaires", "")))
        with c4:
            st.markdown("**Transports utilisés**")
            saved_transport = profile.get("transport", "")
            saved_list = [t.strip() for t in saved_transport.split(",")] if saved_transport else []
            transport_checks = {t: st.checkbox(t, value=(t in saved_list), key=f"tr_{t}") for t in transp_opts}
            transport = ", ".join([t for t, v in transport_checks.items() if v])

        # ── Détail transport pour les alertes ──
        st.markdown("**🚦 Mes lignes & trajets** *(pour les alertes en temps réel)*")
        transport_info = profile.get("transport_detail", {})
        all_lines = [
            "RER A", "RER B", "RER C", "RER D", "RER E",
            "Métro 1", "Métro 2", "Métro 3", "Métro 4", "Métro 5",
            "Métro 6", "Métro 7", "Métro 8", "Métro 9", "Métro 10",
            "Métro 11", "Métro 12", "Métro 13", "Métro 14",
            "Transilien H", "Transilien J", "Transilien K", "Transilien L",
            "Transilien N", "Transilien P", "Transilien R", "Transilien U",
            "TGV", "Intercités", "TER", "Autre ligne",
        ]
        tc_lines = st.multiselect(
            "Lignes empruntées",
            all_lines,
            default=transport_info.get("lines", []),
            placeholder="Ex : RER B, Métro 13…",
        )
        c5, c6 = st.columns(2)
        with c5:
            depart_heure = st.text_input(
                "Heure de départ habituelle",
                value=transport_info.get("depart_heure", ""),
                placeholder="Ex : 08:00",
            )
        with c6:
            has_car = st.checkbox(
                "🚗 J'utilise aussi la voiture",
                value=transport_info.get("has_car", False),
                key="has_car"
            )
        trajet_desc = st.text_input(
            "Décris ton trajet principal *(optionnel)*",
            value=transport_info.get("trajet_desc", ""),
            placeholder="Ex : Saint-Denis → Paris 15e via RER B + Métro 13",
        )

        # ── Réveil ──
        st.markdown("**⏰ Heure de réveil** *(pour la notification matinale)*")
        heure_reveil = st.text_input(
            "Heure de réveil",
            value=profile.get("heure_reveil", ""),
            placeholder="Ex : 07:00",
            help="Eldaana t'enverra une notification à cette heure avec la météo et un message positif",
        )

        st.markdown("**👗 Garde-robe** *(optionnel)*")
        gdr = profile.get("garde_robe", {})
        if not isinstance(gdr, dict):
            gdr = {"description": "", "photos": []}
        garde_desc = st.text_area("Style vestimentaire", value=gdr.get("description", ""),
                                  placeholder="Ex : Style casual, couleurs neutres…")
        photos = st.file_uploader("Photos de tenues", type=["jpg", "jpeg", "png"],
                                  accept_multiple_files=True)

        saved = st.form_submit_button("💾 Enregistrer", use_container_width=True)

    if saved:
        saved_photos = list(gdr.get("photos", []))
        if photos:
            WARDROBE_DIR.mkdir(parents=True, exist_ok=True)
            for p in photos:
                dest = WARDROBE_DIR / p.name
                with open(dest, "wb") as f:
                    f.write(p.getbuffer())
                if p.name not in saved_photos:
                    saved_photos.append(p.name)

        profile.update({
            "prenom":         prenom.strip(),
            "ville":          ville.strip(),
            "age":            int(age) if age else None,
            "poids":          int(poids) if poids else None,
            "taille":         int(taille) if taille else None,
            "budget_mensuel": int(budget_mensuel) if budget_mensuel else 0,
            "sexe":           sexe,
            "profession":     profession.strip(),
            "orientation_sexuelle": orientation,
            "situation_maritale":   situation,
            "famille":   {"a_enfants": a_enfants == "Oui",
                          "nb_enfants": int(nb_enfants) if a_enfants == "Oui" else 0},
            "hobbies":   [h.strip() for h in hobbies.split(",") if h.strip()],
            "habitudes_alimentaires": alim,
            "transport": transport,
            "transport_detail": {
                "lines":        tc_lines,
                "depart_heure": depart_heure.strip(),
                "has_car":      has_car,
                "trajet_desc":  trajet_desc.strip(),
            },
            "garde_robe": {"description": garde_desc, "photos": saved_photos},
            "heure_reveil": heure_reveil.strip(),
            "onboarding_lifestyle_complete": True,
        })
        save_profile(profile)
        st.success("✅ Profil mis à jour !")
        st.rerun()
