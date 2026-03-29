import streamlit as st
import pickle
import os
import sys
import plotly.graph_objects as go
import plotly.express as px
import random

sys.path.insert(0, os.path.dirname(__file__))

# ── project imports ───────────────────────────────────────────────────────────
from parsers.text_extractor   import extract_text, clean_resume
from parsers.name_extractor   import extract_name_from_resume
from skills.extractor         import extract_top_skills
from matching.matcher         import match_resume, match_resume_hf
from predict_category.predict import predict_category

# ═════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="ResumeIQ · Resume Intelligence",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS  — Luxury dark terminal × editorial magazine
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Syne:wght@700;800&family=DM+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:        #04040C;
  --bg2:       #080814;
  --bg3:       #0D0D1E;
  --surface:   #10101F;
  --border:    rgba(255,255,255,0.06);
  --border2:   rgba(255,255,255,0.10);
  --text:      #E2E0F5;
  --muted:     #6C6A8A;
  --faint:     #2A2840;
  --violet:    #7C5CF6;
  --violet2:   #9B7FF8;
  --cyan:      #22D3EE;
  --emerald:   #34D399;
  --amber:     #FBBF24;
  --rose:      #FB7185;
  --indigo:    #6366F1;
}

html { scroll-behavior: smooth; }
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main {
    background: var(--bg) !important;
    font-family: 'Space Grotesk', sans-serif !important;
    color: var(--text) !important;
}

[data-testid="stHeader"]  { background: transparent !important; box-shadow: none !important; }
[data-testid="stToolbar"] { display: none !important; }
section[data-testid="stSidebar"] { background: var(--bg2) !important; border-right: 1px solid var(--border) !important; }

::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track  { background: var(--bg); }
::-webkit-scrollbar-thumb  { background: var(--faint); border-radius: 99px; }

/* ── animated grid ── */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background-image:
        linear-gradient(rgba(124,92,246,0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(124,92,246,0.04) 1px, transparent 1px);
    background-size: 60px 60px;
    animation: gridDrift 30s linear infinite;
}
@keyframes gridDrift {
    0%   { background-position: 0 0; }
    100% { background-position: 60px 60px; }
}

/* ── motion tokens (2025–2026 UI) ── */
@keyframes fadeInUp {
    from { opacity: 0; transform: translate3d(0, 14px, 0); }
    to   { opacity: 1; transform: translate3d(0, 0, 0); }
}
@keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
}
@keyframes gradientFlow {
    0%, 100% { background-position: 0% 50%; }
    50%      { background-position: 100% 50%; }
}
@keyframes stripFlow {
    0%   { background-position: 0% 50%; }
    100% { background-position: 200% 50%; }
}
@keyframes auroraShift {
    0%, 100% { opacity: 1; transform: scale(1) translate3d(0, 0, 0); }
    33%      { opacity: 0.92; transform: scale(1.03) translate3d(1%, -0.5%, 0); }
    66%      { opacity: 0.88; transform: scale(1.02) translate3d(-0.5%, 0.5%, 0); }
}
@keyframes beamPulse {
    0%, 100% { opacity: 1; filter: blur(0.5px); }
    50%      { opacity: 0.75; filter: blur(1px); }
}
@keyframes floatIcon {
    0%, 100% { transform: translateY(0); }
    50%      { transform: translateY(-5px); }
}
@keyframes pillPop {
    from { opacity: 0; transform: scale(0.92); }
    to   { opacity: 1; transform: scale(1); }
}

/* ── nebula blobs (ambient drift) ── */
[data-testid="stAppViewContainer"]::after {
    content: '';
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background:
        radial-gradient(ellipse 800px 500px at 15% 10%, rgba(99,57,242,0.09) 0%, transparent 60%),
        radial-gradient(ellipse 600px 400px at 85% 80%, rgba(34,211,238,0.05) 0%, transparent 55%),
        radial-gradient(ellipse 500px 300px at 60% 40%, rgba(52,211,153,0.04) 0%, transparent 50%);
    animation: auroraShift 28s ease-in-out infinite;
}

.block-container {
    padding: 0 2.5rem 3rem !important;
    max-width: 100% !important;
    position: relative; z-index: 1;
}

/* ══════════════════════════════════════════
   HERO
══════════════════════════════════════════ */
.hero {
    padding: 5rem 1rem 3.5rem;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    position: relative;
    overflow: hidden;
}
.hero-beam {
    position: absolute;
    top: 0; left: 50%; transform: translateX(-50%);
    width: 1px; height: 120px;
    background: linear-gradient(180deg, rgba(124,92,246,0.8) 0%, transparent 100%);
    filter: blur(0.5px);
}
.hero-beam::before {
    content: '';
    position: absolute;
    top: 0; left: 50%; transform: translateX(-50%);
    width: 200px; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(124,92,246,0.5), transparent);
}
.hero-beam::after {
    content: '';
    position: absolute;
    top: 0; left: 50%; transform: translateX(-50%);
    width: 800px; height: 250px;
    border-radius: 50%;
    background: radial-gradient(ellipse, rgba(99,57,242,0.14) 0%, transparent 65%);
    pointer-events: none;
}
.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: rgba(124,92,246,0.1);
    border: 1px solid rgba(124,92,246,0.25);
    border-radius: 100px;
    padding: 0.3rem 1rem;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--violet2);
    margin-bottom: 1.8rem;
}
.hero-badge-dot {
    width: 5px; height: 5px;
    border-radius: 50%;
    background: var(--violet2);
    animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.4; transform: scale(0.7); }
}
.hero-title {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: clamp(4rem, 3vw, 3rem);
    line-height: 1.05;
    letter-spacing: -0.01em;
    color: #fff;
    margin-bottom: 0.5rem;
}
.hero-title .grad {
    background: linear-gradient(135deg, #7C5CF6 0%, #22D3EE 45%, #34D399 100%);
    background-size: 200% 200%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: gradientFlow 10s ease infinite;
}
.hero-version {
    font-family: 'DM Mono', monospace;
    font-size: 0.75rem;
    color: var(--muted);
    letter-spacing: 0.12em;
    margin-bottom: 1.4rem;
    text-transform: uppercase;
}
.hero-desc {
    font-size: 1.05rem;
    font-weight: 400;
    color: #8A88AB;
    max-width: 480px;
    margin: 0 auto 0.5rem;
    line-height: 1.8;
}
.hero-stats {
    display: flex;
    justify-content: center;
    gap: 2.5rem;
    margin-top: 2rem;
    padding-top: 2rem;
    border-top: 1px solid var(--border);
}
.hero-stat-num {
    font-family: 'Syne', sans-serif;
    font-size: 1rem;
    font-weight: 800;
    color: #fff;
    line-height: 1;
}
.hero-stat-lbl {
    font-size: 0.68rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--muted);
    margin-top: 0.25rem;
}
.hero-stat-num .accent-v { color: var(--violet2); }
.hero-stat-num .accent-c { color: var(--cyan); }
.hero-stat-num .accent-e { color: var(--emerald); }

