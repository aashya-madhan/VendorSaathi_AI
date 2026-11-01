"""
Focused tests for the Promotion Library persistence layer in app.py.

Strategy: identical to test_business_profiles.py and test_copilot_history.py —
AST-extract only the DB helper functions, compile them into an isolated namespace
with AUTH_DB pointing to a real on-disk SQLite file in tmp_path, then call them
directly.  No Streamlit, no full app import.
"""

import ast
import sqlite3
import types
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Source extraction
# ---------------------------------------------------------------------------

_APP_PATH = Path(__file__).parent.parent / "app.py"
_TARGET_FUNCS = {
    "init_auth_db",
    "save_promotion",
    "load_saved_promotions",
    "load_promotion_by_id",
    "get_promotion_owner",
    "delete_promotion",
}


def _extract_db_functions() -> str:
    source = _APP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)

    extracted: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in _TARGET_FUNCS:
            start = node.lineno - 1
            end = node.end_lineno
            extracted.append("".join(lines[start:end]) + "\n")

    assert len(extracted) == len(_TARGET_FUNCS), (
        f"Expected {len(_TARGET_FUNCS)} DB functions, found {len(extracted)}. "
        f"Missing: {_TARGET_FUNCS - {n for n in _TARGET_FUNCS}}"
    )
    return "\n".join(extracted)


_DB_FUNCTION_SOURCE = _extract_db_functions()


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def db(tmp_path):
    """
    Returns a SimpleNamespace with AUTH_DB pointing to a fresh tmp file and all
    six DB helpers ready to call.
    """
    db_path = tmp_path / "test_vendor_users.db"

    ns: dict = {
        "__builtins__": __builtins__,
        "sqlite3": sqlite3,
        "AUTH_DB": db_path,
    }
    exec(compile(_DB_FUNCTION_SOURCE, str(_APP_PATH), "exec"), ns)  # noqa: S102
    ns["init_auth_db"]()

    result = types.SimpleNamespace()
    result.AUTH_DB = db_path
    for fn in _TARGET_FUNCS:
        setattr(result, fn, ns[fn])
    return result


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

EMAIL_A = "alice@example.com"
EMAIL_B = "bob@example.com"

PROMO_A = {
    "occasion": "Weekend special",
    "platform": "WhatsApp",
    "tone": "Friendly and welcoming",
    "content": "Come visit Ramu Chaat Corner this weekend for fresh pani puri!",
}

PROMO_B = {
    "occasion": "Festive offer",
    "platform": "Instagram",
    "tone": "Festive and energetic",
    "content": "Celebrate with Silk Stall's festive saree collection!",
}


def _save(db, email, promo):
    return db.save_promotion(
        email,
        promo["occasion"],
        promo["platform"],
        promo["tone"],
        promo["content"],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_save_promotion_returns_integer_id(db):
    """save_promotion returns a positive integer primary key."""
    pid = _save(db, EMAIL_A, PROMO_A)
    assert isinstance(pid, int)
    assert pid > 0


def test_load_saved_promotions_returns_saved_entry(db):
    """A saved promotion appears in load_saved_promotions for that user."""
    _save(db, EMAIL_A, PROMO_A)
    results = db.load_saved_promotions(EMAIL_A)
    assert len(results) == 1
    assert results[0]["content"] == PROMO_A["content"]
    assert results[0]["occasion"] == PROMO_A["occasion"]
    assert results[0]["platform"] == PROMO_A["platform"]
    assert results[0]["tone"] == PROMO_A["tone"]


def test_load_saved_promotions_newest_first(db):
    """load_saved_promotions returns entries newest-first (by id DESC)."""
    id1 = _save(db, EMAIL_A, PROMO_A)
    promo2 = dict(PROMO_A, occasion="Second offer", content="Second content")
    id2 = _save(db, EMAIL_A, promo2)
    promo3 = dict(PROMO_A, occasion="Third offer", content="Third content")
    id3 = _save(db, EMAIL_A, promo3)

    results = db.load_saved_promotions(EMAIL_A)
    assert [r["id"] for r in results] == [id3, id2, id1]


def test_load_saved_promotions_limit(db):
    """load_saved_promotions honours the limit parameter."""
    for i in range(12):
        _save(db, EMAIL_A, dict(PROMO_A, occasion=f"Offer {i}", content=f"Content {i}"))

    results = db.load_saved_promotions(EMAIL_A, limit=10)
    assert len(results) == 10


def test_load_promotion_by_id_returns_full_content(db):
    """load_promotion_by_id returns the complete row for the correct owner."""
    pid = _save(db, EMAIL_A, PROMO_A)
    loaded = db.load_promotion_by_id(pid, EMAIL_A)

    assert loaded is not None
    assert loaded["id"] == pid
    assert loaded["content"] == PROMO_A["content"]
    assert loaded["occasion"] == PROMO_A["occasion"]
    assert loaded["platform"] == PROMO_A["platform"]
    assert loaded["tone"] == PROMO_A["tone"]
    assert loaded["created_at"] is not None


def test_load_promotion_by_id_returns_none_for_missing(db):
    """load_promotion_by_id returns None for a non-existent id."""
    result = db.load_promotion_by_id(99999, EMAIL_A)
    assert result is None


def test_delete_promotion_removes_entry(db):
    """After deletion, the promotion is no longer loadable."""
    pid = _save(db, EMAIL_A, PROMO_A)
    deleted = db.delete_promotion(pid, EMAIL_A)
    assert deleted is True
    assert db.load_promotion_by_id(pid, EMAIL_A) is None
    assert db.load_saved_promotions(EMAIL_A) == []


def test_delete_promotion_wrong_owner_rejected(db):
    """Deleting with a wrong email returns False and leaves the row intact."""
    pid = _save(db, EMAIL_A, PROMO_A)
    deleted = db.delete_promotion(pid, EMAIL_B)  # wrong owner
    assert deleted is False
    # Row must still exist for the real owner
    assert db.load_promotion_by_id(pid, EMAIL_A) is not None


def test_user_isolation(db):
    """Each user's promotions are not visible to the other user."""
    _save(db, EMAIL_A, PROMO_A)
    _save(db, EMAIL_B, PROMO_B)

    results_a = db.load_saved_promotions(EMAIL_A)
    results_b = db.load_saved_promotions(EMAIL_B)

    assert len(results_a) == 1
    assert len(results_b) == 1
    assert results_a[0]["content"] == PROMO_A["content"]
    assert results_b[0]["content"] == PROMO_B["content"]
    assert results_a[0]["content"] != results_b[0]["content"]


def test_load_promotion_by_id_rejects_wrong_owner(db):
    """load_promotion_by_id returns None when the caller is not the owner."""
    pid = _save(db, EMAIL_A, PROMO_A)
    # EMAIL_B attempts to load EMAIL_A's promotion
    result = db.load_promotion_by_id(pid, EMAIL_B)
    assert result is None
    # The row is still intact for the real owner
    assert db.load_promotion_by_id(pid, EMAIL_A) is not None
