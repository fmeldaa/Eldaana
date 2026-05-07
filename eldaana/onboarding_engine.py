"""
onboarding_engine.py — Moteur d'onboarding conversationnel Eldaana.

Fonctions publiques :
  maybe_ask_question(profile, context) → dict | None
  record_answer(profile, qid, user_message, lang) → dict

Convention tier : 'free' / 'essential' / 'premium'  (anglais sans accent).
Erreurs gracieuses : toute exception est catchée — l'onboarding ne casse jamais
la réponse principale d'Eldaana.
"""

import json
from datetime import datetime, timedelta
from typing import Optional

from onboarding_questions import (
    ONBOARDING_QUESTIONS,
    QUESTION_POOL,
    get_question_text,
)

# ============================================================
# RÈGLES DE TIMING
# ============================================================

MIN_MESSAGES_BEFORE_FIRST_QUESTION = 2   # Démarrage : après 2 messages utilisateur
MAX_QUESTIONS_PER_SESSION          = 3   # Max 3 questions par session (onglet)
RETRY_AFTER_HOURS                  = 24  # Délai avant de retenter une question esquivée
RETRY_AFTER_DAYS_HARD_SKIP         = 3   # Délai si l'user a explicitement skip

# Mots-clés d'esquive (FR + EN)
SKIP_KEYWORDS = [
    "skip", "passer", "plus tard", "pas envie", "je veux pas",
    "later", "not now", "don't want", "skip this", "next",
    "j'ai pas envie", "pas le temps", "no time", "aucune idée",
    "je sais pas", "i don't know", "no idea",
]

# ── Correspondance Phase 2 target_field → Phase 1 field (pour compatibilité) ─
# Permet à _is_field_already_filled de retrouver les données remplies via le
# formulaire Phase 1, et à _sync_phase1_fields de garder les deux en sync.
_PHASE1_MAP = {
    "localisation":                  "ville",
    "vie_personnelle.annee_naissance":"date_naissance",
    "vie_personnelle.situation_amoureuse": "situation_maritale",
    "activite":                      "profession",
    "vie_personnelle.passion_principale": "hobbies",
    "famille":                       "famille",
    "vie_personnelle.regime":        "habitudes_alimentaires",
    "transports":                    "transport",
    "reseaux_sociaux":               "social_networks",
    "vie_personnelle.hobbies":       "hobbies",
    "routine":                       "heure_reveil",   # partiel
}


# ============================================================
# FONCTIONS PUBLIQUES
# ============================================================

def maybe_ask_question(profile: dict, context: dict) -> Optional[dict]:
    """
    Décide si on pose une question d'onboarding maintenant.

    Args:
        profile : profil utilisateur complet (modifié en place si question posée)
        context : {
            'session_message_count'   : int   ← nb messages USER uniquement
            'session_questions_asked' : int   ← nb questions posées cette session
            'last_message_was_question': bool
            'lang' : 'fr' | 'en'
            'mode' : 'text' | 'voice'
            'tier' : 'free' | 'essential' | 'premium'
        }

    Returns:
        {'qid': str, 'text': str} ou None
    """
    try:
        # Règle 1 : laisser l'user s'exprimer d'abord
        if context.get("session_message_count", 0) < MIN_MESSAGES_BEFORE_FIRST_QUESTION:
            return None

        # Règle 2 : max 3 questions par session
        if context.get("session_questions_asked", 0) >= MAX_QUESTIONS_PER_SESSION:
            return None

        # Règle 3 : jamais deux questions d'affilée
        if context.get("last_message_was_question", False):
            return None

        tier = context.get("tier", "free")
        lang = context.get("lang", "fr")
        mode = context.get("mode", "text")

        next_qid = _next_eligible_question(profile, tier)
        if next_qid is None:
            return None  # onboarding terminé pour ce tier

        text = get_question_text(next_qid, lang, mode)

        # Marquer dans onboarding_state (persist via save_profile appelé par app.py)
        profile.setdefault("onboarding_state", {}).setdefault("questions_asked", []).append({
            "qid":       next_qid,
            "asked_at":  datetime.utcnow().isoformat(),
            "answered":  False,
            "skipped":   False,
        })

        return {"qid": next_qid, "text": text}

    except Exception:
        return None


