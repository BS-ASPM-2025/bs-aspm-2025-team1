"""

Test session security

"""

import time
from unittest import mock

# Constants from your app/session logic
LOGIN_URL = "/passcode?next=/post_job"
POST_JOB_URL = "/post_job"
LOGOUT_URL = "/logout"
SESSION_TTL_SECONDS = 1800  # Default from app.py/session.py

def test_cannot_post_job_unauthenticated(client):
    """
    Test that a user cannot access the post-job page without being logged in.
    Should redirect to the passcode page.
    """
    # Try GET
    response = client.get(POST_JOB_URL, follow_redirects=False)
    assert response.status_code in (302, 303)
    assert response.headers["location"] == LOGIN_URL

    # Try POST
    response = client.post(POST_JOB_URL, data={"title": "Test"}, follow_redirects=False)
    assert response.status_code in (302, 303)
    assert response.headers["location"] == LOGIN_URL

def test_can_post_job_authenticated(client):
    """
    Test that a logged-in user can access the post-job page.
    """
    # 1. Login
    login_response = client.post(LOGIN_URL, data={"password": "1234"}, follow_redirects=False)
    assert login_response.status_code in (302, 303)
    
    # 2. Access Post Job
    # We need to ensure the client maintains the cookies/session
    response = client.get(POST_JOB_URL, follow_redirects=False)
    assert response.status_code == 200
    assert "Job Title" in response.text  # Assuming the form field label exists

def test_session_expired_cannot_post_job(client):
    """
    Test that after the session expires, the user is redirected to log in.
    """
    # 1. Login
    client.post(LOGIN_URL, data={"password": "1234"})

    # 2. Fast-forward time past TTL
    # We verify that 'time.time()' is called by the session logic and mock it.
    # The session middleware and 'require_company_session' both check time.
    
    current_time = time.time()
    future_time = current_time + SESSION_TTL_SECONDS + 10  # 10 seconds past expiry

    with mock.patch("src.security.session.time.time", return_value=future_time):
        # 3. Try access protected route
        response = client.get(POST_JOB_URL, follow_redirects=False)
        assert response.status_code in (302, 303)
        assert response.headers["location"] == LOGIN_URL

def test_logout_invalidates_session(client):
    """
    Test that logging out prevents further access to protected routes.
    """
    # 1. Login
    client.post(LOGIN_URL, data={"password": "1234"})
    
    # Verify access first
    r_check = client.get(POST_JOB_URL)
    assert r_check.status_code == 200

    # 2. Logout
    client.get(LOGOUT_URL)

    # 3. Try access again
    response = client.get(POST_JOB_URL, follow_redirects=False)
    assert response.status_code in (302, 303)
    assert response.headers["location"] == LOGIN_URL

def test_session_extends_activity(client):
    """
    Test that activity within the TTL extends the session expiration.
    """
    # 1. Login
    client.post(LOGIN_URL, data={"password": "1234"})
    
    initial_time = time.time()
    
    # Move forward halfway through the session
    halfway_time = initial_time + (SESSION_TTL_SECONDS / 2)
    
    with mock.patch("src.security.session.time.time", return_value=halfway_time):
        # Make a request to a protected route to refresh the session
        client.get(POST_JOB_URL)
    
    # Now check if the session is still valid slightly after the *original* expiry would have been
    # but strictly before the *new* expiry.
    # Original expiry: initial + 1800
    # New expiry: halfway + 1800 = initial + 900 + 1800 = initial + 2700
    # Lets check at initial + 2000 (which is > original expiry but < new expiry)
    
    check_time = initial_time + SESSION_TTL_SECONDS + 100
    
    with mock.patch("src.security.session.time.time", return_value=check_time):
        response = client.get(POST_JOB_URL, follow_redirects=False)
        # Should still be 200 OK because the session was extended
        assert response.status_code == 200
