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

    st.markdown("### 🔒 Vie privée & RGPD")
    st.caption("Tes droits sur tes données personnelles.")

    # ── Politique de confidentialité ────────────────────────────────────────────
    with st.expander("📋 Politique de confidentialité complète", expanded=False):
        st.markdown(POLITIQUE_CONFIDENTIALITE)

    st.divider()

    # ── Export des données ──────────────────────────────────────────────────────
    st.markdown("#### 📥 Télécharger mes données")
    st.caption("Conformément à l'Article 20 du RGPD, tu peux télécharger toutes tes données.")

    if st.button("📦 Préparer l'export de mes données", use_container_width=True):
        data = export_user_data(user_id)
        if data:
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            st.download_button(
                label="⬇️ Télécharger (JSON)",
                data=json_str,
                file_name=f"eldaana_data_{prenom}_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True,
            )
            st.success("✅ Tes données sont prêtes au téléchargement.")
        else:
            st.error("Impossible de récupérer les données.")

    st.divider()

    # ── Suppression du compte ───────────────────────────────────────────────────
    st.markdown("#### 🗑️ Supprimer mon compte")
    st.caption(
        "Conformément à l'Article 17 du RGPD (droit à l'oubli), tu peux supprimer toutes tes données. "
        "**Cette action est irréversible.**"
    )

    with st.expander("⚠️ Supprimer mon compte Eldaana", expanded=False):
        st.warning(
            "En supprimant ton compte :\n"
            "- Toutes tes données personnelles seront anonymisées\n"
            "- Ton historique de courses et budget sera effacé\n"
            "- Tu devras recommencer l'onboarding\n"
            "**Cette action ne peut pas être annulée.**"
        )
        confirm_text = st.text_input(
            f"Pour confirmer, tape **SUPPRIMER** (en majuscules) :",
            placeholder="SUPPRIMER",
            key="confirm_delete",
        )
        if st.button("🗑️ Confirmer la suppression", type="primary", use_container_width=True):
            if confirm_text.strip() == "SUPPRIMER":
                if anonymize_user(user_id):
                    st.success("✅ Tes données ont été anonymisées.")
                    st.info("Tu vas être redirigé vers l'onboarding dans quelques secondes.")
                    # Reset session
                    from onboarding import logout
                    logout()
                    st.session_state.page = "onboarding"
                    st.rerun()
                else:
                    st.error("Erreur lors de la suppression.")
            else:
                st.error("Confirmation incorrecte. Tape exactement **SUPPRIMER** pour confirmer.")

    st.divider()

    # ── Consentements ────────────────────────────────────────────────────────────
    st.markdown("#### ✅ Mes consentements")
    consents = profile.get("consents", {})

    c1 = st.checkbox(
        "J'accepte que mes données de profil soient utilisées pour personnaliser les réponses",
        value=consents.get("profil", True),
        key="consent_profil",
    )
    c2 = st.checkbox(
        "J'accepte que mes conversations soient traitées par l'API Claude (Anthropic)",
        value=consents.get("claude", True),
        key="consent_claude",
    )
    c3 = st.checkbox(
        "J'accepte de recevoir des suggestions proactives (courses, budget, humeur)",
        value=consents.get("suggestions", True),
        key="consent_suggestions",
    )

    if st.button("💾 Mettre à jour mes préférences", use_container_width=True):
        from storage import db_load, db_save
        p = db_load(user_id)
        if p:
            p["consents"] = {"profil": c1, "claude": c2, "suggestions": c3}
            db_save(p)
            st.success("✅ Préférences mises à jour.")

    st.markdown(
        '<p style="text-align:center;color:#9ca3af;font-size:0.8rem;margin-top:2rem;">'
        'Contact : eldaana.app@gmail.com · RGPD conforme</p>',
        unsafe_allow_html=True,
    )
