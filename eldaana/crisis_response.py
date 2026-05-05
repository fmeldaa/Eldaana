"""
crisis_response.py — Détection et gestion des situations de détresse.

Trois niveaux :
- LEVEL_1 : Tristesse / mal-être général
- LEVEL_2 : Détresse sérieuse (épuisement, idées sombres)
- LEVEL_3 : Urgence immédiate (idées suicidaires actives, automutilation)

Architecture :
1. detect_crisis_level_fast()  — analyse locale par mots-clés (sans API)
2. detect_crisis_level_ai()    — analyse contextuelle via Haiku (si ambiguë)
3. get_crisis_system_prompt()  — instructions Claude adaptées au niveau
4. get_crisis_resources()      — numéros d'aide par pays
5. format_crisis_card_ui()     — carte HTML pour Streamlit
6. log_crisis_event()          — audit trail anonymisé (RGPD)
"""

import re
from anthropic import Anthropic
from datetime import datetime

client = Anthropic()


# ── HARD LIMITS — détection pédocriminelle et blocage session ─────────────────

# Mots-clés pédocriminels (avec contexte sexuel → block_session)
_PEDO_SEXUAL_KEYWORDS = [
    r"\bpédophil", r"\bpédocriminel",
    r"\babus\w* (sexuel|mineur|enfant)",
    r"\benfant\w* (nu|nue|sexuel|porn|érot)",
    r"\bmineur\w* (sexuel|porn|érot|nu|nue)",
    r"\bporn\w* (enfant|mineur|ado)",
    r"\binceste\w* (enfant|mineur)",
    r"\bsexe? avec (un |une )?(enfant|mineur|gamin|fillette|garçon)",
    r"\battouche\w* (enfant|mineur)",
    r"\bvioler? (un |une )?(enfant|mineur)",
    r"\bfantasme\w* (enfant|mineur|ado)",
    r"\bimage\w* (enfant|mineur)\w* (nud?|sexuel|porn)",
    r"\bcsam\b", r"\bshota\b", r"\bloli\b.{0,20}sexuel",
    # EN
    r"\bchild (porn|sex|abuse|nude|naked|sexu)",
    r"\bminor\w* (sex|porn|nude|sexu|abuse)",
    r"\bpedophil", r"\bpedo (sex|porn|abuse)",
    r"\bchild (molestat|groomin)",
    r"\bsex\w* with (a )?(child|minor|kid)",
]

# Autres catégories → soft_refuse (Claude répond avec HARD_LIMITS dans le prompt)
_SOFT_REFUSE_PATTERNS = [
    # Drogues
    r"\bsynth[eé]s[ei]\w* (de |d[''u])?(héro[ïi]ne|méthamphét|fentanyl|crack|meth\b)",
    r"\bfabriquer? (de |du |l[ae] )?(drogue|stupéfi|héro[ïi]ne|cocaïne|crack|meth)",
    r"\brecette\w* (drogue|héro[ïi]ne|méthamphét|lsd|mdma)",
    r"\bcomment (faire|produire|synthétiser) (de |du )?(drogue|meth|crack|fentanyl)",
    # Instructions pour blesser/tuer
    r"\bcomment (tuer|assassiner|empoisonner) (quelqu[''u]|une personne|mon |ma )",
    r"\binstruction\w* pour (tuer|blesser|attaquer|poignarder|étrangler)",
    r"\bbombe\w* (artisan|fabriqu|instruc)",
    r"\bexplosif\w* (fabriqu|instruc|comment)",
    # Porn explicite
    r"\b(écri[st]|génèr|produi[st]|fais|rédige)\w*.{0,40}(porn|sexe explicit|scène sexuelle explicit)",
]


def detect_hard_limit(message: str) -> str:
    """
    Analyse un message pour détecter les violations des HARD_LIMITS.

    Retourne :
      "block_session" — contenu pédocriminel avec contexte sexuel
                        → log Supabase table 'hard_limit_events' + ne pas envoyer à Claude
      "soft_refuse"   — drogues, violence, porn explicite
                        → envoyer à Claude avec HARD_LIMITS activé dans le prompt
      "ok"            — aucun problème détecté
    """
    msg = message.lower().strip()

    for pattern in _PEDO_SEXUAL_KEYWORDS:
        if re.search(pattern, msg):
            return "block_session"

    for pattern in _SOFT_REFUSE_PATTERNS:
        if re.search(pattern, msg):
            return "soft_refuse"

    return "ok"


