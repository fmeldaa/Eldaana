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
from transport_alerts import get_transport_alerts, is_departure_window
from translations import t, t_list


def show_dashboard(profile: dict, weather: dict | None = None):
    """Affiche le tableau de bord."""
    prenom  = profile.get("prenom", "")
    user_id = profile.get("user_id", "")

    jours  = t_list("days")
    mois   = t_list("months")
    now    = datetime.now()
    date_str = f"{jours[now.weekday()]} {now.day} {mois[now.month - 1]}"

    st.markdown(f"### {t('dash_hello', prenom=prenom)}")
    st.caption(date_str)

    # ── Ligne 1 : Météo + Humeur ──────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(t("dash_weather"))
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
            st.info(t("dash_weather_tip"))

    with col2:
        st.markdown(t("dash_mood"))
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
            st.markdown(f"""
            <div style="background:#f9fafb;border:1.5px dashed #d1d5db;border-radius:16px;
                        padding:1rem;text-align:center;min-height:120px;
                        display:flex;flex-direction:column;justify-content:center;">
                <p style="color:#9ca3af;margin:0;">{t("dash_mood_empty")}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Ligne 2 : Budget + Courses ────────────────────────────────────────────
    col3, col4 = st.columns(2)

    with col3:
        st.markdown(t("dash_budget"))
        summary = get_current_month_total(user_id)
        if summary["budget_mensuel"] > 0:
            pct     = summary["pourcentage"]
            restant = summary["restant"]
            color   = "#22c55e" if pct < 60 else "#f59e0b" if pct < 80 else "#ef4444"
            emoji_b = "🟢" if pct < 60 else "🟡" if pct < 80 else "🔴"
            st.markdown(f"""
            <div style="background:white;border:1.5px solid {color};border-radius:16px;padding:1rem;">
                <p style="margin:0 0 0.3rem 0;font-size:0.85rem;color:#6b7280;">{t("dash_budget_used")}</p>
                <p style="margin:0 0 0.5rem 0;font-size:1.5rem;font-weight:700;color:{color};">
                    {pct:.0f}%
                </p>
                <p style="margin:0;font-size:0.85rem;color:#374151;">
                    {emoji_b} {t("dash_budget_left")} <b>{restant:.0f} €</b>
                </p>
            </div>
            """, unsafe_allow_html=True)
        elif summary["total"] > 0:
            st.markdown(f"""
            <div style="background:white;border:1.5px solid #c084fc;border-radius:16px;padding:1rem;">
                <p style="margin:0;color:#374151;">{t("dash_budget_spent")} <b>{summary['total']:.0f} €</b></p>
                <p style="margin:0.3rem 0 0;font-size:0.8rem;color:#9ca3af;">
                    {t("dash_budget_hint")}
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background:#f9fafb;border:1.5px dashed #d1d5db;border-radius:16px;padding:1rem;">
                <p style="color:#9ca3af;margin:0;text-align:center;">{t("dash_budget_empty")}</p>
            </div>
            """, unsafe_allow_html=True)

    with col4:
        st.markdown(t("dash_shopping"))
        reminders = get_reminders(user_id)
        if reminders:
            urgent = [r for r in reminders if r["days_left"] <= 0]
            bientot = [r for r in reminders if r["days_left"] > 0]
            html = '<div style="background:white;border:1.5px solid #fca5a5;border-radius:16px;padding:1rem;">'
            if urgent:
                for r in urgent[:3]:
                    html += (f'<p style="margin:0 0 0.2rem;font-size:0.9rem;">'
                             f'🔴 <b>{r["name"].capitalize()}</b> — {t("dash_shop_empty")}</p>')
            if bientot:
                for r in bientot[:2]:
                    html += (f'<p style="margin:0 0 0.2rem;font-size:0.9rem;">'
                             f'🟡 <b>{r["name"].capitalize()}</b> — {t("dash_shop_soon", n=r["days_left"])}</p>')
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background:#f0fdf4;border:1.5px solid #86efac;border-radius:16px;padding:1rem;">
                <p style="color:#16a34a;margin:0;text-align:center;">{t("dash_shop_ok")}</p>
            </div>
            """, unsafe_allow_html=True)

    # ── Ligne 3 : Transport ───────────────────────────────────────────────────
    lines_config = profile.get("transport_detail", {}).get("lines", [])
    if lines_config:
        st.markdown(t("dash_transport"))
        depart_heure = profile.get("transport_detail", {}).get("depart_heure", "")
        in_window    = is_departure_window(profile, tz_name=weather.get("timezone") if weather else None)

        if in_window:
            depart_label = (f"{t('dash_depart_soon')} {t('dash_at')} {depart_heure}"
                            if depart_heure else t("dash_depart_soon"))
            st.markdown(f"""
            <div style="background:#fffbeb;border:1.5px solid #f59e0b;border-radius:12px;padding:0.8rem 1rem;">
                <p style="margin:0;font-size:0.9rem;color:#92400e;font-weight:600;">
                    {depart_label}
                </p>
                <p style="margin:0.3rem 0 0;font-size:0.82rem;color:#6b7280;">
                    {t("dash_lines")} {", ".join(lines_config[:3])}
                </p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(t("dash_check_btn"), use_container_width=True, key="dash_transport_check"):
                with st.spinner(t("dash_checking")):
                    alerts = get_transport_alerts(profile, weather)
                if alerts["has_alerts"]:
                    lines_str = ", ".join({a["line"] for a in alerts["tc_alerts"]})
                    st.warning(t("dash_alert", lines=lines_str))
                    st.session_state.page = "chat"
                    st.rerun()
                else:
                    st.success(t("dash_traffic_ok"))
        else:
            depart_str = (f" · {t('dash_depart_usual')} {depart_heure}"
                          if depart_heure else "")
            st.markdown(f"""
            <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:12px;padding:0.6rem 0.8rem;">
                <p style="margin:0;font-size:0.82rem;color:#16a34a;">
                    🚆 {", ".join(lines_config[:3])}{depart_str}
                </p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Suggestion du jour ────────────────────────────────────────────────────
    st.markdown(t("dash_suggestion"))
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
            <p style="margin:0 0 0.3rem 0;font-weight:600;color:#7c3aed;">{t("dash_activity")}</p>
            <p style="margin:0 0 0.5rem 0;color:#374151;">🎯 {activite}</p>
            {"<p style='margin:0;color:#6b7280;font-size:0.85rem;'>🎵 " + musique + "</p>" if musique else ""}
        </div>
        """, unsafe_allow_html=True)
    else:
        heure = datetime.now().hour
        if heure < 10:
            txt = t("sugg_morning")
        elif heure < 14:
            txt = t("sugg_noon")
        elif heure < 19:
            txt = t("sugg_afternoon")
        else:
            txt = t("sugg_evening")
        st.info(txt)

    # ── Accès rapide ──────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(t("dash_quick"))
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        if st.button(t("dash_btn_emails"), use_container_width=True):
            st.session_state.page = "email"
            st.rerun()
    with c2:
        if st.button(t("dash_btn_shopping"), use_container_width=True):
            st.session_state.page = "shopping"
            st.rerun()
    with c3:
        if st.button(t("dash_btn_budget"), use_container_width=True):
            st.session_state.page = "budget"
            st.rerun()
    with c4:
        if st.button(t("dash_btn_predict"), use_container_width=True):
            st.session_state.page = "voyance"
            st.rerun()
    with c5:
        if st.button(t("dash_btn_chat"), use_container_width=True):
            st.session_state.page = "chat"
            st.rerun()
