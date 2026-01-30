"""
Browser-based UI tests for resume upload.
Requires: pytest-playwright, run with `pytest tests/browser/ -v`
Install browsers first: playwright install chromium
"""

import tempfile
from pathlib import Path

import pytest
from playwright.sync_api import Page


# Minimal valid PDF content (PDF header + minimal structure)
MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000101 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF"


@pytest.fixture
def sample_pdf_path():
    """Create a temporary minimal PDF file for upload tests."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(MINIMAL_PDF)
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.mark.browser
def test_upload_resume_page_loads(page: Page, base_url: str):
    """Verify the upload resume page loads and displays key elements."""
    page.goto(f"{base_url}/upload_resume")
    page.wait_for_load_state("networkidle")

    assert page.title() == "Upload Resume"
    assert page.locator("h1:has-text('Upload Your Resume')").is_visible()
    assert page.locator("text=Click or Drag & Drop to Upload").is_visible()
    assert page.locator("text=PDF files only (max 5MB)").is_visible()
    assert page.locator("button:has-text('Upload Resume')").is_visible()


@pytest.mark.browser
def test_upload_resume_valid_pdf_shows_feedback(page: Page, base_url: str, sample_pdf_path: str):
    """Upload a valid PDF and verify redirect to feedback page."""
    page.goto(f"{base_url}/upload_resume")
    page.wait_for_load_state("networkidle")

    # Set file on the file input (it's inside the drop-zone)
    file_input = page.locator('input[type="file"][name="file"]')
    file_input.set_input_files(sample_pdf_path)

    # Submit the form
    page.locator("button:has-text('Upload Resume')").click()

    # Should redirect to feedback page
    page.wait_for_url("**/resume_upload_feedback**", timeout=10000)
    assert "resume_upload_feedback" in page.url
    # Feedback page shows either matches or "No matches found"
    content = page.content()
    assert "No matches found" in content or "Match:" in content or "Delete my resume" in content


@pytest.mark.browser
def test_upload_resume_invalid_file_type_shows_error(page: Page, base_url: str):
    """Upload a non-PDF file and verify error message is shown."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"plain text content")
        txt_path = f.name

    try:
        page.goto(f"{base_url}/upload_resume")
        page.wait_for_load_state("networkidle")

        # Try to set a .txt file - browser may restrict due to accept=".pdf"
        # Use evaluate to bypass if needed, or use a file that looks like PDF but has wrong extension
        # The backend checks content_type - when we upload .txt, browser sends text/plain
        file_input = page.locator('input[type="file"][name="file"]')
        # Remove accept attribute temporarily to allow .txt upload
        page.evaluate("""() => {
            const input = document.querySelector('input[type="file"]');
            if (input) input.removeAttribute('accept');
        }""")
        file_input.set_input_files(txt_path)

        page.locator("button:has-text('Upload Resume')").click()

        # Should stay on upload page with error
        page.wait_for_load_state("networkidle")
        assert "Invalid file type" in page.content()
    finally:
        Path(txt_path).unlink(missing_ok=True)


@pytest.mark.browser
def test_navigate_from_home_to_upload_resume(page: Page, base_url: str):
    """Verify home page has link to upload resume and navigation works."""
    page.goto(base_url)
    page.wait_for_load_state("networkidle")

    upload_link = page.locator('a[href="/upload_resume"]').first
    assert upload_link.is_visible()
    upload_link.click()

    page.wait_for_url(f"{base_url}/upload_resume")
    assert "upload_resume" in page.url
    assert page.locator("h1:has-text('Upload Your Resume')").is_visible()
