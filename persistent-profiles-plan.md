# Persistent User-Specific Business Profiles — Implementation Plan

## Overview

**Goal:** Durably associate each authenticated user's business profile with their account so it survives page refreshes, browser restarts and re-logins.

**Scope:**
- Add a `business_profiles` table to the existing `vendor_users.db` SQLite database.
- Expose three thin DB helpers: `init_business_profiles_table`, `load_business_profile`, `upsert_business_profile`.
- Wire those helpers into the three lifecycle events already present in `app.py`: post-login, save-profile submit, and sign-out.
- Add focused tests for profile creation, retrieval, update and user isolation.

**Non-goals:**
- No UI changes of any kind.
- No changes to authentication logic.
- No migration scripts — `CREATE TABLE IF NOT EXISTS` is sufficient.
- No new dependencies.

**Key constraint:** `st.session_state["vendor"]` must remain the single source-of-truth consumed by all pages. The DB is the persistence layer beneath it.

---

## Migration Risks

| Risk | Mitigation |
|---|---|
| Existing users have no profile row | `load_business_profile` returns `{}` on no-row; existing empty-profile fallbacks in the UI are unchanged |
| `vendor_users.db` is a live file | `CREATE TABLE IF NOT EXISTS` is additive and non-destructive; safe to run at every startup |
| Session state lost on cold restart | Profile load fires whenever `authenticated` is `True` and `"vendor"` is not yet in session state, covering both fresh login and browser refresh |
| `session_state["vendor"]` consumed on multiple pages | All pages already read from this key; populating it from the DB on load requires no page-level changes |

---

## Sub-Tasks

---

### Sub-Task 1 — Add `business_profiles` table and DB helpers

**Status:** [x] done

**Intent:**
Extend `vendor_users.db` with a `business_profiles` table and provide the three helper functions that the rest of the app will call. No application behaviour changes yet.