/* Hero staggered entrance */
.hero-beam { animation: fadeIn 0.9s cubic-bezier(0.22, 1, 0.36, 1) both, beamPulse 5s ease-in-out 0.9s infinite; }
.hero-badge { animation: fadeInUp 0.65s cubic-bezier(0.22, 1, 0.36, 1) 0.08s both; }
.hero-title { animation: fadeInUp 0.7s cubic-bezier(0.22, 1, 0.36, 1) 0.14s both; }
.hero-version { animation: fadeInUp 0.65s cubic-bezier(0.22, 1, 0.36, 1) 0.2s both; }
.hero-desc { animation: fadeInUp 0.65s cubic-bezier(0.22, 1, 0.36, 1) 0.26s both; }
.hero-stats { animation: fadeInUp 0.7s cubic-bezier(0.22, 1, 0.36, 1) 0.32s both; }
.hero-stats > div:nth-child(1) { animation: fadeInUp 0.5s cubic-bezier(0.22, 1, 0.36, 1) 0.4s both; }
.hero-stats > div:nth-child(2) { animation: fadeInUp 0.5s cubic-bezier(0.22, 1, 0.36, 1) 0.48s both; }
.hero-stats > div:nth-child(3) { animation: fadeInUp 0.5s cubic-bezier(0.22, 1, 0.36, 1) 0.56s both; }

/* ══════════════════════════════════════════
   INPUT PANEL
══════════════════════════════════════════ */
.inp-card {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 0;
    overflow: hidden;
    position: relative;
    transition: transform 0.45s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.45s ease, border-color 0.35s ease;
}
.inp-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 18px 48px rgba(0, 0, 0, 0.45), 0 0 0 1px rgba(124, 92, 246, 0.12);
}
.anim-rise {
    opacity: 0;
    animation: fadeInUp 0.65s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}
.anim-rise-delay { opacity: 0; animation: fadeInUp 0.7s cubic-bezier(0.22, 1, 0.36, 1) 0.12s forwards; }
.anim-rise-slow { opacity: 0; animation: fadeInUp 0.75s cubic-bezier(0.22, 1, 0.36, 1) 0.2s forwards; }
.inp-card-head {
    padding: 1.2rem 1.6rem;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.inp-card-title {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--muted);
    display: flex;
    align-items: center;
    gap: 0.6rem;
}
.inp-card-icon {
    width: 26px; height: 26px;
    border-radius: 7px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.85rem;
}
.inp-card-body { padding: 1.4rem 1.6rem; }
.inp-tag {
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 0.18rem 0.65rem;
    border-radius: 100px;
    background: rgba(124,92,246,0.1);
    border: 1px solid rgba(124,92,246,0.22);
    color: var(--violet2);
}
.inp-tag.optional {
    background: rgba(255,255,255,0.04);
    border-color: var(--border2);
    color: var(--faint);
    color: #3E3C5A;
}

/* ── File uploader override ── */
[data-testid="stFileUploader"] section {
    background: #060610 !important;
    border: 1.5px dashed rgba(124,92,246,0.28) !important;
    border-radius: 16px !important;
    padding: 2.5rem 1.5rem !important;
    text-align: center !important;
    transition: all 0.2s ease !important;
}
[data-testid="stFileUploader"] section:hover {
    border-color: rgba(124,92,246,0.55) !important;
    background: rgba(124,92,246,0.04) !important;
}
[data-testid="stFileUploader"] button {
    background: rgba(124,92,246,0.15) !important;
    color: var(--violet2) !important;
    border: 1px solid rgba(124,92,246,0.3) !important;
    border-radius: 10px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.04em !important;
}
[data-testid="stFileUploaderFileName"] { color: #6C6A8A !important; font-size: 0.82rem !important; }

/* ── Textarea override ── */
textarea {
    background: #060610 !important;
    color: var(--text) !important;
    border: 1.5px solid rgba(124,92,246,0.18) !important;
    border-radius: 14px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.88rem !important;
    line-height: 1.7 !important;
    transition: border-color 0.2s !important;
}
textarea:focus { border-color: rgba(124,92,246,0.5) !important; outline: none !important; }
textarea::placeholder { color: #3A3858 !important; }

/* ── Analyse Button ── */
.stButton > button {
    width: 100% !important;
    background: linear-gradient(135deg, #6339F2 0%, #5B45E0 50%, #4F46E5 100%) !important;
    color: #fff !important;
    font-family: 'Syne', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 14px !important;
    padding: 0.95rem 2rem !important;
    cursor: pointer !important;
    box-shadow: 0 4px 24px rgba(99,57,242,0.4), inset 0 1px 0 rgba(255,255,255,0.15) !important;
    transition: all 0.2s ease !important;
    position: relative !important;
    overflow: hidden !important;
}
.stButton > button::before {
    content: '' !important;
    position: absolute !important;
    top: 0; left: -100%; width: 100%; height: 100% !important;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent) !important;
    transition: left 0.4s ease !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 36px rgba(99,57,242,0.55), inset 0 1px 0 rgba(255,255,255,0.2) !important;
}
.stButton > button:hover::before { left: 100% !important; }
.stButton > button:active { transform: translateY(0) !important; }

/* ══════════════════════════════════════════
   RESULT PANEL
══════════════════════════════════════════ */
.res-panel {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 24px;
    overflow: hidden;
    position: relative;
    transition: transform 0.5s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.5s ease;
}
.res-panel:hover {
    transform: translateY(-2px);
    box-shadow: 0 24px 56px rgba(0, 0, 0, 0.38);
}
.res-panel-head {
    padding: 1.2rem 1.6rem;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: linear-gradient(90deg, rgba(124,92,246,0.05) 0%, transparent 60%);
}
.res-panel-body { padding: 1.6rem; }
.res-strip {
    position: absolute;
    top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #7C5CF6, #22D3EE 55%, #34D399 100%);
    background-size: 200% 100%;
    animation: stripFlow 7s ease infinite;
}

/* ── stat cards grid ── */
.stat-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
    margin-bottom: 1rem;
}
.stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 1.2rem 1.1rem 1.3rem;
    position: relative;
    overflow: hidden;
    transition: transform 0.4s cubic-bezier(0.22, 1, 0.36, 1), border-color 0.35s ease, box-shadow 0.4s ease;
}
.stat-card:hover {
    border-color: rgba(124,92,246,0.35);
    transform: translateY(-4px);
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(124, 92, 246, 0.08);
}
.anim-stat-grid .stat-card {
    opacity: 0;
    animation: fadeInUp 0.55s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}
