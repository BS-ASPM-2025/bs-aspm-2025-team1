"""

Module to find a match score between resume text and job description using simple NLP techniques.

"""

import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from models.job import Job

def clean_text(text: str) -> str:
    """Simple text cleaning"""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return text

# Degree equivalence groups: if job and resume each contain any term from same group, it's a match
DEGREE_GROUPS = [
    ["bs", "bachelor", "bachelors", "b.s.", "bsc", "bachelor of science"],
    ["ms", "master", "masters", "m.s.", "msc", "mba", "master of science"],
    ["phd", "ph.d.", "doctorate", "doctoral", "d.phil"],
]

def _skill_in_resume(skill: str, resume_text: str) -> bool:
    """Check if skill appears in resume with word boundaries (avoids 'java' in 'javascript')."""
    if not skill or not resume_text:
        return False
    # Escape special regex chars (e.g. C++, C#)
    pattern = r"\b" + re.escape(skill) + r"\b"
    return bool(re.search(pattern, resume_text, re.IGNORECASE))

def _degree_matches(job_degree: str, resume_text: str) -> bool:
    """Check if resume satisfies degree requirement, including common aliases (BS/Bachelor, etc.)."""
    if not job_degree or not resume_text:
        return False
    job_clean = clean_text(job_degree)
    resume_clean = clean_text(resume_text)
    if job_clean in resume_clean:
        return True
    for group in DEGREE_GROUPS:
        job_has = any(term in job_clean for term in group)
        resume_has = any(term in resume_clean for term in group)
        if job_has and resume_has:
            return True
    return False

def calculate_match_score(resume_text: str, job: Job) -> float:
    """
    Calculate a match score based on weighted criteria using simple NLP (non-AI/DL).
    """
    scores = {}

    # 1. Skills Score (Keyword matching with word boundaries)
    # Extract skills from job and check if they exist in resume (avoids "java" in "javascript")
    if job.required_skills:
        skills = [s.strip() for s in job.required_skills.split(',') if s.strip()]
        if skills:
            found_skills = sum(1 for skill in skills if _skill_in_resume(skill, resume_text))
            scores['skills'] = (found_skills / len(skills)) * 100
        else:
            scores['skills'] = 0.0
    else:
        scores['skills'] = 0.0

    # 2. Degree Score (keyword check with common aliases: BS/Bachelor, MS/Master, etc.)
    if job.degree:
        scores['degree'] = 100.0 if _degree_matches(job.degree, resume_text) else 0.0
    else:
        scores['degree'] = 0.0
        
    # 3. Experience Score (Simple keyword check or basic overlap)
    # This is hard to do perfectly without parsing, but we can check for numeric matches or similarity
    # For now, let's use TF-IDF for experience description vs resume
    if job.experience:
        scores['experience'] = calculate_tfidf_similarity(job.experience, resume_text)
    else:
        scores['experience'] = 0.0

    # 4. General Job Description Match (TF-IDF)
    # Use the full combined text for a semantic-ish match
    scores['general'] = calculate_tfidf_similarity(job.job_text, resume_text)

    # Weighted Average
    # Boost weights for specific requirements to ensure they dominate general text match
    # if the requirement is present.
    w_skills = job.skills_weight * 10 if job.required_skills else job.skills_weight
    w_degree = job.degree_weight * 10 if job.degree else job.degree_weight
    w_experience = job.experience_weight * 10 if job.experience else job.experience_weight
    w_general = job.weight_general

    total_weight = w_skills + w_degree + w_experience + w_general
    
    if total_weight == 0:
        return 0.0
        
    final_score = (
        (scores.get('skills', 0) * w_skills) +
        (scores.get('degree', 0) * w_degree) +
        (scores.get('experience', 0) * w_experience) +
        (scores.get('general', 0) * w_general)
    ) / total_weight

    return round(final_score, 2)

def calculate_tfidf_similarity(text1: str, text2: str) -> float:
    """Calculates cosine similarity between two texts using TF-IDF"""
    if not text1 or not text2:
        return 0.0
        
    # Optimization: if text1 is a short phrase and is contained in text2, give 100%
    # This matches behavior for things like "5 years" or specific requirements
    c1 = clean_text(text1)
    c2 = clean_text(text2)
    if c1 and c1 in c2:
        return 100.0

    try:
        # ngram_range=(1,2) catches phrases like "machine learning", "data science"
        vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return similarity * 100
    except ValueError:
        # Can happen if empty vocabulary
        return 0.0