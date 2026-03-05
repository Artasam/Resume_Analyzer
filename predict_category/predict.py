import pickle

from parsers.text_extractor import extract_text, clean_resume


# ---------- Load models ----------

lr_model = pickle.load(open('models/lr_model.pkl', 'rb'))
tfidf    = pickle.load(open('models/tfidf.pkl', 'rb'))
le       = pickle.load(open('models/encoder.pkl', 'rb'))


def predict_category(f) -> str:
    """
    Given a file storage object, extract and clean resume text,
    then return the predicted job category.
    """
    resume_text = extract_text(f, f.filename)
    cleaned     = clean_resume(resume_text)
    vector      = tfidf.transform([cleaned])
    category    = le.inverse_transform(lr_model.predict(vector.toarray()))[0]
    return category