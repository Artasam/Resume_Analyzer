from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from langchain_huggingface import HuggingFaceEndpointEmbeddings

from parsers.text_extractor import clean_resume


def match_resume(resume_text: str, job_desc: str) -> float:
    """TF-IDF cosine similarity between resume and job description."""
    resume_clean = clean_resume(resume_text)
    job_clean = clean_resume(job_desc)
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform([resume_clean, job_clean])
    similarity = cosine_similarity(vectors[0], vectors[1])[0][0] * 100
    return round(similarity, 1)


def match_resume_hf(resume_text: str, job_desc: str) -> float:
    """HuggingFace sentence-transformer embedding similarity between resume and job description."""
    embedding_model = HuggingFaceEndpointEmbeddings(
        repo_id="sentence-transformers/all-MiniLM-L6-v2",
        task="feature-extraction"
    )

    resume_embedding = embedding_model.embed_query(clean_resume(resume_text))
    job_embedding = embedding_model.embed_query(clean_resume(job_desc))

    similarity = cosine_similarity([resume_embedding], [job_embedding])[0][0] * 100
    return round(similarity, 1)