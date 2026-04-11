"""
timezone_utils.py — Heure locale basée sur la ville du profil.
Utilise les coordonnées de la ville (déjà récupérées par Open-Meteo)
pour déterminer le fuseau horaire exact.
"""

from datetime import datetime
import pytz
from timezonefinder import TimezoneFinder

_tf = TimezoneFinder()


def get_timezone_for_coords(lat: float, lon: float) -> pytz.BaseTzInfo:
    """Retourne le fuseau horaire pytz pour des coordonnées GPS."""
    try:
        tz_name = _tf.timezone_at(lat=lat, lng=lon)
        if tz_name:
            return pytz.timezone(tz_name)
    except Exception:
        pass
    return pytz.utc


def get_local_now(lat: float = None, lon: float = None,
                  tz_name: str = None) -> datetime:
    """
    Retourne datetime.now() dans le fuseau local du user.
    Priorité : tz_name (mis en cache) > coordonnées > UTC
    """
    try:
        if tz_name:
            tz = pytz.timezone(tz_name)
        elif lat is not None and lon is not None:
            tz = get_timezone_for_coords(lat, lon)
        else:
            tz = pytz.utc
        return datetime.now(tz)
    except Exception:
        return datetime.now()


def get_tz_name_for_city(city: str) -> str | None:
    """
    Retourne le nom du fuseau horaire pour une ville
    en utilisant l'API de géocodage Open-Meteo.
    """
    try:
        import requests
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "fr"},
            timeout=5,
        )
        results = r.json().get("results", [])
        if results:
            lat = results[0]["latitude"]
            lon = results[0]["longitude"]
            tz_name = _tf.timezone_at(lat=lat, lng=lon)
            return tz_name
    except Exception:
        pass
    return None
