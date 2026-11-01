# Persistent Copilot Chat History — Implementation Plan (Revised)

## Overview

**Goal:** Persist each authenticated vendor's Copilot conversations in SQLite so
messages survive page navigation and new Streamlit sessions. Allow users to resume
their most recent conversation, view and switch between their last 5 conversations,
and start new conversations without deleting old ones.

**Scope:**
- Two new tables + one index in `vendor_users.db` inside `init_auth_db()`.
- Six new DB helper functions following the existing `load_business_profile` /
  `upsert_business_profile` pattern.
- Targeted edits to the AI Copilot page block in `app.py` (lines 991–1058).
- Two additional `pop` calls in the sign-out block.
- Focused tests in `tests/test_copilot_history.py`.

**Non-goals:**
- No changes to authentication, Granite, RAG, prompts, or any other page.
- No new dependencies.
- No conversation deletion or pruning.
- No redesign of the two-column layout, `st.chat_message` render loop, welcome
  screen, suggestion buttons, or chat input widget.

---

## Assumptions

1. `st.session_state["copilot_messages"]` remains the list consumed by the render
   loop. The DB is the durable layer beneath it.
2. Resume semantics on page entry: load the most-recent session, not a blank slate.
3. Append-on-send: each user+assistant pair is written in one transaction immediately
   after generation, before `st.rerun()`.
4. `source_note` is always a `str` in all code paths (confirmed: defaults to `""`).
5. The history column's session list shows the last 5 sessions ordered newest-first,
   using the first user question of each session as the title.
6. Session switching is achieved with a `st.button` per session entry. Clicking one
   sets `_copilot_session_id` and `copilot_messages` then calls `st.rerun()`.
7. `_copilot_session_id` (leading underscore = internal/infrastructure key) is the
   single source of truth for which session is active. It must be cleared on sign-out.
8. `chat_sessions.created_at` is stored as SQLite `CURRENT_TIMESTAMP` (UTC text,
   format `YYYY-MM-DD HH:MM:SS`). Display format: `YYYY-MM-DD`.
9. Ownership verification: before loading messages for a session switch, confirm the
   session's email matches `st.session_state["account"]["email"]` using
   `get_chat_session_owner`.
10. `copilot_messages` is currently **not** popped on sign-out. The sign-out block
    must be extended (the only pre-existing gap this plan closes).

---

## Migration Risks

| Risk | Mitigation |
|---|---|
| Live users have no session rows | `load_latest_chat_session` returns `None`; code creates a new session and starts empty — identical to today |
| Live `vendor_users.db` in use | `CREATE TABLE IF NOT EXISTS` + `CREATE INDEX IF NOT EXISTS` are additive; no data touched |
| `copilot_messages` not popped on sign-out today | Fixed in Sub-Task 4 |
| Session-id key left in state after sign-out | Also cleared in Sub-Task 4 |
| Adversarial session-id manipulation | `get_chat_session_owner` ownership check in session-switch handler |

