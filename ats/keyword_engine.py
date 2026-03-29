"""
keyword_engine.py  —  Semantic keyword gap analysis
=====================================================
Three-layer keyword analysis — fully cloud-based, no local model downloads.

Layer 1 — TF-IDF importance weighting
  • Extract the top-N most discriminative terms from the JD using TF-IDF
  • Check presence in resume using exact + stem match
  • Produces tfidf_score (0–1)

Layer 2 — Groq semantic similarity  [replaces local S-BERT]
  • Document-level: TF-IDF cosine (fast, deterministic, free)
  • Phrase-level: Groq LLM rates gap-term vs resume-context similarity (0–10)
  • Catches near-misses: "Redux" in JD vs "state management" in resume

Layer 3 — Groq keyword enrichment
  • Classify each gap keyword as Required / Nice-to-have
  • Suggest best placement (Skills, Experience bullet, Summary…)
  • One-line rationale per keyword

Requires: GROQ_API_KEY in .env
"""

from __future__ import annotations

import re
import string
from typing import Any

from .models import Issue, IssueCategory, KeywordGap, KeywordResult, Severity

# Optional heavy-weight imports — graceful degradation
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False


try:
    import nltk
    from nltk.stem import PorterStemmer
    _NLTK_AVAILABLE = True
    _stemmer = PorterStemmer()
except ImportError:
    _NLTK_AVAILABLE = False
    _stemmer = None


# ═══════════════════════════════════════════════════════════════════════════════


