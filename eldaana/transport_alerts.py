"""
transport_alerts.py — Alertes transport PROACTIVES pour Eldaana.

Philosophie : ne pas attendre que l'utilisateur demande.
Vérifier les perturbations 60 min avant le départ habituel
et proposer des alternatives concrètes immédiatement.

APIs :
- IDFM PRIM Navitia : perturbations transports commun IDF
- TomTom Traffic : embouteillages voiture
"""

import requests
import streamlit as st
from datetime import datetime, timedelta
from timezone_utils import get_local_now


# ── IDs des lignes IDFM ───────────────────────────────────────────────────────
NAVITIA_BASE = "https://prim.iledefrance-mobilites.fr/marketplace/v2/navitia"

LINE_IDS = {
    "RER A":  "line:IDFM:C01742", "RER B": "line:IDFM:C01743",
    "RER C":  "line:IDFM:C01727", "RER D": "line:IDFM:C01728",
    "RER E":  "line:IDFM:C01729",
    "Métro 1":  "line:IDFM:C01371", "Métro 2":  "line:IDFM:C01372",
    "Métro 3":  "line:IDFM:C01373", "Métro 4":  "line:IDFM:C01374",
    "Métro 5":  "line:IDFM:C01375", "Métro 6":  "line:IDFM:C01376",
    "Métro 7":  "line:IDFM:C01377", "Métro 8":  "line:IDFM:C01378",
    "Métro 9":  "line:IDFM:C01379", "Métro 10": "line:IDFM:C01380",
    "Métro 11": "line:IDFM:C01381", "Métro 12": "line:IDFM:C01382",
    "Métro 13": "line:IDFM:C01383", "Métro 14": "line:IDFM:C01384",
    "Transilien H": "line:IDFM:C01737", "Transilien J": "line:IDFM:C01738",
    "Transilien K": "line:IDFM:C01739", "Transilien L": "line:IDFM:C01740",
    "Transilien N": "line:IDFM:C01741", "Transilien P": "line:IDFM:C01744",
    "Transilien R": "line:IDFM:C01745", "Transilien U": "line:IDFM:C01746",
}

