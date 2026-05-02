"""
eldaana_voice_server/main.py
Serveur WebSocket temps réel pour le mode vocal Eldaana.
Architecture :
  Flutter ──(audio WAV)──▶ Whisper ──▶ Claude Haiku (stream) ──▶ TTS ──▶ Flutter

Lancement local :
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Variables d'environnement requises :
  ANTHROPIC_API_KEY
  OPENAI_API_KEY
"""

import asyncio
import base64
import io
import json
import os
import re
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
from dotenv import load_dotenv

load_dotenv(override=True)  # .env prime sur les variables Windows héritées
from anthropic import AsyncAnthropic
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Eldaana Voice Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Clients API ───────────────────────────────────────────────────────────────

_anthropic = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
_OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# Vérification au démarrage
if not _OPENAI_KEY:
    print("[STARTUP] ⚠️  OPENAI_API_KEY non configurée — Whisper et TTS désactivés")
    print("[STARTUP]     Fly.io : fly secrets set OPENAI_API_KEY=sk-...")

# ── Prompts ───────────────────────────────────────────────────────────────────

_VOICE_SYSTEM_BASE = """Tu es Eldaana — une confidente chaleureuse, bienveillante et directe.
Tu es en conversation VOCALE en temps réel. Règles strictes :
- Réponds en 2 à 3 phrases maximum
- Aucun markdown (pas de **, *, #, listes, tirets)
- Parle naturellement comme au téléphone
- Sois chaleureuse, directe, spontanée
- Si la question nécessite plus, résume l'essentiel en 2-3 phrases et propose d'envoyer les détails par écrit
Tu parles français."""

# Chemin vers les profils Streamlit (dossier frère eldaana/)
_PROFILES_DIR   = Path(__file__).parent.parent / "eldaana" / "user_data" / "profiles"
_SUPABASE_URL   = os.getenv("SUPABASE_URL", "")
_SUPABASE_KEY   = os.getenv("SUPABASE_KEY", "")
_MAX_HISTORY    = 40  # messages conservés


def _supabase_load_conversation(uid: str) -> list:
    """Charge l'historique depuis Supabase via REST."""
    if not uid or not _SUPABASE_URL or not _SUPABASE_KEY:
        return []
    try:
        resp = requests.get(
            f"{_SUPABASE_URL}/rest/v1/conversations",
            headers={
                "apikey":        _SUPABASE_KEY,
                "Authorization": f"Bearer {_SUPABASE_KEY}",
            },
            params={"uid": f"eq.{uid}", "select": "messages"},
            timeout=5,
        )
        if resp.status_code == 200 and resp.json():
            return resp.json()[0].get("messages", [])
    except Exception as e:
        print(f"[Supabase] load error: {e}")
    return []


def _supabase_save_conversation(uid: str, messages: list):
    """Sauvegarde l'historique dans Supabase via REST (upsert)."""
    if not uid or not _SUPABASE_URL or not _SUPABASE_KEY:
        return
    try:
        requests.post(
            f"{_SUPABASE_URL}/rest/v1/conversations",
            headers={
                "apikey":        _SUPABASE_KEY,
                "Authorization": f"Bearer {_SUPABASE_KEY}",
                "Content-Type":  "application/json",
                "Prefer":        "resolution=merge-duplicates",
            },
            json={
                "uid":        uid,
                "messages":   messages[-_MAX_HISTORY:],
                "updated_at": datetime.utcnow().isoformat() + "Z",
            },
            timeout=5,
        )
    except Exception as e:
        print(f"[Supabase] save error: {e}")


def _is_user_premium(uid: str) -> bool:
    """
    Vérifie si l'utilisateur a un abonnement Premium actif.
    Consulte Supabase profiles — champ premium_status.
    Fallback : accepte si Supabase non configuré (dev/test).
    """
    if not uid:
        return False
    if not _SUPABASE_URL or not _SUPABASE_KEY:
        return True  # Mode dev / Supabase non configuré → pas de blocage
    try:
        resp = requests.get(
            f"{_SUPABASE_URL}/rest/v1/profiles",
            params={"uid": f"eq.{uid}", "select": "premium_status,beta_tester"},
            headers={
                "apikey":        _SUPABASE_KEY,
                "Authorization": f"Bearer {_SUPABASE_KEY}",
            },
            timeout=4,
        )
        rows = resp.json()
        if rows:
            row = rows[0]
            if row.get("beta_tester"):
                return True
            return row.get("premium_status") == "active"
        # Profil non trouvé dans Supabase → refuser par sécurité
        return False
    except Exception as e:
        print(f"[Premium check] erreur: {e}")
        return True  # En cas d'erreur réseau → ne pas bloquer


