"""
Multi-source local retrieval for Street Vendor Growth Copilot.

Indexes readable pages from the configured government / platform PDFs.
Local only: pypdf + scikit-learn + NumPy. No network or IBM calls.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from sklearn.feature_extraction.text import HashingVectorizer


DATA_DIR = Path(__file__).resolve().parent / "data" / "government_docs"

SOURCE_CONFIG = {
    "Udyam_Official_Information.pdf": {
        "pages": None,
        "date_note": (
            "Official Udyam portal page saved as PDF; verify the live portal "
            "for changes."
        ),
    },
    "Benefits_of_Udyam_Registration.pdf": {
        "pages": (14, 15),
        "date_note": (
            "Source document dated February 2021; historical information, "
            "current status not verified."
        ),
    },
    "seller-registration-pre-requisites-v1.2.pdf": {
        "pages": None,
        "date_note": (
            "GeM prerequisites document last updated 29 June 2020; historical, "
            "current requirements not verified."
        ),
    },
    "seller-user-manual.pdf": {
        "pages": None,
        "date_note": (
            "GeM seller manual; publication/update date not established; "
            "treat workflow details as historical until verified."
        ),
    },
    "PM_SVANidhi_Scheme_Guidelines_2025.pdf": {
        "pages": None,
        "date_note": (
            "Official PM SVANidhi Scheme Guidelines, dated 16 September 2025; "
            "verify current eligibility and loan details on pmsvanidhi.mohua.gov.in."
        ),
    },
    "PM_SVANidhi_Loan_Operational_Guidelines_2025.pdf": {
        "pages": None,
        "date_note": (
            "Official PM SVANidhi Loan Operational Guidelines, dated 16 September 2025; "
            "verify current operational procedures on pmsvanidhi.mohua.gov.in."
        ),
    },
}
EXCLUDED_FILES = {"Udyam_Application_Form.pdf"}


@dataclass(frozen=True)
class Passage:
    text: str
    source: str
    page: int
    date_note: str


def _clean_text(text: str) -> str:
    text = text.replace("\u00ad", "")
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", " ", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def _split_units(text: str) -> list[str]:
    text = re.sub(r"\s*[•▪◦]\s*", "\n", text)
    text = re.sub(
        r"(?i)(?<!\w)(Salient features:|Requirement for Registration:|"
        r"Benefits of this registration:|Priority Sector Lending:)",
        r"\n\1",
        text,
    )
    units: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        for part in re.split(r"(?<=[.!?])\s+(?=[A-Z“\"'])", line):
            part = part.strip(" \t•▪◦")
            if len(part) >= 30:
                units.append(part)
    return units


def _pack_chunks(units: list[str], max_words: int = 90) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    count = 0
    for unit in units:
        n = len(unit.split())
        if current and count + n > max_words:
            chunks.append(" ".join(current).strip())
            current, count = [], 0
        current.append(unit)
        count += n
    if current:
        chunks.append(" ".join(current).strip())
    return chunks


def _canonical(text: str) -> str:
    text = text.lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _deduplicate(passages: list[Passage]) -> list[Passage]:
    kept: list[Passage] = []
    token_sets: list[set[str]] = []
    for item in passages:
        normalized = _canonical(item.text)
        tokens = set(normalized.split())
        if not tokens:
            continue
        duplicate = None
        for i, prior in enumerate(token_sets):
            union = tokens | prior
            overlap = len(tokens & prior) / len(union) if union else 1.0
            if normalized == _canonical(kept[i].text) or overlap >= 0.88:
                duplicate = i
                break
        if duplicate is None:
            kept.append(item)
            token_sets.append(tokens)
        elif len(item.text) > len(kept[duplicate].text) + 35:
            kept[duplicate] = item
            token_sets[duplicate] = tokens
    return kept


def load_passages(data_dir: str | Path = DATA_DIR) -> list[Passage]:
    root = Path(data_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Government document folder not found: {root}")

    passages: list[Passage] = []
    for filename, config in SOURCE_CONFIG.items():
        pdf_path = root / filename
        if not pdf_path.is_file():
            continue

        reader = PdfReader(str(pdf_path))
        selected_pages = config["pages"]
        page_numbers = (
            range(1, len(reader.pages) + 1)
            if selected_pages is None
            else selected_pages
        )

        for page_number in page_numbers:
            if page_number < 1 or page_number > len(reader.pages):
                continue
            cleaned = _clean_text(
                reader.pages[page_number - 1].extract_text() or ""
            )
            if len(cleaned) < 30:
                continue

            letters = sum(ch.isalpha() for ch in cleaned)
            latin = sum(ch.isascii() and ch.isalpha() for ch in cleaned)
            if letters and latin / letters < 0.70:
                continue

            for chunk in _pack_chunks(_split_units(cleaned)):
                if len(chunk) >= 45:
                    passages.append(
                        Passage(
                            chunk,
                            filename,
                            page_number,
                            str(config["date_note"]),
                        )
                    )

    passages = _deduplicate(passages)
    if not passages:
        raise ValueError(
            "No readable passages found. Check PDF filenames and text extraction."
        )
    return passages


class LocalRetriever:
    """Lexical retrieval with query-intent guards and source-aware ranking."""

    def __init__(
        self,
        passages: list[Passage] | None = None,
        data_dir: str | Path = DATA_DIR,
        min_score: float = 0.12,
    ) -> None:
        self.passages = passages if passages is not None else load_passages(data_dir)
        self.min_score = float(min_score)
        self.vectorizer = HashingVectorizer(
            n_features=2**16,
            alternate_sign=False,
            norm="l2",
            lowercase=True,
            strip_accents="unicode",
            ngram_range=(1, 2),
            stop_words="english",
            token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9'-]*\b",
        )
        self.matrix = self.vectorizer.transform([p.text for p in self.passages])

    @staticmethod
    def _is_treds_registration_query(query: str) -> bool:
        q = _canonical(query)
        asks_treds = "treds" in q or any(
            term in q for term in ("invoicemart", "m1xchange", "rxil")
        )
        asks_process = any(
            term in q
            for term in (
                "register", "registration", "onboard", "onboarding",
                "how do i", "how to", "steps", "procedure", "documents",
            )
        )
        return asks_treds and asks_process

    @staticmethod
    def _has_treds_process_evidence(text: str) -> bool:
        p = _canonical(text)
        process_phrases = (
            "registration process",
            "register on the platform",
            "register with the platform",
            "sign up",
            "create an account",
            "onboarding process",
            "onboarding steps",
            "documents required",
            "kyc process",
            "complete registration",
            "submit an application",
        )
        return any(phrase in p for phrase in process_phrases)

    @staticmethod
    def _source_priority(query: str, passage: Passage) -> float:
        q = _canonical(query)
        if (
            passage.source == "Udyam_Official_Information.pdf"
            and any(term in q for term in ("udyam", "msme registration"))
        ):
            # Prefer the official portal snapshot over the 2021 explanatory PDF.
            return 0.45
        return 0.0

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        if not query or not query.strip() or top_k <= 0:
            return []

        # The available TReDS source only mentions platforms; it does not
        # contain registration instructions. Do not turn a mention into a guide.
        treds_process_query = self._is_treds_registration_query(query)

        qvec = self.vectorizer.transform([query.strip()])
        base_scores = (self.matrix @ qvec.T).toarray().ravel()
        ranked = []

        for idx, base in enumerate(base_scores):
            passage = self.passages[idx]
            if (
                treds_process_query
                and not self._has_treds_process_evidence(passage.text)
            ):
                continue

            priority = self._source_priority(query, passage)
            adjusted = min(1.0, float(base) + priority)
            ranked.append((adjusted, float(base), idx))

        ranked.sort(reverse=True)

        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for adjusted, base, idx in ranked:
            if base < self.min_score and adjusted < self.min_score:
                continue
            passage = self.passages[idx]
            key = _canonical(passage.text)
            if key in seen:
                continue
            seen.add(key)
            results.append(
                {
                    "text": passage.text,
                    "source": passage.source,
                    "page": passage.page,
                    "date_note": passage.date_note,
                    "score": round(adjusted, 4),
                    "base_score": round(base, 4),
                }
            )
            if len(results) >= top_k:
                break
        return results

    def format_context(self, query: str, top_k: int = 3) -> str:
        return "\n\n".join(
            (
                f"[Source: {hit['source']}, PDF page {hit['page']}; "
                f"{hit['date_note']}]\n{hit['text']}"
            )
            for hit in self.search(query, top_k=top_k)
        )


def run_regression_tests(
    retriever: LocalRetriever,
) -> list[tuple[str, bool, str]]:
    cases = [
        (
            "Is Udyam registration free?",
            "Udyam_Official_Information.pdf",
            "official source should rank first",
        ),
        (
            "GeM seller registration prerequisites",
            "seller-registration-pre-requisites-v1.2.pdf",
            "prerequisite document should appear in top five",
        ),
        (
            "How do I add a product on GeM?",
            "seller-user-manual.pdf",
            "seller manual should appear in top five",
        ),
        (
            "What are current PM SVANidhi loan amounts?",
            None,
            "no unsupported scheme answer should be retrieved",
        ),
        (
            "How do I register on TReDS?",
            None,
            "a platform mention must not be treated as registration guidance",
        ),
    ]

    outcomes = []
    for query, expected_source, reason in cases:
        hits = retriever.search(query, top_k=5)
        if expected_source is None:
            passed = not hits
        elif query.startswith("Is Udyam"):
            passed = bool(hits) and hits[0]["source"] == expected_source
        else:
            passed = any(hit["source"] == expected_source for hit in hits)

        detail = "; ".join(
            f"{hit['source']} p.{hit['page']} score={hit['score']}"
            for hit in hits[:3]
        ) if hits else "no match"
        outcomes.append((query, passed, f"{reason}; {detail}"))
    return outcomes


if __name__ == "__main__":
    retriever = LocalRetriever()
    print(f"Loaded {len(retriever.passages)} deduplicated passages.")

    print("\nSOURCE COVERAGE")
    for filename in SOURCE_CONFIG:
        count = sum(p.source == filename for p in retriever.passages)
        print(
            f"{filename}: {count} passages"
            if count
            else f"{filename}: NOT FOUND / NO READABLE TEXT"
        )
    print(f"Intentionally excluded: {', '.join(sorted(EXCLUDED_FILES))}")

    print("\nREGRESSION TESTS")
    outcomes = run_regression_tests(retriever)
    for query, passed, detail in outcomes:
        print(f"[{'PASS' if passed else 'FAIL'}] {query}")
        print(f"       {detail}")

