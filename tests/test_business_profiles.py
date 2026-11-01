"""
Focused tests for the business_profiles persistence layer in app.py.

Strategy: Rather than importing the full Streamlit app (which executes UI
code on import), we extract and execute only the three DB-layer functions by
compiling the relevant source lines into an isolated namespace.  AUTH_DB is
injected into that namespace before execution, pointing to a tmp_path file.
This means each helper opens a real on-disk SQLite connection — satisfying
the requirement to avoid plain :memory: with multiple connections.
"""

import ast
import sqlite3
import sys
import types
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Source extraction — pull only the DB-layer functions from app.py
# ---------------------------------------------------------------------------

_APP_PATH = Path(__file__).parent.parent / "app.py"
_TARGET_FUNCS = {"init_auth_db", "load_business_profile", "upsert_business_profile"}


def _extract_db_functions() -> str:
    """
    Parse app.py and return source for only the three DB helper functions.
    Uses AST so we never execute any Streamlit or UI code.
    """
    source = _APP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)

    extracted: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in _TARGET_FUNCS:
            start = node.lineno - 1          # 0-based
            end = node.end_lineno            # exclusive slice
            extracted.append("".join(lines[start:end]) + "\n")

    assert len(extracted) == 3, (
        f"Expected 3 DB functions, found {len(extracted)}. "
        "Check that init_auth_db, load_business_profile, upsert_business_profile exist in app.py."
    )
    return "\n".join(extracted)


_DB_FUNCTION_SOURCE = _extract_db_functions()


# ---------------------------------------------------------------------------
# Fixture: build a fresh namespace with the three helpers and a tmp DB
# ---------------------------------------------------------------------------

@pytest.fixture()
def db(tmp_path):
    """
    Returns a namespace object with AUTH_DB pointing to a temp file and the
    three DB helpers (init_auth_db, load_business_profile, upsert_business_profile)
    ready to call.
    """
    db_path = tmp_path / "test_vendor_users.db"

    ns: dict = {
        "__builtins__": __builtins__,
        "sqlite3": sqlite3,
        "AUTH_DB": db_path,
    }
    exec(compile(_DB_FUNCTION_SOURCE, str(_APP_PATH), "exec"), ns)  # noqa: S102

    # Initialise the schema
    ns["init_auth_db"]()

    # Return a simple namespace for attribute-style access in tests
    result = types.SimpleNamespace()
    result.AUTH_DB = db_path
    result.init_auth_db = ns["init_auth_db"]
    result.load_business_profile = ns["load_business_profile"]
    result.upsert_business_profile = ns["upsert_business_profile"]
    return result


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

PROFILE_A = {
    "business_name": "Ramu Chaat Corner",
    "vendor_type": "Food & Beverages",
    "location": "T. Nagar, Chennai",
    "products": "Pani puri, bhel puri",
    "language": "Tamil",
}

PROFILE_B = {
    "business_name": "Silk Stall",
    "vendor_type": "Clothing & Textiles",
    "location": "Mylapore",
    "products": "Sarees, dupattas",
    "language": "English",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_upsert_creates_profile(db):
    """Upserting a profile for a new email stores all fields correctly."""
    email = "ramu@example.com"
    db.upsert_business_profile(email, PROFILE_A)
    result = db.load_business_profile(email)

    assert result["business_name"] == PROFILE_A["business_name"]
    assert result["vendor_type"] == PROFILE_A["vendor_type"]
    assert result["location"] == PROFILE_A["location"]
    assert result["products"] == PROFILE_A["products"]
    assert result["language"] == PROFILE_A["language"]


def test_upsert_updates_profile(db):
    """A second upsert for the same email overwrites all mutable fields."""
    email = "ramu@example.com"
    db.upsert_business_profile(email, PROFILE_A)

    updated = {**PROFILE_A, "business_name": "Ramu Bhel House", "location": "Anna Nagar"}
    db.upsert_business_profile(email, updated)

    result = db.load_business_profile(email)
    assert result["business_name"] == "Ramu Bhel House"
    assert result["location"] == "Anna Nagar"
    # Unchanged fields survive the update
    assert result["vendor_type"] == PROFILE_A["vendor_type"]
    assert result["products"] == PROFILE_A["products"]
    assert result["language"] == PROFILE_A["language"]


def test_load_returns_empty_for_unknown_user(db):
    """load_business_profile returns {} for an email with no saved profile."""
    result = db.load_business_profile("nobody@example.com")
    assert result == {}


def test_user_isolation_load(db):
    """Each user loads only their own profile; no cross-contamination."""
    db.upsert_business_profile("user_a@example.com", PROFILE_A)
    db.upsert_business_profile("user_b@example.com", PROFILE_B)

    result_a = db.load_business_profile("user_a@example.com")
    result_b = db.load_business_profile("user_b@example.com")

    assert result_a["business_name"] == PROFILE_A["business_name"]
    assert result_b["business_name"] == PROFILE_B["business_name"]
    assert result_a["business_name"] != result_b["business_name"]


def test_user_isolation_update_does_not_affect_other(db):
    """Updating one user's profile leaves the other user's profile intact."""
    db.upsert_business_profile("user_a@example.com", PROFILE_A)
    db.upsert_business_profile("user_b@example.com", PROFILE_B)

    db.upsert_business_profile("user_a@example.com", {**PROFILE_A, "business_name": "New Name A"})

    result_b = db.load_business_profile("user_b@example.com")
    assert result_b["business_name"] == PROFILE_B["business_name"]
