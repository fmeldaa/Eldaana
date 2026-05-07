"""
onboarding_questions.py — Banque de questions d'onboarding conversationnel Eldaana.

Chaque question existe en 4 variantes :
  - fr_text  : texte français avec emojis, ton chaleureux
  - fr_voice : version vocale française (sans emojis, phrases courtes)
  - en_text  : texte anglais
  - en_voice : version vocale anglaise

L'engine choisit la bonne variante selon (lang, mode).
"""

ONBOARDING_QUESTIONS = {
    # ============================================================
    # FREE — 5 questions essentielles
    # ============================================================
    "Q01": {
        "theme": "localisation",
        "tier_min": "free",
        "target_field": "localisation",
        "fr_text": "Tu vis où en ce moment ? Ville, pays — juste pour te situer 🌍",
        "fr_voice": "Dis-moi, tu vis dans quelle ville en ce moment ?",
        "en_text": "Where do you live right now? City, country — just so I can place you 🌍",
        "en_voice": "Tell me, what city do you live in right now?",
        "extraction_hint": "Extrait ville ET pays. Si une seule donnée fournie (ex: 'Libreville'), garde la ville et déduis le pays seulement si évident.",
    },
    "Q02": {
        "theme": "annee_naissance",
        "tier_min": "free",
        "target_field": "vie_personnelle.annee_naissance",
        "fr_text": "Tu es né(e) en quelle année ? Promis je ne le dirai à personne 😉",
        "fr_voice": "Tu es né en quelle année ? Promis, je ne le dirai à personne.",
        "en_text": "What year were you born? I promise I won't tell anyone 😉",
        "en_voice": "What year were you born? I promise I won't tell anyone.",
        "extraction_hint": "Extrait l'année (4 chiffres). Si l'user donne son âge, calcule l'année à partir de l'année actuelle (2026).",
    },
    "Q03": {
        "theme": "situation_amoureuse",
        "tier_min": "free",
        "target_field": "vie_personnelle.situation_amoureuse",
        "fr_text": "Côté cœur, tu es plutôt en solo ou en duo ces temps-ci ?",
        "fr_voice": "Côté cœur, tu es plutôt en solo ou en duo ces temps-ci ?",
        "en_text": "On the love side, are you flying solo or with someone these days?",
        "en_voice": "On the love side, are you flying solo or with someone these days?",
        "extraction_hint": "Mappe vers une de ces valeurs : 'célibataire', 'en couple', 'marié(e)', 'pacsé(e)', 'divorcé(e)', 'veuf/veuve'.",
    },
    "Q04": {
        "theme": "activite",
        "tier_min": "free",
        "target_field": "activite",
        "fr_text": "Tu fais quoi de tes journées ? Études, taf, projet perso ?",
        "fr_voice": "Tu fais quoi de tes journées en ce moment ?",
        "en_text": "How do you spend your days? Studies, work, personal project?",
        "en_voice": "How do you spend your days these days?",
        "extraction_hint": "Extrait type ('étudiant', 'salarié', 'entrepreneur', 'sans activité', 'autre') ET un détail libre (ex: 'développeur', 'master en droit').",
    },
    "Q05": {
        "theme": "passion",
        "tier_min": "free",
        "target_field": "vie_personnelle.passion_principale",
        "fr_text": "Si tu avais une journée libre demain, tu ferais quoi ?",
        "fr_voice": "Si tu avais une journée libre demain, tu ferais quoi ?",
        "en_text": "If you had a totally free day tomorrow, what would you do?",
        "en_voice": "If you had a totally free day tomorrow, what would you do?",
        "extraction_hint": "Extrait l'activité principale comme passion (ex: 'lire', 'voyager', 'cuisiner').",
    },

    # ============================================================
    # ESSENTIAL — 5 questions supplémentaires
    # ============================================================
    "Q06": {
        "theme": "famille",
        "tier_min": "essential",
        "target_field": "famille",
        "fr_text": "Tu as des enfants ou c'est pas (encore) au programme ?",
        "fr_voice": "Tu as des enfants ou c'est pas encore au programme ?",
        "en_text": "Do you have kids, or is that not (yet) on the agenda?",
        "en_voice": "Do you have kids, or is that not yet on the agenda?",
        "extraction_hint": "Extrait a_enfants (bool) et nombre_enfants (int) si mentionné.",
    },
    "Q07": {
        "theme": "regime",
        "tier_min": "essential",
        "target_field": "vie_personnelle.regime",
        "fr_text": "Tu manges de tout ou tu as un régime particulier ?",
        "fr_voice": "Tu manges de tout ou tu as un régime particulier ?",
        "en_text": "Do you eat everything or do you follow a specific diet?",
        "en_voice": "Do you eat everything or do you follow a specific diet?",
        "extraction_hint": "Mappe vers : 'omnivore', 'végétarien', 'végan', 'pescétarien', 'halal', 'casher', 'sans gluten', 'autre'.",
    },
    "Q08": {
        "theme": "transport",
        "tier_min": "essential",
        "target_field": "transports",
        "fr_text": "Pour te déplacer au quotidien, tu utilises quoi le plus souvent ?",
        "fr_voice": "Pour te déplacer au quotidien, tu utilises quoi ?",
        "en_text": "For daily travel, what do you use most often?",
        "en_voice": "For daily travel, what do you use most?",
        "extraction_hint": "Liste de moyens parmi : 'voiture', 'transport_commun', 'velo', 'a_pied', 'moto', 'teletravail', 'mixte'.",
    },
    "Q09": {
        "theme": "reseaux",
        "tier_min": "essential",
        "target_field": "reseaux_sociaux",
        "fr_text": "Tu es plutôt actif sur quels réseaux sociaux ?",
        "fr_voice": "Tu es plutôt actif sur quels réseaux sociaux ?",
        "en_text": "Which social networks are you most active on?",
        "en_voice": "Which social networks are you most active on?",
        "extraction_hint": "Liste parmi : 'instagram', 'facebook', 'tiktok', 'linkedin', 'twitter', 'snapchat', 'whatsapp', 'youtube', 'spotify'. Ne pas demander d'identifiants.",
    },
    "Q10": {
        "theme": "hobbies",
        "tier_min": "essential",
        "target_field": "vie_personnelle.hobbies",
        "fr_text": "À part ça, qu'est-ce qui te fait kiffer dans la vie ? 2-3 trucs qui te ressemblent",
        "fr_voice": "À part ça, qu'est-ce qui te fait kiffer dans la vie ? Cite-moi deux ou trois choses.",
        "en_text": "Besides that, what do you love in life? 2 or 3 things that feel like you",
        "en_voice": "Besides that, what do you love in life? Tell me two or three things.",
        "extraction_hint": "Liste de 1 à 5 hobbies en texte libre.",
    },

    # ============================================================
    # PREMIUM — 6 questions psychographiques
    # ============================================================
    "Q11": {
        "theme": "valeurs",
        "tier_min": "premium",
        "target_field": "valeurs.principales",
        "fr_text": "Si tu devais résumer ce qui compte le plus pour toi en 3 mots, ce serait quoi ?",
        "fr_voice": "Si tu devais résumer ce qui compte le plus pour toi en trois mots, ce serait quoi ?",
        "en_text": "If you had to sum up what matters most to you in 3 words, what would they be?",
        "en_voice": "If you had to sum up what matters most to you in three words, what would they be?",
        "extraction_hint": "Liste de 2 à 5 valeurs en mots simples (ex: 'famille', 'liberté', 'foi', 'créativité').",
    },
    "Q12": {
        "theme": "routine_matin",
        "tier_min": "premium",
        "target_field": "routine",
        "fr_text": "Tu te lèves vers quelle heure d'habitude ? Et ton premier réflexe du matin ?",
        "fr_voice": "Tu te lèves vers quelle heure d'habitude ? Et ton premier réflexe du matin ?",
        "en_text": "What time do you usually wake up? And your first morning reflex?",
        "en_voice": "What time do you usually wake up? And your first morning reflex?",
        "extraction_hint": "Extrait heure_lever (format HH:MM ou approximatif) et reflexe_matin (texte libre).",
    },
    "Q13": {
        "theme": "activite_physique",
        "tier_min": "premium",
        "target_field": "routine.activite_physique",
        "fr_text": "Tu bouges comment ? Sport régulier, marche, rien du tout — pas de jugement",
        "fr_voice": "Tu bouges comment au quotidien ? Sport régulier, marche, rien du tout ?",
        "en_text": "How do you move? Regular sport, walking, nothing at all — no judgment",
        "en_voice": "How do you move daily? Regular sport, walking, nothing at all?",
        "extraction_hint": "Extrait type ('sport_régulier', 'marche', 'occasionnel', 'rien') et fréquence si mentionnée.",
    },
    "Q14": {
        "theme": "sommeil",
        "tier_min": "premium",
        "target_field": "routine.heure_coucher",
        "fr_text": "Tu te couches tôt ou tu es plutôt couche-tard ?",
        "fr_voice": "Tu te couches tôt ou tu es plutôt couche-tard ?",
        "en_text": "Are you an early sleeper or a night owl?",
        "en_voice": "Are you an early sleeper or a night owl?",
        "extraction_hint": "Extrait heure_coucher approximative (HH:MM) ou catégorie ('early', 'medium', 'late').",
    },
    "Q15": {
        "theme": "objectifs",
        "tier_min": "premium",
        "target_field": "objectifs.an_1",
        "fr_text": "Sur les 12 prochains mois, qu'est-ce que tu aimerais accomplir ? Pro, perso, peu importe",
        "fr_voice": "Sur les douze prochains mois, qu'est-ce que tu aimerais accomplir ?",
        "en_text": "Over the next 12 months, what would you like to achieve? Work, personal, whatever",
        "en_voice": "Over the next twelve months, what would you like to achieve?",
        "extraction_hint": "Liste de 1 à 3 objectifs en texte libre.",
    },
    "Q16": {
        "theme": "preferences_communication",
        "tier_min": "premium",
        "target_field": "preferences.ton_communication",
        "fr_text": "Tu préfères que je sois plutôt directe et cash, ou plus douce et nuancée ?",
        "fr_voice": "Tu préfères que je sois plutôt directe et cash, ou plus douce et nuancée ?",
        "en_text": "Would you rather I be direct and blunt, or softer and more nuanced?",
        "en_voice": "Would you rather I be direct and blunt, or softer and more nuanced?",
        "extraction_hint": "Mappe vers : 'direct', 'doux', 'equilibre'.",
    },
}


# Ordre des questions selon le tier
QUESTION_POOL = {
    "free":      ["Q01", "Q02", "Q03", "Q04", "Q05"],
    "essential": ["Q01", "Q02", "Q03", "Q04", "Q05",
                  "Q06", "Q07", "Q08", "Q09", "Q10"],
    "premium":   ["Q01", "Q02", "Q03", "Q04", "Q05",
                  "Q06", "Q07", "Q08", "Q09", "Q10",
                  "Q11", "Q12", "Q13", "Q14", "Q15", "Q16"],
}


def get_question_text(qid: str, lang: str, mode: str) -> str:
    """Retourne le texte de la question dans la bonne variante.

    Args:
        qid  : identifiant de la question (ex: "Q01")
        lang : 'fr' ou 'en'
        mode : 'text' ou 'voice'
    """
    q = ONBOARDING_QUESTIONS[qid]
    key = f"{lang}_{mode}"
    return q.get(key, q.get(f"{lang}_text", q["fr_text"]))