def _load_profile(uid: str) -> dict:
    """Charge le profil JSON d'un utilisateur depuis son uid."""
    if not uid:
        return {}
    path = _PROFILES_DIR / f"{uid}.json"
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[Profile] Impossible de charger {uid}: {e}")
    return {}


def _build_system_prompt(profile: dict) -> str:
    """Injecte le profil utilisateur dans le prompt système."""
    if not profile:
        return _VOICE_SYSTEM_BASE

    parts = []
    if p := profile.get("prenom"):       parts.append(f"Prénom : {p}")
    if p := profile.get("age"):          parts.append(f"Âge : {p} ans")
    if p := profile.get("sexe"):         parts.append(f"Genre : {p}")
    if p := profile.get("ville"):        parts.append(f"Ville : {p}")
    if p := profile.get("situation"):    parts.append(f"Situation : {p}")
    if p := profile.get("profession"):   parts.append(f"Profession : {p}")
    if p := profile.get("objectifs"):    parts.append(f"Objectifs : {p}")
    if p := profile.get("centres_interet"): parts.append(f"Centres d'intérêt : {p}")

    if not parts:
        return _VOICE_SYSTEM_BASE

    profile_block = "\n".join(parts)
    prenom = profile.get("prenom", "l'utilisateur")
    return f"""{_VOICE_SYSTEM_BASE}

Profil de {prenom} (utilise ces infos pour personnaliser tes réponses) :
{profile_block}

Appelle-{("la" if profile.get("sexe","").lower() == "femme" else "le")} par son prénom {prenom} de temps en temps."""


# ── Contexte date + météo ─────────────────────────────────────────────────────

_WEATHER_CODES = {
    0: "ciel dégagé ☀️", 1: "peu nuageux 🌤️", 2: "partiellement nuageux ⛅",
    3: "couvert ☁️", 45: "brouillard 🌫️", 48: "brouillard givrant 🌫️",
    51: "bruine légère 🌦️", 61: "pluie légère 🌧️", 63: "pluie modérée 🌧️",
    65: "pluie forte 🌧️", 71: "neige légère ❄️", 73: "neige modérée ❄️",
    75: "neige forte ❄️", 80: "averses légères 🌦️", 81: "averses modérées 🌦️",
    82: "averses fortes ⛈️", 95: "orage ⛈️", 99: "orage avec grêle ⛈️",
}


def _fetch_context(profile: dict) -> str:
    """Retourne un bloc texte avec la date locale et la météo du jour."""
    # ── Date et heure locales ──────────────────────────────────────────────────
    tz_name = profile.get("timezone", "Europe/Paris")
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, Exception):
        tz = ZoneInfo("Europe/Paris")
    now = datetime.now(tz)
    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    mois  = ["janvier","février","mars","avril","mai","juin",
             "juillet","août","septembre","octobre","novembre","décembre"]
    date_str = f"{jours[now.weekday()]} {now.day} {mois[now.month-1]} {now.year}"
    heure_str = now.strftime("%Hh%M")

    lines = [f"Date : {date_str}", f"Heure locale : {heure_str}"]

    # ── Météo via Open-Meteo (gratuit, sans clé) ───────────────────────────────
    ville = profile.get("ville", "")
    if ville:
        try:
            geo = requests.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": ville, "count": 1, "language": "fr"},
                timeout=5,
            ).json().get("results", [])
            if geo:
                lat, lon = geo[0]["latitude"], geo[0]["longitude"]
                w = requests.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": lat, "longitude": lon,
                        "current": "temperature_2m,weathercode,windspeed_10m",
                        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                        "timezone": tz_name, "forecast_days": 1,
                    },
                    timeout=5,
                ).json()
                cur   = w.get("current", {})
                daily = w.get("daily", {})
                temp  = cur.get("temperature_2m", "?")
                code  = cur.get("weathercode", 0)
                desc  = _WEATHER_CODES.get(code, "temps variable")
                tmax  = (daily.get("temperature_2m_max") or [None])[0]
                tmin  = (daily.get("temperature_2m_min") or [None])[0]
                pluie = (daily.get("precipitation_probability_max") or [None])[0]
                lines.append(f"Météo à {ville} : {desc}, {temp}°C actuellement")
                if tmin and tmax:
                    lines.append(f"Températures du jour : {tmin}°C — {tmax}°C")
                if pluie is not None:
                    lines.append(f"Risque de pluie : {pluie}%")
        except Exception as e:
            print(f"[Context] météo indisponible: {e}")

    return "\n".join(lines)

