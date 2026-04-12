"""
transport_alerts.py — Alertes transport en temps réel pour Eldaana.

APIs utilisées :
- Navitia.io (SNCF + RATP + tous transports FR) — clé gratuite sur navitia.io
- TomTom Traffic API — clé gratuite sur developer.tomtom.com
"""

import requests
import streamlit as st
from datetime import datetime


# ─── Navitia : perturbations transports en commun ────────────────────────────

NAVITIA_BASE = "https://prim.iledefrance-mobilites.fr/marketplace/v2/navitia"

# Correspondance noms courants → IDs Navitia Île-de-France
LINE_IDS = {
    # RER
    "RER A": "line:IDFM:C01742", "RER B": "line:IDFM:C01743",
    "RER C": "line:IDFM:C01727", "RER D": "line:IDFM:C01728",
    "RER E": "line:IDFM:C01729",
    # Métro
    "Métro 1": "line:IDFM:C01371", "Métro 2": "line:IDFM:C01372",
    "Métro 3": "line:IDFM:C01373", "Métro 4": "line:IDFM:C01374",
    "Métro 5": "line:IDFM:C01375", "Métro 6": "line:IDFM:C01376",
    "Métro 7": "line:IDFM:C01377", "Métro 8": "line:IDFM:C01378",
    "Métro 9": "line:IDFM:C01379", "Métro 10": "line:IDFM:C01380",
    "Métro 11": "line:IDFM:C01381", "Métro 12": "line:IDFM:C01382",
    "Métro 13": "line:IDFM:C01383", "Métro 14": "line:IDFM:C01384",
    # Transiliens
    "Transilien H": "line:IDFM:C01737", "Transilien J": "line:IDFM:C01738",
    "Transilien K": "line:IDFM:C01739", "Transilien L": "line:IDFM:C01740",
    "Transilien N": "line:IDFM:C01741", "Transilien P": "line:IDFM:C01744",
    "Transilien R": "line:IDFM:C01745", "Transilien U": "line:IDFM:C01746",
}


def _navitia_key() -> str | None:
    try:
        return st.secrets["navitia"]["api_key"]
    except Exception:
        return None


def _tomtom_key() -> str | None:
    try:
        return st.secrets["tomtom"]["api_key"]
    except Exception:
        return None


def get_line_disruptions(line_name: str) -> list[dict]:
    """
    Retourne les perturbations actives pour une ligne donnée.
    Chaque perturbation = {title, message, severity, cause}
    """
    api_key = _navitia_key()
    if not api_key:
        return []

    line_id = LINE_IDS.get(line_name)
    if not line_id:
        # Essayer une recherche générique par nom
        return _search_disruptions_by_name(line_name, api_key)

    try:
        r = requests.get(
            f"{NAVITIA_BASE}/coverage/fr-idf/lines/{line_id}/disruptions",
            headers={"apikey": api_key},
            params={"count": 5},
            timeout=5,
        )
        if r.status_code != 200:
            return []

        disruptions = []
        for d in r.json().get("disruptions", []):
            # Garder seulement les perturbations actives maintenant
            status = d.get("status", "")
            if status not in ("active", "future"):
                continue
            severity = d.get("severity", {}).get("name", "").lower()
            messages = d.get("messages", [])
            text = messages[0].get("text", "") if messages else d.get("cause", "Perturbation")
            disruptions.append({
                "title":    line_name,
                "message":  text[:200],
                "severity": severity,
                "cause":    d.get("cause", ""),
            })
        return disruptions
    except Exception:
        return []


def _search_disruptions_by_name(line_name: str, api_key: str) -> list[dict]:
    """Recherche générique si l'ID n'est pas dans notre mapping."""
    try:
        r = requests.get(
            f"{NAVITIA_BASE}/coverage/fr-idf/disruptions",
            headers={"apikey": api_key},
            params={"count": 20},
            timeout=5,
        )
        if r.status_code != 200:
            return []
        disruptions = []
        for d in r.json().get("disruptions", []):
            if d.get("status") not in ("active", "future"):
                continue
            # Chercher si la ligne est mentionnée dans les impacted_objects
            for obj in d.get("impacted_objects", []):
                name = obj.get("pt_object", {}).get("name", "")
                if line_name.lower() in name.lower():
                    messages = d.get("messages", [])
                    text = messages[0].get("text", "") if messages else d.get("cause", "")
                    disruptions.append({
                        "title":    line_name,
                        "message":  text[:200],
                        "severity": d.get("severity", {}).get("name", ""),
                        "cause":    d.get("cause", ""),
                    })
        return disruptions[:3]
    except Exception:
        return []


# ─── TomTom : embouteillages sur un trajet ───────────────────────────────────