# ── Alternatives par ligne (si perturbée, voici quoi prendre) ────────────────
# Format : {ligne: {"alternatives": [...], "conseil": str, "temps_extra_min": int}}
ALTERNATIVES = {
    "RER A": {
        "temps_extra_min": 20,
        "conseil": "Bus de substitution SNCF/RATP souvent mis en place aux gares principales.",
        "alternatives": [
            {"ligne": "Métro 1",  "note": "La Défense ↔ Château de Vincennes (Paris centre seulement)"},
            {"ligne": "Métro 14", "note": "Saint-Denis Pleyel ↔ Orly — passe par Paris centre"},
            {"ligne": "RER E",    "note": "Haussmann-St-Lazare ↔ Chelles/Tournan (alternative partielle Est)"},
            {"ligne": "Bus RATP", "note": "Lignes 241, 301, 304 en alternative locale"},
        ],
    },
    "RER B": {
        "temps_extra_min": 25,
        "conseil": "Vérifier les annonces en gare — des bus de substitution sont souvent mis en place.",
        "alternatives": [
            {"ligne": "Métro 4",  "note": "Paris Nord ↔ Montrouge (axe Nord-Sud Paris)"},
            {"ligne": "Métro 13", "note": "Saint-Denis ↔ Châtillon/Montrouge"},
            {"ligne": "Orlyval",  "note": "Uniquement pour l'aéroport d'Orly"},
            {"ligne": "TER / Car", "note": "Depuis les grandes gares en banlieue"},
        ],
    },
    "RER C": {
        "temps_extra_min": 30,
        "conseil": "Le RER C a souvent des perturbations entre Invalides et Bibliothèque F. Mitterrand.",
        "alternatives": [
            {"ligne": "Métro 6",        "note": "Nation ↔ Charles de Gaulle Étoile (rive gauche Paris)"},
            {"ligne": "Métro 13",       "note": "Versailles direction via Paris"},
            {"ligne": "Transilien N/L", "note": "Gare Montparnasse ou Saint-Lazare selon secteur"},
            {"ligne": "Tramway T2",     "note": "La Défense ↔ Versailles en alternative"},
        ],
    },
    "RER D": {
        "temps_extra_min": 30,
        "conseil": "Le RER D est la ligne la plus longue d'IDF — les perturbations y sont fréquentes.",
        "alternatives": [
            {"ligne": "Métro 1",       "note": "Paris intra-muros Est-Ouest"},
            {"ligne": "Transilien H",  "note": "Paris Nord ↔ Creil/Persan (partiel Nord)"},
            {"ligne": "Transilien R",  "note": "Gare de Lyon ↔ Melun/Montereau (partiel Sud)"},
            {"ligne": "Bus Transdev",  "note": "Lignes locales selon secteur"},
        ],
    },
    "RER E": {
        "temps_extra_min": 20,
        "conseil": "Le RER E dessert surtout l'Est parisien.",
        "alternatives": [
            {"ligne": "Métro 3",  "note": "Gallieni ↔ Pont de Levallois (Est-Ouest Paris)"},
            {"ligne": "Métro 9",  "note": "Mairie de Montreuil ↔ Pont de Sèvres"},
            {"ligne": "RER A",    "note": "Alternative partielle via correspondance"},
        ],
    },
    "Métro 1": {
        "temps_extra_min": 15,
        "conseil": "La ligne 1 est automatique — les pannes sont rares mais les incidents peuvent survenir.",
        "alternatives": [
            {"ligne": "Métro 14", "note": "Ligne automatique parallèle, moins surchargée"},
            {"ligne": "RER A",    "note": "Alternative rapide sur le même axe Est-Ouest"},
            {"ligne": "Bus 72",   "note": "Longe la Seine en surface"},
        ],
    },
    "Métro 4": {
        "temps_extra_min": 15,
        "conseil": "",
        "alternatives": [
            {"ligne": "RER B",    "note": "Axe Nord-Sud via Paris (Châtelet, Saint-Michel)"},
            {"ligne": "Métro 12", "note": "Axe Nord-Sud proche, Montrouge ↔ Saint-Denis"},
            {"ligne": "Métro 6",  "note": "Nation ↔ Charles de Gaulle Étoile"},
        ],
    },
    "Métro 13": {
        "temps_extra_min": 15,
        "conseil": "La 13 est souvent surchargée aux heures de pointe.",
        "alternatives": [
            {"ligne": "RER B",    "note": "Paris Nord ↔ banlieue Nord (CDG, Saint-Denis)"},
            {"ligne": "Métro 4",  "note": "Axe Nord-Sud central"},
            {"ligne": "Métro 12", "note": "Issy ↔ Saint-Denis-Basilique"},
        ],
    },
    "Métro 14": {
        "temps_extra_min": 15,
        "conseil": "Ligne automatique, fiable — perturbations rares.",
        "alternatives": [
            {"ligne": "Métro 1",  "note": "Parallèle sur l'axe Est-Ouest"},
            {"ligne": "RER A",    "note": "Même axe, plus rapide en grande banlieue"},
        ],
    },
    "Transilien H": {
        "temps_extra_min": 25,
        "conseil": "",
        "alternatives": [
            {"ligne": "RER D",   "note": "Paris Nord ↔ banlieue Nord (partiel)"},
            {"ligne": "Métro 5", "note": "Bobigny ↔ Pantin pour accès Paris"},
        ],
    },
    "Transilien J": {
        "temps_extra_min": 25,
        "conseil": "",
        "alternatives": [
            {"ligne": "RER A",         "note": "Via Cergy/Poissy pour accès Paris"},
            {"ligne": "Métro 13",      "note": "Accès Paris Nord depuis banlieue"},
            {"ligne": "Transilien L",  "note": "Paris Saint-Lazare ↔ Versailles/Cergy"},
        ],
    },
    "Transilien L": {
        "temps_extra_min": 20,
        "conseil": "",
        "alternatives": [
            {"ligne": "RER A",         "note": "Saint-Lazare ↔ La Défense ↔ Cergy"},
            {"ligne": "Transilien J",  "note": "Saint-Lazare ↔ Ermont/Pontoise"},
            {"ligne": "Métro 3",       "note": "Accès Paris depuis Saint-Lazare"},
        ],
    },
    "Transilien N": {
        "temps_extra_min": 25,
        "conseil": "",
        "alternatives": [
            {"ligne": "Métro 6",        "note": "Accès Paris depuis Montparnasse"},
            {"ligne": "Transilien L",   "note": "Montparnasse ↔ Versailles Rive Gauche"},
            {"ligne": "RER C",          "note": "Versailles direction via Paris"},
        ],
    },
}