_WHISPER_ARTIFACTS = {
    "", ".", "..", "...", "…",
    "sous-titres réalisés par la communauté d'amara.org",
    "sous-titres réalisés para la communauté d'amara.org",
    # Hallucinations Whisper connues (silence / bruit de fond)
    "la mise en oeuvre d'opencode et d'un certain nombre d'effets est en train de se réaliser.",
    "la mise en œuvre d'opencode et d'un certain nombre d'effets est en train de se réaliser.",
    "merci d'avoir regardé cette vidéo.",
    "merci d'avoir regardé.",
    "merci pour votre attention.",
    "sous-titres réalisés bénévolement par l'équipe d'amara.org",
    "transcription automatique par whisper.",
}

# ── Helpers synchrones (exécutés dans un thread executor) ─────────────────────

_MIME_EXT = {
    "webm": ("audio.webm", "audio/webm"),
    "wav":  ("audio.wav",  "audio/wav"),
    "mp4":  ("audio.mp4",  "audio/mp4"),
    "ogg":  ("audio.ogg",  "audio/ogg"),
}

def _whisper_sync(audio_bytes: bytes, fmt: str = "wav") -> Optional[str]:
    """Transcription Whisper (synchrone). fmt = 'wav' | 'webm' | 'mp4' | 'ogg'"""
    filename, mime = _MIME_EXT.get(fmt, ("audio.wav", "audio/wav"))
    print(f"[Whisper] envoi {len(audio_bytes)} octets, format={fmt}, mime={mime}")
    try:
        resp = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {_OPENAI_KEY}"},
            files={"file": (filename, io.BytesIO(audio_bytes), mime)},
            data={"model": "whisper-1", "language": "fr"},
            timeout=20,
        )
        print(f"[Whisper] status={resp.status_code}, réponse={resp.text[:200]}")
        if resp.status_code == 200:
            text = resp.json().get("text", "").strip()
            print(f"[Whisper] texte brut: '{text}'")
            return None if text.lower() in _WHISPER_ARTIFACTS else text
        else:
            print(f"[Whisper] ERREUR: {resp.status_code} — {resp.text}")
    except Exception as e:
        print(f"[Whisper] EXCEPTION: {e}")
    return None


def _tts_sync(text: str, voice: str = "nova") -> Optional[bytes]:
    """Génération TTS OpenAI (synchrone)."""
    try:
        resp = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {_OPENAI_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": "tts-1", "input": text, "voice": voice, "speed": 0.95},
            timeout=20,
        )
        return resp.content if resp.status_code == 200 else None
    except Exception:
        return None


# ── Helpers async ─────────────────────────────────────────────────────────────

async def whisper_async(audio: bytes, fmt: str = "wav") -> Optional[str]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _whisper_sync, audio, fmt)


async def tts_async(text: str, voice: str = "nova") -> Optional[bytes]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _tts_sync, text, voice)


def _split_sentences(text: str) -> list[str]:
    """Découpe un texte en phrases à la frontière naturelle."""
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 3]


# ── Helpers WebSocket ─────────────────────────────────────────────────────────

async def _send(ws: WebSocket, payload: dict):
    """Envoie un message JSON via WebSocket."""
    await ws.send_text(json.dumps(payload, ensure_ascii=False))


# ── Endpoint WebSocket principal ──────────────────────────────────────────────

