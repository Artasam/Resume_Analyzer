"""
readability.py  —  Per-platform ATS readability scoring
=========================================================
Each ATS platform has a tolerance profile.
Rather than hardcoded pass/fail rules, we model each platform as a
weight vector over layout and semantic signals — the score for each
platform is the dot product of its weight vector and the feature vector.

Platform profiles are derived from documented real-world parsing
behaviour (see research references in README).

Taleo:     legacy parser, very strict about structure, dates, encoding
Workday:   improved PDF handling, tolerates modern formatting better
Greenhouse: human-first, most tolerant of creative formatting
iCIMS:     enterprise, moderate; strict about table-free content
Lever:     startup/tech hybrid, most tolerant overall
Generic:   worst-case baseline
"""

from __future__ import annotations

import dataclasses
from typing import Any

from .models import (
    Issue, IssueCategory, LayoutResult, Platform,
    ReadabilityResult, SemanticResult, Severity
)


# ═══════════════════════════════════════════════════════════════════════════════
# Platform tolerance profiles
# ═══════════════════════════════════════════════════════════════════════════════

@dataclasses.dataclass
class PlatformProfile:
    name         : Platform
    # Penalty multipliers (1.0 = full penalty, 0.0 = ignores the issue)
    image_pdf_penalty    : float = 1.0
    multi_column_penalty : float = 1.0
    table_penalty        : float = 1.0
    text_box_penalty     : float = 1.0
    header_footer_penalty: float = 1.0
    graphics_penalty     : float = 1.0
    encoding_penalty     : float = 1.0
    missing_section_penalty : float = 1.0
    date_format_penalty  : float = 1.0
    # Platform-specific notes shown in the report
    note: str = ""


