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


def validate_business_profile_output(text: str, vendor: dict):
    """Return (is_valid, issues); only blocks clear unsupported-claim patterns."""
    if not isinstance(text, str) or not text.strip():
        return False, ["The generated profile is empty. Please generate it again."]

    issues = []
    for pattern, label in _UNSUPPORTED_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            issues.append(
                f"Remove or verify the unsupported {label}. "
                f"Matched wording: '{match.group(0)}'."
            )

    # Exact profile facts should not be fabricated or silently replaced.
    # Name and location: normalise whitespace and punctuation spacing before
    # checking, so that saved values like "Rocky  textiles" (double space) or
    # "Porur , Chennai" (space before comma) still match Granite output that
    # normalises those to "Rocky Textiles" / "Porur, Chennai".
    text_norm = _norm_field(text)

    name = (vendor.get("business_name") or "").strip()
    if name and _norm_field(name) not in text_norm:
        issues.append("The generated profile does not include the saved business name.")

    # Category: require at least one significant category token to appear as a
    # whole word *outside* the business name.  Checking outside the name prevents
    # a category word that coincidentally forms part of the business name (e.g.
    # "textiles" in "Rocky Textiles") from satisfying the check on its own.
    # Requiring only one token (rather than all) tolerates natural reformulations
    # such as "clothing store" for "Clothing & Textiles" while still catching
    # outputs that contain no category-related word at all.
    category = (vendor.get("vendor_type") or "").strip()
    if category:
        tokens = _category_tokens(category)
        # Build a version of the text with the (normalised) business name removed,
        # so we check for category words in the descriptive part of the sentence.
        text_cf = text.casefold()
        text_without_name = text_cf
        if name:
            text_without_name = text_cf.replace(_norm_field(name), " ", 1)
        if tokens and not any(
            re.search(r"\b" + re.escape(tok) + r"\b", text_without_name)
            for tok in tokens
        ):
            issues.append("The generated profile does not include the saved business category.")

    location = (vendor.get("location") or "").strip()
    if location and _norm_field(location) not in text_norm:
        issues.append("The generated profile does not include the saved location.")

    return not issues, issues
