"""
Focused tests for the Copilot chat-history persistence layer in app.py.

Strategy: identical to test_business_profiles.py — AST-extract only the DB helper
functions, compile them into an isolated namespace with AUTH_DB pointing to a real
on-disk SQLite file in tmp_path, then call them directly.  No Streamlit, no full app
import.
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
    "create_chat_session",
    "append_chat_messages",
    "load_chat_session_messages",
    "load_latest_chat_session",
    "load_recent_chat_sessions",
    "get_chat_session_owner",
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
        f"Missing: {_TARGET_FUNCS - {n.split('(')[0] for n in extracted}}"
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
    seven DB helpers ready to call.
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
# Tests
# ---------------------------------------------------------------------------

def test_create_session_returns_integer_id(db):
    """create_chat_session returns a positive integer primary key."""
    sid = db.create_chat_session("user@example.com")
    assert isinstance(sid, int)
    assert sid > 0


def test_append_and_load_messages_in_order(db):
    """append_chat_messages stores both messages; load returns them in insertion order."""
    sid = db.create_chat_session("user@example.com")

    db.append_chat_messages(sid, "Question 1", "Answer 1", "Source A")
    db.append_chat_messages(sid, "Question 2", "Answer 2", "Source B")
    db.append_chat_messages(sid, "Question 3", "Answer 3", "")

    messages = db.load_chat_session_messages(sid)
    assert len(messages) == 6

    # Verify order: user then assistant, interleaved
    assert messages[0] == {"role": "user",      "content": "Question 1", "source": ""}
    assert messages[1] == {"role": "assistant",  "content": "Answer 1",   "source": "Source A"}
    assert messages[2] == {"role": "user",      "content": "Question 2", "source": ""}
    assert messages[3] == {"role": "assistant",  "content": "Answer 2",   "source": "Source B"}
    assert messages[4] == {"role": "user",      "content": "Question 3", "source": ""}
    assert messages[5] == {"role": "assistant",  "content": "Answer 3",   "source": ""}


def test_load_latest_session_returns_none_for_unknown_user(db):
    """load_latest_chat_session returns None when the user has no sessions."""
    result = db.load_latest_chat_session("nobody@example.com")
    assert result is None


def test_load_latest_session_returns_most_recent(db):
    """load_latest_chat_session returns the newest session's messages, not an older one."""
    email = "vendor@example.com"

    sid1 = db.create_chat_session(email)
    db.append_chat_messages(sid1, "Old question", "Old answer", "")

    sid2 = db.create_chat_session(email)
    db.append_chat_messages(sid2, "New question", "New answer", "Ref")

    result = db.load_latest_chat_session(email)
    assert result is not None
    session_id, messages = result
    assert session_id == sid2
    assert len(messages) == 2
    assert messages[0]["content"] == "New question"
    assert messages[1]["content"] == "New answer"
    assert messages[1]["source"] == "Ref"


def test_load_recent_sessions_limit_and_order(db):
    """load_recent_chat_sessions returns at most `limit` sessions, newest first."""
    email = "vendor@example.com"
    created_ids = []
    for i in range(7):
        sid = db.create_chat_session(email)
        db.append_chat_messages(sid, f"Question {i}", f"Answer {i}", "")
        created_ids.append(sid)

    recent = db.load_recent_chat_sessions(email, limit=5)
    assert len(recent) == 5

    # Newest first: last 5 created, reversed
    expected_ids = list(reversed(created_ids[-5:]))
    assert [s["id"] for s in recent] == expected_ids

    # first_question populated
    assert recent[0]["first_question"] == "Question 6"


def test_load_recent_sessions_empty_session_shows_none_first_question(db):
    """A session with no messages returns first_question=None in the history list."""
    email = "vendor@example.com"
    db.create_chat_session(email)  # no messages appended

    recent = db.load_recent_chat_sessions(email, limit=5)
    assert len(recent) == 1
    assert recent[0]["first_question"] is None


def test_user_isolation(db):
    """Each user's load_latest_chat_session returns only their own messages."""
    email_a = "alice@example.com"
    email_b = "bob@example.com"

    sid_a = db.create_chat_session(email_a)
    db.append_chat_messages(sid_a, "Alice Q", "Alice A", "")

    sid_b = db.create_chat_session(email_b)
    db.append_chat_messages(sid_b, "Bob Q", "Bob A", "")

    result_a = db.load_latest_chat_session(email_a)
    result_b = db.load_latest_chat_session(email_b)

    assert result_a is not None
    assert result_b is not None

    _, msgs_a = result_a
    _, msgs_b = result_b

    assert msgs_a[0]["content"] == "Alice Q"
    assert msgs_b[0]["content"] == "Bob Q"
    # No cross-contamination
    assert all(m["content"] != "Bob Q" for m in msgs_a)
    assert all(m["content"] != "Alice Q" for m in msgs_b)


def test_session_switch_loads_only_selected_session(db):
    """Switching between two sessions loads exactly that session's messages."""
    email = "vendor@example.com"

    sid1 = db.create_chat_session(email)
    db.append_chat_messages(sid1, "Session1 Q", "Session1 A", "S1 source")

    sid2 = db.create_chat_session(email)
    db.append_chat_messages(sid2, "Session2 Q", "Session2 A", "S2 source")

    # Simulate loading session 1
    msgs1 = db.load_chat_session_messages(sid1)
    assert len(msgs1) == 2
    assert msgs1[0]["content"] == "Session1 Q"
    assert msgs1[1]["content"] == "Session1 A"
    assert msgs1[1]["source"] == "S1 source"
    # Session 2 content not present
    assert all(m["content"] != "Session2 Q" for m in msgs1)

    # Simulate switching to session 2
    msgs2 = db.load_chat_session_messages(sid2)
    assert len(msgs2) == 2
    assert msgs2[0]["content"] == "Session2 Q"
    assert msgs2[1]["content"] == "Session2 A"
    assert msgs2[1]["source"] == "S2 source"
    # Session 1 content not present
    assert all(m["content"] != "Session1 Q" for m in msgs2)


def test_get_chat_session_owner_returns_email(db):
    """get_chat_session_owner returns the correct email for a known session."""
    email = "owner@example.com"
    sid = db.create_chat_session(email)
    assert db.get_chat_session_owner(sid) == email


def test_get_chat_session_owner_returns_none_for_missing_id(db):
    """get_chat_session_owner returns None for a session id that does not exist."""
    assert db.get_chat_session_owner(99999) is None