---

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS chat_sessions (
    id         INTEGER PRIMARY KEY,
    email      TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_email
    ON chat_sessions(email);

CREATE TABLE IF NOT EXISTS chat_messages (
    id         INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role       TEXT NOT NULL,           -- 'user' or 'assistant'
    content    TEXT NOT NULL,
    source     TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Message ordering: `ORDER BY id ASC` (insertion order = chronological order).
Session ordering for history list: `ORDER BY id DESC LIMIT 5`.

---

## New DB Helper Functions

| Function | Signature | Purpose |
|---|---|---|
| `create_chat_session` | `(email: str) -> int` | Inserts a `chat_sessions` row; returns its `id` |
| `append_chat_messages` | `(session_id: int, user_content: str, assistant_content: str, source: str) -> None` | Writes both the user and assistant message in one transaction |
| `load_chat_session_messages` | `(session_id: int) -> list[dict]` | Returns ordered message dicts for a session |
| `load_latest_chat_session` | `(email: str) -> tuple[int, list[dict]] \| None` | Returns `(session_id, messages)` for the user's newest session, or `None` |
| `load_recent_chat_sessions` | `(email: str, limit: int = 5) -> list[dict]` | Returns the last `limit` sessions with `id`, `created_at`, and `first_question` |
| `get_chat_session_owner` | `(session_id: int) -> str \| None` | Returns the email owning the session (used for ownership guard) |

### Notes on `append_chat_messages`
Both messages share one transaction: a single `with sqlite3.connect(AUTH_DB) as conn:`
block with two `conn.execute(INSERT …)` calls and one `conn.commit()`. If either
insert fails the transaction rolls back and neither message is persisted.

### Notes on `load_recent_chat_sessions`
Uses a subquery to find the first user-role message per session:
```sql
SELECT cs.id, cs.created_at,
       (SELECT cm.content FROM chat_messages cm
        WHERE cm.session_id = cs.id AND cm.role = 'user'
        ORDER BY cm.id ASC LIMIT 1) AS first_question
FROM chat_sessions cs
WHERE cs.email = ?
ORDER BY cs.id DESC
LIMIT ?
```
Returns a list of `{"id": int, "created_at": str, "first_question": str | None}`.
Sessions with no messages are included but have `first_question = None` (displayed
as *"Empty conversation"*).

---

## UI Changes (history column only)

The existing history column content is **replaced** as follows.

### Before (lines 1047–1058)
```
Chat history  [SESSION chip]
caption: N exchanges in this session
[＋ New chat button]
— per-message user-question rows  OR  "Your recent questions will appear here."
```

### After
```
Chat history  [SAVED chip]
caption: N exchanges · saved
[＋ New chat button]
— list of up to 5 past sessions, each rendered as a <div class="step"> row:
    icon: ◉ (active session) or ○ (other)
    title: first_question[:55] or "Empty conversation"
    caption: YYYY-MM-DD
    [Load] button (hidden for the active session)
— "No saved conversations yet." if list is empty
```

The `<div class="step">` HTML and CSS classes are already defined and used
consistently across every other page — no new CSS is required.

The chip label changes from `SESSION` to `SAVED` to reflect that history is now
durable.

---

## Exact Edit Points in app.py

| # | Lines (current) | What changes |
|---|---|---|
| E1 | 991–992 | Replace two-line `copilot_messages` init with load-or-create guard |
| E2 | 1022–1044 | After answer is finalised, call `append_chat_messages` before `st.rerun()` |
| E3 | 1047–1058 | Replace history column inner content with session list renderer |
| E4 | 680–683 | Add two `pop` calls in sign-out block |

---

## Sub-Tasks

---

### Sub-Task 1 — Add tables, index and DB helpers

**Status:** [x] done

**Intent:**
Extend `init_auth_db()` with the two tables and index. Add the six helper functions.
No application behaviour changes yet.

**Expected Outcomes:**
- `init_auth_db()` creates `chat_sessions`, `chat_messages` and the index on startup.
- All six helpers are callable with a real SQLite file.
- Existing `business_profiles` table and helpers are untouched.

**Todo List:**
1. Inside `init_auth_db()`, after the `business_profiles` `CREATE TABLE` block and
   before `conn.commit()`, add the `CREATE TABLE IF NOT EXISTS chat_sessions`,
   `CREATE INDEX IF NOT EXISTS idx_chat_sessions_email`, and
   `CREATE TABLE IF NOT EXISTS chat_messages` statements.
2. Add `create_chat_session(email: str) -> int`.
3. Add `append_chat_messages(session_id, user_content, assistant_content, source) -> None`
   with both inserts inside one `with sqlite3.connect(AUTH_DB) as conn:` block.
4. Add `load_chat_session_messages(session_id: int) -> list[dict]`
   — `ORDER BY id ASC`, each row mapped to `{"role", "content", "source"}`.
5. Add `load_latest_chat_session(email: str) -> tuple[int, list[dict]] | None`
   — selects `MAX(id)` from `chat_sessions WHERE email=?`.
6. Add `load_recent_chat_sessions(email: str, limit: int = 5) -> list[dict]`
   — uses the subquery described in the schema section.
7. Add `get_chat_session_owner(session_id: int) -> str | None`.

**Relevant Context:**
- [`init_auth_db()`](app.py:321) — extend; keep one `conn.commit()`.
- [`AUTH_DB`](app.py:319) — module-level path used by all helpers.
- Existing upsert pattern at [lines 364–387](app.py:364).

---

### Sub-Task 2 — Load or create session on Copilot page entry

**Status:** [x] done

**Intent:**
When the user first enters the AI Copilot page in a Streamlit session, resume their
most recent conversation from the DB. If no conversation exists, create a new one.

**Expected Outcomes:**
- `copilot_messages` is populated from the DB on first page visit.
- `_copilot_session_id` is always set before any message is sent.
- Users with no history see the same empty welcome screen as today.
- On subsequent `st.rerun()` calls within the same Streamlit session the guard
  is skipped (key already present).

**Todo List:**
1. At [lines 991–992](app.py:991), replace:
   ```python
   if "copilot_messages" not in st.session_state:
       st.session_state["copilot_messages"] = []
   ```
   with:
   ```python
   _email = st.session_state["account"]["email"]
   if "copilot_messages" not in st.session_state:
       _session = load_latest_chat_session(_email)
       if _session:
           st.session_state["_copilot_session_id"], st.session_state["copilot_messages"] = _session
       else:
           st.session_state["_copilot_session_id"] = create_chat_session(_email)
           st.session_state["copilot_messages"] = []
   ```

**Relevant Context:**
- [lines 991–992](app.py:991).
- `st.session_state["account"]["email"]` guaranteed present (authenticated gate at line 543).

---

### Sub-Task 3 — Persist messages on send and create new session on "New chat"

**Status:** [x] done

**Intent:**
Write each user+assistant pair to the DB immediately after generation.
"＋ New chat" creates a fresh session row without touching previous data.

**Expected Outcomes:**
- Every Q&A exchange is durable after `st.rerun()`.
- "＋ New chat" results in a new `chat_sessions` row and a blank conversation.
- Previous sessions remain intact in the DB and visible in the history list.
- The existing `st.rerun()` timing is unchanged.

**Todo List:**
1. In the `if question:` block, after both `copilot_messages.append(…)` calls
   (lines 1023 and 1043) and before `st.rerun()` (line 1044), insert:
   ```python
   append_chat_messages(
       st.session_state["_copilot_session_id"],
       question,
       answer,
       source_note,
   )
   ```
2. In the `if st.button("＋ New chat", …)` block, replace:
   ```python
   st.session_state["copilot_messages"] = []
   st.rerun()
   ```
   with:
   ```python
   _new_sid = create_chat_session(st.session_state["account"]["email"])
   st.session_state["_copilot_session_id"] = _new_sid
   st.session_state["copilot_messages"] = []
   st.rerun()
   ```

**Relevant Context:**
- Question block end: [lines 1043–1044](app.py:1043).
- New chat button: [lines 1050–1052](app.py:1050).

---

### Sub-Task 4 — Replace history column content with session list

**Status:** [x] done

**Intent:**
Replace the existing per-message question list with a list of up to 5 saved sessions.
Each entry shows the first user question (truncated), the date, and a "Load" button
for sessions other than the active one.

**Expected Outcomes:**
- The history column shows up to 5 past sessions newest-first.
- Clicking "Load" on a past session verifies ownership, sets
  `_copilot_session_id` and `copilot_messages`, then calls `st.rerun()`.
- The active session's entry has no "Load" button (already loaded).
- Sessions with no messages show *"Empty conversation"*.
- The exchange counter and "＋ New chat" button remain in place.
- The chip label changes from `SESSION` to `SAVED`.
- No new CSS classes are introduced.

**Todo List:**
1. Replace [lines 1047–1058](app.py:1047) with the following logic (pseudocode):
   ```
   container(border=True):
       card-heading "Chat history" [SAVED chip]
       caption: "N exchanges · saved"
       button "＋ New chat"  → Sub-Task 3 new-chat logic
       recent = load_recent_chat_sessions(email, limit=5)
       if recent:
           for each session in recent:
               active = (session["id"] == _copilot_session_id)
               icon = "◉" if active else "○"
               title = session["first_question"][:55] if first_question else "Empty conversation"
               date_label = session["created_at"][:10]
               render <div class="step"> with icon, title, date_label
               if not active:
                   button "Load" with key f"load_session_{session['id']}":
                       owner = get_chat_session_owner(session["id"])
                       if owner == email:
                           _copilot_session_id = session["id"]
                           copilot_messages = load_chat_session_messages(session["id"])
                           st.rerun()
       else:
           caption "No saved conversations yet."
   ```
2. Keep the second `with st.container(border=True)` block for "Knowledge assistant"
   (lines 1059–1065) exactly as-is.

**Relevant Context:**
- Lines to replace: [1047–1058](app.py:1047). Lines 1059–1065 are untouched.
- `<div class="step">` pattern already used on this page at [line 1056](app.py:1056).
- `escape()` must be applied to all user-supplied string values rendered in HTML.

---

### Sub-Task 5 — Clear Copilot state on sign-out

**Status:** [x] done

**Intent:**
Prevent conversation data from one user leaking into a subsequent session on the
same browser tab.

**Expected Outcomes:**
- After sign-out, `copilot_messages` and `_copilot_session_id` are absent from
  session state.
- The next authenticated user starts fresh (or resumes their own history from DB).

**Todo List:**
1. In the sign-out block ([lines 676–684](app.py:676)), after
   `st.session_state.pop("checklist_result", None)`, add:
   ```python
   st.session_state.pop("copilot_messages", None)
   st.session_state.pop("_copilot_session_id", None)
   ```

**Relevant Context:**
- Sign-out block: [lines 676–684](app.py:676).

---

### Sub-Task 6 — Add focused tests

**Status:** [x] done

**Intent:**
Verify all six DB helpers and user isolation using a real on-disk SQLite file via
`tmp_path`, following the `test_business_profiles.py` AST-extraction pattern exactly.

**Expected Outcomes:**
- `tests/test_copilot_history.py` passes with `pytest` (7 tests).
- Live `vendor_users.db` is never touched.
- No Streamlit stub or import of the full app module is required.

**Target functions to extract via AST:**
`init_auth_db`, `create_chat_session`, `append_chat_messages`,
`load_chat_session_messages`, `load_latest_chat_session`,
`load_recent_chat_sessions`, `get_chat_session_owner`.

**Todo List:**
1. Create `tests/test_copilot_history.py`.
2. Copy the `_extract_db_functions` / `exec`-into-namespace / `tmp_path` fixture
   pattern from `tests/test_business_profiles.py`, updating `_TARGET_FUNCS` to the
   seven functions listed above.
3. `test_create_session_returns_integer_id` — assert `isinstance(sid, int) and sid > 0`.
4. `test_append_and_load_messages_in_order` — append 3 pairs; assert
   `load_chat_session_messages` returns all 6 messages in insertion order with
   correct `role`, `content`, `source` values.
5. `test_load_latest_session_returns_none_for_unknown_user`.
6. `test_load_latest_session_returns_most_recent` — create two sessions for the same
   email with different messages; assert the second session's messages are returned.
7. `test_load_recent_sessions_limit_and_order` — create 7 sessions; assert
   `load_recent_chat_sessions(email, limit=5)` returns exactly 5, newest first.
8. `test_user_isolation` — two emails, each with a session; assert each user's
   `load_latest_chat_session` returns only their own messages.
9. `test_get_chat_session_owner_returns_email` and
   `test_get_chat_session_owner_returns_none_for_missing_id`.

**Relevant Context:**
- [`tests/test_business_profiles.py`](tests/test_business_profiles.py) — authoritative
  reference for the fixture pattern (AST extraction, `exec`, `tmp_path`,
  `types.SimpleNamespace`).
