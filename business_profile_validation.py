"""Deterministic checks for unsupported claims in generated business profiles."""
import re

# Short words and symbols that carry no discriminating meaning on their own
# and should be skipped when checking whether a category is represented.
_CATEGORY_STOPWORDS = frozenset({"&", "/", "and", "or", "the", "a", "an"})


def _norm_field(value: str) -> str:
    """Normalise a saved profile field for substring matching.

    Collapses multiple internal spaces to one, removes spaces that appear
    immediately before a comma or period, and casefoldes the result.
    This tolerates the common case where a vendor saves "Rocky  textiles"
    (double space) or "Porur , Chennai" (space before comma) while Granite
    normalises those to "Rocky Textiles" / "Porur, Chennai".
    """
    s = re.sub(r"\s+", " ", value).strip()
    s = re.sub(r"\s+([,.])", r"\1", s)
    return s.casefold()


def _category_tokens(category: str) -> list[str]:
    """Return the significant words of a category string.

    Splits on whitespace and punctuation, discards stop-symbols and
    words of two characters or fewer, and returns what remains lower-cased.
    Example: "Clothing & Textiles" → ["clothing", "textiles"]
    """
    words = re.split(r"[\s&/,|]+", category)
    return [
        w.casefold()
        for w in words
        if w.casefold() not in _CATEGORY_STOPWORDS and len(w) > 2
    ]


_UNSUPPORTED_PATTERNS = (
    (r"\bspeciali[sz]e[sd]?\b", "specialization claim"),
    (r"\bknown for\b", "reputation claim"),
    (r"\b(cater|caters|catering) to\b", "customer-preference claim"),
    (r"\b(satisfied|happy|loyal|regular) customers?\b", "customer-sentiment claim"),
    (r"\b(popular|renowned|trusted|well[- ]known)\b", "popularity or reputation claim"),
    (r"\b(high|premium|excellent|superior|top[- ]quality)[- ]quality\b", "product-quality claim"),
    (r"\b(quality products?|best quality|finest quality)\b", "product-quality claim"),
    (r"\b(affordable|competitive|reasonable|lowest) prices?\b", "pricing claim"),
    (r"\b(discounts?|special deals?)\b", "promotion or pricing claim"),
    (r"\b(wide|diverse|extensive|large|vast) (selection|range|collection|variety)\b", "selection-size claim"),
    (r"\b(array|variety) of (products|items|clothing|garments)\b", "selection-size claim"),
    (r"\b(various|different) (fashion )?preferences\b", "customer-preference claim"),
    (r"\b(boutique|fabric (shop|store)|designer store|wholesale store|manufacturer|online store)\b", "unverified business-category claim"),
    (r"\b(vibrant|bustling|prime|heart of) (locality|neighbou?rhood|area|location)\b", "unsupported location description"),
    (r"\b(deliver(y|ies)|home delivery|online order(ing)?)\b", "unverified service claim"),
)

# Languages for which the output will be in a non-Latin script.  For these
# languages the identity checks (name / category / location) cannot rely on
# exact English-string matching because Granite translates or transliterates
# the saved values.  We perform a best-effort Latin-script presence check
# instead of a hard rejection (see _check_identity_non_english for details).
_NON_ENGLISH_LANGUAGES = frozenset({"Tamil", "Hindi"})


def _has_latin_substring(needle: str, haystack: str) -> bool:
    """Return True if the normalised *needle* appears anywhere in *haystack*.

    Both are casefold-normalised before comparison.  This is used for the
    best-effort check on non-English output where Granite may keep proper
    nouns in their original Latin form inside an otherwise Tamil/Hindi profile.
    """
    return _norm_field(needle) in _norm_field(haystack)


def validate_business_profile_output(text: str, vendor: dict):
    """Return (is_valid, issues); only blocks clear unsupported-claim patterns.

    For English profiles all three identity checks (name, category, location)
    are hard requirements — the profile is rejected if any is absent.

    For Tamil and Hindi profiles the unsupported-claim patterns still apply
    (they are English-only regexes so they will not fire on non-Latin script,
    but they will catch any stray English promotional phrases).  The identity
    checks become best-effort: if the saved Latin-script value still appears
    in the output (Granite often keeps proper nouns in their original form)
    the check passes silently; if the value is absent the check is *skipped*
    rather than raising an issue, because the model may have legitimately
    transliterated or translated it in accordance with the prompt instructions.
    The empty-text check applies for all languages.
    """
    if not isinstance(text, str) or not text.strip():
        return False, ["The generated profile is empty. Please generate it again."]

    language = (vendor.get("language") or "English").strip()
    is_non_english = language in _NON_ENGLISH_LANGUAGES

    issues = []

    # ── Unsupported-claim patterns (apply for all languages) ──────────────
    # These are English-only regex patterns.  On Tamil/Hindi output they will
    # not match non-Latin script and will not produce false positives.  They
    # will still catch any stray English promotional phrases that Granite might
    # insert alongside translated text.
    for pattern, label in _UNSUPPORTED_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            issues.append(
                f"Remove or verify the unsupported {label}. "
                f"Matched wording: '{match.group(0)}'."
            )

    # ── Identity checks ───────────────────────────────────────────────────
    # For English: hard requirement — reject if absent.
    # For Tamil / Hindi: best-effort Latin presence check — skip (not fail)
    # if the saved Latin form is not found, because the model is allowed to
    # transliterate or translate proper nouns per the prompt instructions.
    text_norm = _norm_field(text)

    name = (vendor.get("business_name") or "").strip()
    if name:
        name_present = _norm_field(name) in text_norm
        if not name_present:
            if not is_non_english:
                issues.append(
                    "The generated profile does not include the saved business name."
                )
            # For non-English: absence is acceptable (transliteration/translation).

    # Category: require at least one significant category token to appear as a
    # whole word *outside* the business name.  For non-English output the token
    # regex uses simple casefold matching without \b word-boundary anchors near
    # non-Latin characters, to avoid false failures from Unicode boundary issues.
    category = (vendor.get("vendor_type") or "").strip()
    if category:
        tokens = _category_tokens(category)
        text_cf = text.casefold()
        text_without_name = text_cf
        if name:
            text_without_name = text_cf.replace(_norm_field(name), " ", 1)

        if is_non_english:
            # Best-effort: check if any token appears as a Latin substring
            # anywhere in the output (without word-boundary anchors, which
            # break on non-Latin Unicode characters).
            category_present = tokens and any(
                tok in text_without_name for tok in tokens
            )
            # Absence is acceptable for non-English: skip rather than reject.
        else:
            # English: strict word-boundary check.
            category_present = tokens and any(
                re.search(r"\b" + re.escape(tok) + r"\b", text_without_name)
                for tok in tokens
            )
            if not category_present:
                issues.append(
                    "The generated profile does not include the saved business category."
                )

    location = (vendor.get("location") or "").strip()
    if location:
        location_present = _norm_field(location) in text_norm
        if not location_present:
            if not is_non_english:
                issues.append(
                    "The generated profile does not include the saved location."
                )
            # For non-English: absence is acceptable.

    return not issues, issues
