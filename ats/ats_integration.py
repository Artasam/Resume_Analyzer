"""
ats_integration.py
==================
Drop-in Streamlit UI block for wiring the ATSEngine into your existing app.py.
Paste the render_ats_panel() call into your results column, after the existing
skills block.

Requires
--------
    GROQ_API_KEY=gsk_... in your .env file

Usage in app.py
---------------
    from ats_integration import render_ats_panel

    # Inside the `else:` block (after "with st.spinner"):
    ats_report = get_ats_report(uploaded, job_desc)
    render_ats_panel(ats_report)
"""

from __future__ import annotations

import html
from textwrap import dedent

import streamlit as st

from ats import ATSEngine, ATSReport, Platform, Severity

# ── Singleton engine (cached across Streamlit reruns) ─────────────────────────
@st.cache_resource(show_spinner=False)
def _get_engine() -> ATSEngine:
    """
    Singleton ATSEngine — initialised once per Streamlit session.
    Reads GROQ_API_KEY from environment (set in your .env file).
    """
    import os
    from dotenv import load_dotenv
    load_dotenv()
    return ATSEngine(
        groq_model="llama-3.3-70b-versatile",
    )


def get_ats_report(uploaded_file, job_desc: str = "") -> ATSReport:
    """Extract bytes, run engine, return report."""
    engine = _get_engine()
    file_bytes = uploaded_file.getvalue()
    return engine.analyse(
        file_bytes=file_bytes,
        filename=uploaded_file.name,
        job_description=job_desc,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Severity → colour mapping (matches your existing app theme)
# ─────────────────────────────────────────────────────────────────────────────
_SEV_STYLE = {
    Severity.CRITICAL: ("🔴", "rgba(251,113,133,0.10)", "rgba(251,113,133,0.30)", "#FCA5A5"),
    Severity.HIGH:     ("🟠", "rgba(251,146,60,0.10)",  "rgba(251,146,60,0.28)",  "#FDBA74"),
    Severity.MEDIUM:   ("🟡", "rgba(251,191,36,0.08)",  "rgba(251,191,36,0.24)",  "#FCD34D"),
    Severity.LOW:      ("🔵", "rgba(96,165,250,0.08)",  "rgba(96,165,250,0.22)",  "#93C5FD"),
}

_PLATFORM_COLORS = {
    Platform.TALEO:      "#FB7185",
    Platform.WORKDAY:    "#818CF8",
    Platform.GREENHOUSE: "#34D399",
    Platform.ICIMS:      "#22D3EE",
    Platform.LEVER:      "#A78BFA",
    Platform.GENERIC:    "#9CA3AF",
}

# Each st.html() is an isolated iframe — styles must ship with the fragment.
_ATS_FRAME_CSS = (
    "<style>"
    "@keyframes atsFadeUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}"
    ".ats-in{animation:atsFadeUp .52s cubic-bezier(0.22,1,0.36,1) both}"
    "@media (prefers-reduced-motion:reduce){.ats-in{animation:none!important;opacity:1!important}}"
    "</style>"
)


def _emit_html(html_blob: str) -> None:
    """Inject HTML without the Markdown step (avoids indented lines becoming code blocks)."""
    st.html(_ATS_FRAME_CSS + html_blob)


def render_ats_panel(report: ATSReport) -> None:
    """Render the full ATS panel inside the Streamlit results column."""

    # ── ATS Overall Score ─────────────────────────────────────────────────────
    score_color = (
        "#34D399" if report.overall_score >= 75
        else "#FBBF24" if report.overall_score >= 50
        else "#FB7185"
    )
    _emit_html(
        dedent(f"""
        <div class="ats-in" style="background:#0A0A14;border:1px solid rgba(255,255,255,0.06);
                    border-radius:18px;padding:1.3rem 1.4rem;margin-bottom:1rem;">
            <div style="font-size:0.63rem;font-weight:700;letter-spacing:0.14em;
                        text-transform:uppercase;color:#6C6A8A;margin-bottom:0.7rem;">
                🤖 ATS Simulation Score
            </div>
            <div style="display:flex;align-items:baseline;gap:1rem;margin-bottom:0.7rem;">
                <span style="font-family:'Syne',sans-serif;font-size:2.8rem;
                             font-weight:800;color:{score_color};line-height:1;">
                    {report.overall_score}%
                </span>
                <span style="font-size:0.82rem;color:#9B99BF;font-weight:500;">
                    {html.escape(str(report.pass_rate))}
                </span>
            </div>
            <div style="background:rgba(255,255,255,0.05);border-radius:100px;
                        height:5px;overflow:hidden;margin-bottom:0.85rem;">
                <div style="height:100%;border-radius:100px;width:{report.overall_score}%;
                             background:linear-gradient(90deg,{score_color},{score_color}88);
                             transition:width 0.6s ease;"></div>
            </div>
            <div style="font-size:0.78rem;color:#5A5870;">
                Simulated across {len(report.per_platform_scores)} ATS platforms ·
                {len(report.critical_issues)} critical · {len(report.high_issues)} high severity issues
            </div>
        </div>
        """).strip(),
    )

    # ── Per-Platform Score Grid ───────────────────────────────────────────────
    if report.per_platform_scores:
        platform_html = ""
        for platform, score in report.per_platform_scores.items():
            color = _PLATFORM_COLORS.get(platform, "#9CA3AF")
            platform_html += dedent(f"""
            <div style="background:#0A0A14;border:1px solid rgba(255,255,255,0.05);
                        border-radius:14px;padding:0.9rem 1rem;text-align:center;">
                <div style="font-size:0.62rem;font-weight:700;letter-spacing:0.12em;
                            text-transform:uppercase;color:#4A4868;margin-bottom:0.4rem;">
                    {html.escape(platform.value.title())}
                </div>
                <div style="font-family:'Syne',sans-serif;font-size:1.5rem;
                            font-weight:800;color:{color};line-height:1;">
                    {score}%
                </div>
            </div>
            """).strip()
        _emit_html(
            dedent(f"""
            <div class="ats-in" style="display:grid;grid-template-columns:repeat(3,1fr);
                        gap:0.6rem;margin-bottom:1rem;">
            {platform_html}
            </div>
            """).strip(),
        )

    # ── Issues List ───────────────────────────────────────────────────────────
    if report.issues:
        _emit_html(
            dedent("""
            <div class="ats-in" style="font-size:0.63rem;font-weight:700;letter-spacing:0.14em;
                        text-transform:uppercase;color:#6C6A8A;margin-bottom:0.6rem;
                        margin-top:0.4rem;">
                ⚠ Issues Found
            </div>
            """).strip(),
        )

        for issue in report.issues[:12]:   # Show top 12
            ico, bg, border, text_col = _SEV_STYLE.get(
                issue.severity, ("●", "rgba(255,255,255,0.05)", "rgba(255,255,255,0.12)", "#888")
            )
            platform_badge = ""
            if issue.platform:
                p_color = _PLATFORM_COLORS.get(issue.platform, "#888")
                platform_badge = dedent(f"""
                <span style="font-size:0.6rem;font-weight:600;letter-spacing:0.1em;
                             text-transform:uppercase;padding:0.15rem 0.5rem;
                             border-radius:100px;background:{p_color}22;
                             border:1px solid {p_color}44;color:{p_color};
                             margin-left:0.4rem;">
                    {html.escape(issue.platform.value.title())}
                </span>
                """).strip()

            _emit_html(
                dedent(f"""
                <div class="ats-in" style="background:{bg};border:1px solid {border};
                            border-radius:12px;padding:0.8rem 1rem;
                            margin-bottom:0.5rem;">
                    <div style="display:flex;align-items:center;gap:0.4rem;
                                margin-bottom:0.35rem;flex-wrap:wrap;">
                        <span style="font-size:0.9rem;">{ico}</span>
                        <span style="font-size:0.72rem;font-weight:700;letter-spacing:0.1em;
                                     text-transform:uppercase;color:{text_col};">
                            {html.escape(issue.severity.value.upper())} · {html.escape(issue.category.value)}
                        </span>
                        {platform_badge}
                    </div>
                    <div style="font-size:0.83rem;color:#9B99BF;margin-bottom:0.4rem;
                                line-height:1.55;">
                        {html.escape(issue.message)}
                    </div>
                    <div style="font-size:0.78rem;color:#6339F2;font-weight:500;
                                padding-top:0.35rem;border-top:1px solid rgba(255,255,255,0.05);">
                        ✦ Fix: {html.escape(issue.fix)}
                    </div>
                </div>
                """).strip(),
            )

    # ── Keyword Gap Analysis ──────────────────────────────────────────────────
    if report.keyword_analysis and report.keyword_analysis.gaps:
        ka = report.keyword_analysis

        gap_pills = ""
        for gap in ka.gaps[:16]:
            color = "#FB7185" if gap.is_required else "#FBBF24"
            bg    = "rgba(251,113,133,0.12)" if gap.is_required else "rgba(251,191,36,0.09)"
            border = "rgba(251,113,133,0.28)" if gap.is_required else "rgba(251,191,36,0.22)"
            label  = "★ " if gap.is_required else ""
            gap_pills += dedent(f"""
            <span style="font-size:0.74rem;font-weight:500;padding:0.28rem 0.8rem;
                         border-radius:100px;background:{bg};border:1px solid {border};
                         color:{color};letter-spacing:0.02em;"
                  title="{html.escape(gap.suggested_placement, quote=True)}">
                {html.escape(label)}{html.escape(gap.keyword)}
            </span>
            """).strip()

        _emit_html(
            dedent(f"""
            <div class="ats-in" style="background:#0A0A14;border:1px solid rgba(255,255,255,0.06);
                        border-radius:18px;padding:1.3rem 1.4rem;margin-top:0.8rem;">
                <div style="font-size:0.63rem;font-weight:700;letter-spacing:0.14em;
                            text-transform:uppercase;color:#6C6A8A;margin-bottom:0.8rem;">
                    🎯 Keyword Gap Analysis
                </div>
                <div style="display:flex;gap:1.2rem;margin-bottom:1rem;flex-wrap:wrap;">
                    <div>
                        <div style="font-family:'Syne',sans-serif;font-size:1.4rem;
                                    font-weight:800;color:#34D399;line-height:1;">
                            {len(ka.present_keywords)}
                        </div>
                        <div style="font-size:0.62rem;letter-spacing:0.12em;
                                    text-transform:uppercase;color:#4A4868;">Present</div>
                    </div>
                    <div>
                        <div style="font-family:'Syne',sans-serif;font-size:1.4rem;
                                    font-weight:800;color:#FB7185;line-height:1;">
                            {len(ka.gaps)}
                        </div>
                        <div style="font-size:0.62rem;letter-spacing:0.12em;
                                    text-transform:uppercase;color:#4A4868;">Missing</div>
                    </div>
                    <div>
                        <div style="font-family:'Syne',sans-serif;font-size:1.4rem;
                                    font-weight:800;color:#818CF8;line-height:1;">
                            {ka.tfidf_score:.0%}
                        </div>
                        <div style="font-size:0.62rem;letter-spacing:0.12em;
                                    text-transform:uppercase;color:#4A4868;">TF-IDF</div>
                    </div>
                    <div>
                        <div style="font-family:'Syne',sans-serif;font-size:1.4rem;
                                    font-weight:800;color:#22D3EE;line-height:1;">
                            {ka.match_score:.0%}
                        </div>
                        <div style="font-size:0.62rem;letter-spacing:0.12em;
                                    text-transform:uppercase;color:#4A4868;">S-BERT</div>
                    </div>
                </div>
                <div style="font-size:0.62rem;font-weight:700;letter-spacing:0.12em;
                            text-transform:uppercase;color:#4A4868;margin-bottom:0.5rem;">
                    Missing Keywords <span style="color:#FB7185;font-size:0.58rem;">★ = required</span>
                </div>
                <div style="display:flex;flex-wrap:wrap;gap:0.4rem;">
                    {gap_pills}
                </div>
            </div>
            """).strip(),
        )