def record_answer(profile: dict, qid: str, user_message: str,
                  lang: str = "fr") -> dict:
    """
    Tente d'extraire la réponse à la question qid depuis le message user.

    Args:
        profile      : profil utilisateur (modifié en place si extraction OK)
        qid          : identifiant de la question (ex: 'Q01')
        user_message : message brut de l'utilisateur
        lang         : 'fr' ou 'en' (pour le prompt d'extraction)

    Returns:
        {'extracted': bool, 'value': any, 'confidence': float}
        ou {'extracted': False, 'skip': True}
        ou {'extracted': False, 'low_confidence': True}
        ou {'extracted': False, 'error': str}
    """
    try:
        if _is_skip_response(user_message):
            _mark_skipped(profile, qid)
            return {"extracted": False, "skip": True}

        extracted = _extract_with_llm(qid, user_message, lang)

        if extracted is None:
            return {"extracted": False, "error": "llm_failed"}

        if extracted.get("confidence", 0) < 0.7:
            return {"extracted": False, "low_confidence": True}

        value = extracted["value"]
        target_field = ONBOARDING_QUESTIONS[qid]["target_field"]

        # Écriture dans le chemin Phase 2
        _set_nested_field(profile, target_field, value)

        # Écriture dans le chemin Phase 1 pour la compatibilité (indicateur %)
        _sync_phase1_fields(profile, qid, value)

        _mark_answered(profile, qid)

        return {
            "extracted":  True,
            "value":      value,
            "confidence": extracted["confidence"],
        }

    except Exception as e:
        return {"extracted": False, "error": str(e)}


# ============================================================
# HELPERS PRIVÉS
# ============================================================

def _next_eligible_question(profile: dict, tier: str) -> Optional[str]:
    """Retourne le QID de la prochaine question à poser, ou None."""
    pool = QUESTION_POOL.get(tier, QUESTION_POOL["free"])
    state = profile.get("onboarding_state", {})
    asked_records = state.get("questions_asked", [])

    # QIDs déjà traités (répondus ou en cooldown)
    blocked = {
        rec["qid"]
        for rec in asked_records
        if rec.get("answered") or _is_in_cooldown(rec)
    }

    for qid in pool:
        if qid in blocked:
            continue
        target = ONBOARDING_QUESTIONS[qid]["target_field"]
        if _is_field_already_filled(profile, target):
            continue
        return qid

    return None  # onboarding terminé pour ce tier


def _is_in_cooldown(record: dict) -> bool:
    """True si la question est en période de cooldown (esquivée ou posée récemment)."""
    if record.get("answered"):
        return True
    try:
        asked_at = datetime.fromisoformat(record["asked_at"])
    except Exception:
        return False
    cooldown = (
        timedelta(days=RETRY_AFTER_DAYS_HARD_SKIP)
        if record.get("skipped")
        else timedelta(hours=RETRY_AFTER_HOURS)
    )
    return datetime.utcnow() - asked_at < cooldown


def _is_field_already_filled(profile: dict, field_path: str) -> bool:
    """
    Vérifie si le champ cible (Phase 2) ou son équivalent Phase 1 est rempli.
    """
    # Vérification Phase 1 legacy en priorité
    legacy_key = _PHASE1_MAP.get(field_path)
    if legacy_key:
        val = profile.get(legacy_key)
        return _is_truthy(val)

    # Vérification dot-notation Phase 2
    parts = field_path.split(".")
    current = profile
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return _is_truthy(current)


def _is_truthy(val) -> bool:
    """Retourne True si val contient une donnée utilisable."""
    if val is None:
        return False
    if isinstance(val, bool):
        return True
    if isinstance(val, (int, float)):
        return val > 0
    if isinstance(val, str):
        return bool(val.strip())
    if isinstance(val, list):
        return len(val) > 0
    if isinstance(val, dict):
        return bool(val)
    return bool(val)


def _set_nested_field(profile: dict, field_path: str, value):
    """Écrit une valeur dans un chemin imbriqué (ex: 'vie_personnelle.regime')."""
    parts = field_path.split(".")
    current = profile
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