_PROFILES: dict[Platform, PlatformProfile] = {
    Platform.TALEO: PlatformProfile(
        name=Platform.TALEO,
        image_pdf_penalty=1.0,
        multi_column_penalty=1.0,
        table_penalty=1.0,
        text_box_penalty=1.0,
        header_footer_penalty=1.0,
        graphics_penalty=1.0,
        encoding_penalty=1.0,
        missing_section_penalty=1.0,
        date_format_penalty=1.0,
        note=(
            "Taleo is the strictest legacy parser. "
            "It expects rigid section headers, Month-Year dates, "
            "single-column layout, and DOCX format over PDF. "
            "Multi-column and table layouts will cause complete mis-parse."
        ),
    ),
    Platform.WORKDAY: PlatformProfile(
        name=Platform.WORKDAY,
        image_pdf_penalty=1.0,
        multi_column_penalty=0.8,   # Improved PDF handling since 2024
        table_penalty=0.85,
        text_box_penalty=1.0,
        header_footer_penalty=0.9,
        graphics_penalty=0.8,
        encoding_penalty=0.8,
        missing_section_penalty=0.9,
        date_format_penalty=0.7,
        note=(
            "Workday has significantly improved PDF parsing since 2024, "
            "but multi-column layouts and tables remain risky. "
            "Contact info in headers/footers is still commonly lost."
        ),
    ),
    Platform.GREENHOUSE: PlatformProfile(
        name=Platform.GREENHOUSE,
        image_pdf_penalty=1.0,
        multi_column_penalty=0.4,   # Handles two-column well
        table_penalty=0.5,
        text_box_penalty=0.7,
        header_footer_penalty=0.6,
        graphics_penalty=0.5,
        encoding_penalty=0.6,
        missing_section_penalty=0.5,  # Human reviewers compensate
        date_format_penalty=0.3,
        note=(
            "Greenhouse is the most formatting-tolerant platform. "
            "It supports human-first review with scorecards. "
            "Two-column layouts parse reasonably well. "
            "Still, single-column is always safer."
        ),
    ),
    Platform.ICIMS: PlatformProfile(
        name=Platform.ICIMS,
        image_pdf_penalty=1.0,
        multi_column_penalty=0.9,
        table_penalty=0.9,
        text_box_penalty=1.0,
        header_footer_penalty=0.9,
        graphics_penalty=0.8,
        encoding_penalty=0.9,
        missing_section_penalty=0.85,
        date_format_penalty=0.7,
        note=(
            "iCIMS is an enterprise-standard system used by healthcare "
            "and retail employers. It is moderately strict — better than "
            "Taleo but less tolerant than Greenhouse. Tables and multi-column "
            "layouts are unreliable."
        ),
    ),
    Platform.LEVER: PlatformProfile(
        name=Platform.LEVER,
        image_pdf_penalty=0.9,
        multi_column_penalty=0.35,
        table_penalty=0.4,
        text_box_penalty=0.5,
        header_footer_penalty=0.5,
        graphics_penalty=0.4,
        encoding_penalty=0.5,
        missing_section_penalty=0.4,
        date_format_penalty=0.2,
        note=(
            "Lever is an ATS + CRM hybrid popular at tech companies and startups. "
            "It is the most tolerant of modern formatting. "
            "Creative layouts, two-column designs, and non-standard headers "
            "are generally handled without issue."
        ),
    ),
    Platform.GENERIC: PlatformProfile(
        name=Platform.GENERIC,
        # Generic uses maximum penalty across all issues
        image_pdf_penalty=1.0,
        multi_column_penalty=1.0,
        table_penalty=1.0,
        text_box_penalty=1.0,
        header_footer_penalty=1.0,
        graphics_penalty=1.0,
        encoding_penalty=1.0,
        missing_section_penalty=1.0,
        date_format_penalty=1.0,
        note="Generic baseline: formats for the worst-case (lowest-common-denominator) ATS.",
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
class ReadabilityScorer:

    def score(
        self,
        layout: LayoutResult,
        semantic: SemanticResult,
        platforms: list[Platform],
    ) -> ReadabilityResult:

        # Build a feature vector from layout and semantic signals
        features = _extract_features(layout, semantic)

        platform_scores: dict[Platform, int] = {}
        all_issues: list[Issue] = []

        for platform in platforms:
            profile = _PROFILES[platform]
            pscore, pissues = _score_for_platform(features, profile)
            platform_scores[platform] = pscore
            # Only add platform-specific issues once
            all_issues += pissues

        # Aggregate readability score = weighted average of platform scores
        overall = int(sum(platform_scores.values()) / max(len(platform_scores), 1))

        # Add platform comparison insight
        if platform_scores:
            best  = max(platform_scores, key=platform_scores.get)
            worst = min(platform_scores, key=platform_scores.get)
            spread = platform_scores[best] - platform_scores[worst]
            if spread >= 25:
                all_issues.append(Issue(
                    severity=Severity.MEDIUM,
                    category=IssueCategory.READABILITY,
                    message=(
                        f"Large ATS score gap: {best.value.title()} ({platform_scores[best]}%) "
                        f"vs {worst.value.title()} ({platform_scores[worst]}%). "
                        "Formatting choices are hurting you on strict platforms."
                    ),
                    fix="Format for the strictest platform you're applying to (single column, standard headers, no tables).",
                    platform=None,
                ))

        return ReadabilityResult(
            score=float(overall),
            platform_scores=platform_scores,
            issues=all_issues,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_features(layout: LayoutResult, semantic: SemanticResult) -> dict[str, float]:
    """Convert layout + semantic results into a normalised feature vector."""
    meta = layout.meta
    return {
        "image_pdf"        : float(meta.is_image_pdf),
        "multi_column"     : float(meta.column_count >= 2),
        "table"            : float(meta.has_tables),
        "text_box"         : float(meta.has_text_boxes),
        "header_footer"    : float(meta.has_header_footer_content),
        "graphics"         : float(meta.has_graphics),
        "encoding"         : float(meta.special_char_ratio > 0.03),
        "missing_sections" : float(len(semantic.sections_missing) > 0),
        "date_format"      : float(
            any(i.category == IssueCategory.DATES for i in semantic.issues)
        ),
    }


# Penalty values per feature (points deducted from 100)
_FEATURE_PENALTIES = {
    "image_pdf"        : 50,
    "multi_column"     : 20,
    "table"            : 15,
    "text_box"         : 15,
    "header_footer"    : 12,
    "graphics"         : 10,
    "encoding"         : 8,
    "missing_sections" : 10,
    "date_format"      : 7,
}


def _score_for_platform(
    features: dict[str, float],
    profile: PlatformProfile,
) -> tuple[int, list[Issue]]:
    """Compute platform-specific ATS score using profile multipliers."""
    multipliers = {
        "image_pdf"        : profile.image_pdf_penalty,
        "multi_column"     : profile.multi_column_penalty,
        "table"            : profile.table_penalty,
        "text_box"         : profile.text_box_penalty,
        "header_footer"    : profile.header_footer_penalty,
        "graphics"         : profile.graphics_penalty,
        "encoding"         : profile.encoding_penalty,
        "missing_sections" : profile.missing_section_penalty,
        "date_format"      : profile.date_format_penalty,
    }

    score = 100.0
    issues: list[Issue] = []

    for feature, active in features.items():
        if active:
            base_penalty   = _FEATURE_PENALTIES.get(feature, 0)
            platform_mult  = multipliers.get(feature, 1.0)
            actual_penalty = base_penalty * platform_mult
            score -= actual_penalty

    return max(0, min(100, round(score))), issues
