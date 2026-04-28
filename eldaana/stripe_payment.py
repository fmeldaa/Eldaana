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

PRICE_EUR_ESSENTIAL  = 999    # centimes — 9,99 €/mois
PRICE_EUR_PREMIUM    = 2900   # centimes — 29 €/mois
PRICE_EUR            = PRICE_EUR_ESSENTIAL  # rétrocompatibilité
PRICE_CURRENCY       = "eur"
PRODUCT_NAME_ESSENTIAL = "Eldaana Essentiel"
PRODUCT_DESC_ESSENTIAL = "Mode vocal · Prédictions journalières · Budget · Transport"
PRODUCT_NAME_PREMIUM   = "Eldaana Premium"
PRODUCT_DESC_PREMIUM   = "Tout Essentiel + voix illimitée · Forecast 30j · Facteurs détaillés · Accès bêta"
PRODUCT_NAME = PRODUCT_NAME_ESSENTIAL  # rétrocompatibilité
PRODUCT_DESC = PRODUCT_DESC_ESSENTIAL  # rétrocompatibilité


def _init():
    stripe.api_key = st.secrets["stripe"]["secret_key"]


# ── Création / récupération du price_id Stripe ────────────────────────────────

@st.cache_data(ttl=3600)
def _get_or_create_price_id(mode: str) -> str:
    """Crée le produit+prix Eldaana Essentiel (9,99€) s'il n'existe pas encore.
    Garde le lookup_key existant pour ne pas casser les abonnements en cours."""
    _init()
    # Note: le lookup_key historique est 'eldaana_premium_monthly_{mode}'
    # On le conserve pour la rétrocompatibilité (abonnés existants)
    _lookup_key = f"eldaana_premium_monthly_{mode}"
    prices = stripe.Price.list(lookup_keys=[_lookup_key], limit=1)
    if prices.data:
        return prices.data[0].id

    product = stripe.Product.create(
        name=PRODUCT_NAME_ESSENTIAL,
        description=PRODUCT_DESC_ESSENTIAL,
        metadata={"app": "eldaana", "tier": "essential"},
    )
    price = stripe.Price.create(
        product=product.id,
        unit_amount=PRICE_EUR_ESSENTIAL,
        currency=PRICE_CURRENCY,
        recurring={"interval": "month"},
        lookup_key=_lookup_key,
        transfer_lookup_key=True,
    )
    return price.id


@st.cache_data(ttl=3600)
def _get_or_create_price_id_premium29(mode: str) -> str:
    """Crée le produit+prix Eldaana Premium (29€) s'il n'existe pas encore."""
    _init()
    _lookup_key = f"eldaana_premium29_monthly_{mode}"
    prices = stripe.Price.list(lookup_keys=[_lookup_key], limit=1)
    if prices.data:
        return prices.data[0].id

    product = stripe.Product.create(
        name=PRODUCT_NAME_PREMIUM,
        description=PRODUCT_DESC_PREMIUM,
        metadata={"app": "eldaana", "tier": "premium"},
    )
    price = stripe.Price.create(
        product=product.id,
        unit_amount=PRICE_EUR_PREMIUM,
        currency=PRICE_CURRENCY,
        recurring={"interval": "month"},
        lookup_key=_lookup_key,
        transfer_lookup_key=True,
    )
    return price.id


def _current_mode() -> str:
    return "test" if st.secrets["stripe"]["secret_key"].startswith("sk_test") else "live"


# ── Checkout ──────────────────────────────────────────────────────────────────

def create_checkout_url(uid: str, email: str, return_url: str) -> str | None:
    """
    Crée une session Stripe Checkout et retourne l'URL de paiement.
    return_url : URL de l'app (ex: https://xxx.streamlit.app/?uid=...)
    """
    try:
        _init()
        price_id = _get_or_create_price_id(_current_mode())

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
        else:
            # Vérifier que le customer existe dans le mode actuel (test vs live)
            # Un customer live n'existe pas en mode test et vice-versa
            try:
                stripe.Customer.retrieve(customer_id)
            except stripe.error.InvalidRequestError:
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


def create_checkout_url_premium(uid: str, email: str, return_url: str) -> str | None:
    """Crée une session Stripe Checkout pour le plan Premium 29€/mois."""
    try:
        _init()
        price_id = _get_or_create_price_id_premium29(_current_mode())
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
        else:
            try:
                stripe.Customer.retrieve(customer_id)
            except stripe.error.InvalidRequestError:
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
            metadata={"eldaana_uid": uid, "tier": "premium"},
        )
        return session.url
    except Exception as e:
        st.error(f"Erreur Stripe Premium : {e}")
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

    # Beta-testeurs : accès premium sans abonnement Stripe
    if profile.get("beta_tester"):
        st.session_state[cache_key] = True
        return True

    # Vérification locale d'abord (plus rapide)
    if profile.get("premium_status") == "active":
        # Vérifier avec Stripe toutes les 24h max
        customer_id = profile.get("stripe_customer_id")
        if customer_id:
            try:
                _init()
                # Vérifier d'abord que le customer existe dans ce mode
                stripe.Customer.retrieve(customer_id)
                subs = stripe.Subscription.list(
                    customer=customer_id, status="active", limit=1
                )
                result = bool(subs.data)
                st.session_state[cache_key] = result
                if not result:
                    # Le customer existe MAIS n'a plus d'abonnement actif
                    # → on désactive vraiment (annulation, expiration…)
                    profile["premium_status"] = "inactive"
                    db_save(profile)
                return result
            except stripe.error.InvalidRequestError:
                # Customer créé dans un autre mode (test ↔ live) :
                # on NE touche PAS à Supabase — on fait confiance au statut local
                st.session_state[cache_key] = True
                return True
            except Exception:
                pass
        st.session_state[cache_key] = True
        return True

    st.session_state[cache_key] = False
    return False


def get_user_plan(uid: str) -> str:
    """
    Retourne le plan actif de l'utilisateur : 'free' | 'essential' | 'premium'.
    Distingue Essentiel (9,99€) de Premium (29€) en comparant le price_id
    de la souscription active avec les deux price_ids connus.
    """
    if not uid:
        return "free"

    cache_key = f"_plan_{uid}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    profile = db_load(uid) or {}

    # Beta-testeurs → premium complet
    if profile.get("beta_tester"):
        st.session_state[cache_key] = "premium"
        return "premium"

    if profile.get("premium_status") != "active":
        st.session_state[cache_key] = "free"
        return "free"

    customer_id = profile.get("stripe_customer_id")
    if not customer_id:
        st.session_state[cache_key] = "essential"  # statut local sans customer_id
        return "essential"

    try:
        _init()
        mode = _current_mode()
        price_id_premium29 = _get_or_create_price_id_premium29(mode)
        subs = stripe.Subscription.list(customer=customer_id, status="active", limit=5)
        plan = "free"
        for sub in subs.data:
            for item in sub["items"]["data"]:
                pid = item["price"]["id"]
                if pid == price_id_premium29:
                    plan = "premium"
                    break
                else:
                    plan = "essential"
            if plan == "premium":
                break

        st.session_state[cache_key] = plan
        if plan == "free":
            profile["premium_status"] = "inactive"
            db_save(profile)
        return plan

    except stripe.error.InvalidRequestError:
        # Mode test ↔ live : on fait confiance au statut local
        st.session_state[cache_key] = "essential"
        return "essential"
    except Exception:
        st.session_state[cache_key] = "essential"
        return "essential"


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