# Valeur par défaut pour les lignes non mappées
DEFAULT_ALTERNATIVE = {
    "temps_extra_min": 20,
    "conseil": "Consultez l'application IDFM ou Citymapper pour des alternatives en temps réel.",
    "alternatives": [
        {"ligne": "Citymapper / Google Maps", "note": "Recalculez l'itinéraire en temps réel"},
        {"ligne": "VTC / Taxi",               "note": "Option de secours si délai critique"},
    ],
}


# ── Clés API ──────────────────────────────────────────────────────────────────

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


# ── Logique temporelle : fenêtre de départ ────────────────────────────────────

def _minutes_before_departure(profile: dict, tz_name: str = None) -> int | None:
    """
    Retourne le nombre de minutes avant le départ habituel.
    Retourne None si l'heure de départ n'est pas renseignée.
    Retourne une valeur négative si on est après l'heure de départ.
    """
    depart_str = profile.get("transport_detail", {}).get("depart_heure", "")
    if not depart_str:
        # Essayer l'heure de réveil + 1h comme fallback
        reveil = profile.get("heure_reveil", "")
        if reveil:
            try:
                h, m = map(int, reveil.split(":"))
                depart_str = f"{h+1:02d}:{m:02d}"
            except Exception:
                return None
        else:
            return None

    try:
        h, m = map(int, depart_str.split(":"))
        now  = get_local_now(tz_name=tz_name)
        # Heure de départ aujourd'hui
        depart = now.replace(hour=h, minute=m, second=0, microsecond=0)
        delta  = (depart - now).total_seconds() / 60
        return round(delta)
    except Exception:
        return None


def is_departure_window(profile: dict, tz_name: str = None,
                         window_min: int = 90) -> bool:
    """
    True si on est dans la fenêtre d'alerte avant le départ
    (entre -15 min et +window_min avant le départ).
    """
    mins = _minutes_before_departure(profile, tz_name)
    if mins is None:
        return False
    return -15 <= mins <= window_min


def minutes_until_departure_label(profile: dict, tz_name: str = None) -> str:
    """Ex: 'dans 45 min', 'maintenant', 'il y a 10 min'"""
    mins = _minutes_before_departure(profile, tz_name)
    if mins is None:
        return ""
    if mins > 60:
        h = mins // 60
        m = mins % 60
        return f"dans {h}h{m:02d}" if m else f"dans {h}h"
    if mins > 5:
        return f"dans {mins} min"
    if mins >= -5:
        return "maintenant"
    return f"il y a {abs(mins)} min"


# ── Appels API Navitia ────────────────────────────────────────────────────────

def get_line_disruptions(line_name: str) -> list[dict]:
    """Retourne les perturbations actives pour une ligne."""
    api_key = _navitia_key()
    if not api_key:
        return []

    line_id = LINE_IDS.get(line_name)
    if not line_id:
        return _search_disruptions_by_name(line_name, api_key)

    try:
        r = requests.get(
            f"{NAVITIA_BASE}/coverage/fr-idf/lines/{line_id}/disruptions",
            headers={"apikey": api_key},
            params={"count": 5},
            timeout=6,
        )
        if r.status_code != 200:
            return []

        disruptions = []
        for d in r.json().get("disruptions", []):
            if d.get("status") not in ("active", "future"):
                continue
            severity = d.get("severity", {}).get("name", "").lower()
            messages = d.get("messages", [])
            text = messages[0].get("text", "") if messages else d.get("cause", "Perturbation")
            disruptions.append({
                "line":     line_name,
                "message":  text[:250],
                "severity": severity,
                "cause":    d.get("cause", ""),
                "blocking": "blocking" in severity,
            })
        return disruptions

    except Exception:
        return []


