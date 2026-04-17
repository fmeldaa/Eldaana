"""
weather.py — Météo en temps réel via Open-Meteo (gratuit, sans clé API)
et génération du briefing du matin personnalisé.
"""

import requests
from datetime import datetime
from timezone_utils import get_local_now
from transport_alerts import (
    get_transport_alerts, format_transport_for_briefing,
    check_departure_alert, format_departure_alert_message,
    is_departure_window,
)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL   = "https://api.open-meteo.com/v1/forecast"

# Codes météo WMO → (description française, emoji)
WEATHER_CODES = {
    0:  ("Ciel dégagé",           "☀️"),
    1:  ("Peu nuageux",            "🌤️"),
    2:  ("Partiellement nuageux",  "⛅"),
    3:  ("Couvert",                "☁️"),
    45: ("Brouillard",             "🌫️"),
    48: ("Brouillard givrant",     "🌫️"),
    51: ("Bruine légère",          "🌦️"),
    53: ("Bruine modérée",         "🌦️"),
    55: ("Bruine dense",           "🌦️"),
    61: ("Pluie légère",           "🌧️"),
    63: ("Pluie modérée",          "🌧️"),
    65: ("Pluie forte",            "🌧️"),
    71: ("Neige légère",           "❄️"),
    73: ("Neige modérée",          "❄️"),
    75: ("Neige forte",            "❄️"),
    77: ("Grains de neige",        "❄️"),
    80: ("Averses légères",        "🌦️"),
    81: ("Averses modérées",       "🌦️"),
    82: ("Averses fortes",         "⛈️"),
    85: ("Averses de neige",       "❄️"),
    86: ("Averses de neige fortes","❄️"),
    95: ("Orage",                  "⛈️"),
    96: ("Orage avec grêle",       "⛈️"),
    99: ("Orage avec forte grêle", "⛈️"),
}


def get_coordinates(city: str) -> tuple[float, float, str] | None:
    """Retourne (latitude, longitude, nom_ville) pour une ville."""
    try:
        r = requests.get(
            GEOCODING_URL,
            params={"name": city, "count": 1, "language": "fr"},
            timeout=5,
        )
        results = r.json().get("results", [])
        if results:
            res = results[0]
            return res["latitude"], res["longitude"], res.get("name", city)
    except Exception:
        pass
    return None


def get_weather(city: str) -> dict | None:
    """
    Retourne les données météo du jour pour une ville.
    Retourne None si la ville est introuvable ou en cas d'erreur réseau.
    """
    coords = get_coordinates(city)
    if not coords:
        return None

    lat, lon, city_name = coords

    try:
        r = requests.get(
            WEATHER_URL,
            params={
                "latitude":  lat,
                "longitude": lon,
                "current": ",".join([
                    "temperature_2m",
                    "weathercode",
                    "windspeed_10m",
                    "relative_humidity_2m",
                ]),
                "daily": ",".join([
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_probability_max",
                    "weathercode",
                ]),
                "timezone":      "auto",
                "forecast_days": 1,
            },
            timeout=5,
        )
        data = r.json()
    except Exception:
        return None

    current = data.get("current", {})
    daily   = data.get("daily",   {})

    wcode = current.get("weathercode", 0)
    desc, emoji = WEATHER_CODES.get(wcode, ("Conditions variables", "🌡️"))

    # Timezone via timezonefinder
    from timezone_utils import get_timezone_for_coords
    import pytz
    tz      = get_timezone_for_coords(lat, lon)
    tz_name = str(tz) if tz != pytz.utc else None

    return {
        "city":         city_name,
        "temp_current": round(current.get("temperature_2m", 0)),
        "temp_max":     round((daily.get("temperature_2m_max") or [0])[0]),
        "temp_min":     round((daily.get("temperature_2m_min") or [0])[0]),
        "description":  desc,
        "emoji":        emoji,
        "wind":         round(current.get("windspeed_10m", 0)),
        "humidity":     round(current.get("relative_humidity_2m", 0)),
        "rain_prob":    (daily.get("precipitation_probability_max") or [0])[0],
        "weathercode":  wcode,
        "timezone":     tz_name,
        "lat":          lat,
        "lon":          lon,
    }


