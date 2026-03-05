import re
import json

from config.settings import MODEL, llm_available

# Optional: spaCy may not be installed in some environments
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    USE_SPACY = True
except Exception:
    USE_SPACY = False
    nlp = None
    print("SpaCy model not found. Using basic extraction/heuristics.")


def is_valid_name(name: str) -> bool:
    if not name:
        return False

    name = re.sub(r'\s+', ' ', name.strip())
    if len(name) < 2:
        return False

    words = name.split()
    if not (2 <= len(words) <= 4):
        return False

    if re.search(r'[0-9@#$%^&*+=\[\]{}|\\:";<>?,/`~]', name):
        return False

    if name.islower():
        return False
    if not (name.isupper() or all(w[:1].isalpha() and (w[:1].isupper() or w[:1] in ["'", "-"]) for w in words)):
        return False

    non_names = {
        'dear sir', 'dear madam', 'to whom', 'hiring manager', 'human resources',
        'cover letter', 'resume', 'curriculum vitae', 'contact information',
        'personal information', 'objective statement', 'career objective',
        'professional summary', 'work experience', 'education background',
        'skills summary', 'references available', 'upon request', 'phone number',
        'email address', 'home address', 'linkedin profile', 'portfolio website',
        'career goals', 'professional goals', 'job title', 'position applied',
        'application for', 'interested in', 'looking for', 'seeking position',
        'available immediately', 'notice period', 'salary expectation',
        'executive summary', 'personal statement', 'profile summary',
        'key qualifications', 'core competencies', 'technical proficiencies',
        'language skills', 'soft skills', 'hard skills', 'summary of qualifications',
        'professional profile', 'career summary', 'objective summary',
        'employment objective', 'professional objective', 'career profile'
    }
    if name.lower() in non_names:
        return False

    if any(len(w) < 2 or len(w) > 30 for w in words):
        return False

    return True


def extract_name_from_resume(text: str) -> str:
    if llm_available():
        prompt = f"""
        You are an expert resume parser. Return JSON only.
        Extract candidate's full name. If not found, return "Name Not Found".

        Example:
        {{"name": "John Doe"}}

        Resume:
        {text[:2000]}
        """
        try:
            resp = MODEL.invoke(prompt)
            if resp and hasattr(resp, 'content'):
                try:
                    parsed = json.loads(resp.content)
                    return parsed.get("name", "Name Not Found")
                except Exception:
                    return resp.content.strip() or "Name Not Found"
        except Exception:
            pass

    if USE_SPACY and text:
        try:
            doc = nlp(text[:2000])
            person_entities = [ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON"]
            for entity in person_entities:
                if is_valid_name(entity):
                    return entity
        except Exception:
            pass

    lines = text.split('\n')[:20] if text else []
    name_patterns = [
        r'^([A-Z][a-z]{1,30}(?:\s+[A-Z][a-z]{1,30}){1,3})\s*$',
        r'^Name:\s*([A-Z][a-z]{1,30}(?:\s+[A-Z][a-z]{1,30}){1,3})',
        r'^([A-Z][a-z]{1,30}\s+[A-Z]\.\s+[A-Z][a-z]{1,30})',
        r'^([A-Z]{2,30}(?:\s+[A-Z]{2,30}){1,3})\s*$',
    ]
    for line in lines:
        s = line.strip()
        if len(s) < 2:
            continue
        for pattern in name_patterns:
            m = re.search(pattern, s)
            if m:
                candidate = m.group(1).strip()
                if is_valid_name(candidate):
                    return candidate

    header_section = re.sub(
        r'(resume|curriculum vitae|cv|profile|contact|personal information)',
        '', (text or '')[:600], flags=re.IGNORECASE
    )
    m = re.search(r'\b([A-Z][a-z]{2,30}\s+[A-Z][a-z]{2,30}(?:\s+[A-Z][a-z]{2,30})?)\b', header_section)
    if m:
        candidate = m.group(1)
        if is_valid_name(candidate):
            return candidate

    return "Name Not Found"