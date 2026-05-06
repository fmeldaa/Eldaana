"""
rgpd.py — Conformité RGPD / vie privée d'Eldaana.

Fonctionnalités :
- Export des données personnelles (JSON)
- Droit à l'oubli (suppression du compte)
- Politique de confidentialité
- Consentement explicite
"""

import streamlit as st
import json
from datetime import datetime
from pathlib import Path
from storage import db_load, db_save
from translations import t as _t


def export_user_data(user_id: str) -> dict:
    """Exporte toutes les données d'un utilisateur."""
    profile = db_load(user_id)
    if not profile:
        return {}

    # Retirer les données sensibles non-exportables
    export = {k: v for k, v in profile.items() if k not in ("google_sub",)}
    export["export_date"] = datetime.now().isoformat()
    export["export_info"] = "Données personnelles Eldaana — Conformité RGPD Article 20"
    return export


def anonymize_user(user_id: str) -> bool:
    """Anonymise toutes les données de l'utilisateur (droit à l'oubli)."""
    profile = db_load(user_id)
    if not profile:
        return False

    # Garder un enregistrement anonyme minimal
    anon = {
        "user_id":           user_id,
        "prenom":            "[Supprimé]",
        "ville":             "",
        "age":               None,
        "sexe":              "",
        "profession":        "",
        "google_email":      "",
        "google_picture":    "",
        "google_sub":        "",
        "onboarding_complete": False,
        "deleted_at":        datetime.now().isoformat(),
        "anonymized":        True,
    }
    db_save(anon)
    return True


POLITIQUE_CONFIDENTIALITE = """
## Politique de confidentialité Eldaana

**Dernière mise à jour : Avril 2026**

### 1. Données collectées
Eldaana collecte uniquement les données que vous renseignez volontairement :
- Prénom, ville, âge, genre, profession
- Habitudes alimentaires, loisirs, situation amoureuse
- Humeur quotidienne, courses, dépenses
- Messages de conversation (stockés temporairement en mémoire de session)

### 2. Finalité
Ces données sont utilisées **uniquement** pour personnaliser les réponses et prédictions d'Eldaana.
Elles ne sont jamais vendues, partagées ou transmises à des tiers.

### 3. Stockage
Vos données sont stockées de façon sécurisée (Supabase ou fichiers JSON locaux).
Les conversations ne sont pas persistées entre sessions.

### 4. Vos droits (RGPD)
- **Droit d'accès** : vous pouvez télécharger toutes vos données (Article 20)
- **Droit à l'oubli** : vous pouvez supprimer votre compte et vos données (Article 17)
- **Droit de rectification** : modifiez vos données via "Enrichir mon profil" (Article 16)
- **Droit à la portabilité** : export JSON disponible ci-dessous

### 5. Intelligence artificielle
Les conversations sont traitées via l'API Claude (Anthropic).
Consultez la politique de confidentialité d'Anthropic : https://www.anthropic.com/privacy

### 6. Contact
Pour toute question : **eldaana.app@gmail.com**

### 7. Modifications
Toute modification importante de cette politique vous sera notifiée dans l'application.
"""


def show_rgpd_page(profile: dict):
    """Page RGPD dans Streamlit."""
    user_id = profile.get("user_id", "")
    prenom  = profile.get("prenom", "")

    st.markdown(_t("rgpd_title"))
    st.caption(_t("rgpd_subtitle"))

    # ── Politique de confidentialité ────────────────────────────────────────────
    with st.expander(_t("rgpd_policy_expander"), expanded=False):
        st.markdown(POLITIQUE_CONFIDENTIALITE)

    st.divider()

    # ── Export des données ──────────────────────────────────────────────────────
    st.markdown(_t("rgpd_export_title"))
    st.caption(_t("rgpd_export_caption"))

    if st.button(_t("rgpd_export_btn"), use_container_width=True):
        data = export_user_data(user_id)
        if data:
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            st.download_button(
                label=_t("rgpd_download_btn"),
                data=json_str,
                file_name=f"eldaana_data_{prenom}_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True,
            )
            st.success(_t("rgpd_export_ok"))
        else:
            st.error(_t("rgpd_export_error"))

    st.divider()

    # ── Suppression du compte ───────────────────────────────────────────────────
    st.markdown(_t("rgpd_delete_title"))
    st.caption(_t("rgpd_delete_caption"))

    with st.expander(_t("rgpd_delete_expander"), expanded=False):
        st.warning(_t("rgpd_delete_warning"))
        confirm_text = st.text_input(
            _t("rgpd_delete_confirm"),
            placeholder=_t("rgpd_delete_ph"),
            key="confirm_delete",
        )
        if st.button(_t("rgpd_delete_btn"), type="primary", use_container_width=True):
            if confirm_text.strip() == _t("rgpd_delete_word"):
                if anonymize_user(user_id):
                    st.success(_t("rgpd_delete_ok"))
                    st.info(_t("rgpd_delete_redirect"))
                    # Reset session
                    from onboarding import logout
                    logout()
                    st.session_state.page = "onboarding"
                    st.rerun()
                else:
                    st.error(_t("rgpd_delete_error"))
            else:
                st.error(_t("rgpd_delete_wrong"))

    st.divider()

    # ── Consentements ────────────────────────────────────────────────────────────
    st.markdown(_t("rgpd_consents_title"))
    consents = profile.get("consents", {})

    c1 = st.checkbox(
        _t("rgpd_consent1"),
        value=consents.get("profil", True),
        key="consent_profil",
    )
    c2 = st.checkbox(
        _t("rgpd_consent2"),
        value=consents.get("claude", True),
        key="consent_claude",
    )
    c3 = st.checkbox(
        _t("rgpd_consent3"),
        value=consents.get("suggestions", True),
        key="consent_suggestions",
    )

    if st.button(_t("rgpd_save_prefs"), use_container_width=True):
        from storage import db_load, db_save
        p = db_load(user_id)
        if p:
            p["consents"] = {"profil": c1, "claude": c2, "suggestions": c3}
            db_save(p)
            st.success(_t("rgpd_prefs_ok"))

    st.markdown(
        f'<p style="text-align:center;color:#9ca3af;font-size:0.8rem;margin-top:2rem;">'
        f'{_t("rgpd_contact")}</p>',
        unsafe_allow_html=True,
    )
