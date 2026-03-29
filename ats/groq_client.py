"""
groq_client.py  —  Groq API client for ResumeIQ ATS Engine
============================================================
Centralises ALL Groq interactions so every sub-module calls
the same battle-tested client instead of rolling its own.

Responsibilities
----------------
1. Chat completions  →  section classification, keyword enrichment,
                        issue fix suggestions, section-header fallback
2. Semantic embeddings  →  replaces sentence-transformers / S-BERT
   Groq does not expose an embeddings endpoint, so we use a lightweight
   fallback (sklearn TF-IDF cosine) for doc-level similarity and a
   Groq chat call for per-keyword semantic judgement where precision matters.

3. Retry / rate-limit handling  →  exponential back-off, max 3 retries
4. Token budget guard  →  truncates payloads that exceed context limits
5. Structured JSON responses  →  all calls use response_format or
   explicit JSON parsing with a repair pass

Configuration
-------------
Set GROQ_API_KEY in your .env file.  All other settings have defaults.

    GROQ_API_KEY=gsk_...
    GROQ_MODEL=llama-3.3-70b-versatile        # default
    GROQ_EMBEDDING_MODEL=llama-3.3-70b-versatile   # same model for embedding proxy
    GROQ_MAX_TOKENS=1024
    GROQ_TEMPERATURE=0.1                      # low for deterministic parsing tasks
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

from groq import Groq, RateLimitError, APIError


# ═══════════════════════════════════════════════════════════════════════════════
# Defaults
# ═══════════════════════════════════════════════════════════════════════════════
_DEFAULT_MODEL       = "llama-3.3-70b-versatile"
_DEFAULT_MAX_TOKENS  = 1024
_DEFAULT_TEMPERATURE = 0.1
_MAX_RETRIES         = 3
_RETRY_BASE_DELAY    = 1.5     # seconds


class GroqClient:
    """
    Single shared client for all Groq LLM calls in the ATS engine.

    Usage
    -----
    client = GroqClient()                         # reads GROQ_API_KEY from env
    client = GroqClient(api_key="gsk_...")        # explicit key (testing)

    # Plain text completion
    text = client.complete("Classify this section header: 'Accomplishments'")

    # Structured JSON completion (returns dict, never raises on parse error)
    result = client.complete_json(
        prompt="Return JSON: {required: bool, placement: str}",
        schema_hint={"required": False, "placement": "Skills section"},
    )

    # Semantic similarity via Groq proxy (0.0–1.0)
    score = client.semantic_similarity(text_a, text_b)

    # Batch keyword judgement
    judgements = client.judge_keywords(gap_keywords, jd_snippet)
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ):
        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            raise EnvironmentError(
                "GROQ_API_KEY not found. "
                "Set it in your .env file or pass api_key= explicitly."
            )

        self._client      = Groq(api_key=key)
        self._model       = model       or os.getenv("GROQ_MODEL",       _DEFAULT_MODEL)
        self._max_tokens  = max_tokens  or int(os.getenv("GROQ_MAX_TOKENS",  str(_DEFAULT_MAX_TOKENS)))
        self._temperature = temperature or float(os.getenv("GROQ_TEMPERATURE", str(_DEFAULT_TEMPERATURE)))

    # ───────────────────────────────────────────────────────────────────────────
    # Core: plain text completion
    # ───────────────────────────────────────────────────────────────────────────
    def complete(
        self,
        prompt: str,
        system: str = "You are an expert ATS (Applicant Tracking System) analyst.",
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """
        Send a single-turn prompt to Groq and return the text response.
        Retries on rate-limit with exponential back-off.
        """
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": _truncate(prompt, 100_000)},
        ]

        for attempt in range(_MAX_RETRIES):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    max_tokens=max_tokens or self._max_tokens,
                    temperature=temperature or self._temperature,
                )
                return response.choices[0].message.content.strip()

            except RateLimitError:
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_RETRY_BASE_DELAY * (2 ** attempt))
                else:
                    raise

            except APIError as e:
                raise RuntimeError(f"Groq API error: {e}") from e

        return ""   # unreachable but satisfies type checker

    # ───────────────────────────────────────────────────────────────────────────
    # Core: structured JSON completion
    # ───────────────────────────────────────────────────────────────────────────
    def complete_json(
        self,
        prompt: str,
        system: str = "You are an expert ATS analyst. Always respond with valid JSON only.",
        schema_hint: dict | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict | list:
        """
        Returns parsed JSON.  On parse failure, returns schema_hint (default)
        instead of raising — keeps the pipeline running with graceful degradation.
        """
        # Put JSON format instructions in the system message so they are never
        # truncated when the user prompt (e.g. a full resume) is very long.
        schema_str = f"\nExpected JSON schema example:\n{json.dumps(schema_hint)}" if schema_hint else ""
        json_system = (
            system.rstrip()
            + "\n\nIMPORTANT: Respond with valid JSON only. "
            "No markdown fences, no explanations, no extra text."
            + schema_str
        )
        full_prompt = prompt + "\n\nRespond with valid JSON only."

        raw = self.complete(
            full_prompt,
            system=json_system,
            max_tokens=max_tokens or self._max_tokens,
            temperature=temperature,
        )

        # Strip markdown code fences if Groq wraps response
        cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Repair pass: extract first {...} or [...] block
            m = re.search(r"(\{.*\}|\[.*\])", cleaned, re.S)
            if m:
                try:
                    return json.loads(m.group(1))
                except json.JSONDecodeError:
                    pass
            return schema_hint or {}

    # ───────────────────────────────────────────────────────────────────────────
    # Semantic similarity (Groq proxy — replaces S-BERT local download)
    # ───────────────────────────────────────────────────────────────────────────
    def semantic_similarity(self, text_a: str, text_b: str) -> float:
        """
        Returns a 0.0–1.0 semantic similarity score between two texts.

        Strategy:
          For document-level comparison (resume vs JD) we use TF-IDF cosine
          similarity which is fast and deterministic — Groq is overkill here.

          For fine-grained phrase-level judgement (gap keyword vs resume context)
          we ask Groq to rate similarity on a 0–10 scale, then normalise.

        This hybrid avoids unnecessary API calls for bulk operations while
        keeping precision where it matters.
        """
        # Short texts → Groq rating (more accurate for semantic nuance)
        if len(text_a.split()) < 50 and len(text_b.split()) < 50:
            return self._groq_similarity_score(text_a, text_b)

        # Long texts → TF-IDF cosine (fast, no API call needed)
        return _tfidf_cosine(text_a, text_b)

    def _groq_similarity_score(self, text_a: str, text_b: str) -> float:
        prompt = (
            f"Rate the semantic similarity between these two texts on a scale of 0 to 10.\n"
            f"0 = completely unrelated, 10 = identical meaning.\n\n"
            f"Text A: {text_a[:300]}\n"
            f"Text B: {text_b[:300]}\n\n"
            f"Respond with a single number only (e.g. 7)."
        )
        try:
            result = self.complete(prompt, max_tokens=10, temperature=0.0)
            score = float(re.search(r"\d+\.?\d*", result).group())
            return min(1.0, max(0.0, score / 10.0))
        except Exception:
            return 0.5   # safe default

    # ───────────────────────────────────────────────────────────────────────────
    # Keyword enrichment
    # ───────────────────────────────────────────────────────────────────────────
    def judge_keywords(
        self,
        gap_keywords: list[str],
        jd_snippet: str,
        resume_snippet: str = "",
    ) -> dict[str, dict]:
        """
        For each missing keyword, determine:
          - is_required : bool   (hard requirement vs nice-to-have)
          - placement   : str    (where in the resume to add it)
          - rationale   : str    (one-line explanation)

        Returns {keyword: {required: bool, placement: str, rationale: str}}
        """
        if not gap_keywords:
            return {}

        kw_list = ", ".join(f'"{k}"' for k in gap_keywords[:20])
        schema_hint = {
            gap_keywords[0]: {
                "required": True,
                "placement": "Skills section",
                "rationale": "Appears multiple times in the job description as a core requirement.",
            }
        }

        prompt = (
            f"You are an ATS expert. A resume is missing the following keywords "
            f"that appear in a job description.\n\n"
            f"Job Description (snippet):\n{jd_snippet[:800]}\n\n"
            f"Missing Keywords: {kw_list}\n\n"
            f"For each keyword:\n"
            f"1. Is it a hard requirement? (true if the JD uses language like 'required', 'must have', 'essential')\n"
            f"2. Where should the candidate add it? Choose one of: "
            f"Skills section, Experience bullet, Professional Summary, Certifications, Education\n"
            f"3. One-line rationale.\n\n"
            f"Return a JSON object where each key is a keyword."
        )

        result = self.complete_json(prompt, schema_hint=schema_hint)
        if isinstance(result, dict):
            return result
        return {}

    # ───────────────────────────────────────────────────────────────────────────
    # Section classification
    # ───────────────────────────────────────────────────────────────────────────
    def classify_section(self, header: str, body_snippet: str) -> str | None:
        """
        Classify an ambiguous resume section header into a canonical category.
        Returns one of: contact | summary | experience | education |
                        skills | projects | certifications | other
        """
        valid = {"contact","summary","experience","education","skills","projects","certifications","other"}
        prompt = (
            f"Classify this resume section into exactly one of these categories:\n"
            f"contact, summary, experience, education, skills, projects, certifications, other\n\n"
            f"Section header: '{header}'\n"
            f"Content preview: '{body_snippet[:200]}'\n\n"
            f"Reply with the category name only. No explanation."
        )
        try:
            result = self.complete(prompt, max_tokens=15, temperature=0.0).lower().strip()
            return result if result in valid else None
        except Exception:
            return None

    # ───────────────────────────────────────────────────────────────────────────
    # Fix suggestions  (used by issue enrichment pass)
    # ───────────────────────────────────────────────────────────────────────────
    def suggest_fix(self, issue_message: str, context_snippet: str) -> str:
        """
        Generate a concrete, actionable fix for a detected ATS issue.
        Used to enrich auto-detected issues with richer guidance.
        """
        prompt = (
            f"An ATS resume scanner detected this issue:\n'{issue_message}'\n\n"
            f"Relevant resume snippet:\n'{context_snippet[:300]}'\n\n"
            f"Give a single, specific, actionable fix instruction in 1–2 sentences. "
            f"Be concrete — tell the candidate exactly what to change."
        )
        try:
            return self.complete(prompt, max_tokens=120, temperature=0.2)
        except Exception:
            return "Review and correct this issue manually."

    # ───────────────────────────────────────────────────────────────────────────
    # Compatibility shim  (so existing code calling .predict() still works)
    # ───────────────────────────────────────────────────────────────────────────
    def predict(self, prompt: str) -> str:
        """LangChain-style .predict() shim for backward compatibility."""
        return self.complete(prompt)


# ═══════════════════════════════════════════════════════════════════════════════
# Module-level helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _truncate(text: str, max_chars: int) -> str:
    """Trim text to stay within Groq context limits."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n[truncated]"


def _tfidf_cosine(text_a: str, text_b: str) -> float:
    """
    Fast TF-IDF cosine similarity for long document comparison.
    No API call needed — used for resume vs JD document-level scoring.
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        vec = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True)
        matrix = vec.fit_transform([text_a, text_b])
        return float(cosine_similarity(matrix[0], matrix[1])[0][0])
    except Exception:
        return 0.5