**Expected Outcomes:**
- `init_auth_db()` also creates `business_profiles` if it does not exist.
- `load_business_profile(email)` returns a `dict` or `{}`.
- `upsert_business_profile(email, vendor_dict)` inserts or replaces the profile row.
- No passwords or API keys are stored in the profile table.

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS business_profiles (
    email          TEXT PRIMARY KEY REFERENCES users(email) ON DELETE CASCADE,
    business_name  TEXT NOT NULL,
    vendor_type    TEXT NOT NULL,
    location       TEXT,
    products       TEXT,
    language       TEXT NOT NULL DEFAULT 'English',
    updated_at     TEXT DEFAULT CURRENT_TIMESTAMP
)
```

**Todo List:**
1. Inside `init_auth_db()` in `app.py`, add the `CREATE TABLE IF NOT EXISTS business_profiles` statement after the `users` table creation.
2. Add `load_business_profile(email: str) -> dict` — queries by email, maps columns to the `vendor` dict shape, returns `{}` if no row found.
3. Add `upsert_business_profile(email: str, vendor: dict)` — uses `INSERT OR REPLACE` with the five profile fields plus `updated_at = CURRENT_TIMESTAMP`.

**Relevant Context:**
- [`init_auth_db()`](app.py:321) — extend this function; keep one `conn.commit()` at the end.
- [`AUTH_DB`](app.py:319) — same path variable used by all DB helpers.
- `vendor` dict shape: `business_name`, `vendor_type`, `location`, `products`, `language` — matches form fields at [lines 739-743](app.py:739).

---

### Sub-Task 2 — Load profile after login and on app rerun

**Intent:**
Populate `st.session_state["vendor"]` from the DB immediately after a successful login, and again on any app rerun where the user is already authenticated but `"vendor"` is not yet in session state (covers browser refreshes).

**Expected Outcomes:**
- After a successful sign-in, the Business Profile page pre-fills with the user's saved data.
- On a hard browser refresh, the profile is restored from DB rather than showing empty fields.
- Users with no saved profile see the same empty-field behaviour as before.

**Status:** [x] done

**Todo List:**
1. In `render_login()`, after `st.session_state["account"] = account` (line 444), call `st.session_state["vendor"] = load_business_profile(account["email"])`.
2. After the `init_auth_db()` call and the initial session-state setup block (around line 366-375), add a guard: if `authenticated` is `True` and `"vendor"` not in `st.session_state`, call `load_business_profile` using `st.session_state["account"]["email"]` and assign to `st.session_state["vendor"]`.

**Relevant Context:**
- Login success block: [`render_login()`](app.py:440-446).
- Session-state initialisation block: [lines 368-375](app.py:368).
- `st.session_state["account"]` holds `{"email": …, "full_name": …}` after login.

---

### Sub-Task 3 — Persist profile on "Save business details"

**Intent:**
When the user submits the business profile form, write the validated profile to the DB in addition to updating session state.

**Expected Outcomes:**
- After saving, the profile survives a page refresh or re-login.
- The DB row is created on first save and updated on every subsequent save.
- The success message and `st.rerun()` behaviour are unchanged.

**Status:** [x] done

**Todo List:**
1. In the `if save_profile:` block (lines 735-745), after the `st.session_state["vendor"] = {…}` assignment, call `upsert_business_profile(st.session_state["account"]["email"], st.session_state["vendor"])`.

**Relevant Context:**
- Save block: [lines 735-745](app.py:735).
- `st.session_state["account"]["email"]` is always available here because the app gate at line 488 ensures only authenticated users reach this page.

---

### Sub-Task 4 — Clear profile data on sign-out

**Intent:**
Ensure no user-specific profile data leaks into a subsequent session on the same browser tab.

**Expected Outcomes:**
- After sign-out, `st.session_state["vendor"]` is removed.
- The existing `st.session_state.pop("vendor", None)` call at line 618 already does this; verify it is present and sufficient.
- Confirm no other user-specific keys need clearing (e.g. `profile_result`).

**Status:** [x] done

**Todo List:**
1. Read the sign-out block (lines 614-619) and confirm `st.session_state.pop("vendor", None)` is present.
2. Add `st.session_state.pop("profile_result", None)` to the sign-out block so a previously generated AI profile text is not shown to the next user.
3. No other user-specific keys require clearing at this stage.

**Relevant Context:**
- Sign-out block: [lines 614-619](app.py:614).
- `"profile_result"` is set at [line 762](app.py:762) and displayed at [line 766](app.py:766).

---

### Sub-Task 5 — Add focused tests

**Intent:**
Verify the four profile operations and user isolation with an in-memory SQLite database so tests run with zero external dependencies.

**Expected Outcomes:**
- A new file `tests/test_business_profiles.py` passes with `pytest`.
- Tests cover: profile creation, profile retrieval, profile update, isolation between two users, and graceful empty return for a user with no profile.
- Tests do not touch the live `vendor_users.db` file.

**Status:** [x] done

**Todo List:**
1. Create `tests/test_business_profiles.py`.
2. Use `pytest` fixtures to create an in-memory SQLite DB and monkey-patch `AUTH_DB` in `app` to point to it.
3. Write test `test_upsert_creates_profile` — insert a profile, load it back, assert all fields match.
4. Write test `test_upsert_updates_profile` — insert, then upsert with changed fields, load and assert updated values.
5. Write test `test_load_returns_empty_for_unknown_user` — call `load_business_profile` for an email with no row, assert `{}` is returned.
6. Write test `test_user_isolation` — create profiles for two different emails, assert each user loads only their own profile.

**Relevant Context:**
- DB helpers added in Sub-Task 1: `init_auth_db`, `load_business_profile`, `upsert_business_profile`.
- `AUTH_DB` is a module-level `Path` variable in `app.py` — patchable via `monkeypatch.setattr`.
- No `tests/` directory exists yet; it must be created.