def _search_disruptions_by_name(line_name: str, api_key: str) -> list[dict]:
    """Recherche générique par nom si l'ID n'est pas dans notre mapping."""
    try:
        r = requests.get(
            f"{NAVITIA_BASE}/coverage/fr-idf/disruptions",
            headers={"apikey": api_key},
            params={"count": 30},
            timeout=6,
        )
        if r.status_code != 200:
            return []
        results = []
        for d in r.json().get("disruptions", []):
            if d.get("status") not in ("active", "future"):
                continue
            for obj in d.get("impacted_objects", []):
                name = obj.get("pt_object", {}).get("name", "")
                if line_name.lower() in name.lower():
                    messages = d.get("messages", [])
                    text = messages[0].get("text", "") if messages else d.get("cause", "")
                    severity = d.get("severity", {}).get("name", "").lower()
                    results.append({
                        "line":     line_name,
                        "message":  text[:250],
                        "severity": severity,
                        "cause":    d.get("cause", ""),
                        "blocking": "blocking" in severity,
                    })
        return results[:3]
    except Exception:
        return []


# ── TomTom trafic voiture ────────────────────────────────────────────────────

def get_traffic_incidents(lat: float, lon: float, radius_km: int = 10) -> list[dict]:
    api_key = _tomtom_key()
    if not api_key:
        return []
    try:
        delta = radius_km / 111.0
        bbox  = f"{lon-delta},{lat-delta},{lon+delta},{lat+delta}"
        r = requests.get(
            "https://api.tomtom.com/traffic/services/5/incidentDetails",
            params={
                "key":      api_key,
                "bbox":     bbox,
                "fields":   "{incidents{type,properties{iconCategory,magnitudeOfDelay,events{description},startTime,endTime,from,to,delay,roadNumbers,timeValidity}}}",
                "language": "fr-FR",
                "t":        1335,
                "timeValidityFilter": "present",
            },
            timeout=6,
        )
        if r.status_code != 200:
            return []
        incidents = []
        for inc in r.json().get("incidents", []):
            props     = inc.get("properties", {})
            delay     = props.get("delay", 0)
            if delay < 120:
                continue
            events    = props.get("events", [])
            desc      = events[0].get("description", "Incident") if events else "Incident"
            incidents.append({
                "description": desc,
                "from":        props.get("from", ""),
                "to":          props.get("to", ""),
                "delay_min":   round(delay / 60),
                "road":        ", ".join(props.get("roadNumbers", [])),
            })
        incidents.sort(key=lambda x: x["delay_min"], reverse=True)
        return incidents[:3]
    except Exception:
        return []


# ── Logique principale ────────────────────────────────────────────────────────

def get_transport_alerts(profile: dict, weather: dict = None) -> dict:
    """
    Récupère toutes les alertes transport pour l'utilisateur.
    Inclut la sévérité et les alternatives si perturbation.
    """
    transport_info = profile.get("transport_detail", {})
    lines   = transport_info.get("lines", [])
    has_car = transport_info.get("has_car", False)
    tz_name = (weather or {}).get("timezone") or profile.get("timezone")

    tc_alerts = []
    traffic   = []

    for line in lines:
        disruptions = get_line_disruptions(line)
        for d in disruptions:
            # Attacher les alternatives
            d["alternatives_info"] = ALTERNATIVES.get(line, DEFAULT_ALTERNATIVE)
        tc_alerts.extend(disruptions)

    if has_car and weather:
        lat = weather.get("lat")
        lon = weather.get("lon")
        if lat and lon:
            traffic = get_traffic_incidents(lat, lon, radius_km=15)

    mins_before = _minutes_before_departure(profile, tz_name)
    in_window   = is_departure_window(profile, tz_name)
    depart_label = minutes_until_departure_label(profile, tz_name)

    # Séparer bloquants vs. mineurs
    blocking = [a for a in tc_alerts if a.get("blocking")]
    minors   = [a for a in tc_alerts if not a.get("blocking")]

    return {
        "tc_alerts":     tc_alerts,
        "blocking":      blocking,
        "minors":        minors,
        "traffic":       traffic,
        "has_alerts":    bool(tc_alerts or traffic),
        "is_urgent":     bool(blocking and in_window),
        "in_window":     in_window,
        "mins_before":   mins_before,
        "depart_label":  depart_label,
        "depart_heure":  transport_info.get("depart_heure", ""),
        "lines_checked": lines,
    }