def get_traffic_incidents(lat: float, lon: float, radius_km: int = 10) -> list[dict]:
    """
    Retourne les incidents de trafic autour d'un point GPS.
    radius_km : rayon de recherche en km
    """
    api_key = _tomtom_key()
    if not api_key:
        return []

    try:
        # Bounding box autour du point
        delta = radius_km / 111.0  # ~1 degré = 111 km
        bbox  = f"{lon-delta},{lat-delta},{lon+delta},{lat+delta}"

        r = requests.get(
            "https://api.tomtom.com/traffic/services/5/incidentDetails",
            params={
                "key":      api_key,
                "bbox":     bbox,
                "fields":   "{incidents{type,geometry{type,coordinates},properties{iconCategory,magnitudeOfDelay,events{description,code,iconCategory},startTime,endTime,from,to,length,delay,roadNumbers,timeValidity}}}",
                "language": "fr-FR",
                "t":        1335,
                "categoryFilter": "0,1,2,3,4,5,6,7,8,9,10,11",
                "timeValidityFilter": "present",
            },
            timeout=5,
        )
        if r.status_code != 200:
            return []

        incidents = []
        for inc in r.json().get("incidents", []):
            props = inc.get("properties", {})
            delay = props.get("delay", 0)
            if delay < 120:   # ignorer les retards < 2 min
                continue
            events = props.get("events", [])
            desc   = events[0].get("description", "") if events else "Incident routier"
            from_  = props.get("from", "")
            to_    = props.get("to", "")
            delay_min = round(delay / 60)
            incidents.append({
                "description": desc,
                "from":        from_,
                "to":          to_,
                "delay_min":   delay_min,
                "road":        ", ".join(props.get("roadNumbers", [])),
            })
        # Trier par délai décroissant
        incidents.sort(key=lambda x: x["delay_min"], reverse=True)
        return incidents[:3]
    except Exception:
        return []


# ─── Fonction principale : récupère tout pour un profil ──────────────────────

def get_transport_alerts(profile: dict, weather: dict = None) -> dict:
    """
    Retourne toutes les alertes transport pour l'utilisateur.
    Retourne : {
        "tc_alerts":      [...],  # perturbations transports en commun
        "traffic":        [...],  # embouteillages
        "has_alerts":     bool,
    }
    """
    transport_info = profile.get("transport_detail", {})
    lines   = transport_info.get("lines", [])     # ex: ["RER B", "Métro 13"]
    has_car = transport_info.get("has_car", False)

    tc_alerts = []
    traffic   = []

    # Perturbations transports en commun
    for line in lines:
        alerts = get_line_disruptions(line)
        tc_alerts.extend(alerts)

    # Embouteillages si l'utilisateur a une voiture
    if has_car and weather:
        lat = weather.get("lat")
        lon = weather.get("lon")
        if lat and lon:
            traffic = get_traffic_incidents(lat, lon, radius_km=15)

    return {
        "tc_alerts":  tc_alerts,
        "traffic":    traffic,
        "has_alerts": bool(tc_alerts or traffic),
    }


def format_transport_for_briefing(alerts: dict) -> str:
    """Formate les alertes pour le message d'accueil."""
    if not alerts.get("has_alerts"):
        return ""

    lines = ["\n🚦 **Infos transport du moment :**\n"]

    for a in alerts.get("tc_alerts", []):
        sev = a.get("severity", "")
        emoji = "🔴" if "blocking" in sev else "🟠" if "reduced" in sev else "🟡"
        lines.append(f"{emoji} **{a['title']}** — {a['message']}")

    for t in alerts.get("traffic", []):
        road = f" ({t['road']})" if t.get("road") else ""
        loc  = f" · {t['from']} → {t['to']}" if t.get("from") else ""
        lines.append(
            f"🚗 **+{t['delay_min']} min**{road}{loc} — {t['description']}"
        )

    return "\n".join(lines)


def format_transport_for_prompt(profile: dict) -> str:
    """Formate les infos transport du profil pour le system prompt."""
    transport_info = profile.get("transport_detail", {})
    if not transport_info:
        return ""

    lines = ["\n### Transports habituels\n"]

    lines_list = transport_info.get("lines", [])
    if lines_list:
        lines.append(f"- Lignes utilisées : {', '.join(lines_list)}")

    if transport_info.get("depart_heure"):
        lines.append(f"- Heure de départ habituelle : {transport_info['depart_heure']}")

    if transport_info.get("trajet_desc"):
        lines.append(f"- Trajet : {transport_info['trajet_desc']}")

    if transport_info.get("has_car"):
        lines.append("- Utilise aussi la voiture")

    return "\n".join(lines)