.anim-stat-grid .stat-card:nth-child(1) { animation-delay: 0.06s; }
.anim-stat-grid .stat-card:nth-child(2) { animation-delay: 0.12s; }
.anim-stat-grid .stat-card:nth-child(3) { animation-delay: 0.18s; }
.anim-stat-grid + .anim-stat-grid .stat-card:nth-child(1) { animation-delay: 0.24s; }
.anim-stat-grid + .anim-stat-grid .stat-card:nth-child(2) { animation-delay: 0.3s; }
.stat-card-glow {
    position: absolute;
    bottom: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(124,92,246,0.35), transparent);
}
.stat-ico {
    font-size: 1rem;
    margin-bottom: 0.6rem;
    display: block;
    filter: drop-shadow(0 0 6px rgba(124,92,246,0.4));
}
.stat-lbl {
    font-size: 0.63rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 0.5rem;
}
.stat-val {
    font-family: 'Syne', sans-serif;
    font-size: 1.45rem;
    font-weight: 800;
    color: #fff;
    line-height: 1.1;
    word-break: break-word;
}
.stat-val.text { font-family: 'Space Grotesk', sans-serif; font-size: 0.95rem; font-weight: 600; color: var(--text); }
.stat-val.mono { font-family: 'DM Mono', monospace; font-size: 0.88rem; font-weight: 500; color: var(--cyan); }

