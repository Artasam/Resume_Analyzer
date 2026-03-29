"""
ats_engine.py  —  ResumeIQ ATS Simulation Engine
=================================================
All LLM calls go through GroqClient (groq_client.py).
Set GROQ_API_KEY in your .env — no local model downloads required.
"""

from __future__ import annotations

from pathlib import Path

from .layout_analyser import LayoutAnalyser
from .semantic_parser import SemanticParser
from .keyword_engine  import KeywordEngine
from .readability     import ReadabilityScorer
from .models          import ATSReport, Issue, Severity, Platform
from .groq_client     import GroqClient


class ATSEngine:
    """
    Public entry point.

    Usage
    -----
    engine = ATSEngine()                         # reads GROQ_API_KEY from env
    engine = ATSEngine(groq_api_key="gsk_...")   # explicit key
    report = engine.analyse(file_bytes, filename, job_description)
    """

    def __init__(
        self,
        groq_api_key: str | None = None,
        groq_model: str = "llama-3.3-70b-versatile",
        spacy_model: str = "en_core_web_lg",
        target_platforms: list[Platform] | None = None,
    ):
        self.target_platforms = target_platforms or list(Platform)

        # Single shared Groq client — passed to all sub-engines
        self._groq = GroqClient(api_key=groq_api_key, model=groq_model)

        self._layout      = LayoutAnalyser()
        self._semantic    = SemanticParser(spacy_model=spacy_model, groq_client=self._groq)
        self._keywords    = KeywordEngine(groq_client=self._groq)
        self._readability = ReadabilityScorer()

    def analyse(
        self,
        file_bytes: bytes,
        filename: str,
        job_description: str = "",
    ) -> ATSReport:
        ext = Path(filename).suffix.lower()

        layout_result   = self._layout.analyse(file_bytes, ext)
        semantic_result = self._semantic.parse(layout_result.plain_text, ext)

        keyword_result = None
        if job_description.strip():
            keyword_result = self._keywords.analyse(
                resume_text=layout_result.plain_text,
                jd_text=job_description,
            )

        readability_result = self._readability.score(
            layout=layout_result,
            semantic=semantic_result,
            platforms=self.target_platforms,
        )

        all_issues = (
            layout_result.issues
            + semantic_result.issues
            + readability_result.issues
        )
        if keyword_result:
            all_issues += keyword_result.issues

        return ATSReport(
            overall_score=_compute_overall(layout_result, semantic_result, readability_result),
            per_platform_scores=readability_result.platform_scores,
            issues=_deduplicate_and_rank(all_issues),
            parsed_fields=semantic_result.fields,
            keyword_analysis=keyword_result,
            layout_meta=layout_result.meta,
        )


def _compute_overall(layout, semantic, readability) -> int:
    score = (
        layout.score       * 0.40
        + semantic.score   * 0.30
        + readability.score * 0.30
    )
    return max(0, min(100, round(score)))


def _deduplicate_and_rank(issues: list[Issue]) -> list[Issue]:
    seen, unique = set(), []
    for issue in issues:
        key = (issue.category, issue.message[:60])
        if key not in seen:
            seen.add(key)
            unique.append(issue)
    order = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2, Severity.LOW: 3}
    return sorted(unique, key=lambda i: order[i.severity])