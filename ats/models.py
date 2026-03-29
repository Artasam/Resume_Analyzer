"""
models.py  —  Shared dataclasses & enums for the ATS engine
"""

from __future__ import annotations

import dataclasses
from enum import Enum
from typing import Any, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════

class Severity(Enum):
    CRITICAL = "critical"   # Will almost certainly cause mis-parse or rank-zero
    HIGH     = "high"       # Likely to hurt score significantly
    MEDIUM   = "medium"     # May hurt score in strict platforms
    LOW      = "low"        # Best-practice recommendation


class Platform(Enum):
    """ATS platforms to simulate. Each has its own tolerance profile."""
    TALEO     = "taleo"       # Strictest parser; legacy engine; DOCX preferred
    WORKDAY   = "workday"     # Large enterprises; improved PDF handling since 2024
    GREENHOUSE = "greenhouse" # Most tolerant; human-first review culture
    ICIMS     = "icims"       # Enterprise standard; moderate strictness
    LEVER     = "lever"       # Startup / tech; ATS + CRM hybrid; tolerant
    GENERIC   = "generic"     # Lowest-common-denominator safe baseline


class IssueCategory(Enum):
    LAYOUT      = "Layout & Formatting"
    STRUCTURE   = "Section Structure"
    CONTENT     = "Content Quality"
    KEYWORDS    = "Keyword Gaps"
    ENCODING    = "Encoding & Characters"
    CONTACT     = "Contact Information"
    DATES       = "Date Formatting"
    READABILITY = "ATS Readability"


# ═══════════════════════════════════════════════════════════════════════════════
# Core dataclasses
# ═══════════════════════════════════════════════════════════════════════════════

@dataclasses.dataclass
class Issue:
    severity : Severity
    category : IssueCategory
    message  : str                     # Human-readable description
    fix      : str                     # Concrete, actionable fix instruction
    platform : Platform | None = None  # None = affects all platforms
    line_hint: str | None = None       # Snippet from resume that triggered this


@dataclasses.dataclass
class KeywordGap:
    keyword    : str
    frequency_in_jd : int
    in_resume  : bool
    is_required: bool          # True if flagged as hard requirement by LLM
    suggested_placement: str   # e.g. "Add to Skills section" or "Weave into Experience bullet 2"


@dataclasses.dataclass
class KeywordResult:
    match_score      : float           # 0.0–1.0 semantic similarity (SBERT)
    tfidf_score      : float           # 0.0–1.0 TF-IDF cosine similarity
    gaps             : list[KeywordGap]
    present_keywords : list[str]
    issues           : list[Issue]


@dataclasses.dataclass
class LayoutMeta:
    file_format     : str              # "pdf" | "docx" | "txt"
    is_image_pdf    : bool             # Scanned / non-selectable text
    column_count    : int              # 1 | 2 | 3+
    has_tables      : bool
    has_text_boxes  : bool             # Floating text boxes (Word artifacts)
    has_header_footer_content: bool    # Contact info placed in header/footer
    has_graphics    : bool             # Photos, icons, logos
    has_columns_via_table: bool        # Fake columns using HTML/DOCX tables
    font_count      : int              # Unique fonts used
    special_char_ratio: float          # Ratio of non-ASCII characters
    character_encoding: str            # "utf-8" | "latin-1" | unknown
    page_count      : int
    word_count      : int


@dataclasses.dataclass
class LayoutResult:
    score      : float                 # 0–100
    plain_text : str                   # Clean extracted text (best-effort)
    meta       : LayoutMeta
    issues     : list[Issue]


@dataclasses.dataclass
class SemanticResult:
    score  : float                     # 0–100
    fields : dict[str, Any]            # e.g. {"name": "...", "experience": [...]}
    sections_found    : list[str]      # Detected section headers (normalised)
    sections_missing  : list[str]      # Expected but absent sections
    issues : list[Issue]


@dataclasses.dataclass
class ReadabilityResult:
    score           : float
    platform_scores : dict[Platform, int]
    issues          : list[Issue]


@dataclasses.dataclass
class ATSReport:
    overall_score       : int                   # 0–100
    per_platform_scores : dict[Platform, int]   # Per-ATS scores
    issues              : list[Issue]           # Ranked by severity
    parsed_fields       : dict[str, Any]        # Extracted structured data
    keyword_analysis    : KeywordResult | None  # None if no JD supplied
    layout_meta         : LayoutMeta

    # ── Convenience properties ───────────────────────────────────────────────
    @property
    def critical_issues(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == Severity.CRITICAL]

    @property
    def high_issues(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == Severity.HIGH]

    @property
    def pass_rate(self) -> str:
        """Human-readable likelihood of passing ATS screening."""
        if self.overall_score >= 85: return "Very Likely to Pass"
        if self.overall_score >= 70: return "Likely to Pass"
        if self.overall_score >= 50: return "Borderline"
        if self.overall_score >= 30: return "At Risk"
        return "Likely to Fail"
