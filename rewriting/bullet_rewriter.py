"""
Identify weak experience bullets in a resume and rewrite them into
achievement-focused lines via Groq (same stack as the ATS engine).
"""

from __future__ import annotations

import os
import re
from typing import Any

# Reuse central client (env: GROQ_API_KEY, GROQ_MODEL, etc.)
from ats.groq_client import GroqClient

_MAX_RESUME_CHARS = 50_000
_DEFAULT_MAX_BULLETS = 8


def _truncate(text: str, limit: int) -> str:
    t = text.strip()
    if len(t) <= limit:
        return t
    return t[: limit - 20] + "\n… [truncated]"


def extract_candidate_bullets(text: str, limit: int = 20) -> list[str]:
    """
    Heuristic fallback: lines that look like list bullets (for UI pre-fill).
    """
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if len(line) < 14:
            continue
        if re.match(r"^[-*•◦▪]\s+", line) or re.match(r"^\d+[\.)]\s+", line):
            cleaned = re.sub(r"^[-*•◦▪]\s+", "", line)
            cleaned = re.sub(r"^\d+[\.)]\s+", "", cleaned).strip()
            if len(cleaned) >= 12:
                out.append(cleaned)
        elif len(out) > 0 and line and line[0].islower() and len(line) > 25:
            # continuation of previous bullet
            out[-1] = (out[-1] + " " + line).strip()
    return out[:limit]


def rewrite_weak_bullets(
    resume_text: str,
    job_description: str = "",
    *,
    max_bullets: int = _DEFAULT_MAX_BULLETS,
    custom_bullets: list[str] | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    """
    Returns (rows, error_message).

    Each row: {"original": str, "rewritten": str, "why": str (optional)}

    If ``custom_bullets`` is set, those lines are rewritten instead of auto-picking weak lines from the resume.
    """
    if not resume_text.strip() and not (custom_bullets or []):
        return [], "No resume text or bullets to work with."

    try:
        client = GroqClient()
    except EnvironmentError as e:
        return [], str(e)

    resume_snip = _truncate(resume_text, _MAX_RESUME_CHARS)
    jd_snip = _truncate(job_description, 4000) if job_description.strip() else ""

    if custom_bullets:
        bullet_block = "\n".join(f"- {b.strip()}" for b in custom_bullets if b.strip())
        user = f"""Rewrite these resume bullet lines into stronger, achievement-focused bullets.

Rules:
- One rewritten bullet per input line; keep the same order as listed.
- Strong action verb first; add scope, impact, and metrics when reasonably supported by context; if you infer a number, prefix with "~" or say "approximately".
- Do not invent employers, job titles, tools, or credentials not present in the resume or bullet list.
- Each line ≤ 40 words, ATS-friendly (no special Unicode bullets in output).

BULLETS TO REWRITE:
{bullet_block}

RESUME (for context only):
{resume_snip}
"""
    else:
        user = f"""You are an expert resume coach. From the resume below, find up to {max_bullets} experience or project lines that are comparatively weak: vague duties, passive voice, missing outcomes/metrics, or "responsible for" style.

For each chosen line, copy the ORIGINAL text as one string (single line or the shortest faithful quote from the resume).

Return a rewrite that:
- Starts with a strong past-tense action verb (or present for current role if clearly current).
- Adds impact, scope, and quantified results when the resume supports it; use "~" or "approximately" when estimating.
- Stays truthful: no fabricated employers, dates, tools, or metrics.
- Keeps each bullet ≤ 40 words and plain text (no leading "•" in the rewritten field).

If fewer weak lines exist, return fewer items. Skip summary/objective paragraphs.

RESUME:
{resume_snip}
"""

    if jd_snip and not custom_bullets:
        user += f"""

OPTIONAL JOB DESCRIPTION (align keywords naturally; do not copy verbatim):
{jd_snip}
"""

    schema_hint = {
        "bullets": [
            {
                "original": "exact or closest line from resume",
                "rewritten": "Improved achievement bullet",
                "why": "one short phrase e.g. added metric, stronger verb",
            }
        ]
    }

    rewrite_tokens = int(os.getenv("GROQ_REWRITE_MAX_TOKENS", "2048"))
    rewrite_temp = float(os.getenv("GROQ_REWRITE_TEMPERATURE", "0.35"))
    system = (
        "You are an expert resume and career coach. "
        "Respond with valid JSON only matching the schema; no markdown fences."
    )

    data = client.complete_json(
        user,
        system=system,
        schema_hint=schema_hint,
        max_tokens=rewrite_tokens,
        temperature=rewrite_temp,
    )

    raw_list: list[Any]
    if isinstance(data, dict):
        # Try common key names the model might use for the bullets array
        raw_list = (
            data.get("bullets")
            or data.get("items")
            or data.get("rewrites")
            or data.get("results")
            or data.get("suggestions")
            or data.get("bullet_rewrites")
            or data.get("rewritten_bullets")
            or []
        )
        # If none of the known keys matched, grab the first list value
        if not raw_list:
            for v in data.values():
                if isinstance(v, list) and v:
                    raw_list = v
                    break
    elif isinstance(data, list):
        raw_list = data
    else:
        raw_list = []

    rows: list[dict[str, Any]] = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        orig = (
            item.get("original") or item.get("before") or item.get("current")
            or item.get("old") or item.get("input") or ""
        ).strip()
        new = (
            item.get("rewritten") or item.get("after") or item.get("improved")
            or item.get("new") or item.get("suggested") or item.get("suggestion")
            or item.get("output") or item.get("revised") or ""
        ).strip()
        if not orig or not new:
            continue
        row = {"original": orig, "rewritten": new}
        why = (item.get("why") or item.get("rationale") or item.get("reason") or "").strip()
        if why:
            row["why"] = why
        rows.append(row)

    if not rows:
        return [], "The model returned no bullets. Try pasting specific lines into the box, or shorten the resume and retry."

    return rows, None
