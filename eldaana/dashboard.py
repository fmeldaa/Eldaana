"""
dashboard.py — Tableau de bord Eldaana.

Vue d'ensemble rapide :
- Météo du jour
- Humeur
- Budget restant
- Rappels courses
- Suggestion du jour
"""

import streamlit as st
from datetime import datetime
from humeur import load_humeur, SUGGESTIONS_HUMEUR
from budget import get_current_month_total
from shopping import get_reminders


def show_dashboard(profile: dict, weather: dict | None = None):
    """Affiche le tableau de bord."""
    prenom  = profile.get("prenom", "")
    user_id = profile.get("user_id", "")

    mois_fr = ["janvier","février","mars","avril","mai","juin",
               "juillet","août","septembre","octobre","novembre","décembre"]
    jours_fr = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
    now = datetime.now()
    date_str = f"{jours_fr[now.weekday()]} {now.day} {mois_fr[now.month-1]}"

    st.markdown(f"### 🏠 Bonjour {prenom} !")
    st.caption(date_str)

    # ── Ligne 1 : Météo + Humeur ─────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**☀️ Météo**")
        if weather:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#fdf4ff,#e8f8ff);
                        border:1.5px solid #c084fc;border-radius:16px;
                        padding:1rem;text-align:center;">
                <p style="font-size:2.5rem;margin:0 0 0.2rem 0;">{weather['emoji']}</p>
                <p style="font-size:1.4rem;font-weight:700;color:#7c3aed;margin:0;">
                    {weather['temp_current']}°C
                </p>
                <p style="color:#6b7280;margin:0;font-size:0.85rem;">
                    {weather['description']}<br>
                    ↑{weather['temp_max']}° ↓{weather['temp_min']}°
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Ajoute ta ville dans le profil pour voir la météo")

    with col2:
        st.markdown("**😊 Humeur du jour**")
        humeur = load_humeur(user_id)
        if humeur:
            code  = humeur.get("code", "")
            label = humeur.get("label", "")
            sugg  = SUGGESTIONS_HUMEUR.get(code, {})
            titre = sugg.get("titre", "")
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#fdf4ff,#f0f4ff);
                        border:1.5px solid #c084fc;border-radius:16px;
                        padding:1rem;text-align:center;min-height:120px;
                        display:flex;flex-direction:column;justify-content:center;">
                <p style="font-size:1.8rem;margin:0 0 0.3rem 0;">{label.split()[0]}</p>
                <p style="color:#7c3aed;font-weight:600;margin:0;font-size:0.9rem;">{titre}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#f9fafb;border:1.5px dashed #d1d5db;border-radius:16px;
                        padding:1rem;text-align:center;min-height:120px;
                        display:flex;flex-direction:column;justify-content:center;">
                <p style="color:#9ca3af;margin:0;">Non renseignée</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Ligne 2 : Budget + Courses ───────────────────────────────────────────────
    col3, col4 = st.columns(2)

    with col3:
        st.markdown("**💰 Budget du mois**")
        summary = get_current_month_total(user_id)
        if summary["budget_mensuel"] > 0:
            pct      = summary["pourcentage"]
            restant  = summary["restant"]
            color    = "#22c55e" if pct < 60 else "#f59e0b" if pct < 80 else "#ef4444"
            emoji_b  = "🟢" if pct < 60 else "🟡" if pct < 80 else "🔴"
            st.markdown(f"""
            <div style="background:white;border:1.5px solid {color};border-radius:16px;padding:1rem;">
                <p style="margin:0 0 0.3rem 0;font-size:0.85rem;color:#6b7280;">Utilisé</p>
                <p style="margin:0 0 0.5rem 0;font-size:1.5rem;font-weight:700;color:{color};">
                    {pct:.0f}%
                </p>
                <p style="margin:0;font-size:0.85rem;color:#374151;">
                    {emoji_b} Restant : <b>{restant:.0f} €</b>
                </p>
            </div>
            """, unsafe_allow_html=True)
        elif summary["total"] > 0:
            st.markdown(f"""
            <div style="background:white;border:1.5px solid #c084fc;border-radius:16px;padding:1rem;">
                <p style="margin:0;color:#374151;">💸 Dépensé ce mois : <b>{summary['total']:.0f} €</b></p>
                <p style="margin:0.3rem 0 0;font-size:0.8rem;color:#9ca3af;">
                    Définis un budget mensuel pour le suivi
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#f9fafb;border:1.5px dashed #d1d5db;border-radius:16px;padding:1rem;">
                <p style="color:#9ca3af;margin:0;text-align:center;">Aucune donnée budget</p>
            </div>
            """, unsafe_allow_html=True)

    with col4:
        st.markdown("**🛒 Courses à faire**")
        reminders = get_reminders(user_id)
        if reminders:
            urgent = [r for r in reminders if r["days_left"] <= 0]
            bientot = [r for r in reminders if r["days_left"] > 0]
            html = '<div style="background:white;border:1.5px solid #fca5a5;border-radius:16px;padding:1rem;">'
            if urgent:
                for r in urgent[:3]:
                    html += f'<p style="margin:0 0 0.2rem;font-size:0.9rem;">🔴 <b>{r["name"].capitalize()}</b> — épuisé</p>'
            if bientot:
                for r in bientot[:2]:
                    html += f'<p style="margin:0 0 0.2rem;font-size:0.9rem;">🟡 <b>{r["name"].capitalize()}</b> — dans {r["days_left"]}j</p>'
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#f0fdf4;border:1.5px solid #86efac;border-radius:16px;padding:1rem;">
                <p style="color:#16a34a;margin:0;text-align:center;">✅ Tout est OK !</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Suggestion du jour ───────────────────────────────────────────────────────
    st.markdown("**✨ Suggestion du jour**")
    humeur = load_humeur(user_id)
    code   = humeur.get("code", "") if humeur else ""
    sugg   = SUGGESTIONS_HUMEUR.get(code, {})
    actvts = sugg.get("activites", [])

    if actvts:
        import random
        activite = random.choice(actvts)
        musique  = sugg.get("musique", "")
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#7c3aed15,#c084fc15);
                    border:1.5px solid #c084fc;border-radius:16px;padding:1rem 1.2rem;">
            <p style="margin:0 0 0.3rem 0;font-weight:600;color:#7c3aed;">Activité suggérée</p>
            <p style="margin:0 0 0.5rem 0;color:#374151;">🎯 {activite}</p>
            {"<p style='margin:0;color:#6b7280;font-size:0.85rem;'>🎵 " + musique + "</p>" if musique else ""}
        </div>
        """, unsafe_allow_html=True)
    else:
        # Suggestions génériques
        heure = datetime.now().hour
        if heure < 10:
            txt = "🌅 Commence ta journée avec 5 min de plein air — ça change tout !"
        elif heure < 14:
            txt = "☀️ Prends une vraie pause déjeuner aujourd'hui."
        elif heure < 19:
            txt = "💪 Tu as bien avancé. Prends un moment pour toi avant ce soir."
        else:
            txt = "🌙 Prépare-toi à une bonne nuit. Pose ton téléphone 30 min avant de dormir."
        st.info(txt)

    # ── Accès rapide ──────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Accès rapide**")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        if st.button("📧 Emails", use_container_width=True):
            st.session_state.page = "email"
            st.rerun()
    with c2:
        if st.button("🛒 Courses", use_container_width=True):
            st.session_state.page = "shopping"
            st.rerun()
    with c3:
        if st.button("💰 Budget", use_container_width=True):
            st.session_state.page = "budget"
            st.rerun()
    with c4:
        if st.button("🔮 Voyance", use_container_width=True):
            st.session_state.page = "voyance"
            st.rerun()
    with c5:
        if st.button("💬 Chat", use_container_width=True):
            st.session_state.page = "chat"
            st.rerun()
