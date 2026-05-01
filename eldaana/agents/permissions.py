"""
permissions.py — Système de consentement Eldaana Agent.

Chaque catégorie d'action a un niveau de permission distinct.
L'utilisateur valide une fois dans les paramètres.
Toute action est loggée dans Supabase.
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import streamlit as st
from storage import db_load, db_save


class PermissionLevel(Enum):
    READ_ONLY  = "read_only"   # Lecture seule — jamais d'action
    DRAFT      = "draft"       # Rédige mais ne fait rien sans confirmation
    SEMI_AUTO  = "semi_auto"   # Agit avec confirmation avant chaque action
    FULL_AUTO  = "full_auto"   # Agit librement dans les limites définies


@dataclass
class AgentPermission:
    category:        str
    level:           PermissionLevel
    max_amount:      float = 0.0
    allowed_actions: list  = field(default_factory=list)
    enabled:         bool  = False
    granted_at:      str   = ""


# ── Permissions par défaut (tout désactivé) ────────────────────────────────────

DEFAULT_PERMISSIONS = {
    "email": AgentPermission(
        category="email",
        level=PermissionLevel.READ_ONLY,
        allowed_actions=["read", "summarize"],
        enabled=False,
    ),
    "shopping": AgentPermission(
        category="shopping",
        level=PermissionLevel.SEMI_AUTO,
        max_amount=150.0,
        allowed_actions=["list", "search", "suggest"],
        enabled=False,
    ),
    "notifications": AgentPermission(
        category="notifications",
        level=PermissionLevel.READ_ONLY,
        allowed_actions=["read_sms", "read_calls", "read_voicemail"],
        enabled=False,
    ),
}


def load_permissions(uid: str) -> dict:
    """Charge les permissions de l'utilisateur depuis Supabase."""
    data = db_load(uid, "agent_permissions")
    if not data:
        return {k: AgentPermission(**{**vars(v)}) for k, v in DEFAULT_PERMISSIONS.items()}
    perms = {}
    for cat, raw in data.items():
        perms[cat] = AgentPermission(
            category=cat,
            level=PermissionLevel(raw.get("level", "read_only")),
            max_amount=raw.get("max_amount", 0.0),
            allowed_actions=raw.get("allowed_actions", []),
            enabled=raw.get("enabled", False),
            granted_at=raw.get("granted_at", ""),
        )
    # S'assurer que toutes les catégories existent
    for cat in DEFAULT_PERMISSIONS:
        if cat not in perms:
            perms[cat] = AgentPermission(**{**vars(DEFAULT_PERMISSIONS[cat])})
    return perms


def save_permissions(uid: str, perms: dict):
    """Sauvegarde les permissions dans Supabase."""
    data = {}
    for cat, p in perms.items():
        data[cat] = {
            "level":           p.level.value,
            "max_amount":      p.max_amount,
            "allowed_actions": p.allowed_actions,
            "enabled":         p.enabled,
            "granted_at":      p.granted_at,
        }
    db_save(uid, "agent_permissions", data)


def has_permission(uid: str, category: str, action: str) -> bool:
    """Vérifie si une action spécifique est autorisée."""
    perms = load_permissions(uid)
    perm  = perms.get(category)
    if not perm or not perm.enabled:
        return False
    return action in perm.allowed_actions


