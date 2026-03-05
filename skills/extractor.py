import re
import json

from config.settings import MODEL, llm_available
from skills.database import _COMPILED_SKILL_PATTERNS


def extract_skills_section(text: str) -> str:
    lines = (text or '').splitlines()
    indicators = [
        r'\bskills?\b', r'\btechnical\s+skills?\b', r'\bcore\s+skills?\b',
        r'\bkey\s+skills?\b', r'\bareas?\s+of\s+expertise\b',
        r'\bcompetencies\b', r'\btechnologies\b', r'\bproficiencies\b',
        r'\btools?\s+and\s+technologies\b', r'\bsoftware\s+skills?\b',
        r'\bprogramming\s+languages?\b', r'\btechnical\s+expertise\b'
    ]
    start = -1
    for i, line in enumerate(lines[:200]):
        lc = line.strip().lower()
        if any(re.search(p, lc) for p in indicators):
            start = i
            break
    if start == -1:
        return ""

    end_indicators = [
        r'\bexperience\b', r'\bwork\s+experience\b', r'\bemployment\s+history\b',
        r'\beducation\b', r'\bprojects?\b', r'\bachievements?\b',
        r'\bcertifications?\b', r'\bawards?\b', r'\breferences?\b',
        r'\bpublications?\b', r'\bsummary\b', r'\bprofile\b'
    ]
    end = len(lines)
    for i in range(start + 1, min(len(lines), start + 80)):
        lc = lines[i].strip().lower()
        if lc and any(re.fullmatch(p, lc) for p in end_indicators):
            end = i
            break
    return '\n'.join(lines[start:end])


def extract_top_skills(text: str, num_skills: int = 3) -> list:
    if llm_available():
        prompt = f"""
You are a precise resume-skills extractor. Your only output must be a single valid JSON object — no prose, no markdown, no code fences, no explanation.

## TASK
Extract the top {num_skills} HARD / TECHNICAL skills from the resume below.

## SKILL SECTION DETECTION
The skills section may be titled any of: Skills, Core Skills, Key Skills, Technical Skills,
Professional Skills, Summary of Skills, Key Competencies, Areas of Expertise, Technologies,
Competencies, Proficiencies, Tools & Technologies, Software Skills, Programming Languages,
Tech Stack, Tools, Frameworks, Platforms, Expertise, or similar headings.
Skills may also appear in a bulleted list, pipe-separated row (e.g. Python | SQL | AWS),
comma-separated list, or a table. Parse ALL of these formats.

## STRICT EXTRACTION RULES
1. Extract ONLY concrete, specific skills — programming languages, frameworks, libraries,
   tools, platforms, databases, cloud services, methodologies (Agile/Scrum), certifications.
2. DO NOT include soft skills or personality traits such as: communication, teamwork,
   leadership, problem-solving, critical thinking, time management, adaptability,
   attention to detail, work ethic, interpersonal skills, or any similar vague attribute.
3. DO NOT include job titles, company names, degree names, or generic phrases.
4. Normalise each skill to its canonical name:
   - "MS Excel" → "Excel", "ReactJS" → "React", "Node" → "Node.js",
     "Postgres" → "PostgreSQL", "k8s" → "Kubernetes", "tf" → "TensorFlow"
5. Deduplicate: if two entries refer to the same skill (e.g. "ML" and "Machine Learning"),
   keep only the more descriptive form. Return each skill EXACTLY ONCE.
6. Each skill must be 1–5 words maximum. Reject anything longer.
7. Rank by prominence: skills listed first, repeated, or appearing in multiple sections
   rank higher.
8. Return EXACTLY {num_skills} skills if available, fewer only if the resume has fewer.
9. If NO skills section or recognisable skill list exists anywhere in the resume,
   return an empty list — do not invent skills from job descriptions or education.

## OUTPUT FORMAT — JSON ONLY
{{"skills": ["Skill1", "Skill2", "Skill3"]}}

## BAD OUTPUT EXAMPLES (never do this)
{{"skills": ["Good communicator", "Team player", "Fast learner", "Responsible", "Microsoft Office Suite and related productivity tools"]}}

## GOOD OUTPUT EXAMPLES
{{"skills": ["Python", "PostgreSQL", "Docker", "AWS", "React", "Machine Learning"]}}

## RESUME
{text}
"""
        try:
            resp = MODEL.invoke(prompt)
            if resp and hasattr(resp, 'content'):
                try:
                    parsed = json.loads(resp.content)
                    return parsed.get("skills", [])[:num_skills]
                except Exception:
                    skills = re.findall(r'\b[\w#+.]+\b', resp.content)
                    return skills[:num_skills] if skills else []
        except Exception:
            pass

    skills_text = extract_skills_section(text)
    if not skills_text:
        return []

    lt = skills_text.lower()
    matches = {}
    for skill, pat in _COMPILED_SKILL_PATTERNS.items():
        cnt = len(pat.findall(lt))
        if cnt:
            matches[skill] = cnt

    top_sorted = sorted(matches.items(), key=lambda kv: kv[1], reverse=True)
    return [k for k, _ in top_sorted[:max(0, num_skills)]]