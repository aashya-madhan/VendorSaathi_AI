# VendorSaathi AI — redesigned Streamlit project

This is a UI redesign of the supplied Street Vendor Growth Copilot. It retains the original `llm.py`, `rag.py`, `prompts.py`, and government reference PDFs. The interface is reorganized into a modern workspace with sidebar navigation, dashboard, profile generator, promo studio, checklist, government Q&A, AI Copilot and knowledge-source view.

## Run locally

1. Create and activate a Python virtual environment.
2. Install the dependencies listed below.
3. Configure watsonx credentials as environment variables (or a local `.env` file that is NOT committed).
4. Run `streamlit run app.py`.

### Dependencies
- streamlit
- python-dotenv
- ibm-watsonx-ai
- pypdf
- scikit-learn

## IBM watsonx.ai configuration

Set:
- `WATSONX_API_KEY`
- `WATSONX_PROJECT_ID`
- `WATSONX_URL` (optional; defaults to the original Dallas endpoint)
- `WATSONX_MODEL_ID` (optional; defaults to `ibm/granite-4-h-small`)

Do not put credentials in frontend code or commit `.env`.

## Important implementation notes

- Original Granite client wrapper and RAG/prompt modules are preserved from the supplied project.
- The RAG pipeline continues to index local PDFs in `data/government_docs`.
- Dashboard counts describe bundled capabilities/source passages, not vendor business performance.
- This is a redesigned Streamlit UI, not a production deployment.
- UPI QR generation, live payments, user authentication, persistent vendor profiles, live government APIs, and real sales analytics are not implemented in the supplied code and are not falsely represented as live features.
- The AI Copilot UI currently routes to the existing government-scheme RAG workflow; the other three existing generation workflows remain separate pages.
