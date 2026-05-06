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

WEATHER_CODES_EN = {
    0:  "Clear sky",
    1:  "Mainly clear",
    2:  "Partly cloudy",
    3:  "Overcast",
    45: "Foggy",
    48: "Icy fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Heavy drizzle",
    61: "Light rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Light showers",
    81: "Moderate showers",
    82: "Heavy showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}


def get_weather_desc(code: int, lang: str = "fr") -> str:
    """Retourne la description météo traduite pour le code WMO donné."""
    if lang == "en":
        return WEATHER_CODES_EN.get(code, "Variable conditions")
    desc, _ = WEATHER_CODES.get(code, ("Conditions variables", "🌡️"))
    return desc


def _c_to_f(celsius: float) -> int:
    """Convertit °C en °F."""
    return round(celsius * 9 / 5 + 32)


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


def get_weather(city: str, profile: dict = None) -> dict | None:
    """
    Retourne les données météo du jour pour une ville.
    profile (optionnel) : pour adapter les unités selon le pays (°F, mph).
    Retourne None si la ville est introuvable ou en cas d'erreur réseau.
    """
    coords = get_coordinates(city)
    if not coords:
        return None

    lat, lon, city_name = coords

    _profile    = profile or {}
    unit_temp   = _profile.get("unit_temp", "C")
    unit_speed  = _profile.get("unit_speed", "km/h")

    # Open-Meteo supporte nativement °F et mph
    temp_unit  = "fahrenheit" if unit_temp == "F" else "celsius"
    speed_unit = "mph"        if unit_speed == "mph" else "kmh"

    try:
        r = requests.get(
            WEATHER_URL,
            params={
                "latitude":         lat,
                "longitude":        lon,
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
                "timezone":           "auto",
                "forecast_days":      1,
                "temperature_unit":   temp_unit,
                "wind_speed_unit":    speed_unit,
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
        "unit_temp":    unit_temp,
        "unit_speed":   unit_speed,
    }


def outfit_suggestion(weather: dict, sexe: str = "") -> str:
    """Suggère une tenue selon la météo, le genre et la langue active."""
    import datetime, random
    from translations import t as _t_o
    temp   = weather["temp_max"]
    rain   = weather["rain_prob"] or 0
    wcode  = weather["weathercode"]
    femme  = sexe.lower() in ["femme"]

    # Seed basé sur le jour pour varier sans être aléatoire à chaque rechargement
    day_seed = datetime.date.today().toordinal()
    rng = random.Random(day_seed)

    # ── Choix des tenues selon la langue active ───────────────────────────────
    try:
        import streamlit as _st
        lang = _st.session_state.get("lang", "fr")
    except Exception:
        lang = "fr"

    _choices: dict = {
        "fr": {
            "hot_f":    ["une robe légère ou un short","une robe fluide et des sandales","un crop top + jupe légère","une combinaison estivale"],
            "hot_h":    ["un short et un t-shirt","bermuda et polo","short en lin et t-shirt léger","tenue légère sport-chic"],
            "warm_f":   ["une tenue légère — robe ou jupe","jupe midi + top","robe printanière","jean clair + blouse légère"],
            "warm_h":   ["pantalon léger et chemise","chino et polo","jean slim + t-shirt","pantalon en lin et chemise courte"],
            "mild_f":   ["jean + haut + veste légère","trench léger sur une robe","jean slim + pull fin + baskets","blazer décontracté sur un top"],
            "mild_h":   ["jean et veste légère","chino + chemise + cardigan","jean + pull col V","pantalon droit + bomber léger"],
            "cool_f":   ["manteau chaud + collants","doudoune courte + collants épais","manteau long + boots","pull oversize + legging chaud"],
            "cool_h":   ["manteau chaud + pull épais","doudoune + jean chaud","parka + pull en laine","manteau + écharpe légère"],
            "cold":     ["tenue bien chaude : manteau, écharpe et gants","grosse doudoune, bonnet et gants","manteau long, écharpe et sous-vêtements thermiques","tenue hivernale complète — couvre-toi bien !"],
        },
        "en": {
            "hot_f":    ["a light dress or shorts","a flowy dress and sandals","crop top + light skirt","a summer jumpsuit"],
            "hot_h":    ["shorts and a t-shirt","bermuda shorts and a polo","linen shorts and a light tee","casual sport-chic outfit"],
            "warm_f":   ["a light outfit — dress or skirt","midi skirt + top","a spring dress","light jeans + blouse"],
            "warm_h":   ["light trousers and a shirt","chinos and a polo","slim jeans + t-shirt","linen trousers and a short-sleeve shirt"],
            "mild_f":   ["jeans + top + light jacket","light trench coat over a dress","slim jeans + thin sweater + sneakers","relaxed blazer over a top"],
            "mild_h":   ["jeans and a light jacket","chinos + shirt + cardigan","jeans + V-neck sweater","straight trousers + light bomber"],
            "cool_f":   ["warm coat + tights","short puffer jacket + thick tights","long coat + boots","oversized sweater + warm leggings"],
            "cool_h":   ["warm coat + thick sweater","puffer jacket + warm jeans","parka + wool sweater","coat + light scarf"],
            "cold":     ["bundle up: coat, scarf and gloves","heavy puffer jacket, beanie and gloves","long coat, scarf and thermal underwear","full winter outfit — wrap up warm!"],
        },
    }
    c = _choices.get(lang, _choices["fr"])

    parts = []
    if temp >= 28:
        parts.append(rng.choice(c["hot_f"] if femme else c["hot_h"]))
        parts.append(_t_o("outfit_light_colors"))
    elif temp >= 22:
        parts.append(rng.choice(c["warm_f"] if femme else c["warm_h"]))
    elif temp >= 15:
        parts.append(rng.choice(c["mild_f"] if femme else c["mild_h"]))
    elif temp >= 8:
        parts.append(rng.choice(c["cool_f"] if femme else c["cool_h"]))
    else:
        parts.append(rng.choice(c["cold"]))

    if rain >= 60 or wcode in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
        parts.append(_t_o("outfit_rain_heavy"))
    elif rain >= 30:
        parts.append(_t_o("outfit_rain_light"))

    if wcode in [71, 73, 75, 77, 85, 86]:
        parts.append(_t_o("outfit_snow"))

    if weather.get("wind", 0) >= 40:
        parts.append(_t_o("outfit_wind"))

    return " — ".join(parts) if parts else _t_o("outfit_fallback")


def build_wakeup_message(weather: dict, profile: dict) -> str:
    """
    Message parlé au réveil : heure + météo + message positif.
    Optimisé pour la synthèse vocale (pas de markdown).
    """
    from translations import t as _t_w
    tz_name   = weather.get("timezone") or profile.get("timezone")
    now       = get_local_now(tz_name=tz_name)
    prenom    = profile.get("prenom", "")
    sexe      = profile.get("sexe", "").lower()
    heure_str = now.strftime("%H:%M")

    wcode = weather.get("weathercode", 0)
    if wcode == 0:
        positif = _t_w("wakeup_sunny")
    elif wcode in [71, 73, 75, 77, 85, 86]:
        positif = _t_w("wakeup_snow")
    elif wcode >= 51:
        positif = _t_w("wakeup_rain")
    else:
        positif = _t_w("wakeup_cloudy")

    try:
        import streamlit as _st_wu
        _lang_wu = _st_wu.session_state.get("lang", "fr")
    except Exception:
        _lang_wu = "fr"

    _desc_wu = get_weather_desc(weather.get("weathercode", 0), _lang_wu)
    _temp_wu = _c_to_f(weather["temp_current"]) if _lang_wu == "en" else weather["temp_current"]
    _tmax_wu = _c_to_f(weather["temp_max"])     if _lang_wu == "en" else weather["temp_max"]

    base = _t_w("wakeup_greeting",
                prenom=prenom,
                heure=heure_str,
                city=weather["city"],
                desc=_desc_wu,
                temp=_temp_wu,
                tmax=_tmax_wu,
                positif=positif)

    # Alertes transport au réveil (si départ bientôt)
    transport_alert = ""
    if is_departure_window(profile, tz_name=tz_name, window_min=120):
        departure_alerts = check_departure_alert(profile, weather)
        if departure_alerts and departure_alerts.get("tc_alerts"):
            transport_alert = " " + format_departure_alert_message(departure_alerts)

    ready_key = "wakeup_ready_f" if sexe == "femme" else "wakeup_ready_m"
    suffix = transport_alert if transport_alert else _t_w(ready_key)

    return base + suffix


def build_briefing(weather: dict, profile: dict, lang: str = "fr") -> str:
    """
    Génère le briefing personnalisé du matin / début de journée.
    C'est le premier message qu'Eldaana envoie à l'ouverture de l'app.
    Supporte FR et EN via le paramètre lang.
    """
    # t() lit st.session_state.lang automatiquement — appel dans le contexte Streamlit
    from translations import t as _t_w, t_list as _tl_w

    tz_name = weather.get("timezone") or profile.get("timezone")
    now     = get_local_now(tz_name=tz_name)
    hour    = now.hour
    prenom  = profile.get("prenom", "")
    sexe    = profile.get("sexe", "")

    jours  = _tl_w("days")
    mois   = _tl_w("months")
    date_str = f"{jours[now.weekday()]} {now.day} {mois[now.month - 1]}"

    # Salutation selon l'heure
    if hour < 12:
        salut = _t_w("greeting_morning", prenom=prenom)
    elif hour < 18:
        salut = _t_w("greeting_afternoon", prenom=prenom)
    else:
        salut = _t_w("greeting_evening", prenom=prenom)

    outfit = outfit_suggestion(weather, sexe)

    # Langue active pour description traduite et unité température
    try:
        import streamlit as _st_brf
        _lang_brf = _st_brf.session_state.get("lang", "fr")
    except Exception:
        _lang_brf = "fr"

    _desc_brf = get_weather_desc(weather.get("weathercode", 0), _lang_brf)

    # Conversion °C → °F si EN
    _tc  = weather["temp_current"]
    _tmin = weather["temp_min"]
    _tmax = weather["temp_max"]
    if _lang_brf == "en":
        _tc   = _c_to_f(_tc)
        _tmin = _c_to_f(_tmin)
        _tmax = _c_to_f(_tmax)

    lines = [
        f"{salut} {_t_w('greeting_date', date=date_str)}",
        "",
        _t_w("greeting_weather",
             emoji=weather["emoji"],
             city=weather["city"],
             desc=_desc_brf,
             temp=_tc,
             tmin=_tmin,
             tmax=_tmax),
    ]

    if weather["rain_prob"] and weather["rain_prob"] >= 30:
        lines.append(_t_w("greeting_rain", pct=weather["rain_prob"]))

    lines += [
        "",
        _t_w("greeting_outfit", outfit=outfit),
    ]

    # Alertes transport en temps réel
    transport_section = format_transport_for_briefing(
        get_transport_alerts(profile, weather)
    )
    if transport_section:
        lines.append(transport_section)

    close_key = "greeting_close_f" if sexe.lower() == "femme" else "greeting_close_m"
    lines += ["", _t_w(close_key)]

    return "\n".join(lines)