@app.websocket("/voice")
async def voice_endpoint(ws: WebSocket):
    """
    Protocole WebSocket Eldaana :
      Client → Server  {"type": "audio",  "data": "<base64 WAV>", "voice": "nova"}
      Server → Client  {"type": "status", "step": "transcribing"|"thinking"|"speaking"}
      Server → Client  {"type": "transcript", "text": "..."}
      Server → Client  {"type": "text_chunk", "text": "..."}   ← streaming texte
      Server → Client  {"type": "audio", "data": "<base64 MP3>", "index": N, "total": N}
      Server → Client  {"type": "done"}
      Server → Client  {"type": "error", "message": "..."}
    """
    # ── Vérification Premium avant acceptation ────────────────────────────────
    uid = ws.query_params.get("uid", "")
    if not _is_user_premium(uid):
        await ws.accept()
        await _send(ws, {
            "type":    "error",
            "message": "Mode vocal réservé au plan Premium (29,99€/mois). "
                       "Passe à Premium pour accéder à Eldaana Voice.",
        })
        await ws.close()
        print(f"[WS] uid={uid!r} — accès refusé (non Premium)")
        return

    await ws.accept()

    # Charger le profil utilisateur depuis le uid (query param ?uid=)
    uid     = ws.query_params.get("uid", "")
    profile = _load_profile(uid)
    context = _fetch_context(profile)
    base_prompt = _build_system_prompt(profile)
    system  = f"{base_prompt}\n\nContexte actuel :\n{context}"
    prenom  = profile.get("prenom", "")
    print(f"[WS] uid={uid!r} profil={'chargé' if profile else 'anonyme'} prénom={prenom!r}")
    print(f"[WS] contexte: {context[:120]}")

    # Historique de conversation — chargé depuis Supabase pour continuité texte/voix
    history: list[dict] = _supabase_load_conversation(uid)
    print(f"[WS] historique chargé: {len(history)} messages")

    greeting = f"Coucou {prenom} ! Appuie sur le bouton et parle-moi 🎙️" if prenom \
               else "Coucou ! Appuie sur le bouton et parle-moi 🎙️"
    await _send(ws, {"type": "ready", "message": greeting})

    pending_meta = None

    while True:
        # ── Réception ─────────────────────────────────────────────────────────
        try:
            data = await ws.receive()
        except WebSocketDisconnect:
            print("[WS] client déconnecté")
            return

        # Trame de déconnexion WebSocket (cas ngrok / proxy)
        if data.get("type") == "websocket.disconnect":
            print("[WS] client déconnecté (disconnect frame)")
            return

        print(f"[WS] reçu: keys={list(data.keys())} text={data.get('text','')[:80]} bytes={len(data.get('bytes') or b'')}")

        # ── Décoder le message entrant ────────────────────────────────────────
        if "text" in data:
            try:
                msg = json.loads(data["text"])
            except Exception:
                continue
            if msg.get("type") == "audio_meta":
                pending_meta = msg
                continue
            if msg.get("type") == "audio":
                audio_bytes = base64.b64decode(msg["data"])
                voice_id    = msg.get("voice", "nova")
                audio_fmt   = msg.get("format", "wav")
            else:
                continue
        elif "bytes" in data:
            if not pending_meta:
                print("[WS] binaire sans meta — ignoré")
                continue
            audio_bytes  = data["bytes"]
            voice_id     = pending_meta.get("voice", "nova")
            audio_fmt    = pending_meta.get("format", "webm")
            pending_meta = None
            print(f"[WS] audio binaire: {len(audio_bytes)} octets fmt={audio_fmt}")
        else:
            continue

        # ── Pipeline complet — toute exception garde la connexion ouverte ─────
        try:
            # Étape 1 : Whisper ───────────────────────────────────────────────
            if not _OPENAI_KEY:
                await _send(ws, {"type": "error",
                    "message": "Clé OpenAI non configurée sur le serveur. "
                               "Contactez l'administrateur (fly secrets set OPENAI_API_KEY=…)"})
                continue

            print("[Pipeline] → Whisper")
            await _send(ws, {"type": "status", "step": "transcribing"})
            transcript = await whisper_async(audio_bytes, audio_fmt)

            if not transcript:
                await _send(ws, {"type": "error",
                    "message": "Rien capturé — parle plus fort ou plus longtemps"})
                continue

            print(f"[Pipeline] transcript: {transcript!r}")
            await _send(ws, {"type": "transcript", "text": transcript})
            history.append({"role": "user", "content": transcript})

            # ── Détection de crise (vocal) ────────────────────────────────────
            _crisis_system = system
            try:
                import sys, os
                # Chercher crisis_response.py dans le répertoire parent (eldaana/)
                _eldaana_path = os.path.join(os.path.dirname(__file__), "..", "eldaana")
                if _eldaana_path not in sys.path:
                    sys.path.insert(0, _eldaana_path)
                from crisis_response import (
                    detect_crisis_level_fast, get_crisis_system_prompt,
                    log_crisis_event,
                )
                _crisis_level = detect_crisis_level_fast(transcript)
                if _crisis_level >= 2:
                    log_crisis_event(uid, _crisis_level, transcript)
                _crisis_instr = get_crisis_system_prompt(_crisis_level, profile)
                if _crisis_instr:
                    _crisis_system = _crisis_instr + "\n\n---\n\n" + system
                    print(f"[Pipeline] crise niveau {_crisis_level} détectée")
            except Exception as _e:
                print(f"[Pipeline] crisis_response import error: {_e}")

            # Étape 2 : Claude ────────────────────────────────────────────────
            print("[Pipeline] → Claude")
            await _send(ws, {"type": "status", "step": "thinking"})

            full_text = ""
            buf       = ""
            sentences = []
            tts_tasks = {}

            async with _anthropic.messages.stream(
                model="claude-haiku-4-5-20251001",
                max_tokens=350,
                system=[{"type": "text", "text": _crisis_system,
                         "cache_control": {"type": "ephemeral"}}],
                messages=history,
            ) as stream:
                async for chunk in stream.text_stream:
                    full_text += chunk
                    buf       += chunk
                    await _send(ws, {"type": "text_chunk", "text": chunk})

                    for sep in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
                        idx = buf.find(sep)
                        if idx > 15:
                            sentence = buf[:idx + 1].strip()
                            buf      = buf[idx + len(sep):]
                            i = len(sentences)
                            sentences.append(sentence)
                            tts_tasks[i] = asyncio.create_task(
                                tts_async(sentence, voice_id)
                            )
                            break

            if buf.strip():
                i = len(sentences)
                sentences.append(buf.strip())
                tts_tasks[i] = asyncio.create_task(tts_async(buf.strip(), voice_id))

            print(f"[Pipeline] Claude OK — {len(sentences)} phrase(s), {len(full_text)} chars")
            history.append({"role": "assistant", "content": full_text})
            # Sauvegarde dans Supabase après chaque échange voix
            _supabase_save_conversation(uid, history)

            # Étape 3 : TTS + envoi ───────────────────────────────────────────
            print("[Pipeline] → TTS")
            await _send(ws, {"type": "status", "step": "speaking"})

            total = len(sentences)
            for i in range(total):
                task = tts_tasks.get(i)
                if not task:
                    continue
                try:
                    audio_data = await task
                except Exception as tts_err:
                    print(f"[TTS] phrase {i} ERREUR: {tts_err}")
                    audio_data = None
                if audio_data:
                    print(f"[TTS] phrase {i} → {len(audio_data)} octets envoyés")
                    await _send(ws, {
                        "type":  "audio",
                        "data":  base64.b64encode(audio_data).decode(),
                        "index": i,
                        "total": total,
                    })

            await _send(ws, {"type": "done"})
            print("[Pipeline] ✓ done")

        except WebSocketDisconnect:
            print("[Pipeline] WebSocket fermé pendant le traitement")
            return
        except Exception as exc:
            import traceback
            print(f"[Pipeline] ERREUR: {exc}")
            traceback.print_exc()
            if history and history[-1]["role"] == "user":
                history.pop()
            try:
                await _send(ws, {"type": "error", "message": str(exc)})
            except Exception:
                pass
            # connexion conservée → continue la boucle


# ── Page principale (permission micro permanente via HTTP) ────────────────────

_HERE = os.path.dirname(os.path.abspath(__file__))

@app.get("/")
async def index():
    resp = FileResponse(os.path.join(_HERE, "client_test.html"))
    resp.headers["ngrok-skip-browser-warning"] = "true"
    resp.headers["X-Frame-Options"] = "ALLOWALL"
    resp.headers["Content-Security-Policy"] = "frame-ancestors *"
    return resp

# Sert le logo Eldaana : cherche d'abord dans le dossier local (Docker),
# puis dans le dossier parent (développement local)
@app.get("/eldaana/logo.png")
async def logo():
    for path in [
        os.path.join(_HERE, "eldaana", "logo.png"),       # Docker : /app/eldaana/logo.png
        os.path.join(_HERE, "..", "eldaana", "logo.png"),  # Local  : ../eldaana/logo.png
    ]:
        if os.path.exists(path):
            return FileResponse(path)
    from fastapi import Response
    return Response(status_code=404)

# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "eldaana-voice-server"}
