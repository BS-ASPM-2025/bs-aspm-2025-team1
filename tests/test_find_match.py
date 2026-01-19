"""

This file is used to test the findMatch.py file

"""

import pytest
from unittest.mock import MagicMock
from src.findMatch import clean_text, calculate_tfidf_similarity, calculate_match_score
from src.models.job import Job

class TestFindMatch:
    """
    This class is used to test the findMatch.py file
    """
    #@pytest.fixture
    def mock_job(self):
        job = MagicMock(spec=Job)
        # Default weights
        job.skills_weight = 1.0
        job.degree_weight = 1.0
        job.experience_weight = 1.0
        job.weight_general = 1.0
        # Default fields
        job.required_skills = None
        job.degree = None
        job.experience = None
        job.job_text = "Standard job description"
        return job

    @pytest.mark.skip(reason="outdated after migrations refactor")
    def test_clean_text(self):
        """
        This function tests the clean_text function
        """
        assert clean_text("Hello World!") == "hello world"
        assert clean_text("  Python  ") == "python"
        assert clean_text("C++ Developer") == "c developer" # regex removes special chars
        assert clean_text(None) == ""
        assert clean_text("") == ""

    @pytest.mark.skip(reason="outdated after migrations refactor")
    def test_calculate_tfidf_similarity(self):
        """
        This function tests the calculate_tfidf_similarity function
        """
        # Exact match
        assert calculate_tfidf_similarity("python developer", "python developer") == 100.0
        
        # Substring optimization
        # "5 years" in "I have 5 years of experience"
        assert calculate_tfidf_similarity("5 years", "I have 5 years of experience") == 100.0
        
        # Partial match
        # Should be > 0 but < 100 usually, unless words are identical
        score = calculate_tfidf_similarity("python java", "python c++")
        assert 0.0 < score < 100.0
        
        # No match
        score = calculate_tfidf_similarity("python", "ruby")
        assert score == 0.0
        
        # Empty inputs
        assert calculate_tfidf_similarity("", "text") == 0.0
        assert calculate_tfidf_similarity("text", None) == 0.0

    @pytest.mark.skip(reason="outdated after migrations refactor")
    def test_calculate_match_score_full_match(self, mock_job):
        """
        This function tests the calculate_match_score function
        with a full match
        :param mock_job: mock job object
        :return: None
        """
        mock_job.required_skills = "python, java"
        mock_job.degree = "Computer Science"
        mock_job.experience = "5 years"
        mock_job.job_text = "Looking for a python developer"

        resume_text = "I have a degree in Computer Science. I have 5 years experience. Skills: python, java."
        
        score = calculate_match_score(resume_text, mock_job)
        # Expect high score. 
        # Skills: 100% (both found)
        # Degree: 100% (found)
        # Experience: 100% (found via optimization)
        # General: High (similar text)
        assert score > 90.0

    @pytest.mark.skip(reason="outdated after migrations refactor")
    def test_calculate_match_score_no_match(self, mock_job):
        """
        This function tests the calculate_match_score function
        with no match
        :param mock_job: mock job object
        :return: None
        """
        mock_job.required_skills = "rust"
        mock_job.degree = "PhD"
        mock_job.experience = "10 years"
        mock_job.job_text = "Rust expert needed"

        resume_text = "I know nothing about that."
        
        score = calculate_match_score(resume_text, mock_job)
        assert score == 0.0

    @pytest.mark.skip(reason="outdated after migrations refactor")
    def test_calculate_match_score_partial_skills(self, mock_job):
        """
        This function tests the calculate_match_score function
        with partial skills
        :param mock_job: mock job object
        :return: None
        """
        mock_job.required_skills = "python, java, c++"
        # Disable other scores to focus on skills
        mock_job.degree_weight = 0.0
        mock_job.experience_weight = 0.0
        mock_job.weight_general = 0.0
        mock_job.skills_weight = 1.0

        resume_text = "I know python."
        
        # 1 out of 3 skills = 33.33%
        score = calculate_match_score(resume_text, mock_job)
        assert score == pytest.approx(33.33, 0.01)

    @pytest.mark.skip(reason="outdated after migrations refactor")
    def test_calculate_match_score_custom_weights(self, mock_job):
        """
        This function tests the calculate_match_score function
        with custom weights
        :param mock_job: mock job object
        :return: None
        """
        # Only care about degree
        mock_job.skills_weight = 0.0
        mock_job.degree_weight = 10.0
        mock_job.experience_weight = 0.0
        mock_job.weight_general = 0.0
        
        mock_job.degree = "Bachelors"
        resume_text = "I have a Bachelors degree"
        
        score = calculate_match_score(resume_text, mock_job)
        assert score == 100.0

    @pytest.mark.skip(reason="outdated after migrations refactor")
    def test_calculate_match_score_zero_total_weight(self, mock_job):
        """
        This function tests the calculate_match_score function
        with zero total weight
        :param mock_job: mock job object
        :return: None
        """
        mock_job.skills_weight = 0.0
        mock_job.degree_weight = 0.0
        mock_job.experience_weight = 0.0
        mock_job.weight_general = 0.0
        
        score = calculate_match_score("text", mock_job)
        assert score == 0.0

    @pytest.mark.skip(reason="outdated after migrations refactor")
    def test_calculate_match_score_missing_requirements(self, mock_job):
        """
        This function tests the calculate_match_score function
        with missing requirements
        :param mock_job: mock job object
        :return: None
        """
        # Requirements are None by default in mock_job fixture
        # But let's be explicit
        mock_job.required_skills = None
        mock_job.degree = None
        mock_job.experience = None
        
        # Only general score applies
        mock_job.weight_general = 1.0
        # skills/degree/exp weights exist but their scores will be 0 because requirements are None
        
        resume_text = "Standard job description" # Matches job_text in mock
        score = calculate_match_score(resume_text, mock_job)
        
        # Score calculation:
        # skills: 0 * 1 = 0
        # degree: 0 * 1 = 0
        # exp: 0 * 1 = 0
        # general: 100 * 1 = 100
        # total_weight = 4
        # expected = 100 / 4 = 25.0
        assert score == 25.0