def check_departure_alert(profile: dict, weather: dict = None) -> dict | None:
    """
    Retourne une alerte de départ si :
    - On est dans la fenêtre pré-départ (< 90 min)
    - ET au moins une perturbation bloquante est détectée
    Retourne None si tout va bien ou si hors fenêtre.
    """
    transport_info = profile.get("transport_detail", {})
    if not transport_info.get("lines"):
        return None

    tz_name = (weather or {}).get("timezone") or profile.get("timezone")
    if not is_departure_window(profile, tz_name, window_min=90):
        return None

    alerts = get_transport_alerts(profile, weather)
    if not alerts["tc_alerts"]:
        return None

    return alerts


# ── Formatage pour le briefing / prompt ──────────────────────────────────────

def format_transport_for_briefing(alerts: dict) -> str:
    """Formate les alertes pour le message de briefing (texte simple)."""
    if not alerts.get("has_alerts"):
        return ""

    lines = ["\n🚦 **Infos transport :**\n"]

    for a in alerts.get("tc_alerts", []):
        emoji = "🔴" if a.get("blocking") else "🟡"
        lines.append(f"{emoji} **{a['line']}** — {a['message'][:120]}")

    for t in alerts.get("traffic", []):
        road = f" ({t['road']})" if t.get("road") else ""
        lines.append(f"🚗 **+{t['delay_min']} min**{road} — {t['description']}")

    return "\n".join(lines)


def format_departure_alert_message(alerts: dict) -> str:
    """
    Message vocal / texte d'alerte départ avec alternatives.
    Optimisé pour être lu par la synthèse vocale.
    """
    if not alerts or not alerts.get("tc_alerts"):
        return ""

    lines_affected = list({a["line"] for a in alerts["tc_alerts"]})
    depart_label   = alerts.get("depart_label", "")

    msg = f"Attention, perturbation sur {' et '.join(lines_affected)}"
    if depart_label:
        msg += f". Ton départ est prévu {depart_label}."

    # Ajouter la première alternative
    first_alt_info = alerts["tc_alerts"][0].get("alternatives_info", {})
    alts = first_alt_info.get("alternatives", [])
    if alts:
        msg += f" Alternative possible : {alts[0]['ligne']}, {alts[0]['note']}."
        temps_extra = first_alt_info.get("temps_extra_min", 0)
        if temps_extra:
            msg += f" Prévoir environ {temps_extra} minutes de plus."

    conseil = first_alt_info.get("conseil", "")
    if conseil:
        msg += f" {conseil}"

    return msg


def format_transport_for_prompt(profile: dict) -> str:
    """Formate les infos transport du profil pour le system prompt."""
    transport_info = profile.get("transport_detail", {})
    if not transport_info:
        return ""

    lines_list = transport_info.get("lines", [])
    lines = ["\n### Transports habituels\n"]
    if lines_list:
        lines.append(f"- Lignes utilisées : {', '.join(lines_list)}")
    if transport_info.get("depart_heure"):
        lines.append(f"- Heure de départ habituelle : {transport_info['depart_heure']}")
    if transport_info.get("trajet_desc"):
        lines.append(f"- Trajet : {transport_info['trajet_desc']}")
    if transport_info.get("has_car"):
        lines.append("- Utilise aussi la voiture")
    return "\n".join(lines)


# ── Widget Streamlit : bannière d'alerte urgente ─────────────────────────────