def outfit_suggestion(weather: dict, sexe: str = "") -> str:
    """Suggère une tenue selon la météo et le genre."""
    temp   = weather["temp_max"]
    rain   = weather["rain_prob"] or 0
    wcode  = weather["weathercode"]
    femme  = sexe.lower() in ["femme"]

    parts = []

    # Vêtements principaux selon température
    if temp >= 28:
        parts.append("une robe légère ou un short" if femme else "un short et un t-shirt")
        parts.append("couleurs claires recommandées")
    elif temp >= 22:
        parts.append("une tenue légère — robe ou jupe" if femme else "pantalon léger et chemise")
    elif temp >= 15:
        parts.append("jean + haut + veste légère" if femme else "jean et veste légère")
    elif temp >= 8:
        parts.append("manteau chaud" + (" + collants" if femme else " + pull épais"))
    else:
        parts.append("tenue bien chaude : manteau, écharpe et gants")

    # Pluie
    if rain >= 60 or wcode in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
        parts.append("🌂 parapluie indispensable")
    elif rain >= 30:
        parts.append("imperméable au cas où")

    # Neige
    if wcode in [71, 73, 75, 77, 85, 86]:
        parts.append("🥾 bottes imperméables")

    # Vent fort
    if weather.get("wind", 0) >= 40:
        parts.append("attention au vent fort")

    return " — ".join(parts) if parts else "tenue adaptée à la météo"


def build_wakeup_message(weather: dict, profile: dict) -> str:
    """
    Message parlé au réveil : heure + météo + message positif.
    Optimisé pour la synthèse vocale (pas de markdown).
    """
    tz_name   = weather.get("timezone") or profile.get("timezone")
    now       = get_local_now(tz_name=tz_name)
    prenom    = profile.get("prenom", "")
    sexe      = profile.get("sexe", "").lower()
    heure_str = now.strftime("%Hh%M")

    wcode = weather.get("weathercode", 0)
    if wcode == 0:
        positif = "Le soleil est là, ça s'annonce comme une belle journée !"
    elif wcode in [71, 73, 75, 77, 85, 86]:
        positif = "Il neige dehors, prends ton temps, c'est beau !"
    elif wcode >= 51:
        positif = "Un peu de pluie ne t'arrêtera pas, tu vas briller aujourd'hui !"
    else:
        positif = "Quelques nuages, mais rien qui tienne face à toi aujourd'hui !"

    accord = "prête" if sexe == "femme" else "prêt"

    base = (
        f"Bonjour {prenom} ! Il est {heure_str}. "
        f"Aujourd'hui à {weather['city']} : {weather['description']}, "
        f"{weather['temp_current']} degrés, avec un max de {weather['temp_max']}. "
        f"{positif} "
    )

    # Alertes transport au réveil (si départ bientôt)
    transport_alert = ""
    if is_departure_window(profile, tz_name=tz_name, window_min=120):
        departure_alerts = check_departure_alert(profile, weather)
        if departure_alerts and departure_alerts.get("tc_alerts"):
            transport_alert = " " + format_departure_alert_message(departure_alerts)

    suffix = transport_alert if transport_alert else f"Tu es {accord} pour cette nouvelle journée ?"

    return base + suffix


def build_briefing(weather: dict, profile: dict) -> str:
    """
    Génère le briefing personnalisé du matin / début de journée.
    C'est le premier message qu'Eldaana envoie à l'ouverture de l'app.
    """
    tz_name = weather.get("timezone") or profile.get("timezone")
    now     = get_local_now(tz_name=tz_name)
    hour    = now.hour
    prenom = profile.get("prenom", "")
    sexe   = profile.get("sexe", "")

    jours_fr = ["lundi", "mardi", "mercredi", "jeudi",
                "vendredi", "samedi", "dimanche"]
    mois_fr  = ["janvier", "février", "mars", "avril", "mai", "juin",
                "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    date_str = f"{jours_fr[now.weekday()]} {now.day} {mois_fr[now.month - 1]}"

    # Salutation selon l'heure
    if hour < 12:
        salut = f"Bonjour {prenom} 🌸"
    elif hour < 18:
        salut = f"Bon après-midi {prenom} ☀️"
    else:
        salut = f"Bonsoir {prenom} 🌙"

    outfit = outfit_suggestion(weather, sexe)

    lines = [
        f"{salut} Nous sommes le **{date_str}**.",
        "",
        f"**{weather['emoji']} Météo à {weather['city']} :** "
        f"{weather['description']} · {weather['temp_current']}°C "
        f"(min {weather['temp_min']}° / max {weather['temp_max']}°)",
    ]

    if weather["rain_prob"] and weather["rain_prob"] >= 30:
        lines.append(f"☔ Risque de pluie : **{weather['rain_prob']}%**")

    lines += [
        "",
        f"**👗 Suggestion tenue :** {outfit}",
    ]

    # Alertes transport en temps réel
    transport_section = format_transport_for_briefing(
        get_transport_alerts(profile, weather)
    )
    if transport_section:
        lines.append(transport_section)

    lines += [
        "",
        f"Dis-moi comment tu vas — comment puis-je te rendre {'heureuse' if profile.get('sexe','').lower() == 'femme' else 'heureux'} aujourd'hui ? 💜",
    ]

    return "\n".join(lines)