class KeywordEngine:

    def __init__(self, groq_client=None):
        self._groq  = groq_client
        # Groq handles semantic similarity — no local SBERT download

        
        

    # ───────────────────────────────────────────────────────────────────────────
    def analyse(self, resume_text: str, jd_text: str) -> KeywordResult:
        issues: list[Issue] = []

        resume_clean = _clean(resume_text)
        jd_clean     = _clean(jd_text)

        # ── Layer 1: TF-IDF keyword extraction & coverage ────────────────────
        tfidf_score, jd_keywords, covered, gaps_raw = self._tfidf_analysis(
            resume_clean, jd_clean
        )

        # ── Layer 2: S-BERT semantic similarity ──────────────────────────────
        sbert_score, gap_sims = self._groq_semantic_analysis(
            resume_clean, jd_clean, gaps_raw
        )

        # ── Layer 3: LLM enrichment (optional) ───────────────────────────────
        keyword_meta = {}
        if self._groq and gaps_raw:
            keyword_meta = self._groq_enrich(gaps_raw, jd_text)

        # ── Assemble KeywordGap objects ───────────────────────────────────────
        gap_objects: list[KeywordGap] = []
        for kw in gaps_raw:
            meta = keyword_meta.get(kw, {})
            gap_objects.append(KeywordGap(
                keyword=kw,
                frequency_in_jd=jd_keywords.get(kw, 1),
                in_resume=False,
                is_required=meta.get("required", False),
                suggested_placement=meta.get("placement", "Add to Skills section"),
            ))

        # Sort: required first, then by JD frequency
        gap_objects.sort(key=lambda g: (not g.is_required, -g.frequency_in_jd))

        # ── Quality issues ────────────────────────────────────────────────────
        coverage_pct = len(covered) / len(jd_keywords) if jd_keywords else 1.0

        if coverage_pct < 0.40:
            issues.append(Issue(
                severity=Severity.CRITICAL,
                category=IssueCategory.KEYWORDS,
                message=f"Only {coverage_pct:.0%} of important JD keywords found in resume. ATS will rank this very low.",
                fix="Add a dedicated Skills section and weave critical JD keywords naturally into experience bullets.",
                platform=None,
            ))
        elif coverage_pct < 0.65:
            issues.append(Issue(
                severity=Severity.HIGH,
                category=IssueCategory.KEYWORDS,
                message=f"{coverage_pct:.0%} keyword coverage. {len(gaps_raw)} important JD terms are missing.",
                fix="Review the Missing Keywords list and incorporate the top 5–8 terms into your resume.",
                platform=None,
            ))

        # Check for keyword stuffing
        resume_kw_density = _keyword_density(resume_clean, list(jd_keywords.keys()))
        if resume_kw_density > 0.07:
            issues.append(Issue(
                severity=Severity.MEDIUM,
                category=IssueCategory.KEYWORDS,
                message="Keyword density appears very high (possible keyword stuffing). Modern ATS and recruiters penalise this.",
                fix="Ensure keywords appear naturally within sentences, not as repetitive lists.",
                platform=None,
            ))

        return KeywordResult(
            match_score=sbert_score,
            tfidf_score=tfidf_score,
            gaps=gap_objects,
            present_keywords=list(covered),
            issues=issues,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Layer 1: TF-IDF
    # ─────────────────────────────────────────────────────────────────────────
    def _tfidf_analysis(
        self,
        resume: str,
        jd: str,
    ) -> tuple[float, dict[str, int], set[str], list[str]]:
        """
        Returns:
          tfidf_score   — cosine similarity between jd and resume tf-idf vectors
          jd_keywords   — {term: raw_count} of top N JD terms
          covered       — set of JD keywords present in resume (stem-matched)
          gaps_raw      — list of important JD keywords missing from resume
        """
        if not _SKLEARN_AVAILABLE:
            return 0.5, {}, set(), []

        # Fit vectorizer on both documents
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words="english",
            min_df=1,
            max_features=500,
            sublinear_tf=True,
        )
        matrix = vectorizer.fit_transform([jd, resume])
        feature_names = vectorizer.get_feature_names_out()

        jd_vec     = matrix[0]
        resume_vec = matrix[1]

        # Cosine similarity
        sim = float(cosine_similarity(jd_vec, resume_vec)[0][0])

        # Top JD keywords by TF-IDF weight
        jd_scores = zip(feature_names, jd_vec.toarray()[0])
        top_jd = sorted(jd_scores, key=lambda x: -x[1])[:40]

        # Build frequency map from raw JD text
        jd_raw_tokens = _tokenize(jd)
        jd_keywords = {}
        for term, score in top_jd:
            if score > 0.01:  # Ignore negligible terms
                jd_keywords[term] = jd_raw_tokens.count(term.split()[0])

        # Check coverage using stem-matching
        resume_stems = _stem_set(_tokenize(resume))
        covered: set[str] = set()
        gaps: list[str] = []

        for term in jd_keywords:
            term_stems = _stem_set(term.split())
            if term_stems & resume_stems or term.lower() in resume.lower():
                covered.add(term)
            else:
                gaps.append(term)

        return sim, jd_keywords, covered, gaps

    # ─────────────────────────────────────────────────────────────────────────
    # Layer 2: S-BERT
    # ─────────────────────────────────────────────────────────────────────────
    def _groq_semantic_analysis(
        self,
        resume: str,
        jd: str,
        gaps: list[str],
    ) -> tuple[float, dict[str, float]]:
        """
        Document-level similarity via TF-IDF cosine (fast, no API call).
        Per-gap semantic judgement via Groq (precision where it matters).

        Replaces the previous local S-BERT / sentence-transformers approach.
        No model downloads required.
        """
        # Document-level: TF-IDF cosine (deterministic, free, no API call)
        from .groq_client import _tfidf_cosine
        doc_similarity = _tfidf_cosine(resume, jd)

        # Per-gap: ask Groq to rate how semantically close each gap term
        # is to the resume context — catches near-misses like
        # "Redux" in JD vs "state management" in resume.
        gap_sims: dict[str, float] = {}
        if gaps and self._groq:
            resume_context = " ".join(resume.split()[:200])   # first 200 words
            for gap_term in gaps[:15]:                        # cap API calls
                try:
                    gap_sims[gap_term] = self._groq.semantic_similarity(
                        gap_term, resume_context
                    )
                except Exception:
                    gap_sims[gap_term] = 0.0

        return doc_similarity, gap_sims

    # ─────────────────────────────────────────────────────────────────────────
    # Layer 3: Groq keyword enrichment
    # ─────────────────────────────────────────────────────────────────────────
    def _groq_enrich(self, gaps: list[str], jd_text: str) -> dict[str, dict]:
        """
        Ask Groq to classify each missing keyword as required / nice-to-have
        and suggest the best placement in the resume.
        Returns {keyword: {required: bool, placement: str, rationale: str}}
        """
        if not self._groq or not gaps:
            return {}

        try:
            return self._groq.judge_keywords(
                gap_keywords=gaps,
                jd_snippet=jd_text,
            )
        except Exception:
            return {}

# ═══════════════════════════════════════════════════════════════════════════════

def _clean(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s\-\+\#\.]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _tokenize(text: str) -> list[str]:
    return [w for w in re.split(r"\W+", text.lower()) if len(w) > 2]


def _stem_set(tokens: list[str]) -> set[str]:
    if _nltk_available():
        return {_stemmer.stem(t) for t in tokens}
    return set(tokens)


def _nltk_available() -> bool:
    return _NLTK_AVAILABLE and _stemmer is not None


def _keyword_density(text: str, keywords: list[str]) -> float:
    if not text or not keywords:
        return 0.0
    total_words = len(text.split())
    kw_occurrences = sum(text.lower().count(k.lower()) for k in keywords)
    return kw_occurrences / max(total_words, 1)