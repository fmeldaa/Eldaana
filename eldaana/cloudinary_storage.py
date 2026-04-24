"""
Gestion du stockage Cloudinary pour Eldaana.
Photos de profil et photos de tenues.
"""
import streamlit as st
import cloudinary
import cloudinary.uploader
import cloudinary.api


def _init():
    """Configure Cloudinary à partir des secrets Streamlit."""
    cfg = st.secrets.get("cloudinary", {})
    cloudinary.config(
        cloud_name=cfg.get("cloud_name", ""),
        api_key=cfg.get("api_key", ""),
        api_secret=cfg.get("api_secret", ""),
        secure=True,
    )


def upload_profile_photo(file_bytes: bytes, uid: str) -> str | None:
    """
    Upload la photo de profil sur Cloudinary.
    Retourne l'URL publique ou None en cas d'erreur.
    """
    try:
        _init()
        result = cloudinary.uploader.upload(
            file_bytes,
            public_id=f"eldaana/profiles/{uid}",
            overwrite=True,
            resource_type="image",
        )
        return result.get("secure_url")
    except Exception as e:
        st.error(f"Erreur upload photo : {e}")
        return None


def get_profile_photo_url(uid: str) -> str | None:
    """
    Retourne l'URL Cloudinary de la photo de profil, ou None si elle n'existe pas.
    Utilise un cache session pour éviter les appels répétés.
    """
    if not uid:
        return None

    cache_key = f"_cloudinary_photo_{uid}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    try:
        _init()
        result = cloudinary.api.resource(f"eldaana/profiles/{uid}")
        url = result.get("secure_url")
        st.session_state[cache_key] = url
        return url
    except Exception:
        st.session_state[cache_key] = None
        return None


def invalidate_photo_cache(uid: str):
    """Vide le cache photo pour forcer un rechargement."""
    st.session_state.pop(f"_cloudinary_photo_{uid}", None)
