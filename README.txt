VendorSaathi AI - Local SEO validator update

Files:
- local_seo_validation.py: updated validator
- test_local_seo_validation.py: updated regression tests

Installation:
1. Back up your existing local_seo_validation.py.
2. Replace it with the file in this package.
3. Replace tests/test_local_seo_validation.py with this test file.
4. Run: python -m pytest -q

Behavior:
- Unsupported claims, unsupported specific products/services, unresolved placeholders,
  and empty drafts remain blocking errors.
- "near me" and long-sentence checks are now non-blocking suggestions.
- get_local_seo_warnings(text) returns those suggestions for optional UI display.

Compatibility note:
app.py does not need to change for the main behavior change: drafts containing only
these non-blocking SEO/readability issues will now pass validation and be displayed.
The current app.py does not yet render the non-blocking suggestions; it only uses the
validator's blocking result. To show those suggestions in the Streamlit UI, a separate
small app.py change would be needed.