def _sync_phase1_fields(profile: dict, qid: str, value):
    """
    Synchronise les champs Phase 1 après une extraction Phase 2.
    Garantit que l'indicateur de complétion (Phase 1) progresse en temps réel.
    """
    try:
        if qid == "Q01":
            # value peut être {"ville": "Paris", "pays": "France"} ou "Paris"
            if isinstance(value, dict):
                profile["ville"] = value.get("ville", "")
            elif isinstance(value, str):
                profile["ville"] = value

        elif qid == "Q02":
            profile["date_naissance"] = str(value)

        elif qid == "Q03":
            profile["situation_maritale"] = str(value)

        elif qid == "Q04":
            # value peut être {"type": "salarié", "detail": "développeur"} ou str
            if isinstance(value, dict):
                profile["profession"] = value.get("detail", value.get("type", ""))
            else:
                profile["profession"] = str(value)

        elif qid == "Q05":
            existing = profile.get("hobbies", [])
            if isinstance(existing, list):
                entry = str(value)
                if entry not in existing:
                    existing.append(entry)
                profile["hobbies"] = existing
            else:
                profile["hobbies"] = [str(value)]

        elif qid == "Q06":
            fam = profile.setdefault("famille", {})
            if isinstance(value, dict):
                fam["a_enfants"]   = bool(value.get("a_enfants", False))
                fam["nb_enfants"]  = int(value.get("nombre_enfants", 0))
            else:
                fam["a_enfants"]   = bool(value)

        elif qid == "Q07":
            profile["habitudes_alimentaires"] = str(value)

        elif qid == "Q08":
            if isinstance(value, list):
                profile["transport"] = ", ".join(value)
            else:
                profile["transport"] = str(value)

        elif qid == "Q10":
            if isinstance(value, list):
                profile["hobbies"] = value
            else:
                profile["hobbies"] = [str(value)]

        elif qid == "Q12":
            if isinstance(value, dict):
                profile["heure_reveil"] = value.get("heure_lever", "")
            elif isinstance(value, str):
                profile["heure_reveil"] = value

    except Exception:
        pass  # Sync non-critique


def _is_skip_response(message: str) -> bool:
    """Détecte si l'utilisateur veut esquiver la question."""
    msg_lower = message.lower().strip()
    return any(kw in msg_lower for kw in SKIP_KEYWORDS)


def _mark_skipped(profile: dict, qid: str):
    """Marque une question comme esquivée (cooldown RETRY_AFTER_DAYS_HARD_SKIP)."""
    state = profile.setdefault("onboarding_state", {})
    for rec in state.get("questions_asked", []):
        if rec["qid"] == qid and not rec.get("answered"):
            rec["skipped"] = True
            return
    # Si la question n'a pas encore été enregistrée, l'ajouter comme esquivée
    state.setdefault("questions_asked", []).append({
        "qid":      qid,
        "asked_at": datetime.utcnow().isoformat(),
        "answered": False,
        "skipped":  True,
    })


def _mark_answered(profile: dict, qid: str):
    """Marque une question comme répondue."""
    state = profile.setdefault("onboarding_state", {})
    for rec in state.get("questions_asked", []):
        if rec["qid"] == qid:
            rec["answered"]    = True
            rec["answered_at"] = datetime.utcnow().isoformat()
            return


def _extract_with_llm(qid: str, user_message: str, lang: str = "fr") -> Optional[dict]:
    """
    Appelle Claude Haiku pour extraire la réponse de l'utilisateur.
    Retourne {'value': ..., 'confidence': float} ou None en cas d'erreur.

    Erreurs gracieuses : toute exception retourne None (jamais levée).
    """
    try:
        import anthropic

        question = ONBOARDING_QUESTIONS[qid]
        # Utilise la variante texte dans la bonne langue pour le contexte
        q_text = question.get(f"{lang}_text", question["fr_text"])

        prompt = (
            f'Tu es un extracteur de données silencieux. '
            f'Une question a été posée à l\'utilisateur :\n"{q_text}"\n\n'
            f'L\'utilisateur a répondu :\n"{user_message}"\n\n'
            f'Indication d\'extraction : {question["extraction_hint"]}\n\n'
            f'Retourne UNIQUEMENT un JSON valide, sans texte autour :\n'
            f'{{"value": <valeur extraite>, "confidence": <float 0-1>}}\n\n'
            f'Si la réponse est vague, hors-sujet ou inexploitable, retourne :\n'
            f'{{"value": null, "confidence": 0}}'
        )

        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()

        # Nettoyage des éventuels blocs ```json ... ```
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.lower().startswith("json"):
                text = text[4:].strip()

        return json.loads(text)

    except Exception:
        return None
