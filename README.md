# VendorSaathi AI

**An AI-powered growth copilot for street vendors in India, built with IBM Granite and Streamlit.**

VendorSaathi AI helps street vendors go digital by generating professional business profiles, local SEO content, promotional messages, digitalization checklists, and grounded answers to government scheme queries — all from a single workspace.

---
live demo  - https://vendorsaathiai-3vkutcv2g8ly7dsgwv8txg.streamlit.app/
## Features

| Tool | What it does |
|---|---|
| **AI Copilot** | Free-form Q&A grounded in official government PDFs via a local RAG pipeline |
| **Business Profile** | Generates a factual, customer-ready digital business description |
| **Local SEO Kit** | Location-aware keywords, Google Business listing text, and visibility actions |
| **Promo Studio** | Ready-to-share WhatsApp and social media promotional messages |
| **Digitalization Checklist** | Step-by-step plan for taking the business digital |
| **Government Schemes** | Answers about PM SVANidhi, Udyam, GeM, BHIM — sourced from official PDFs |
| **Knowledge Sources** | Browse the indexed government reference documents |

All content is grounded in the vendor's saved Business Profile. The validation layer blocks fabricated claims, invented products, unverified quality assertions, and unsupported customer-sentiment language.

---

## Tech Stack

- **AI** — IBM watsonx.ai · IBM Granite (`ibm/granite-4-h-small`)
- **RAG** — Local lexical retrieval with `pypdf` + `scikit-learn` (no external vector DB)
- **UI** — Streamlit (dark green workspace theme)
- **Auth** — Local SQLite account system with PBKDF2-salted passwords
- **Language support** — English, Tamil, Hindi

---

## Project Structure

```
VendorSaathi_AI/
├── app.py                          # Main Streamlit application
├── llm.py                          # IBM watsonx.ai client wrapper
├── rag.py                          # Local PDF retrieval pipeline
├── prompts.py                      # Prompt builders for every AI tool
├── business_profile_validation.py  # Validation for profile output
├── local_seo_validation.py         # Validation for Local SEO output
├── checklist_validation.py         # Validation for checklist output
├── scheme_answer_validation.py     # Validation for government scheme answers
├── requirements.txt
├── .env.example
├── .streamlit/
│   └── config.toml                 # Streamlit theme config
├── data/
│   └── government_docs/            # Official PDFs indexed by the RAG pipeline
│       ├── PM_SVANidhi_Scheme_Guidelines_2025.pdf
│       ├── PM_SVANidhi_Loan_Operational_Guidelines_2025.pdf
│       ├── Udyam_Official_Information.pdf
│       ├── Benefits_of_Udyam_Registration.pdf
│       ├── Udyam_Application_Form.pdf
│       ├── seller-registration-pre-requisites-v1.2.pdf
│       ├── seller-user-manual.pdf
│       ├── BHIM_Official_FAQs.pdf
│       └── BHIM_UPI_Merchant_QR_Guidelines_2026.pdf
└── tests/                          # Pytest test suite (195 tests)
```

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/aashya-madhan/VendorSaathi_AI.git
cd VendorSaathi_AI
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure IBM watsonx.ai credentials

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```env
WATSONX_API_KEY=your_ibm_cloud_api_key
WATSONX_PROJECT_ID=your_watsonx_project_id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-4-h-small
```

> **Never commit `.env` to version control.** It is already in `.gitignore`.

You can get your API key and project ID from [IBM Cloud](https://cloud.ibm.com) → watsonx.ai.

### 5. Run the app

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`. Create a free account on the sign-in screen to get started.

---

## How It Works

```
User question
     │
     ▼
Local RAG pipeline (pypdf + scikit-learn)
     │  searches government PDFs
     ▼
Retrieved passages → IBM Granite (watsonx.ai)
     │  generates grounded response
     ▼
Validation layer
     │  blocks unsupported claims
     ▼
Displayed to user with source citations
```

The RAG pipeline is fully local — no external vector database or embedding API is required. Retrieval uses TF-IDF cosine similarity over deduplicated passage chunks extracted from the bundled PDFs.

---

## Running Tests

```bash
pytest tests/ -v
```

193 of 195 tests pass. The 2 skipped tests require `python-dotenv` to be importable in the test environment — they pass when running via `streamlit run`.

---

## Important Notes

- This app uses a **local SQLite database** (`vendor_users.db`) for user accounts and chat history. It is not intended for multi-user production deployment.
- All AI-generated content is advisory only. It is not legal, financial, or regulatory advice.
- Government scheme information is sourced from the bundled PDFs. Verify current requirements on official portals before acting.
- The RAG pipeline indexes only the PDFs included in `data/government_docs/`. It does not fetch live government data.

---

## License

This project is submitted as an academic/hackathon project. All IBM watsonx.ai usage is subject to [IBM's terms of service](https://www.ibm.com/legal).
