import pytest

import src.tools.matching_scorer as scorer


class _DummyResume:
    def __init__(self, raw_text: str | None):
        self.raw_text = raw_text


class _DummyJob:
    def __init__(
        self,
        *,
        raw_text: str | None = None,
        required_skills: str | None = None,
        degree: str | None = None,
        experience: str | None = None,
        skills_weight: float = 1.0,
        degree_weight: float = 1.0,
        experience_weight: float = 1.0,
        weight_general: float = 1.0,
    ):
        self.raw_text = raw_text
        self.required_skills = required_skills
        self.degree = degree
        self.experience = experience

        self.skills_weight = skills_weight
        self.degree_weight = degree_weight
        self.experience_weight = experience_weight
        self.weight_general = weight_general


# -------------------------
# calculate_tfidf_similarity (smoke)
# -------------------------

def test_calculate_tfidf_similarity_empty_returns_0():
    assert scorer.calculate_tfidf_similarity("", "x") == 0.0
    assert scorer.calculate_tfidf_similarity("x", "") == 0.0
    assert scorer.calculate_tfidf_similarity("   ", "x") == 0.0


def test_calculate_tfidf_similarity_identical_texts_is_high():
    s = scorer.calculate_tfidf_similarity("python fastapi sql", "python fastapi sql")
    assert s == pytest.approx(1.0, abs=1e-9) or s > 0.90


def test_calculate_tfidf_similarity_different_texts_is_low():
    # Smoke-test: unrelated texts should be low-ish (not necessarily 0 due to tokenization quirks)
    s = scorer.calculate_tfidf_similarity("python fastapi sql", "gardening flowers soil")
    assert 0.0 <= s < 0.50


# -------------------------
# score_resume_against_job (logic + weights; mock similarity)
# -------------------------

def test_score_resume_against_job_empty_resume_returns_zero():
    r = _DummyResume(raw_text="   ")
    j = _DummyJob(raw_text="job", required_skills="skills", degree="deg", experience="exp")
    score = scorer.score_resume_against_job(r, j)
    assert score.total_percent == 0
    assert score.skills_match == 0
    assert score.degree_match == 0
    assert score.experience_match == 0


def test_score_resume_against_job_all_job_fields_empty_returns_zero(monkeypatch):
    # Even if resume has text, if all job fields are empty => total_weight = 0 => total = 0
    r = _DummyResume(raw_text="some resume")
    j = _DummyJob(raw_text="   ", required_skills=None, degree="", experience="   ",
                  skills_weight=1.0, degree_weight=2.0, experience_weight=3.0, weight_general=4.0)

    # Similarity function should not matter; weights should be treated as 0 due to empty fields
    monkeypatch.setattr(scorer, "calculate_tfidf_similarity", lambda a, b: 1.0)

    score = scorer.score_resume_against_job(r, j)
    assert score.total_percent == 0
    assert score.skills_match == 0
    assert score.degree_match == 0
    assert score.experience_match == 0


def test_score_resume_against_job_ignores_weights_for_empty_fields(monkeypatch):
    r = _DummyResume(raw_text="resume text")
    # skills/degree empty but weights > 0; should be ignored by setting weight=0
    j = _DummyJob(
        raw_text="job text",
        required_skills="   ",
        degree=None,
        experience="exp text",
        skills_weight=10.0,
        degree_weight=10.0,
        experience_weight=1.0,
        weight_general=1.0,
    )

    # Return fixed sims by matching text2 (job field)
    def fake_sim(text1, text2):
        if text2.strip() == "exp text":
            return 0.30
        if text2.strip() == "job text":
            return 0.70
        return 0.99  # would apply if empty fields were incorrectly processed

    monkeypatch.setattr(scorer, "calculate_tfidf_similarity", fake_sim)

    score = scorer.score_resume_against_job(r, j)

    # Only experience (0.30) and general (0.70) contribute equally (weights 1 and 1)
    # final = (0.30*1 + 0.70*1) / 2 = 0.50 => 50%
    assert score.total_percent == 50
    assert score.experience_match == 30
    # skills/degree empty => 0
    assert score.skills_match == 0
    assert score.degree_match == 0


def test_score_resume_against_job_weighted_average_math(monkeypatch):
    """
    Verify weighted average:
      final = (skills_sim*skills_w + degree_sim*degree_w + exp_sim*exp_w + gen_sim*gen_w) / sum(weights)
    """
    r = _DummyResume(raw_text="resume text")
    j = _DummyJob(
        raw_text="job text",
        required_skills="skills text",
        degree="degree text",
        experience="exp text",
        skills_weight=2.0,
        degree_weight=1.0,
        experience_weight=1.0,
        weight_general=0.0,  # exclude general intentionally
    )

    sims = {
        "skills text": 0.90,
        "degree text": 0.20,
        "exp text": 0.40,
        "job text": 0.99,  # should not matter due to weight_general=0
    }

    monkeypatch.setattr(scorer, "calculate_tfidf_similarity", lambda a, b: sims[b.strip()])

    score = scorer.score_resume_against_job(r, j)

    # total_weight = 2 + 1 + 1 + 0 = 4
    # weighted_sum = 0.90*2 + 0.20*1 + 0.40*1 + 0.99*0 = 1.8 + 0.2 + 0.4 = 2.4
    # final = 2.4 / 4 = 0.6 => 60%
    assert score.total_percent == 60
    assert score.skills_match == 90
    assert score.degree_match == 20
    assert score.experience_match == 40


def test_score_resume_against_job_clamps_to_0_100(monkeypatch):
    r = _DummyResume(raw_text="resume text")
    j = _DummyJob(raw_text="job text", required_skills="skills", degree="deg", experience="exp")

    # Force invalid similarity to ensure clamp (even though cosine normally won't do this)
    monkeypatch.setattr(scorer, "calculate_tfidf_similarity", lambda a, b: 999.0)

    score = scorer.score_resume_against_job(r, j)
    assert 0 <= score.total_percent <= 100
    assert score.total_percent == 100
    assert score.skills_match == 100
    assert score.degree_match == 100
    assert score.experience_match == 100
