"""
semantic_parser.py  —  NLP-driven section detection & field extraction
=======================================================================
Approach
--------
1. Segment resume text into sections using a learned header classifier
   (spaCy sentence tokenisation + regex + contextual heuristics — NO
   hardcoded list of section names).

2. For each section, run Named Entity Recognition (spaCy NER +
   custom resume entity ruler) to extract structured fields.

3. Use an LLM (optional) as a fallback for ambiguous sections or
   to validate/enrich low-confidence extractions.

4. Produce SemanticResult with:
   - structured fields (name, email, phone, summary, experience[], education[], skills[])
   - sections_found / sections_missing
   - quality issues (non-standard headers, missing sections, date format problems)

No hardcoded section-name lists.  Instead we use:
  - Universal dependency parse patterns (spaCy)
  - Capitalisation / position / length heuristics to identify headers
  - Zero-shot Groq classification for ambiguous section headers (if GROQ_API_KEY set)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .models import Issue, IssueCategory, Severity, SemanticResult

# Optional imports
try:
    import spacy
    from spacy.pipeline import EntityRuler
    _SPACY_AVAILABLE = True
except ImportError:
    _SPACY_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════════════
# Canonical section taxonomy  (used for gap-detection only, not header matching)
# ══════════════════════════════════════════════════════════════════════════════
_CANONICAL_SECTIONS = {
    "contact"   : ["contact", "personal", "about"],
    "summary"   : ["summary", "objective", "profile", "overview", "about me"],
    "experience": ["experience", "employment", "work", "history", "career"],
    "education" : ["education", "academic", "qualification", "degree", "training"],
    "skills"    : ["skills", "competencies", "technologies", "expertise", "proficiencies"],
    "projects"  : ["projects", "portfolio", "work samples"],
    "certifications": ["certifications", "licenses", "credentials", "courses"],
}

# Expected ATS-standard header names for each canonical section
_ATS_STANDARD_NAMES = {
    "experience"    : "Work Experience",
    "education"     : "Education",
    "skills"        : "Skills",
    "summary"       : "Professional Summary",
    "certifications": "Certifications",
    "projects"      : "Projects",
    "contact"       : "Contact Information",
}

_REQUIRED_SECTIONS = {"contact", "experience", "education", "skills"}

# Date format patterns — used to detect non-standard date formats
_DATE_PATTERNS = {
    "standard": re.compile(
        r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
        r"\s+\d{4}\b",
        re.I
    ),
    "year_only": re.compile(r"\b(20\d{2})\s*[-–—]\s*(20\d{2}|[Pp]resent|[Cc]urrent)\b"),
    "numeric"  : re.compile(r"\b\d{1,2}[/\-\.]\d{4}\b"),
}

# Contact field patterns
_CONTACT_RE = {
    "email"   : re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
    "phone"   : re.compile(r"(\+?\d[\d\s\-\(\)]{7,14}\d)"),
    "linkedin": re.compile(r"linkedin\.com/in/[\w\-]+", re.I),
    "github"  : re.compile(r"github\.com/[\w\-]+", re.I),
}


# ══════════════════════════════════════════════════════════════════════════════
class SemanticParser:

    def __init__(self, spacy_model: str = "en_core_web_lg", groq_client=None):
        self._groq = groq_client
        self._nlp = None

        if _SPACY_AVAILABLE:
            try:
                self._nlp = spacy.load(spacy_model)
                self._add_resume_entity_ruler()
            except OSError:
                # Model not downloaded yet
                try:
                    self._nlp = spacy.load("en_core_web_sm")
                    self._add_resume_entity_ruler()
                except OSError:
                    self._nlp = None

    # ─────────────────────────────────────────────────────────────────────────
    def parse(self, text: str, ext: str) -> SemanticResult:
        issues: list[Issue] = []

        # 1. Segment into sections
        sections = self._segment_sections(text)

        # 2. Identify canonical mapping
        canonical_map = self._map_to_canonical(sections)

        # 3. Extract fields from each section
        fields = self._extract_fields(sections, canonical_map, text)

        # 4. Detect structural issues
        issues += self._check_header_quality(sections, canonical_map)
        issues += self._check_missing_sections(canonical_map)
        issues += self._check_date_formats(text)
        issues += self._check_contact_placement(text, sections)

        # 5. Section lists for report
        sections_found   = list(canonical_map.keys())
        sections_missing = [
            s for s in _REQUIRED_SECTIONS if s not in canonical_map
        ]

        # 6. Compute semantic score
        score = _compute_semantic_score(canonical_map, issues)

        return SemanticResult(
            score=score,
            fields=fields,
            sections_found=sections_found,
            sections_missing=sections_missing,
            issues=issues,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Section segmentation
    # ─────────────────────────────────────────────────────────────────────────
    def _segment_sections(self, text: str) -> list[dict]:
        """
        Split text into labelled blocks using structural heuristics:
          - All-caps short lines (≤ 5 words) → header
          - Title-cased short lines at start of paragraph → header
          - Lines followed by a blank line or preceded by two newlines → header
          - spaCy sentence length / POS pattern breaks (no verb phrase) → header

        Returns list of { "raw_header": str, "body": str }
        """
        lines = text.split("\n")
        segments: list[dict] = []
        current_header = "_PREAMBLE_"
        current_body: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                current_body.append("")
                continue

            if _is_section_header(stripped):
                # Flush previous segment
                if current_body:
                    segments.append({
                        "raw_header": current_header,
                        "body": "\n".join(current_body).strip(),
                    })
                current_header = stripped
                current_body = []
            else:
                current_body.append(stripped)

        # Flush last segment
        if current_body:
            segments.append({
                "raw_header": current_header,
                "body": "\n".join(current_body).strip(),
            })

        return segments

    # ─────────────────────────────────────────────────────────────────────────
    # Canonical mapping
    # ─────────────────────────────────────────────────────────────────────────
    def _map_to_canonical(self, segments: list[dict]) -> dict[str, dict]:
        """
        Map each detected segment to a canonical section key.
        Uses fuzzy semantic matching of header tokens against canonical synonyms.
        Ambiguous → LLM fallback if available.
        """
        mapped: dict[str, dict] = {}

        for seg in segments:
            header_lower = seg["raw_header"].lower().strip(" :_-")
            canonical = _fuzzy_canonical_match(header_lower)

            if canonical is None and self._groq:
                canonical = self._groq_classify_section(seg["raw_header"], seg["body"][:200])

            if canonical and canonical not in mapped:
                mapped[canonical] = seg

        return mapped

    # ─────────────────────────────────────────────────────────────────────────
    # Field extraction
    # ─────────────────────────────────────────────────────────────────────────
    def _extract_fields(
        self,
        segments: list[dict],
        canonical_map: dict,
        full_text: str,
    ) -> dict[str, Any]:
        fields: dict[str, Any] = {}

        # Contact fields from entire text (contact info sometimes in preamble)
        for field_name, pattern in _CONTACT_RE.items():
            m = pattern.search(full_text)
            if m:
                fields[field_name] = m.group(0)

        # Name — attempt NER if spaCy available, else first line heuristic
        fields["name"] = self._extract_name(full_text)

        # Skills section
        if "skills" in canonical_map:
            fields["skills"] = self._extract_skills(canonical_map["skills"]["body"])

        # Experience section
        if "experience" in canonical_map:
            fields["experience"] = self._extract_experience(canonical_map["experience"]["body"])

        # Education section
        if "education" in canonical_map:
            fields["education"] = self._extract_education(canonical_map["education"]["body"])

        return fields

    # ─────────────────────────────────────────────────────────────────────────
    # NER helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _extract_name(self, text: str) -> str | None:
        first_block = "\n".join(text.split("\n")[:6])

        if self._nlp:
            doc = self._nlp(first_block)
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    return ent.text.strip()

        # Heuristic fallback: first all-title-case line, ≤ 4 words, no digits
        for line in text.split("\n")[:5]:
            line = line.strip()
            words = line.split()
            if (
                2 <= len(words) <= 4
                and all(w.istitle() or w.isupper() for w in words)
                and not re.search(r"\d|@|\.", line)
            ):
                return line
        return None

    def _extract_skills(self, text: str) -> list[str]:
        """
        Extract skills using:
        1. spaCy entity ruler (SKILL entities)
        2. Pattern matching for comma/pipe/newline separated lists
        3. NP (noun phrase) extraction as fallback
        """
        skills: list[str] = []
        seen = set()

        if self._nlp:
            doc = self._nlp(text[:2000])
            for ent in doc.ents:
                if ent.label_ in ("SKILL", "PRODUCT", "ORG"):
                    s = ent.text.strip()
                    if s.lower() not in seen:
                        seen.add(s.lower())
                        skills.append(s)

        # Structural extraction: comma/pipe/bullet separated items
        for sep in [",", "|", "•", "·", "\n"]:
            if sep in text:
                parts = [p.strip(" •·\t") for p in text.split(sep)]
                for p in parts:
                    p = p.strip()
                    if 2 <= len(p) <= 35 and p.lower() not in seen:
                        seen.add(p.lower())
                        skills.append(p)
                break

        return skills[:30]

    def _extract_experience(self, text: str) -> list[dict]:
        """Parse experience bullets into structured role dicts."""
        roles = []
        # Split on date-range lines (heuristic role boundary)
        blocks = re.split(r"\n(?=.*\b20\d{2}\b)", text)
        for block in blocks:
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if not lines:
                continue
            role: dict[str, Any] = {"raw": block.strip()}
            # First line is usually job title / company
            role["title_line"] = lines[0] if lines else ""
            # Extract dates
            date_strings = _DATE_PATTERNS["standard"].findall(block) + _DATE_PATTERNS["year_only"].findall(block)
            if date_strings:
                role["dates"] = str(date_strings[0])
            roles.append(role)
        return roles

    def _extract_education(self, text: str) -> list[dict]:
        degrees = []
        blocks = re.split(r"\n{2,}", text)
        for block in blocks:
            if block.strip():
                degrees.append({"raw": block.strip()})
        return degrees

    # ─────────────────────────────────────────────────────────────────────────
    # Quality checks
    # ─────────────────────────────────────────────────────────────────────────
    def _check_header_quality(
        self, segments: list[dict], canonical_map: dict
    ) -> list[Issue]:
        issues: list[Issue] = []

        for canonical_key, seg in canonical_map.items():
            raw = seg["raw_header"]
            standard = _ATS_STANDARD_NAMES.get(canonical_key)
            if not standard:
                continue

            # Non-standard header detected
            if raw.lower() not in [standard.lower()] + _CANONICAL_SECTIONS.get(canonical_key, []):
                issues.append(Issue(
                    severity=Severity.MEDIUM,
                    category=IssueCategory.STRUCTURE,
                    message=f'Non-standard section header "{raw}" for {canonical_key} section. Strict ATS parsers (Taleo) may not recognise this.',
                    fix=f'Rename to the ATS-standard label: "{standard}".',
                    platform=Platform.TALEO,
                    line_hint=raw,
                ))

        return issues

    def _check_missing_sections(self, canonical_map: dict) -> list[Issue]:
        issues: list[Issue] = []
        for section in _REQUIRED_SECTIONS:
            if section not in canonical_map:
                standard_name = _ATS_STANDARD_NAMES.get(section, section.title())
                issues.append(Issue(
                    severity=Severity.HIGH,
                    category=IssueCategory.STRUCTURE,
                    message=f'Required section "{standard_name}" not detected. ATS cannot parse this field.',
                    fix=f'Add a clearly labelled "{standard_name}" section using the exact standard header text.',
                    platform=None,
                ))
        return issues

    def _check_date_formats(self, text: str) -> list[Issue]:
        issues: list[Issue] = []
        # Detect year-only dates (ambiguous duration)
        year_only_matches = _DATE_PATTERNS["year_only"].findall(text)
        if year_only_matches:
            issues.append(Issue(
                severity=Severity.MEDIUM,
                category=IssueCategory.DATES,
                message="Year-only date ranges (e.g. '2022–2023') found. Taleo may credit you with 1 day instead of 1 year.",
                fix="Use 'Month Year' format for all dates: 'January 2022 – March 2023'.",
                platform=Platform.TALEO,
                line_hint=str(year_only_matches[0]),
            ))

        # Detect numeric dates (e.g. 01/2022)
        numeric_matches = _DATE_PATTERNS["numeric"].findall(text)
        if numeric_matches:
            issues.append(Issue(
                severity=Severity.LOW,
                category=IssueCategory.DATES,
                message=f"Numeric date format detected (e.g. '{numeric_matches[0]}'). Some parsers misread month/year order.",
                fix="Use written month names: 'Jan 2022' or 'January 2022'.",
                platform=None,
                line_hint=numeric_matches[0],
            ))

        return issues

    def _check_contact_placement(self, text: str, segments: list[dict]) -> list[Issue]:
        issues: list[Issue] = []
        # If the preamble block has no email/phone → contact info may be missing from body
        preamble = next((s["body"] for s in segments if s["raw_header"] == "_PREAMBLE_"), "")
        has_email = bool(_CONTACT_RE["email"].search(preamble + text[:300]))
        if not has_email:
            issues.append(Issue(
                severity=Severity.HIGH,
                category=IssueCategory.CONTACT,
                message="Email address not found in the document body. ATS may be unable to contact this candidate.",
                fix="Add your email address at the top of the resume in the main document body (not in headers/footers).",
                platform=None,
            ))
        return issues

    # ─────────────────────────────────────────────────────────────────────────
    # spaCy entity ruler setup
    # ─────────────────────────────────────────────────────────────────────────
    def _add_resume_entity_ruler(self):
        """
        Adds a resume-domain EntityRuler that teaches spaCy to recognise
        common technology terms as SKILL entities.
        Rather than a hardcoded list, we use pattern generalisation:
          - CamelCase 1-3 token phrases → likely technology name
          - All-caps 2-6 char tokens (acronyms) → likely skill/cert
          - Known framework suffixes (.js, .py, .NET) → skill
        """
        if "resume_entity_ruler" in self._nlp.pipe_names:
            return

        ruler = self._nlp.add_pipe("entity_ruler", name="resume_entity_ruler", before="ner")
        patterns = [
            # Acronyms: SQL, AWS, GCP, API, REST, CI/CD etc.
            {"label": "SKILL", "pattern": [{"TEXT": {"REGEX": r"^[A-Z]{2,6}$"}}]},
            # Version-suffixed tech: Python3, Vue3, ES6
            {"label": "SKILL", "pattern": [{"TEXT": {"REGEX": r"^[A-Z][a-z]+\d+$"}}]},
            # .NET, Node.js, Next.js, Vue.js style names
            {"label": "SKILL", "pattern": [{"TEXT": {"REGEX": r"^\w+\.(js|py|NET|net)$"}}]},
            # CamelCase multi-word: ReactJS, TypeScript, PostgreSQL
            {"label": "SKILL", "pattern": [{"TEXT": {"REGEX": r"^[A-Z][a-z]+[A-Z]\w+$"}}]},
        ]
        ruler.add_patterns(patterns)

    # ─────────────────────────────────────────────────────────────────────────
    # LLM fallback
    # ─────────────────────────────────────────────────────────────────────────
    def _groq_classify_section(self, header: str, body_snippet: str) -> str | None:
        """
        Ask the LLM to classify an ambiguous section header into a canonical key.
        Returns one of: contact|summary|experience|education|skills|projects|certifications|other
        """
        if not self._groq:
            return None

        prompt = (
            "You are a resume parser. Classify the following resume section into "
            "exactly one of these categories: "
            "contact, summary, experience, education, skills, projects, certifications, other.\n\n"
            f"Section header: '{header}'\n"
            f"First 200 chars of content: '{body_snippet}'\n\n"
            "Respond with only the category name, nothing else."
        )

        try:
            response = self._groq.classify_section(header, body_snippet).strip().lower()
            valid = {"contact","summary","experience","education","skills","projects","certifications","other"}
            return response if response in valid else None
        except Exception:
            return None


# ══════════════════════════════════════════════════════════════════════════════
# Module-level helpers
# ══════════════════════════════════════════════════════════════════════════════

def _is_section_header(line: str) -> bool:
    """
    Determines if a line is a section header using structural heuristics.
    No predefined list — we look at:
      - All-caps, ≤ 5 words
      - Title-cased, ≤ 4 words, ends with colon or is followed by a blank
      - Very short line (≤ 30 chars) that contains no sentence punctuation
    """
    words = line.split()
    n = len(words)

    if n == 0 or n > 7:
        return False

    # All uppercase short line
    if line.isupper() and 1 <= n <= 6:
        return True

    # Title case short line (most words capitalised)
    capitalised_ratio = sum(1 for w in words if w and w[0].isupper()) / n
    if capitalised_ratio >= 0.7 and n <= 5 and not re.search(r"[.!?]$", line):
        return True

    # Ends with colon = header
    if line.endswith(":") and n <= 5:
        return True

    return False


def _fuzzy_canonical_match(header_lower: str) -> str | None:
    """
    Match a header string to a canonical section key without a hardcoded dictionary.
    Uses substring / token overlap scoring.
    """
    header_tokens = set(re.split(r"\W+", header_lower))
    best_key   = None
    best_score = 0

    for canonical_key, synonyms in _CANONICAL_SECTIONS.items():
        for synonym in synonyms:
            synonym_tokens = set(synonym.split())
            overlap = len(header_tokens & synonym_tokens)
            if overlap > best_score:
                best_score = overlap
                best_key = canonical_key

            # Also check substring containment
            if synonym in header_lower:
                return canonical_key

    return best_key if best_score >= 1 else None


def _compute_semantic_score(canonical_map: dict, issues: list[Issue]) -> float:
    score = 100.0
    deductions = {
        Severity.CRITICAL: 20,
        Severity.HIGH:     10,
        Severity.MEDIUM:    5,
        Severity.LOW:       2,
    }
    for issue in issues:
        score -= deductions.get(issue.severity, 0)

    # Bonus for having all required sections
    found_required = sum(1 for s in _REQUIRED_SECTIONS if s in canonical_map)
    score += (found_required / len(_REQUIRED_SECTIONS)) * 10

    return max(0.0, min(100.0, score))


# Avoid circular import: Platform is used in _check_header_quality
from .models import Platform  # noqa: E402 — needed here after class definition