def log_hard_limit_event(uid: str, result: str, message_snippet: str):
    """Log dans Supabase table 'hard_limit_events' (RGPD : 60 chars max)."""
    try:
        from supabase_client import supabase
        supabase.table("hard_limit_events").insert({
            "uid_hash":   hash(uid) % 9999999,
            "result":     result,
            "snippet":    message_snippet[:60] + "…",
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception:
        pass


# Message affiché quand block_session (jamais envoyé à Claude)
BLOCK_SESSION_MESSAGE = (
    "Je ne peux pas continuer sur ce sujet. "
    "Si tu traverses quelque chose de difficile, je suis là pour t'écouter autrement."
)


# ── MOTS-CLÉS PAR NIVEAU ──────────────────────────────────────────────────────
# Détection locale AVANT tout appel API — rapidité + économie de tokens

KEYWORDS_LEVEL_3 = [
    # FR
    "je vais me tuer", "je veux mourir", "je vais me suicider",
    "je veux en finir", "je vais me faire du mal", "je vais sauter",
    "j'ai envie de mourir", "je ne veux plus vivre", "je vais disparaître",
    "je prépare ma mort", "je passe à l'acte",
    # EN
    "i want to die", "i'm going to kill myself", "i want to end it",
    "i'm going to hurt myself", "i don't want to live",
]

KEYWORDS_LEVEL_2 = [
    # FR
    "je n'en peux plus", "j'en ai marre de vivre", "à quoi ça sert",
    "je veux disparaître", "je suis à bout", "je ne vois pas d'issue",
    "idées noires", "idées sombres", "plus envie de rien",
    "envie de tout arrêter", "je souffre trop", "insupportable",
    "je me sens inutile", "personne ne m'aime", "je suis un fardeau",
    "harcèlement", "on me harcèle", "je suis harcelé",
    "je me fais du mal", "je me blesse",
    # EN
    "i can't take it anymore", "what's the point", "i want to disappear",
    "harassed", "bullied", "hurting myself",
]

KEYWORDS_LEVEL_1 = [
    # FR
    "je suis déprimé", "dépression", "je suis triste", "je vais mal",
    "anxiété", "angoisse", "je souffre", "burnout", "épuisé",
    "je me sens seul", "isolé", "personne ne me comprend",
    "j'ai du mal", "c'est dur", "je n'y arrive plus",
    # EN
    "i'm depressed", "i'm sad", "i'm struggling", "anxiety", "burnout",
    "i feel alone", "nobody understands",
]


def detect_crisis_level_fast(message: str) -> int:
    """
    Détection rapide par mots-clés (sans appel API).
    Retourne 0, 1, 2 ou 3.
    0 = aucun signal détecté → continuer normalement.
    """
    msg_lower = message.lower().strip()

    for kw in KEYWORDS_LEVEL_3:
        if kw in msg_lower:
            return 3

    for kw in KEYWORDS_LEVEL_2:
        if kw in msg_lower:
            return 2

    for kw in KEYWORDS_LEVEL_1:
        if kw in msg_lower:
            return 1

    return 0


def detect_crisis_level_ai(message: str, conversation_history: list) -> int:
    """
    Détection approfondie via Claude Haiku.
    Appelée uniquement quand le contexte général de la conversation semble sombre
    sans mot-clé explicite.
    """
    recent = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
    context = "\n".join([
        f"{m['role'].upper()}: {m['content'][:200]}"
        for m in recent
        if isinstance(m.get("content"), str)
    ])

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            system=(
                "Analyse ce message et le contexte de conversation.\n"
                "Détermine le niveau de détresse émotionnelle.\n"
                "Réponds UNIQUEMENT par un chiffre : 0, 1, 2 ou 3.\n"
                "0 = aucune détresse particulière\n"
                "1 = tristesse / mal-être général\n"
                "2 = détresse sérieuse (épuisement, idées sombres, harcèlement)\n"
                "3 = urgence (idées suicidaires actives, automutilation imminente)\n"
                "Sois conservateur : si tu hésites entre 2 et 3, réponds 3."
            ),
            messages=[{
                "role": "user",
                "content": f"Contexte récent :\n{context}\n\nDernier message : {message}",
            }],
        )
        level_str = response.content[0].text.strip()
        return int(level_str) if level_str in ("0", "1", "2", "3") else 1
    except Exception:
        return 1  # Par sécurité, traiter comme niveau 1


# ── RESSOURCES PAR PAYS ───────────────────────────────────────────────────────

CRISIS_RESOURCES: dict = {
    "FR": {
        "crisis_line": "3114",
        "crisis_label": "Numéro National de Prévention du Suicide",
        "crisis_desc": "Gratuit · 24h/24 · 7j/7 · Professionnels de santé",
        "emergency": "15 (SAMU) ou 112",
        "chat_online": "https://www.3114.fr",
        "extra": [
            {"name": "SOS Amitié",       "number": "09 72 39 40 50"},
            {"name": "Fil Santé Jeunes", "number": "3224"},
        ],
    },
    "BE": {
        "crisis_line": "0800 32 123",
        "crisis_label": "Centre de Prévention du Suicide",
        "crisis_desc": "Gratuit · 24h/24",
        "emergency": "112",
        "chat_online": "https://www.preventionsuicide.be",
        "extra": [{"name": "Télé-Accueil", "number": "107"}],
    },
    "CH": {
        "crisis_line": "143",
        "crisis_label": "La Main Tendue",
        "crisis_desc": "Gratuit · 24h/24 · Anonyme",
        "emergency": "144",
        "chat_online": "https://www.143.ch",
        "extra": [{"name": "Die Dargebotene Hand", "number": "143"}],
    },
    "GB": {
        "crisis_line": "116 123",
        "crisis_label": "Samaritans",
        "crisis_desc": "Free · 24/7 · Anonymous",
        "emergency": "999",
        "chat_online": "https://www.samaritans.org",
        "extra": [{"name": "Crisis Text Line", "number": "Text SHOUT to 85258"}],
    },
    "CA": {
        "crisis_line": "1-866-APPELLE",
        "crisis_label": "Ligne québécoise de prévention du suicide",
        "crisis_desc": "Gratuit · 24h/24",
        "emergency": "911",
        "chat_online": "https://www.aqps.info",
        "extra": [{"name": "Talk Suicide Canada", "number": "1-833-456-4566"}],
    },
    "US": {
        "crisis_line": "988",
        "crisis_label": "988 Suicide & Crisis Lifeline",
        "crisis_desc": "Free · 24/7 · Call or text",
        "emergency": "911",
        "chat_online": "https://988lifeline.org",
        "extra": [{"name": "Crisis Text Line", "number": "Text HOME to 741741"}],
    },
    "CD": {
        "crisis_line": None,
        "crisis_label": "Service d'urgence",
        "crisis_desc": "",
        "emergency": "112",
        "chat_online": None,
        "extra": [],
    },
    "GA": {
        "crisis_line": None,
        "crisis_label": "Service d'urgence",
        "crisis_desc": "",
        "emergency": "1730",
        "chat_online": None,
        "extra": [],
    },
}


def get_crisis_resources(profile: dict) -> dict:
    """Retourne les ressources d'aide selon le pays de l'utilisateur."""
    country = profile.get("country", "FR")
    return CRISIS_RESOURCES.get(country, CRISIS_RESOURCES["FR"])


# ── INSTRUCTIONS SYSTÈME ADAPTÉES AU NIVEAU ───────────────────────────────────

def get_crisis_system_prompt(level: int, profile: dict) -> str:
    """
    Retourne le bloc d'instructions à injecter EN TÊTE du system prompt
    selon le niveau de détresse. Priorité absolue sur tout le reste.
    """
    if level == 0:
        return ""

    resources   = get_crisis_resources(profile)
    crisis_line = resources.get("crisis_line")
    emergency   = resources.get("emergency", "112")
    chat_online = resources.get("chat_online", "")

    if level == 3:
        num = crisis_line or emergency
        return f"""
⚠️ SITUATION D'URGENCE ÉMOTIONNELLE DÉTECTÉE — NIVEAU 3 ⚠️

L'utilisateur exprime des idées suicidaires actives ou une intention de se faire du mal.

INSTRUCTIONS ABSOLUES (priorité sur tout le reste du prompt) :
1. Commence par reconnaître la douleur avec chaleur : "“Je t'entends. Ce que tu ressens est réel.”"
2. Donne le numéro d'urgence EN PREMIER dans ta réponse : {num}
3. Sois directe sans être froide : "J'ai besoin que tu appelles le {num} maintenant."
4. Reste présente : ne termine JAMAIS la conversation, ne dis jamais "je ne peux pas t'aider"
5. NE donne AUCUNE information sur des méthodes, même indirectement
6. NE minimise PAS ("ça va aller", "c'est temporaire") avant d'avoir validé la douleur
7. NE joue PAS au thérapeute — tu es là pour écouter et orienter, pas diagnostiquer
8. Si la personne dit qu'elle est déjà en train d'agir : "Appelle le {emergency} maintenant."
"""

    elif level == 2:
        crisis_ref = f"le {crisis_line}" if crisis_line else f"les services d'urgence ({emergency})"
        extra = f"\nChat en ligne : {chat_online}" if chat_online else ""
        label = resources.get("crisis_label", "")
        desc  = resources.get("crisis_desc", "")
        return f"""
⚠️ DÉTRESSE ÉMOTIONNELLE SÉRIEUSE DÉTECTÉE — NIVEAU 2 ⚠️

L'utilisateur exprime une détresse profonde (épuisement, harcèlement, idées sombres).

INSTRUCTIONS :
1. Valide l'émotion en premier, sans minimiser ni précipiter les solutions
2. Écoute activement : pose une question douce pour comprendre la situation
3. Après avoir écouté, mentionne naturellement {crisis_ref} comme une option
4. NE dis PAS "tu devrais consulter un médecin" de façon froide et mécanique
5. Reste dans la chaleur de la relation : tu es sa confidente
6. Si la situation semble s'aggraver → appliquer les instructions niveau 3
7. NE joue PAS au thérapeute — sois présente, pas prescriptive

Ressource à mentionner si pertinent :
{f'Le {crisis_line} ({label}) — {desc}' if crisis_line else f'Les services d\'urgence : {emergency}'}{extra}
"""

    elif level == 1:
        return """
\U0001f49c MAL-Être DÉTECTÉ — NIVEAU 1

L'utilisateur exprime de la tristesse, de l'anxiété ou un mal-être général.

INSTRUCTIONS :
1. Accueille l'émotion avec douceur — ne passe pas directement aux conseils
2. Pose une question ouverte pour comprendre : "Qu'est-ce qui se passe en ce moment ?"
3. Sois présente et chaleureuse — c'est ta valeur principale ici
4. Si la personne semble aller mieux : accompagne-la doucement vers des pistes positives
5. Si la situation s'assombrit : escalader vers les instructions niveau 2
6. Tu peux mentionner des ressources de façon douce si c'est naturel
7. NE diagnostic PAS, NE prescris PAS, NE minimise PAS
"""

    return ""


# ── LOG ANONYMISÉ ─────────────────────────────────────────────────────────────

def log_crisis_event(uid: str, level: int, message_snippet: str):
    """
    Enregistre un événement de crise de façon anonymisée.
    NE stocke PAS le message complet — juste les 50 premiers caractères.
    """
    try:
        from supabase_client import supabase
        supabase.table("crisis_events").insert({
            "uid_hash":   hash(uid) % 999999,
            "level":      level,
            "snippet":    message_snippet[:50] + "...",
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception:
        pass


# ── CARTE UI STREAMLIT ────────────────────────────────────────────────────────

def format_crisis_card_ui(level: int, resources: dict) -> str:
    """Formate une carte d'aide visuelle pour l'affichage dans Streamlit."""
    crisis_line = resources.get("crisis_line")
    emergency   = resources.get("emergency", "112")
    label       = resources.get("crisis_label", "Aide disponible")
    desc        = resources.get("crisis_desc", "")
    chat        = resources.get("chat_online", "")
    extras      = resources.get("extra", [])

    bg     = "#FFF0F0" if level == 3 else "#F0F4FF"
    border = "#E24B4A" if level == 3 else "#7C3AED"
    title  = "\U0001f198 Aide disponible maintenant" if level == 3 else "\U0001f49c Tu n'es pas seul(e)"

    extra_html = "".join([
        f'<p style="margin:4px 0;font-size:0.82rem;color:#374151;">'
        f'• {e["name"]} : <strong>{e["number"]}</strong></p>'
        for e in extras
    ])

    chat_html = (
        f'<a href="{chat}" target="_blank" style="font-size:0.82rem;color:{border};">'
        f'\U0001f4ac Chat en ligne →</a>'
        if chat else ""
    )

    main_number = crisis_line or emergency

    return (
        f'<div style="background:{bg};border:2px solid {border};border-radius:16px;'
        f'padding:1rem 1.2rem;margin:1rem 0;">'
        f'<p style="font-size:1rem;font-weight:700;color:{border};margin:0 0 0.5rem 0;">'
        f'{title}</p>'
        f'<p style="font-size:0.88rem;color:#374151;margin:0 0 0.3rem 0;">'
        f'<strong>{label}</strong></p>'
        f'<p style="font-size:1.5rem;font-weight:800;color:{border};margin:0.3rem 0;">'
        f'\U0001f4de {main_number}</p>'
        + (f'<p style="font-size:0.8rem;color:#6b7280;margin:0 0 0.5rem 0;">{desc}</p>' if desc else "")
        + extra_html
        + chat_html
        + "</div>"
    )
