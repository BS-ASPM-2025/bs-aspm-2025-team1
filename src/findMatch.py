from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
from models.job import Job

def clean_text(text: str) -> str:
    """Simple text cleaning"""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return text

def calculate_match_score(resume_text: str, job: Job) -> float:
    """
    Calculate match score based on weighted criteria using simple NLP (non-AI/DL).
    """
    scores = {}

    # 1. Skills Score (Keyword matching)
    # Extract skills from job and check if they exist in resume
    if job.required_skills:
        skills = [s.strip().lower() for s in job.required_skills.split(',') if s.strip()]
        if skills:
            resume_lower = resume_text.lower()
            found_skills = sum(1 for skill in skills if skill in resume_lower)
            scores['skills'] = (found_skills / len(skills)) * 100
        else:
            scores['skills'] = 0.0
    else:
        scores['skills'] = 0.0

    # 2. Degree Score (Simple keyword check)
    if job.degree:
        # Check if any part of the degree requirement is in the resume
        scores['degree'] = 100.0 if clean_text(job.degree) in clean_text(resume_text) else 0.0
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
    total_weight = (
        job.skills_weight + 
        job.degree_weight + 
        job.experience_weight + 
        job.weight_general
    )
    
    if total_weight == 0:
        return 0.0
        
    final_score = (
        (scores.get('skills', 0) * job.skills_weight) +
        (scores.get('degree', 0) * job.degree_weight) +
        (scores.get('experience', 0) * job.experience_weight) +
        (scores.get('general', 0) * job.weight_general)
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
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return similarity * 100
    except ValueError:
        # Can happen if empty vocabulary
        return 0.0