"""Tests for llm.py error handling and exception classification.

Verifies that IBM watsonx.ai exceptions are caught and classified correctly
without exposing credentials, tokens, or internal error details to users.

These tests verify the error handling structure exists. Full exception-raising
tests would require complex module mocking that is fragile across SDK versions.
"""
from pathlib import Path


def test_error_handling_code_exists():
    """Verify that llm.py contains improved error handling code."""
    llm_path = Path(__file__).parent.parent / "llm.py"
    source = llm_path.read_text(encoding="utf-8")
    
    # Verify specific exception types are imported and handled
    assert "from ibm_watsonx_ai.wml_client_error import WMLClientError, ApiRequestFailure" in source
    assert "except ApiRequestFailure as exc:" in source
    assert "except WMLClientError as exc:" in source
    
    # Verify status code handling
    assert "status_code = getattr(exc, \"status_code\", None)" in source
    assert "if status_code == 401:" in source
    assert "Authentication failed" in source
    assert "if status_code == 403:" in source
    assert "Access forbidden" in source
    assert "if status_code == 429:" in source
    assert "Rate limit exceeded" in source
    assert "500 <= status_code < 600" in source
    assert "service error" in source
    
    # Verify no credential exposure
    assert "Never expose" in source or "never the message" in source
    
    # Verify catch-all still exists
    assert "except Exception as exc:" in source


def test_successful_generation_still_works():
    """Verify that actual IBM Granite generation works (if configured)."""
    from llm import is_configured, generate
    
    if not is_configured():
        # Skip if credentials not configured
        return
    
    # Test with minimal prompt
    result, error = generate("Say hello in 3 words.", max_tokens=50)
    
    if error:
        # If there's an error, verify it follows the new format
        assert isinstance(error, str)
        assert len(error) > 0
        # Should not contain raw exception messages or tokens
        assert "Bearer" not in error
        assert "eyJ" not in error  # JWT token prefix
        assert "API_KEY" not in error
    else:
        # Success case
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0


def test_configuration_check_unchanged():
    """Verify configuration check still works."""
    from llm import is_configured, configuration_message
    
    # This should work regardless of whether credentials are actually configured
    assert isinstance(is_configured(), bool)
    message = configuration_message()
    assert isinstance(message, str)
    
    if not is_configured():
        # Should mention missing variables
        assert "WATSONX" in message
    else:
        assert "present" in message.lower() or "configured" in message.lower()


def test_error_messages_are_user_friendly():
    """Verify error messages contain helpful guidance."""
    llm_path = Path(__file__).parent.parent / "llm.py"
    source = llm_path.read_text(encoding="utf-8")
    
    # Check for user-friendly error messages
    user_friendly_phrases = [
        "Check your IBM Cloud API key",
        "Check your project ID",
        "Rate limit exceeded",
        "Wait a moment",
        "Try again later",
        "Check your credentials",
    ]
    
    for phrase in user_friendly_phrases:
        assert phrase in source, f"Expected user-friendly phrase not found: {phrase}"


def test_no_sensitive_data_in_error_strings():
    """Verify that error handling code doesn't expose sensitive data."""
    llm_path = Path(__file__).parent.parent / "llm.py"
    source = llm_path.read_text(encoding="utf-8")
    
    # Find all error return statements
    error_returns = []
    for line in source.split("\n"):
        if "return None," in line and '"' in line:
            # Extract the error message
            start = line.find('"')
            if start != -1:
                end = line.find('"', start + 1)
                if end != -1:
                    error_returns.append(line[start+1:end])
    
    # Verify no sensitive patterns in error messages
    for error_msg in error_returns:
        assert "{exc}" not in error_msg  # No direct exception interpolation
        assert "str(exc)" not in error_msg
        # Only error_type (class name) should be used
        if "{" in error_msg:
            assert "error_type" in error_msg or "status_code" in error_msg