def log_agent_action(uid: str, agent: str, action: str, detail: str, status: str):
    """Enregistre chaque action dans le log Supabase (audit trail)."""
    try:
        from supabase_client import supabase
        supabase.table("agent_logs").insert({
            "uid":        uid,
            "agent":      agent,
            "action":     action,
            "detail":     detail,
            "status":     status,
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception:
        pass  # Logging ne doit jamais bloquer l'action principale


# ── UI Paramètres permissions ──────────────────────────────────────────────────

def show_permissions_settings(profile: dict):
    """Page de paramètres des permissions agent — réservée aux comptes Premium."""
    uid   = profile.get("user_id", "")
    perms = load_permissions(uid)

    st.markdown("### 🤖 Permissions de l'Agent Eldaana")
    st.caption(
        "Choisissez ce qu'Eldaana peut faire en votre nom. "
        "Vous pouvez modifier ou révoquer ces permissions à tout moment."
    )

    # ── EMAIL ──────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📧 Email")

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("**Connexion email** (IMAP/SMTP)")
        st.caption("Eldaana lit, résume et rédige vos emails.")
    with col2:
        email_enabled = st.toggle(
            "Activer email", value=perms["email"].enabled,
            label_visibility="collapsed", key="perm_email"
        )

    if email_enabled:
        _level_str = perms["email"].level.value
        opts = ["read_only", "draft", "semi_auto"]
        idx  = opts.index(_level_str) if _level_str in opts else 0
        email_level = st.radio(
            "Niveau d'action email",
            ["Lecture seule (résumés uniquement)",
             "Rédaction de brouillons (vous validez avant envoi)",
             "Envoi semi-auto (confirmation avant chaque envoi)"],
            index=idx,
            key="email_level"
        )
        level_map = {
            "Lecture seule (résumés uniquement)":              PermissionLevel.READ_ONLY,
            "Rédaction de brouillons (vous validez avant envoi)": PermissionLevel.DRAFT,
            "Envoi semi-auto (confirmation avant chaque envoi)": PermissionLevel.SEMI_AUTO,
        }
        perms["email"].level = level_map[email_level]
        perms["email"].allowed_actions = {
            PermissionLevel.READ_ONLY: ["read", "summarize"],
            PermissionLevel.DRAFT:     ["read", "summarize", "draft"],
            PermissionLevel.SEMI_AUTO: ["read", "summarize", "draft", "send"],
        }[perms["email"].level]

        if not profile.get("imap_configured"):
            st.warning("⚠️ Email non configuré — connectez votre compte dans les paramètres.")
            if st.button("🔗 Connecter mon email", key="btn_connect_email"):
                st.session_state.show_email_setup = True

    perms["email"].enabled = email_enabled
    if email_enabled:
        perms["email"].granted_at = datetime.utcnow().isoformat()

    # ── SHOPPING ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🛒 Courses & Shopping")

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("**Agent courses & commandes**")
        st.caption("Eldaana gère vos listes, recherche et commande avec votre accord.")
    with col2:
        shop_enabled = st.toggle(
            "Activer shopping", value=perms["shopping"].enabled,
            label_visibility="collapsed", key="perm_shop"
        )

    if shop_enabled:
        st.markdown("**Montant maximum par commande :**")
        max_amount = st.slider(
            "Limite par commande (€)", min_value=10, max_value=500,
            value=int(perms["shopping"].max_amount), step=10, key="shop_limit"
        )
        perms["shopping"].max_amount = float(max_amount)

        shop_level = st.radio(
            "Mode de commande",
            ["Suggestions uniquement (pas de commande réelle)",
             "Liste + commande avec confirmation obligatoire",
             "Commande directe sous la limite définie"],
            key="shop_level"
        )
        level_map_shop = {
            "Suggestions uniquement (pas de commande réelle)": PermissionLevel.READ_ONLY,
            "Liste + commande avec confirmation obligatoire":   PermissionLevel.SEMI_AUTO,
            "Commande directe sous la limite définie":          PermissionLevel.FULL_AUTO,
        }
        perms["shopping"].level = level_map_shop[shop_level]
        perms["shopping"].allowed_actions = {
            PermissionLevel.READ_ONLY: ["list", "search", "suggest"],
            PermissionLevel.SEMI_AUTO: ["list", "search", "suggest", "add_to_cart", "order_confirm"],
            PermissionLevel.FULL_AUTO: ["list", "search", "suggest", "add_to_cart", "order_auto"],
        }[perms["shopping"].level]

        st.info(
            f"💳 Eldaana ne peut commander que des articles inférieurs à **{max_amount}€** par transaction. "
            "Au-delà, elle vous demandera toujours confirmation."
        )

    perms["shopping"].enabled = shop_enabled

    # ── NOTIFICATIONS ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📱 Appels, SMS & Messages vocaux")

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("**Accès aux notifications Android & WhatsApp**")
        st.caption("Eldaana lit vos appels manqués, SMS et messages vocaux pour vous alerter.")
    with col2:
        notif_enabled = st.toggle(
            "Activer notifications", value=perms["notifications"].enabled,
            label_visibility="collapsed", key="perm_notif"
        )

    if notif_enabled:
        action_map = {
            "Appels manqués":                "read_calls",
            "SMS (lecture)":                 "read_sms",
            "Messages vocaux":               "read_voicemail",
            "WhatsApp (messages entrants)":  "read_whatsapp",
            "Résumé d'appel vocal WhatsApp": "summarize_whatsapp_voice",
        }
        reverse_map = {v: k for k, v in action_map.items()}
        current_labels = [
            reverse_map[a] for a in perms["notifications"].allowed_actions
            if a in reverse_map
        ]
        notif_actions = st.multiselect(
            "Eldaana peut accéder à :",
            list(action_map.keys()),
            default=current_labels,
            key="notif_actions"
        )
        perms["notifications"].allowed_actions = [action_map[a] for a in notif_actions]

        notif_response = st.radio(
            "Que peut faire Eldaana quand elle détecte un message important ?",
            ["M'alerter uniquement (notification push)",
             "M'alerter + rédiger une réponse suggérée (je valide)"],
            key="notif_response"
        )
        if "réponse suggérée" in notif_response and "draft_reply" not in perms["notifications"].allowed_actions:
            perms["notifications"].allowed_actions.append("draft_reply")

    perms["notifications"].enabled = notif_enabled

    # ── SAUVEGARDE ─────────────────────────────────────────────────────────────
    st.markdown("---")
    if st.button("💾 Sauvegarder mes permissions", type="primary", use_container_width=True):
        save_permissions(uid, perms)
        st.success("✅ Permissions mises à jour.")
        st.rerun()

    st.markdown(
        "<p style='font-size:0.75rem;color:#9ca3af;text-align:center;margin-top:1rem;'>"
        "🔒 Vos données restent sur nos serveurs sécurisés. "
        "Eldaana n'accède à vos comptes que dans les limites que vous avez définies. "
        "Toutes les actions sont enregistrées et consultables dans l'historique agent."
        "</p>",
        unsafe_allow_html=True
    )