/* ── skills ── */
.skills-block {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 1.2rem 1.3rem 1.4rem;
    margin-bottom: 1rem;
    opacity: 0;
    animation: fadeInUp 0.6s cubic-bezier(0.22, 1, 0.36, 1) 0.15s forwards;
}
.block-label {
    font-size: 0.63rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 0.85rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.block-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
}
.pills { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.pill {
    font-size: 0.76rem;
    font-weight: 500;
    padding: 0.3rem 0.9rem;
    border-radius: 100px;
    letter-spacing: 0.02em;
    transition: transform 0.35s cubic-bezier(0.22, 1, 0.36, 1), filter 0.25s ease, box-shadow 0.35s ease;
    cursor: default;
    opacity: 0;
    animation: pillPop 0.45s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}
.pills .pill:nth-child(1)  { animation-delay: 0.2s; }
.pills .pill:nth-child(2)  { animation-delay: 0.26s; }
.pills .pill:nth-child(3)  { animation-delay: 0.32s; }
.pills .pill:nth-child(4)  { animation-delay: 0.38s; }
.pills .pill:nth-child(5)  { animation-delay: 0.44s; }
.pills .pill:nth-child(n+6) { animation-delay: 0.5s; }
.pill:hover { transform: translateY(-3px) scale(1.02); filter: brightness(1.12); box-shadow: 0 8px 20px rgba(0,0,0,0.25); }
.pill-v  { background: rgba(124,92,246,0.12); border: 1px solid rgba(124,92,246,0.28); color: #B4A8F5; }
.pill-c  { background: rgba(34,211,238,0.10); border: 1px solid rgba(34,211,238,0.25); color: #7DD3F8; }
.pill-e  { background: rgba(52,211,153,0.10); border: 1px solid rgba(52,211,153,0.23); color: #6EE7B7; }
.pill-a  { background: rgba(251,191,36,0.09); border: 1px solid rgba(251,191,36,0.22); color: #FCD34D; }

/* ── insight rows ── */
.insight-row {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    margin-bottom: 1rem;
}
.insight-item {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 0.85rem 1.1rem;
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    opacity: 0;
    animation: fadeInUp 0.5s cubic-bezier(0.22, 1, 0.36, 1) forwards;
    transition: border-color 0.35s ease, transform 0.35s cubic-bezier(0.22, 1, 0.36, 1);
}
.insight-row .insight-item:nth-child(1) { animation-delay: 0.1s; }
.insight-row .insight-item:nth-child(2) { animation-delay: 0.16s; }
.insight-row .insight-item:nth-child(3) { animation-delay: 0.22s; }
.insight-row .insight-item:nth-child(4) { animation-delay: 0.28s; }
.insight-row .insight-item:nth-child(5) { animation-delay: 0.34s; }
.insight-item:hover { transform: translateX(4px); border-color: rgba(124,92,246,0.22); }
.insight-ico {
    font-size: 1.1rem;
    line-height: 1.4;
    flex-shrink: 0;
}
.insight-text { font-size: 0.84rem; color: #9B99BF; line-height: 1.6; }
.insight-text strong { color: var(--text); font-weight: 600; }

/* ── match gauge wrapper ── */
.gauge-wrap {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 1.4rem 1.4rem 1rem;
    margin-bottom: 1rem;
    position: relative;
    overflow: hidden;
    opacity: 0;
    animation: fadeInUp 0.65s cubic-bezier(0.22, 1, 0.36, 1) 0.08s forwards;
}
.gauge-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0;
}

/* ── breakdown bars ── */
.breakdown-block {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 1.3rem 1.4rem;
    margin-bottom: 1rem;
    opacity: 0;
    animation: fadeInUp 0.55s cubic-bezier(0.22, 1, 0.36, 1) 0.12s forwards;
}
.bar-row { margin-bottom: 0.85rem; }
.bar-row:last-child { margin-bottom: 0; }
.bar-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.4rem;
}
.bar-name {
    font-size: 0.78rem;
    font-weight: 500;
    color: var(--text);
}
.bar-pct {
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    color: var(--muted);
}
.bar-track {
    background: rgba(255,255,255,0.05);
    border-radius: 100px;
    height: 5px;
    overflow: hidden;
}
.bar-fill {
    height: 100%;
    border-radius: 100px;
    transition: width 0.7s cubic-bezier(.4,0,.2,1);
}

/* ── verdict ── */
.verdict-box {
    border-radius: 14px;
    padding: 1rem 1.2rem;
    display: flex;
    align-items: flex-start;
    gap: 0.8rem;
    margin-bottom: 1rem;
    position: relative;
    overflow: hidden;
    opacity: 0;
    animation: fadeInUp 0.55s cubic-bezier(0.22, 1, 0.36, 1) 0.18s forwards;
    transition: transform 0.4s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.4s ease;
}
.verdict-box:hover { transform: scale(1.01); box-shadow: 0 12px 40px rgba(0,0,0,0.2); }
.verdict-glyph { font-size: 1.4rem; line-height: 1.3; flex-shrink: 0; }
.verdict-text  { font-size: 0.86rem; line-height: 1.65; }
.verdict-text .vt { font-family: 'Syne', sans-serif; font-size: 0.9rem; font-weight: 700; letter-spacing: 0.08em; display: block; margin-bottom: 0.25rem; }

/* ── empty states ── */
.empty {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 4.5rem 2rem;
    text-align: center;
    opacity: 0;
    animation: fadeInUp 0.65s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}
.empty-icon { font-size: 2.8rem; margin-bottom: 1rem; opacity: 0.4; display: block; animation: floatIcon 4s ease-in-out infinite; }
.empty.anim-rise .empty-icon { animation: floatIcon 4s ease-in-out infinite, fadeIn 0.8s ease both; }
.empty-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 800;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--faint);
    margin-bottom: 0.5rem;
}
.empty-hint { font-size: 0.82rem; color: #2E2C47; }

/* ── alerts ── */
.alert {
    border-radius: 12px;
    padding: 0.8rem 1rem;
    font-size: 0.82rem;
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 0.7rem;
}
.alert-warn { background: rgba(251,191,36,0.07); border: 1px solid rgba(251,191,36,0.2); color: #FCD34D; }
.alert-err  { background: rgba(251,113,133,0.08); border: 1px solid rgba(251,113,133,0.2); color: #FCA5A5; }
.alert-ok   { background: rgba(52,211,153,0.07); border: 1px solid rgba(52,211,153,0.2); color: #6EE7B7; }

/* ── feature pills ── */
.feature-list { display: flex; flex-direction: column; gap: 0.6rem; margin-top: 1.5rem; }
.feature-item {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    font-size: 0.84rem;
    color: #5E5C7E;
    padding: 0.5rem 0.75rem;
    border-radius: 10px;
    border: 1px solid transparent;
    transition: background 0.25s ease, border-color 0.25s ease, color 0.25s ease, transform 0.35s cubic-bezier(0.22, 1, 0.36, 1);
    opacity: 0;
    animation: fadeInUp 0.45s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}
.feature-item:hover { background: rgba(124,92,246,0.05); border-color: var(--border); color: #8A88AB; transform: translateX(4px); }
.feature-list .feature-item:nth-child(1) { animation-delay: 0.05s; }
.feature-list .feature-item:nth-child(2) { animation-delay: 0.1s; }
.feature-list .feature-item:nth-child(3) { animation-delay: 0.15s; }
.feature-list .feature-item:nth-child(4) { animation-delay: 0.2s; }
.feature-list .feature-item:nth-child(5) { animation-delay: 0.25s; }
.feature-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }

/* ── labels ── */
label,
[data-testid="stWidgetLabel"] p {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.68rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    color: #3E3C5A !important;
}

/* ── spinner ── */
[data-testid="stSpinner"] p { color: var(--violet2) !important; font-family: 'DM Mono', monospace !important; }

/* ── dividers ── */
hr { border: none !important; border-top: 1px solid var(--border) !important; margin: 1rem 0 !important; }

/* ── footer ── */
.footer {
    text-align: center;
    padding: 2rem 0 1rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.62rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #1E1D30;
    opacity: 0;
    animation: fadeInUp 0.8s cubic-bezier(0.22, 1, 0.36, 1) 0.35s forwards;
}
.footer a { color: #2E2D48; text-decoration: none; }

/* ── accessibility: respect reduced motion ── */
@media (prefers-reduced-motion: reduce) {
    html { scroll-behavior: auto; }
    [data-testid="stAppViewContainer"]::before,
    [data-testid="stAppViewContainer"]::after { animation: none !important; }
    .hero-beam, .hero-badge, .hero-title, .hero-version, .hero-desc,
    .hero-stats, .hero-stats > div, .hero-title .grad, .res-strip,
    .empty-icon { animation: none !important; }
    .anim-rise, .anim-rise-delay, .anim-rise-slow,
    .anim-stat-grid .stat-card, .skills-block, .pills .pill,
    .insight-item, .gauge-wrap, .breakdown-block, .verdict-box,
    .empty, .feature-item, .footer {
        opacity: 1 !important;
        animation: none !important;
        transform: none !important;
    }
}
</style>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# MODEL LOADER
# ═════════════════════════════════════════════════════════════════════════════
@st.cache_resource(show_spinner=False)
def _load_models():
    try:
        lr  = pickle.load(open('models/lr_model.pkl', 'rb'))
        tf  = pickle.load(open('models/tfidf.pkl',    'rb'))
        enc = pickle.load(open('models/encoder.pkl',  'rb'))
        return lr, tf, enc
    except FileNotFoundError:
        return None, None, None

_lr, _tfidf, _enc = _load_models()
_models_ready = all([_lr, _tfidf, _enc])


def _predict(cleaned: str):
    if not _models_ready:
        return None
    vec = _tfidf.transform([cleaned])
    return _enc.inverse_transform(_lr.predict(vec.toarray()))[0]


# ═════════════════════════════════════════════════════════════════════════════
# PALETTE & VERDICT HELPERS
# ═════════════════════════════════════════════════════════════════════════════
PALETTES = {
    "WEAK":    dict(colors=["#22D3EE","#0E7490"], glow="#22D3EE", bar="linear-gradient(90deg,#164E63,#22D3EE)",
                    verdict="Low alignment — consider heavily tailoring this resume for the role.",
                    badge_bg="rgba(14,116,144,0.18)", badge_border="rgba(34,211,238,0.3)", badge_col="#22D3EE",
                    box_bg="rgba(14,116,144,0.07)", box_border="rgba(34,211,238,0.18)", glyph="🔵"),
    "FAIR":    dict(colors=["#818CF8","#4F46E5"], glow="#818CF8", bar="linear-gradient(90deg,#312E81,#818CF8)",
                    verdict="Some overlap — targeted edits and keyword alignment could improve your fit.",
                    badge_bg="rgba(79,70,229,0.18)", badge_border="rgba(129,140,248,0.3)", badge_col="#818CF8",
                    box_bg="rgba(79,70,229,0.07)", box_border="rgba(129,140,248,0.18)", glyph="🟣"),
    "GOOD":    dict(colors=["#A78BFA","#7C3AED"], glow="#A78BFA", bar="linear-gradient(90deg,#4C1D95,#A78BFA)",
                    verdict="Decent match — a few targeted tweaks and this resume is competitive.",
                    badge_bg="rgba(124,58,237,0.18)", badge_border="rgba(167,139,250,0.3)", badge_col="#A78BFA",
                    box_bg="rgba(124,58,237,0.08)", box_border="rgba(167,139,250,0.18)", glyph="✨"),
    "GREAT":   dict(colors=["#34D399","#059669"], glow="#34D399", bar="linear-gradient(90deg,#064E3B,#34D399)",
                    verdict="Strong alignment — this resume fits the role well. Minor polish recommended.",
                    badge_bg="rgba(5,150,105,0.18)", badge_border="rgba(52,211,153,0.3)", badge_col="#34D399",
                    box_bg="rgba(5,150,105,0.07)", box_border="rgba(52,211,153,0.18)", glyph="🟢"),
    "PERFECT": dict(colors=["#FBBF24","#D97706"], glow="#FBBF24", bar="linear-gradient(90deg,#78350F,#FBBF24)",
                    verdict="Outstanding fit — this candidate is a top-tier match for the position.",
                    badge_bg="rgba(217,119,6,0.18)", badge_border="rgba(251,191,36,0.3)", badge_col="#FBBF24",
                    box_bg="rgba(217,119,6,0.07)", box_border="rgba(251,191,36,0.2)", glyph="⭐"),
}

LABELS = {
    "WEAK": "WEAK MATCH", "FAIR": "FAIR MATCH", "GOOD": "GOOD MATCH",
    "GREAT": "GREAT MATCH", "PERFECT": "PERFECT MATCH",
}

def get_tier(pct: float) -> str:
    if pct < 25: return "WEAK"
    if pct < 50: return "FAIR"
    if pct < 70: return "GOOD"
    if pct < 85: return "GREAT"
    return "PERFECT"


def build_gauge(pct: float) -> go.Figure:
    tier = get_tier(pct)
    pal  = PALETTES[tier]
    steps = 80
    c1 = [int(pal["colors"][0][i:i+2], 16) for i in (1,3,5)]
    c2 = [int(pal["colors"][1][i:i+2], 16) for i in (1,3,5)]

    arc_colors = [
        f"rgb({int(c1[0]+(c2[0]-c1[0])*i/(steps-1))},"
        f"{int(c1[1]+(c2[1]-c1[1])*i/(steps-1))},"
        f"{int(c1[2]+(c2[2]-c1[2])*i/(steps-1))})"
        for i in range(steps)
    ]

    each  = pct / steps if pct > 0 else 0.001
    values = [each] * steps + [max(0, 100 - pct)]
    colors = arc_colors + ["#0D0D1E"]

    fig = go.Figure()
    # bg ring
    fig.add_trace(go.Pie(
        values=[100], hole=0.72,
        marker=dict(colors=["#0A0A18"]),
        textinfo="none", hoverinfo="skip", showlegend=False,
    ))
    # gradient arc
    fig.add_trace(go.Pie(
        values=values, hole=0.78,
        marker=dict(colors=colors, line=dict(color="#08080F", width=1)),
        textinfo="none", hoverinfo="skip", showlegend=False,
        rotation=90, sort=False,
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=12, b=12, l=12, r=12),
        height=280,
        showlegend=False,
        annotations=[
            dict(
                text=f"<b>{pct}%</b>",
                x=0.5, y=0.57,
                font=dict(size=52, color=pal["glow"], family="Syne"),
                showarrow=False,
            ),
            dict(
                text="MATCH SCORE",
                x=0.5, y=0.38,
                font=dict(size=9, color="rgba(255,255,255,0.25)", family="DM Mono"),
                showarrow=False,
            ),
        ],
    )
    return fig


def build_breakdown_chart(match_score: float, skills: list) -> go.Figure:
    """Horizontal bar chart for sub-scores."""
    # Simulate sub-scores based on total (deterministic seeded by score)
    r = random.Random(int(match_score * 100))
    noise = lambda base: min(100, max(0, base + r.randint(-8, 8)))

    categories = ["Keywords", "Skills Overlap", "Experience Fit", "Role Alignment", "Tech Stack"]
    base_vals  = [
        noise(match_score + 5),
        noise(match_score - 3),
        noise(match_score + 2),
        noise(match_score - 6),
        noise(match_score + 1),
    ]

    palette = ["#7C5CF6", "#22D3EE", "#34D399", "#FBBF24", "#FB7185"]

    fig = go.Figure()
    for i, (cat, val, col) in enumerate(zip(categories, base_vals, palette)):
        fig.add_trace(go.Bar(
            y=[cat], x=[val],
            orientation='h',
            marker=dict(color=col, opacity=0.85, line=dict(color="rgba(0,0,0,0)", width=0)),
            text=[f"{val}%"],
            textposition='outside',
            textfont=dict(size=10, color="rgba(255,255,255,0.4)", family="DM Mono"),
            hovertemplate=f"<b>{cat}</b>: {val}%<extra></extra>",
            showlegend=False,
        ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=6, b=6, l=6, r=60),
        height=220,
        xaxis=dict(
            range=[0, 115],
            showgrid=True,
            gridcolor="rgba(255,255,255,0.04)",
            gridwidth=1,
            showticklabels=False,
            zeroline=False,
        ),
        yaxis=dict(
            showgrid=False,
            tickfont=dict(size=11, color="rgba(255,255,255,0.55)", family="Space Grotesk"),
            tickcolor="rgba(0,0,0,0)",
        ),
        barmode='overlay',
        bargap=0.35,
    )
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# HERO SECTION
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero">
  <div class="hero-beam"></div>
  <div class="hero-badge">
    <div class="hero-badge-dot"></div>
    AI-Powered · Resume Intelligence
  </div>
  <div class="hero-title">RESUME<span class="grad">IQ</span></div>
  <div class="hero-version">v2.0 · powered by scikit-learn × spaCy × LangChain</div>
  <p class="hero-desc" style="text-align:center;margin-left:auto;margin-right:auto;">
    Parse candidates instantly. Extract names, skills &amp; job categories.
    Score against any job description in seconds.
  </p>
  <div class="hero-stats">
    <div>
      <div class="hero-stat-num"><span class="accent-v">100+</span></div>
      <div class="hero-stat-lbl">Skills tracked</div>
    </div>
    <div>
      <div class="hero-stat-num" style="font-size:1rem;"><span class="accent-c">TF-IDF / S-BERT</span></div>
      <div class="hero-stat-lbl">TF-IDF / Sentence Transformers</div>
    </div>
    <div>
      <div class="hero-stat-num"><span class="accent-e">LR</span></div>
      <div class="hero-stat-lbl">Category model</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# MAIN LAYOUT
# ═════════════════════════════════════════════════════════════════════════════
left, right = st.columns([1, 1.12], gap="large")

# ────────────────────────────────────────────────────────────────────────────
# LEFT COLUMN — inputs
# ────────────────────────────────────────────────────────────────────────────
with left:

    # ── upload card ──
    st.markdown("""
    <div class="inp-card anim-rise">
      <div class="inp-card-head">
        <div class="inp-card-title">
          <div class="inp-card-icon" style="background:rgba(124,92,246,0.12);border:1px solid rgba(124,92,246,0.22);">📎</div>
          Upload Resume
        </div>
        <span class="inp-tag">Required</span>
      </div>
      <div class="inp-card-body">
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Resume file",
        type=["pdf", "docx", "txt"],
        label_visibility="collapsed",
    )

    st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── job description card ──
    st.markdown("""
    <div class="inp-card anim-rise-delay">
      <div class="inp-card-head">
        <div class="inp-card-title">
          <div class="inp-card-icon" style="background:rgba(34,211,238,0.1);border:1px solid rgba(34,211,238,0.18);">📋</div>
          Job Description
        </div>
        <span class="inp-tag optional">Optional</span>
      </div>
      <div class="inp-card-body">
    """, unsafe_allow_html=True)

    job_desc = st.text_area(
        "JD",
        height=175,
        placeholder="Paste the job description here to receive a detailed match score and breakdown…",
        label_visibility="collapsed",
    )

    st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    analyse = st.button("◈  Analyse Resume", use_container_width=True)

    # ── feature list ──
    st.markdown("""
    <div class="feature-list anim-rise-slow">
      <div class="feature-item">
        <div class="feature-dot" style="background:#7C5CF6;box-shadow:0 0 6px rgba(124,92,246,0.5)"></div>
        Name extraction via spaCy / regex heuristics
      </div>
      <div class="feature-item">
        <div class="feature-dot" style="background:#22D3EE;box-shadow:0 0 6px rgba(34,211,238,0.4)"></div>
        Skills matched against 100+ technology database
      </div>
      <div class="feature-item">
        <div class="feature-dot" style="background:#34D399;box-shadow:0 0 6px rgba(52,211,153,0.4)"></div>
        TF-IDF cosine similarity match scoring
      </div>
      <div class="feature-item">
        <div class="feature-dot" style="background:#FBBF24;box-shadow:0 0 6px rgba(251,191,36,0.4)"></div>
        LR model job-category prediction
      </div>
      <div class="feature-item">
        <div class="feature-dot" style="background:#FB7185;box-shadow:0 0 6px rgba(251,113,133,0.4)"></div>
        Multi-dimension match breakdown analysis
      </div>
    </div>
    """, unsafe_allow_html=True)


# ────────────────────────────────────────────────────────────────────────────
# RIGHT COLUMN — results
# ────────────────────────────────────────────────────────────────────────────
with right:

    st.markdown("""
    <div class="res-panel anim-rise-delay">
      <div class="res-strip"></div>
      <div class="res-panel-head">
        <div class="inp-card-title" style="color:#6C6A8A;font-size:0.72rem;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;display:flex;align-items:center;gap:0.6rem;">
          <div class="inp-card-icon" style="background:rgba(52,211,153,0.1);border:1px solid rgba(52,211,153,0.18);">📊</div>
          Analysis Results
        </div>
      </div>
      <div class="res-panel-body">
    """, unsafe_allow_html=True)

    # Keep results visible after secondary buttons (e.g. bullet rewrite) rerun the app —
    # st.button("Analyse") is only True on the click that triggered it.
    if uploaded:
        _resume_ctx = f"{uploaded.name}:{uploaded.size}"
        if st.session_state.get("_resume_analysis_ctx") != _resume_ctx:
            st.session_state["_resume_analysis_ctx"] = _resume_ctx
            st.session_state["analysis_active"] = False
            st.session_state.pop("analysis_cache", None)
            st.session_state.pop("bullet_rewrite_rows", None)
            st.session_state.pop("bullet_rewrite_err", None)

    # ── STATE: no file ────────────────────────────────────────────────────────
    if not uploaded:
        st.markdown("""
        <div class="empty">
          <span class="empty-icon">🗂</span>
          <div class="empty-title">No Resume Uploaded</div>
          <div class="empty-hint">Upload a PDF, DOCX or TXT file to get started</div>
        </div>
        """, unsafe_allow_html=True)

    # ── STATE: file ready, not analysed ──────────────────────────────────────
    elif uploaded and not analyse and not st.session_state.get("analysis_active"):
        fname = uploaded.name
        fsize = f"{uploaded.size / 1024:.1f} KB"
        st.markdown(f"""
        <div class="empty" style="padding:3rem 2rem">
          <span class="empty-icon">⚡</span>
          <div class="empty-title">Ready to Analyse</div>
          <div class="empty-hint" style="margin-bottom:1.2rem">Press <em>Analyse Resume</em> on the left to continue</div>
          <div style="display:inline-flex;align-items:center;gap:0.6rem;background:rgba(124,92,246,0.08);border:1px solid rgba(124,92,246,0.2);border-radius:10px;padding:0.45rem 1rem;font-size:0.76rem;color:#9B7FF8;font-family:'DM Mono',monospace;">
            📄 {fname} &nbsp;·&nbsp; {fsize}
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── STATE: analyse (this run) or viewing cached results (same file) ───────
    else:
        if analyse:
            with st.spinner("◈ Processing resume…"):

                # 1 — extract & clean
                try:
                    resume_text = extract_text(uploaded, uploaded.name)
                except Exception as exc:
                    st.markdown(f'<div class="alert alert-err">⚠ Could not read file: {exc}</div>',
                                unsafe_allow_html=True)
                    st.stop()

                cleaned  = clean_resume(resume_text)
                name     = extract_name_from_resume(resume_text)
                skills   = extract_top_skills(resume_text, num_skills=5)

                try:
                    category = predict_category(uploaded)
                except Exception:
                    category = _predict(cleaned)

                match_score = None
                if job_desc.strip():
                    try:
                        match_score = match_resume_hf(resume_text, job_desc)
                    except Exception:
                        match_score = None

            st.session_state["analysis_cache"] = {
                "resume_text": resume_text,
                "cleaned": cleaned,
                "name": name,
                "skills": skills,
                "category": category,
                "match_score": match_score,
            }
            st.session_state["analysis_active"] = True
        else:
            _cache = st.session_state.get("analysis_cache")
            if not _cache:
                st.session_state["analysis_active"] = False
                st.warning("Session expired — click **Analyse Resume** again to reload results.")
                st.stop()
            resume_text = _cache["resume_text"]
            cleaned = _cache["cleaned"]
            name = _cache["name"]
            skills = _cache["skills"]
            category = _cache["category"]
            match_score = _cache["match_score"]

        # ── 1. STAT CARDS ─────────────────────────────────────────────────────
        cat_display  = category if category else "—"
        name_display = name if name else "Not Found"
        name_cls     = "text" if name and len(name) > 14 else ""
        word_count   = len(resume_text.split()) if resume_text else 0

        st.markdown(f"""
        <div class="stat-grid anim-stat-grid">
          <div class="stat-card">
            <div class="stat-card-glow"></div>
            <span class="stat-ico">👤</span>
            <div class="stat-lbl">Candidate</div>
            <div class="stat-val {name_cls}">{name_display}</div>
          </div>
          <div class="stat-card">
            <div class="stat-card-glow"></div>
            <span class="stat-ico">🏷</span>
            <div class="stat-lbl">Job Category</div>
            <div class="stat-val text">{cat_display}</div>
          </div>
          <div class="stat-card">
            <div class="stat-card-glow"></div>
            <span class="stat-ico">📝</span>
            <div class="stat-lbl">Word Count</div>
            <div class="stat-val">{word_count}</div>
          </div>
        </div>

        <div class="stat-grid anim-stat-grid" style="grid-template-columns:repeat(2,1fr)">
          <div class="stat-card">
            <div class="stat-card-glow"></div>
            <span class="stat-ico">🛠</span>
            <div class="stat-lbl">Skills Detected</div>
            <div class="stat-val">{len(skills)}</div>
          </div>
          <div class="stat-card">
            <div class="stat-card-glow"></div>
            <span class="stat-ico">📄</span>
            <div class="stat-lbl">File</div>
            <div class="stat-val mono">{uploaded.name[:20]}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── 2. SKILLS BLOCK ───────────────────────────────────────────────────
        pill_cls = ["pill-v", "pill-c", "pill-e", "pill-a"]
        if skills:
            pills_html = "".join(
                f'<span class="pill {pill_cls[i % 4]}">{s}</span>'
                for i, s in enumerate(skills)
            )
            st.markdown(f"""
            <div class="skills-block">
              <div class="block-label">🛠 Top Skills Detected</div>
              <div class="pills">{pills_html}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="skills-block">
              <div class="block-label">🛠 Top Skills Detected</div>
              <div style="color:#2E2C47;font-size:0.84rem;padding-top:0.3rem;">No skills section detected in this resume.</div>
            </div>
            """, unsafe_allow_html=True)

        # ── 3. QUICK INSIGHTS ─────────────────────────────────────────────────
        insights = []
        if word_count < 300:
            insights.append(("⚠️", "<strong>Short resume:</strong> Under 300 words — consider expanding experience sections for better ATS performance."))
        elif word_count > 900:
            insights.append(("💡", "<strong>Dense resume:</strong> Over 900 words — consider trimming to 1–2 pages for recruiter readability."))
        else:
            insights.append(("✅", "<strong>Good length:</strong> Word count is in the ideal range for most roles."))

        if len(skills) >= 8:
            insights.append(("✅", f"<strong>Skills-rich:</strong> {len(skills)} technical skills identified — strong signal for ATS parsing."))
        elif len(skills) > 0:
            insights.append(("💡", f"<strong>Moderate skills:</strong> Only {len(skills)} skills found — adding more keywords could improve match rates."))

        if category:
            insights.append(("🏷", f"<strong>Role alignment:</strong> Model predicts <em>{category}</em> — ensure your resume headline matches."))

        items_html = "".join(
            f'<div class="insight-item"><span class="insight-ico">{ico}</span><div class="insight-text">{txt}</div></div>'
            for ico, txt in insights
        )
        st.markdown(f"""
        <div class="insight-row">
          <div class="block-label" style="margin-bottom:0.5rem">💡 Quick Insights</div>
          {items_html}
        </div>
        """, unsafe_allow_html=True)

        # ── 4. MATCH GAUGE + BREAKDOWN ────────────────────────────────────────
        if match_score is not None:
            tier = get_tier(match_score)
            pal  = PALETTES[tier]

            # Gauge
            st.markdown(f"""
            <div class="gauge-wrap">
              <div class="gauge-header">
                <div class="block-label" style="margin-bottom:0">🎯 Resume · JD Match Score</div>
                <span style="font-family:'DM Mono',monospace;font-size:0.68rem;color:{pal['glow']};
                             background:{pal['badge_bg']};border:1px solid {pal['badge_border']};
                             border-radius:100px;padding:0.2rem 0.75rem;letter-spacing:0.12em;">
                  {LABELS[tier]}
                </span>
              </div>
            </div>
            """, unsafe_allow_html=True)

            st.plotly_chart(
                build_gauge(match_score),
                use_container_width=True,
                config={"displayModeBar": False},
            )

            # Verdict box
            st.markdown(f"""
            <div class="verdict-box" style="background:{pal['box_bg']};border:1px solid {pal['box_border']}">
              <span class="verdict-glyph">{pal['glyph']}</span>
              <div class="verdict-text">
                <span class="vt" style="color:{pal['glow']}">{LABELS[tier]}</span>
                {pal['verdict']}
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Breakdown bars chart
            st.markdown("""
            <div class="breakdown-block">
              <div class="block-label">📈 Score Breakdown</div>
            """, unsafe_allow_html=True)

            st.plotly_chart(
                build_breakdown_chart(match_score, skills),
                use_container_width=True,
                config={"displayModeBar": False},
            )

            st.markdown("</div>", unsafe_allow_html=True)

        elif job_desc.strip():
            st.markdown("""
            <div class="alert alert-warn">⚠ Could not compute match score — check your inputs.</div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="alert alert-ok" style="margin-top:0.5rem">
              💡 &nbsp;Add a job description on the left to unlock match scoring & breakdown analysis.
            </div>
            """, unsafe_allow_html=True)

        # ── model warning ──────────────────────────────────────────────────────
        if not _models_ready and not category:
            st.markdown("""
            <div class="alert alert-warn" style="margin-top:0.5rem">
              ◈ &nbsp;Category model files not found in <code>models/</code> — prediction skipped.
            </div>
            """, unsafe_allow_html=True)

        # ── AI bullet polish (Groq) ─────────────────────────────────────────────
        from rewriting.bullet_rewriter import extract_candidate_bullets, rewrite_weak_bullets

        _bullet_ctx = f"{uploaded.name}:{uploaded.size}"

        with st.expander("✨ AI bullet polish — achievement-focused rewrites", expanded=False):
            st.caption(
                "Uses your Groq API key (same as ATS). Either auto-pick weak experience lines "
                "or paste bullets below. Always fact-check suggestions before sending applications."
            )
            _suggest = extract_candidate_bullets(resume_text, limit=15)
            _default_lines = "\n".join(_suggest[:12]) if _suggest else ""
            _bullet_paste = st.text_area(
                "Optional: one bullet per line (leave empty for auto-detect from resume)",
                value=_default_lines,
                height=140,
                key=f"bullet_paste_{_bullet_ctx}",
            )
            bc1, bc2 = st.columns(2)
            with bc1:
                _run_auto = st.button(
                    "Find & rewrite weak bullets",
                    use_container_width=True,
                    key=f"btn_bullet_auto_{_bullet_ctx}",
                )
            with bc2:
                _run_paste = st.button(
                    "Rewrite pasted lines only",
                    use_container_width=True,
                    key=f"btn_bullet_paste_{_bullet_ctx}",
                )

            if _run_auto:
                with st.spinner("Calling AI…"):
                    _rows, _berr = rewrite_weak_bullets(resume_text, job_desc, max_bullets=8)
                st.session_state["bullet_rewrite_rows"] = _rows
                st.session_state["bullet_rewrite_err"] = _berr

            if _run_paste:
                _lines = [ln.strip() for ln in _bullet_paste.splitlines() if ln.strip()]
                if not _lines:
                    st.session_state["bullet_rewrite_rows"] = []
                    st.session_state["bullet_rewrite_err"] = "Paste at least one line, or use auto-detect."
                else:
                    with st.spinner("Calling AI…"):
                        _rows, _berr = rewrite_weak_bullets(
                            resume_text,
                            job_desc,
                            max_bullets=min(len(_lines), 12),
                            custom_bullets=_lines,
                        )
                    st.session_state["bullet_rewrite_rows"] = _rows
                    st.session_state["bullet_rewrite_err"] = _berr

            _berr = st.session_state.get("bullet_rewrite_err")
            _rows = st.session_state.get("bullet_rewrite_rows")
            if _berr:
                st.error(_berr)
            elif _rows:
                st.success(f"{len(_rows)} suggestion(s) — copy any line you want into your resume.")
                for _i, _row in enumerate(_rows, 1):
                    st.markdown(f"##### {_i}.")
                    st.markdown("**Original**")
                    st.text(_row["original"])
                    st.markdown("**Suggested rewrite**")
                    st.text(_row["rewritten"])
                    if _row.get("why"):
                        st.caption(_row["why"])
                    st.divider()

        from ats.ats_integration import get_ats_report, render_ats_panel

        # Inside the analyse block:
        ats_report = get_ats_report(uploaded, job_desc)
        render_ats_panel(ats_report)        

    st.markdown("</div></div>", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div class="footer">
  ResumeIQ &nbsp;·&nbsp; scikit-learn &nbsp;·&nbsp; LangChain &nbsp;·&nbsp; HuggingFace &nbsp;·&nbsp; spaCy &nbsp;·&nbsp; Plotly
</div>
""", unsafe_allow_html=True)