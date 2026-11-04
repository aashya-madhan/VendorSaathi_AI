VendorSaathi AI — Local SEO prompt update

Files:
- prompts.py: updated build_local_seo_prompt() instructions only.
- test_local_seo_prompt.py: two focused regression tests for the prompt.

Install:
1. Back up your existing prompts.py.
2. Replace prompts.py with the supplied version.
3. Copy test_local_seo_prompt.py into your tests/ directory.
4. Run: python -m pytest -q

No changes are required to app.py, llm.py, rag.py, or local_seo_validation.py.
The deterministic Local SEO validator remains the final safety check.

Note: prompt instructions reduce the chance of unsupported marketing claims;
they cannot guarantee model compliance. The validator remains necessary.
