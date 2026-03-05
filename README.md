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
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

> Parse candidates instantly. Extract names, skills & job categories.  
> Score resumes against any job description in seconds.

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Tech Stack](#-tech-stack)
- [Installation](#-installation)
- [Usage](#-usage)
- [How It Works](#-how-it-works)
- [Model Training](#-model-training)
- [Configuration](#-configuration)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🧠 Overview

**ResumeIQ** is a full-stack AI-powered resume analysis platform built with Streamlit. It allows recruiters and hiring managers to instantly parse resumes, extract structured information, predict job categories, and score candidates against job descriptions — all from a sleek, dark-themed web interface.

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

### 4. Download spaCy language model

```bash
python -m spacy download en_core_web_sm
```

### 5. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your API keys if needed
```

### 6. Run the app

```bash
streamlit run app.py
```

The app will be available at `http://localhost:8501`

---

## 🚀 Usage

1. **Upload a Resume** — Drag and drop or browse for a PDF, DOCX, or TXT file
2. **Add a Job Description** *(optional)* — Paste any job posting to enable match scoring
3. **Click "Analyse Resume"** — The pipeline runs in seconds
4. **Review Results:**
   - Candidate name, job category, word count, and skill count
   - Detected skills as color-coded pills
   - Smart insights about resume quality
   - Match score gauge (0–100%) with tier label
   - 5-dimension score breakdown chart

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
    └──► Match Scoring        (TF-IDF cosine similarity / Sentence Transformers)
              │
              └──► Score Breakdown (5 weighted dimensions)
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
# Optional: HuggingFace API token for private models
HUGGINGFACE_TOKEN=your_token_here
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

Built with ❤️ using Streamlit · scikit-learn · spaCy · LangChain · HuggingFace

</div>
