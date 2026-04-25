"""
stripe_payment.py — Gestion des abonnements Stripe pour Eldaana Premium.

Flux :
  1. create_checkout_session(uid, email, return_url)
     → redirige vers Stripe Checkout (9,99 €/mois)
  2. Stripe redirige vers ?stripe_success=1&session_id=xxx
  3. handle_stripe_return(uid) vérifie la session et met à jour le profil
  4. is_premium(uid) vérifie le statut à chaque chargement
"""

import streamlit as st
import stripe
from storage import db_load, db_save

PRICE_EUR      = 999          # centimes
PRICE_CURRENCY = "eur"
PRODUCT_NAME   = "Eldaana Premium"
PRODUCT_DESC   = "Mode vocal · Prédictions avancées · Agents autonomes · Budget & banque"


def _init():
    stripe.api_key = st.secrets["stripe"]["secret_key"]


# ── Création / récupération du price_id Stripe ────────────────────────────────

@st.cache_data(ttl=3600)
def _get_or_create_price_id() -> str:
    """Crée le produit+prix Eldaana Premium s'il n'existe pas encore."""
    _init()
    # Le lookup_key inclut le mode (test/live) pour éviter les conflits entre modes
    _mode = "test" if st.secrets["stripe"]["secret_key"].startswith("sk_test") else "live"
    _lookup_key = f"eldaana_premium_monthly_{_mode}"
    # Chercher un prix existant avec les mêmes métadonnées
    prices = stripe.Price.list(lookup_keys=[_lookup_key], limit=1)
    if prices.data:
        return prices.data[0].id

    # Créer le produit
    product = stripe.Product.create(
        name=PRODUCT_NAME,
        description=PRODUCT_DESC,
        metadata={"app": "eldaana"},
    )
    # Créer le prix récurrent
    price = stripe.Price.create(
        product=product.id,
        unit_amount=PRICE_EUR,
        currency=PRICE_CURRENCY,
        recurring={"interval": "month"},
        lookup_key=_lookup_key,
        transfer_lookup_key=True,
    )
    return price.id


# ── Checkout ──────────────────────────────────────────────────────────────────

def create_checkout_url(uid: str, email: str, return_url: str) -> str | None:
    """
    Crée une session Stripe Checkout et retourne l'URL de paiement.
    return_url : URL de l'app (ex: https://xxx.streamlit.app/?uid=...)
    """
    try:
        _init()
        price_id = _get_or_create_price_id()

        # Récupérer ou créer le customer Stripe
        profile = db_load(uid) or {}
        customer_id = profile.get("stripe_customer_id")

        if not customer_id:
            customer = stripe.Customer.create(
                email=email or None,
                metadata={"eldaana_uid": uid},
            )
            customer_id = customer.id
            profile["stripe_customer_id"] = customer_id
            db_save(profile)

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=return_url + "&stripe_success=1&session_id={CHECKOUT_SESSION_ID}",
            cancel_url=return_url + "&stripe_cancel=1",
            allow_promotion_codes=True,
            metadata={"eldaana_uid": uid},
        )
        return session.url
    except Exception as e:
        st.error(f"Erreur Stripe : {e}")
        return None


# ── Vérification retour Stripe ────────────────────────────────────────────────

def handle_stripe_return(uid: str) -> bool:
    """
    Appelé quand ?stripe_success=1 est dans l'URL.
    Vérifie la session et active le premium.
    Retourne True si premium activé.
    """
    session_id = st.query_params.get("session_id", "")
    if not session_id:
        return False
    try:
        _init()
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == "paid" or session.status == "complete":
            _activate_premium(uid, session.customer)
            return True
    except Exception:
        pass
    return False


# ── Vérification statut premium ───────────────────────────────────────────────

def is_premium(uid: str) -> bool:
    """
    Vérifie si l'utilisateur a un abonnement actif.
    Utilise le cache session pour éviter les appels Stripe répétés.
    """
    if not uid:
        return False

    cache_key = f"_premium_{uid}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    profile = db_load(uid) or {}

    # Vérification locale d'abord (plus rapide)
    if profile.get("premium_status") == "active":
        # Vérifier avec Stripe toutes les 24h max
        customer_id = profile.get("stripe_customer_id")
        if customer_id:
            try:
                _init()
                subs = stripe.Subscription.list(
                    customer=customer_id, status="active", limit=1
                )
                result = bool(subs.data)
                st.session_state[cache_key] = result
                if not result:
                    profile["premium_status"] = "inactive"
                    db_save(profile)
                return result
            except Exception:
                pass
        st.session_state[cache_key] = True
        return True

    st.session_state[cache_key] = False
    return False


def _activate_premium(uid: str, customer_id: str):
    """Met à jour le profil avec le statut premium."""
    profile = db_load(uid) or {}
    profile["premium_status"]    = "active"
    profile["stripe_customer_id"] = customer_id
    db_save(profile)
    st.session_state[f"_premium_{uid}"] = True


# ── Annulation ────────────────────────────────────────────────────────────────

def create_portal_url(uid: str, return_url: str) -> str | None:
    """Crée un lien vers le portail client Stripe (gérer/annuler l'abonnement)."""
    try:
        _init()
        profile = db_load(uid) or {}
        customer_id = profile.get("stripe_customer_id")
        if not customer_id:
            return None
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session.url
    except Exception:
        return None