def show_departure_alert_banner(alerts: dict):
    """
    Affiche une bannière d'alerte proactive en haut de la page.
    À appeler AVANT l'affichage du chat quand une perturbation est détectée.
    """
    if not alerts or not alerts.get("tc_alerts"):
        return

    is_urgent   = alerts.get("is_urgent", False)
    depart_label = alerts.get("depart_label", "")
    depart_heure = alerts.get("depart_heure", "")

    banner_bg    = "#fef2f2" if is_urgent else "#fffbeb"
    banner_border = "#ef4444" if is_urgent else "#f59e0b"
    icon = "🚨" if is_urgent else "⚠️"
    titre = "Perturbation sur ta ligne de départ !" if is_urgent else "Perturbation en cours"

    st.markdown(f"""
    <div style="
        background:{banner_bg};
        border:2px solid {banner_border};
        border-radius:16px;
        padding:1rem 1.2rem;
        margin-bottom:1rem;
    ">
        <p style="margin:0 0 0.3rem;font-size:1.05rem;font-weight:700;color:#991b1b;">
            {icon} {titre}
        </p>
        {"<p style='margin:0 0 0.5rem;font-size:0.9rem;color:#374151;'>Départ prévu à <b>" + depart_heure + "</b> (" + depart_label + ")</p>" if depart_heure else ""}
    </div>
    """, unsafe_allow_html=True)

    # Détail par ligne
    for alert in alerts["tc_alerts"]:
        line    = alert["line"]
        message = alert["message"]
        alt_info = alert.get("alternatives_info", DEFAULT_ALTERNATIVE)
        alts     = alt_info.get("alternatives", [])
        temps    = alt_info.get("temps_extra_min", 0)
        conseil  = alt_info.get("conseil", "")

        severity_emoji = "🔴" if alert.get("blocking") else "🟡"
        severity_label = "Trafic interrompu" if alert.get("blocking") else "Trafic perturbé"

        with st.expander(
            f"{severity_emoji} **{line}** — {severity_label}",
            expanded=is_urgent
        ):
            st.markdown(f"""
            <div style="background:white;border-radius:10px;padding:0.8rem;
                        border-left:4px solid {banner_border};margin-bottom:0.8rem;">
                <p style="margin:0;color:#374151;font-size:0.9rem;">{message}</p>
            </div>
            """, unsafe_allow_html=True)

            if alts:
                st.markdown(f"**🔄 Alternatives recommandées**"
                            + (f" *(prévoir +{temps} min)*" if temps else ""))
                for alt in alts:
                    st.markdown(f"""
                    <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:10px;
                                padding:0.6rem 0.8rem;margin:0.3rem 0;display:flex;align-items:center;">
                        <span style="font-weight:700;color:#16a34a;min-width:150px;">
                            🚇 {alt['ligne']}
                        </span>
                        <span style="color:#374151;font-size:0.88rem;">{alt['note']}</span>
                    </div>
                    """, unsafe_allow_html=True)

            if conseil:
                st.info(f"💡 {conseil}")

    # Lien Citymapper
    st.markdown("""
    <div style="margin-top:0.5rem;text-align:center;">
        <a href="https://citymapper.com/paris" target="_blank"
           style="color:#7c3aed;font-size:0.85rem;text-decoration:none;">
            📍 Ouvrir Citymapper pour l'itinéraire en temps réel →
        </a>
    </div>
    """, unsafe_allow_html=True)


def show_transport_status_sidebar(profile: dict, weather: dict = None):
    """
    Affiche un mini-résumé transport dans la sidebar.
    Vert si tout va bien, rouge si perturbation.
    """
    lines = profile.get("transport_detail", {}).get("lines", [])
    if not lines:
        return

    api_key = _navitia_key()
    if not api_key:
        return

    alerts = get_transport_alerts(profile, weather)
    depart_heure = profile.get("transport_detail", {}).get("depart_heure", "")

    if alerts["has_alerts"]:
        nb = len(alerts["tc_alerts"])
        label_lines = ", ".join(list({a["line"] for a in alerts["tc_alerts"]})[:2])
        st.markdown(f"""
        <div style="background:#fef2f2;border:1px solid #ef4444;border-radius:10px;
                    padding:0.5rem 0.7rem;margin:0.3rem 0;">
            <p style="margin:0;font-size:0.82rem;color:#991b1b;font-weight:600;">
                🔴 Perturbation — {label_lines}
            </p>
            {"<p style='margin:0;font-size:0.78rem;color:#6b7280;'>Départ : " + depart_heure + "</p>" if depart_heure else ""}
        </div>
        """, unsafe_allow_html=True)
    else:
        label = f"{', '.join(lines[:2])}"
        st.markdown(f"""
        <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:10px;
                    padding:0.5rem 0.7rem;margin:0.3rem 0;">
            <p style="margin:0;font-size:0.82rem;color:#16a34a;font-weight:600;">
                ✅ {label} — trafic normal
            </p>
            {"<p style='margin:0;font-size:0.78rem;color:#6b7280;'>Départ : " + depart_heure + "</p>" if depart_heure else ""}
        </div>
        """, unsafe_allow_html=True)
