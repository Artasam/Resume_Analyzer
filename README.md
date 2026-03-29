## AI-Powered Resume-Analyzer

Streamlit App
Link: https://resumeanalyzerak47.streamlit.app/

<div align="center">

# 📝 ResumeIQ

### AI-Powered Resume Intelligence Platform

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-F7931E?style=flat-square&logo=scikit-learn&logoColor=white)
![spaCy](https://img.shields.io/badge/spaCy-NLP-09A3D5?style=flat-square&logo=spacy&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-LLM-F55036?style=flat-square&logo=groq&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

> Parse candidates instantly. Extract names, skills & job categories.  
> Score resumes against any job description in seconds.  
> Simulate ATS screening across 6 platforms. AI-polish weak bullets.

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [What's New (v2.0)](#-whats-new-v20)
- [Project Structure](#-project-structure)
- [Tech Stack](#-tech-stack)
- [Installation](#-installation)
- [Usage](#-usage)
- [How It Works](#-how-it-works)
- [ATS Simulation Engine](#-ats-simulation-engine)
- [AI Bullet Polish](#-ai-bullet-polish)
- [Model Training](#-model-training)
- [Configuration](#-configuration)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🧠 Overview

**ResumeIQ** is a full-stack AI-powered resume analysis platform built with Streamlit. It allows recruiters and hiring managers to instantly parse resumes, extract structured information, predict job categories, and score candidates against job descriptions — all from a sleek, dark-themed web interface.

**v2.0** adds a full **ATS Simulation Engine** (powered by Groq LLM) that audits resumes against 6 real-world ATS platforms, plus an **AI Bullet Polish** feature that rewrites weak experience lines into achievement-focused statements.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📄 **Multi-format Parsing** | Supports PDF, DOCX, and TXT resume uploads |
| 👤 **Name Extraction** | Identifies candidate names via spaCy NER + regex heuristics or Use LLM as a fallback |
| 🛠 **Skills Detection** | Matches against a curated database of 100+ technical skills, with LLM as an intelligent fallback for unlisted or emerging skills |
| 🏷 **Job Category Prediction** | Logistic Regression model predicts the most fitting job category |
| 🎯 **Match Scoring** | TF-IDF / Sentence Transformers cosine similarity against any JD |
| 📊 **Score Breakdown** | 5-dimension analysis: Keywords, Skills Overlap, Experience Fit, Role Alignment, Tech Stack |
| 💡 **Smart Insights** | Auto-generated feedback on resume length, skill density, and role alignment |
| 🤖 **ATS Simulation** | Simulates resume screening across 6 ATS platforms (Taleo, Workday, Greenhouse, iCIMS, Lever, Generic) with per-platform scores, severity-ranked issues, and actionable fix suggestions |
| 🎯 **Keyword Gap Analysis** | Identifies missing JD keywords, flags required vs. nice-to-have, and suggests exact placement in the resume |
| ✨ **AI Bullet Polish** | Detects weak experience bullets and rewrites them into achievement-focused lines with metrics and strong action verbs via Groq LLM |

---

## 🆕 What's New (v2.0)

### 🤖 ATS Simulation Engine
- Full multi-platform ATS audit (Taleo, Workday, Greenhouse, iCIMS, Lever, Generic)
- Layout & formatting analysis (column detection, tables, text boxes, image PDFs, fonts, encoding)
- Semantic section parsing with LLM-assisted classification for ambiguous headers
- Readability scoring with platform-specific tolerance profiles
- Keyword gap analysis with LLM-powered requirement classification and placement suggestions
- Severity-ranked issues (Critical / High / Medium / Low) with concrete, actionable fix instructions
- Powered by **Groq API** (Llama 3.3 70B) — no local model downloads required

### ✨ AI Bullet Polish
- Auto-detects weak experience bullets (vague duties, passive voice, missing metrics)
- Rewrites into achievement-focused statements with strong action verbs and quantified impact
- Supports both auto-pick and manual paste modes
- Optionally aligns rewrites with a job description for keyword relevance
- Groq-backed (same API key as ATS engine)

### 🔧 Infrastructure Improvements
- Centralised `GroqClient` with retry / rate-limit handling, token budget guards, and structured JSON responses with repair pass
- Prompt truncation fix for long resumes (up to 100K chars for prompts, 50K for bullet rewriting)
- JSON schema instructions moved to system message to prevent truncation with long user prompts
- Analysis results cached in `st.session_state` so bullet rewrite / ATS actions don't reset the analysis

---

## 📁 Project Structure

```
resumeiq/
│
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── resave_models.py          # Utility to re-serialize trained models
├── .env                      # Environment variables (not committed)
├── .gitignore
│
├── parsers/
│   ├── text_extractor.py     # PDF/DOCX/TXT text extraction & cleaning
│   └── name_extractor.py     # Candidate name extraction via spaCy
│
├── skills/
│   └── extractor.py          # Skill matching against technology database
│
├── matching/
│   └── matcher.py            # TF-IDF / Sentence Transformer match scoring
│
├── predict_category/
│   └── predict.py            # Job category prediction pipeline
│
├── ats/                      # ★ NEW — ATS Simulation Engine
│   ├── __init__.py           # Public API (ATSEngine, ATSReport, etc.)
│   ├── ats_engine.py         # Orchestrator — runs all sub-engines
│   ├── ats_integration.py    # Streamlit UI panel for ATS results
│   ├── groq_client.py        # Centralised Groq LLM client (retry, JSON, similarity)
│   ├── keyword_engine.py     # JD keyword extraction & gap analysis
│   ├── layout_analyser.py    # PDF/DOCX layout, column, table detection
│   ├── semantic_parser.py    # Section parsing & LLM-assisted classification
│   ├── readability.py        # Per-platform ATS readability scoring
│   └── models.py             # Dataclasses & enums (ATSReport, Issue, Severity, Platform, etc.)
│
├── rewriting/                # ★ NEW — AI Bullet Polish
│   ├── __init__.py           # Public API (rewrite_weak_bullets)
│   └── bullet_rewriter.py   # Weak bullet detection & Groq-powered rewriting
│
├── models/
│   ├── lr_model.pkl          # Trained Logistic Regression model
│   ├── tfidf.pkl             # Fitted TF-IDF vectorizer
│   └── encoder.pkl           # Label encoder for job categories
│
├── config/
│   └── ...                   # App configuration files
│
└── RS/
    └── ...                   # Raw resume dataset (excluded from git)
```

---

## 🛠 Tech Stack

**Frontend**
- [Streamlit](https://streamlit.io/) — Interactive web UI
- [Plotly](https://plotly.com/) — Gauge charts & breakdown visualizations
- Custom CSS — Dark luxury theme with animated grid, Syne + Space Grotesk + DM Mono fonts

**NLP & ML**
- [spaCy](https://spacy.io/) — Named entity recognition for name extraction
- [scikit-learn](https://scikit-learn.org/) — TF-IDF vectorizer + Logistic Regression classifier
- [Sentence Transformers](https://www.sbert.net/) — Semantic similarity scoring (S-BERT)
- [LangChain](https://www.langchain.com/) — LLM orchestration layer

**LLM / AI**
- [Groq](https://groq.com/) — Ultra-fast LLM inference (Llama 3.3 70B Versatile)
  - ATS section classification, keyword enrichment, fix suggestions
  - Bullet rewriting with achievement-focused prompts
  - Semantic similarity proxy for fine-grained phrase comparison
  - Structured JSON responses with retry & repair pipeline

**Data Processing**
- [pdfplumber](https://github.com/jsvine/pdfplumber) — PDF text extraction
- [python-docx](https://python-docx.readthedocs.io/) — DOCX parsing
- [HuggingFace Transformers](https://huggingface.co/) — Pre-trained model hub

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/resumeiq.git
cd resumeiq
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Download spaCy language models

```bash
python -m spacy download en_core_web_sm
python -m spacy download en_core_web_lg
```

> **Note:** `en_core_web_sm` is used for name extraction; `en_core_web_lg` is used by the ATS semantic parser for higher-accuracy section parsing.

### 5. Set up environment variables

Create a `.env` file in the project root:

```env
# Required for ATS Simulation & AI Bullet Polish
GROQ_API_KEY=gsk_your_groq_api_key_here

# Optional: HuggingFace API token for private models
HUGGINGFACEHUB_API_TOKEN=your_token_here

# Optional: Override Groq defaults
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_MAX_TOKENS=1024
GROQ_TEMPERATURE=0.1
GROQ_REWRITE_MAX_TOKENS=2048
GROQ_REWRITE_TEMPERATURE=0.35
```

### 6. Run the app

```bash
streamlit run app.py
```

The app will be available at `http://localhost:8501`

---

## 🚀 Usage

1. **Upload a Resume** — Drag and drop or browse for a PDF, DOCX, or TXT file
2. **Add a Job Description** *(optional)* — Paste any job posting to enable match scoring & keyword gap analysis
3. **Click "Analyse Resume"** — The pipeline runs in seconds
4. **Review Results:**
   - Candidate name, job category, word count, and skill count
   - Detected skills as color-coded pills
   - Smart insights about resume quality
   - Match score gauge (0–100%) with tier label
   - 5-dimension score breakdown chart
5. **ATS Simulation** *(automatic)* — Per-platform scores, severity-ranked issues with fix instructions, keyword gap analysis
6. **AI Bullet Polish** *(expandable panel)* — Auto-detect weak bullets or paste your own, get achievement-focused rewrites

---

## 🔍 How It Works

```
Resume File
    │
    ▼
Text Extraction (parsers/text_extractor.py)
    │   PDF  → pdfplumber
    │   DOCX → python-docx
    │   TXT  → direct read
    ▼
Text Cleaning & Normalization
    │
    ├──► Name Extraction      (spaCy NER + regex heuristics)
    │
    ├──► Skills Detection     (keyword matching vs. 100+ tech database)
    │
    ├──► Category Prediction  (TF-IDF → Logistic Regression → LabelEncoder)
    │
    ├──► Match Scoring        (TF-IDF cosine similarity / Sentence Transformers)
    │         │
    │         └──► Score Breakdown (5 weighted dimensions)
    │
    ├──► ATS Simulation       ★ NEW
    │         │
    │         ├──► Layout Analysis     (columns, tables, fonts, encoding, images)
    │         ├──► Semantic Parsing    (section detection + LLM classification)
    │         ├──► Readability Scoring (per-platform tolerance profiles)
    │         └──► Keyword Gap Analysis (TF-IDF + Groq LLM judgement)
    │
    └──► AI Bullet Polish     ★ NEW
              │
              ├──► Weak Bullet Detection (passive voice, vague duties, missing metrics)
              └──► Groq LLM Rewrite     (achievement-focused, quantified, ATS-friendly)
```

### Match Scoring Dimensions

| Dimension | Description |
|---|---|
| **Keywords** | Overlap of important JD keywords in the resume |
| **Skills Overlap** | Matching technical skills between resume and JD |
| **Experience Fit** | Estimated seniority and experience alignment |
| **Role Alignment** | Job title and responsibility similarity |
| **Tech Stack** | Programming languages, tools, and framework match |

### Score Tiers

| Score | Tier | Meaning |
|---|---|---|
| 0 – 24% | 🔵 Weak Match | Low alignment, heavy tailoring needed |
| 25 – 49% | 🟣 Fair Match | Some overlap, keyword edits recommended |
| 50 – 69% | ✨ Good Match | Decent fit, a few tweaks needed |
| 70 – 84% | 🟢 Great Match | Strong alignment, minor polish recommended |
| 85 – 100% | ⭐ Perfect Match | Outstanding fit, top-tier candidate |

---

## 🤖 ATS Simulation Engine

The ATS engine (`ats/`) simulates how 6 real-world Applicant Tracking Systems parse and score a resume. It provides:

### Platforms Simulated

| Platform | Strictness | Notes |
|---|---|---|
| **Taleo** | 🔴 Strictest | Legacy parser; DOCX preferred; fails on multi-column layouts |
| **Workday** | 🟠 Strict | Improved PDF handling since 2024; strict on encoding |
| **iCIMS** | 🟡 Moderate | Enterprise standard; moderate tolerance |
| **Greenhouse** | 🟢 Tolerant | Human-first review culture; most forgiving parser |
| **Lever** | 🟢 Tolerant | Startup/tech focused; ATS + CRM hybrid |
| **Generic** | ⚪ Baseline | Lowest-common-denominator safe benchmark |

### Analysis Dimensions

| Component | Weight | What It Checks |
|---|---|---|
| **Layout & Formatting** | 40% | Columns, tables, text boxes, image PDFs, fonts, special characters, encoding |
| **Semantic Structure** | 30% | Section headers, missing sections, field extraction, LLM-assisted classification |
| **Readability** | 30% | Per-platform tolerance scoring, ATS-specific readability rules |

### Issue Severity Levels

| Level | Icon | Meaning |
|---|---|---|
| **Critical** | 🔴 | Will almost certainly cause mis-parse or rank-zero result |
| **High** | 🟠 | Likely to hurt score significantly |
| **Medium** | 🟡 | May hurt score on strict platforms |
| **Low** | 🔵 | Best-practice recommendation |

### Keyword Gap Analysis

When a job description is provided, the engine also performs:
- **TF-IDF keyword extraction** from the JD
- **Gap detection** — keywords present in JD but missing from resume
- **LLM-powered classification** — flags each gap as *required* vs. *nice-to-have*
- **Placement suggestions** — tells candidates exactly where to add each keyword (Skills section, Experience bullet, Summary, etc.)

---

## ✨ AI Bullet Polish

The bullet rewriter (`rewriting/`) identifies weak experience lines and rewrites them into stronger, achievement-focused statements.

### How It Works

1. **Auto-detection** — Scans resume for bullet-style lines that are weak (vague duties, passive voice, "responsible for" patterns, missing outcomes/metrics)
2. **LLM Rewrite** — Sends weak bullets to Groq with constraints:
   - Strong past-tense action verb first
   - Add scope, impact, and quantified results (uses `~` or `approximately` when estimating)
   - Stays truthful — no fabricated employers, tools, or metrics
   - Each bullet ≤ 40 words, plain text, ATS-friendly
3. **JD Alignment** *(optional)* — When a JD is provided, rewrites naturally incorporate relevant keywords

### Modes

| Mode | Description |
|---|---|
| **Auto-pick** | Finds up to 8 weak bullets from the resume and rewrites them |
| **Paste lines** | User pastes specific lines (up to 12) for targeted rewriting |

---

## 🤖 Model Training

The category prediction model was trained on a labeled resume dataset.

To retrain or re-serialize the models:

```bash
python resave_models.py
```

This regenerates `models/lr_model.pkl`, `models/tfidf.pkl`, and `models/encoder.pkl`.

> **Note:** Model files are excluded from git by default (see `.gitignore`).  
> Place pre-trained `.pkl` files in the `models/` directory before running the app.

---

## 🔧 Configuration

Environment variables (`.env`):

```env
# Required for ATS Simulation & AI Bullet Polish
GROQ_API_KEY=gsk_your_groq_api_key_here

# Optional: HuggingFace API token for private models
HUGGINGFACEHUB_API_TOKEN=your_token_here

# Optional: Override Groq defaults
GROQ_MODEL=llama-3.3-70b-versatile          # default model
GROQ_MAX_TOKENS=1024                         # default max response tokens
GROQ_TEMPERATURE=0.1                         # low for deterministic parsing
GROQ_REWRITE_MAX_TOKENS=2048                 # max tokens for bullet rewriting
GROQ_REWRITE_TEMPERATURE=0.35                # slightly higher for creative rewrites
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

Please follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Built with ❤️ using Streamlit · scikit-learn · spaCy · LangChain · HuggingFace · Groq

</div>
