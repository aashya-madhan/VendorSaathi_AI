"""Validation for digitalization checklist output."""
import re
from typing import List, Tuple


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(value).lower())).strip()


def _singularize_token(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith(("ches", "shes", "xes", "zes", "sses")):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        return token[:-1]
    return token


def _tokens(value: str) -> List[str]:
    return [_singularize_token(t) for t in re.findall(r"[a-z0-9]+", _normalize(value))]


def _contains_phrase(text: str, phrase: str) -> bool:
    haystack = " ".join(_tokens(text))
    needle = " ".join(_tokens(phrase))
    return bool(needle) and f" {needle} " in f" {haystack} "


def validate_checklist_output(checklist: str, vendor: dict,
                              declared_tools: list = None) -> Tuple[bool, List[str]]:
    """Return (is_valid, blocking_issues) for a generated checklist."""
    if not isinstance(checklist, str) or not checklist.strip():
        return False, ["Checklist is empty"]
    if not isinstance(vendor, dict):
        return False, ["Vendor profile must be a dictionary"]

    declared = {_normalize(t) for t in (declared_tools or []) if str(t).strip()}
    issues = []
    issues.extend(_check_invented_products(checklist, vendor))
    issues.extend(_check_assumed_services(checklist, vendor, declared))
    issues.extend(_check_customer_behavior_claims(checklist))
    issues.extend(_check_outcome_guarantees(checklist))
    issues.extend(_check_assumed_tools(checklist, declared))
    return len(issues) == 0, issues


def _check_invented_products(checklist: str, vendor: dict) -> List[str]:
    """Targeted checks for common product terms; not general entity recognition."""
    products = str(vendor.get("products", "") or "")
    candidates = [
        "avocado", "fig", "dragonfruit", "kiwi", "pomegranate",
        "quinoa", "chia", "exotic", "imported", "organic",
        "premium", "specialty", "gourmet",
    ]
    return [
        f"Mentions '{item}' which is not in the vendor's saved product list. "
        "Only reference products explicitly listed in the profile."
        for item in candidates
        if _contains_phrase(checklist, item) and not _contains_phrase(products, item)
    ]


def _match_contexts(text: str, pattern: str):
    """Yield a match and only its local sentence/line context."""
    for match in re.finditer(pattern, text, re.IGNORECASE):
        starts = [
            text.rfind("\n", 0, match.start()),
            text.rfind(".", 0, match.start()),
            text.rfind(";", 0, match.start()),
        ]
        start = max(starts) + 1
        ends = [
            p for p in (
                text.find("\n", match.end()),
                text.find(".", match.end()),
                text.find(";", match.end()),
            ) if p != -1
        ]
        end = min(ends) if ends else len(text)
        yield match, text[start:end]


def _is_conditional(text: str, pattern: str) -> bool:
    """A condition must occur in the same sentence/line as the matched phrase."""
    markers = (
        r"\bif\b", r"\bconsider\b", r"\bcould\b", r"\bcan\b",
        r"\bmay\b", r"\bmight\b", r"\bwhen\b", r"\bonce\b", r"\bin case\b",
    )
    return any(
        re.search(marker, context, re.IGNORECASE)
        for _, context in _match_contexts(text, pattern)
        for marker in markers
    )


def _check_assumed_services(checklist: str, vendor: dict, declared_tools: set) -> List[str]:
    issues = []
    delivery_patterns = [
        (r"\bdelivery\s+(?:zone|area|time|schedule|service)s?\b", "delivery zones/schedules"),
        (r"\bestimated\s+arrival\b", "estimated arrival times"),
        (r"\bdelivery\s+radius\b", "delivery radius"),
        (r"\bfree\s+delivery\b", "free delivery claims"),
        (r"\bshipping\s+(?:option|method|cost)s?\b", "shipping options"),
        (r"\border\s+tracking\b", "order tracking"),
        (r"\btrack\s+(?:your|customer|the)?\s*orders?\b", "order tracking"),
        (r"\bdispatch\s+(?:status|updates?)\b", "dispatch updates"),
    ]
    for pattern, description in delivery_patterns:
        if re.search(pattern, checklist, re.IGNORECASE):
            issues.append(
                f"Assumes delivery service exists ({description}). "
                "Confirm delivery is offered before recommending delivery-specific features."
            )

    ordering_patterns = [
        (r"\bonline\s+ordering\s+(?:system|platform|portal)\b", "online ordering system"),
        (r"\baccept\s+(?:online|direct)\s+orders?\b", "accepting online orders"),
        (r"\border\s+management\s+(?:system|software)\b", "order management system"),
        (r"\bcustomer\s+order\s+portal\b", "customer order portal"),
    ]
    for pattern, description in ordering_patterns:
        if re.search(pattern, checklist, re.IGNORECASE) and not _is_conditional(checklist, pattern):
            issues.append(
                f"Assumes online ordering capability exists ({description}). "
                "Use conditional phrasing, such as 'If you plan to accept online orders...'."
            )

    website_patterns = [
        (r"\bupdate\s+(?:your|the)\s+website\b", "website updates"),
        (r"\bwebsite\s+(?:content|design|layout)\b", "website content"),
        (r"\badd\s+.{0,40}\s+to\s+(?:your|the)\s+website\b", "adding to website"),
        (r"\b(?:your|the)\s+website\b", "website use"),
    ]
    for pattern, description in website_patterns:
        if re.search(pattern, checklist, re.IGNORECASE) and not _is_conditional(checklist, pattern):
            issues.append(
                f"Assumes website exists ({description}). "
                "Use conditional phrasing, such as 'If you have a website...'."
            )

    payment_patterns = [
        (r"\bintegrate\s+.{0,30}\bpayment\s+gateway\b", "payment gateway integration"),
        (r"\bpayment\s+gateway\s+(?:integration|setup)\b", "payment gateway setup"),
        (r"\bonline\s+payment\s+processing\b", "online payment processing"),
        (r"\bmerchant\s+account\s+with\s+(?:a\s+)?payment\b", "merchant account setup"),
    ]
    for pattern, description in payment_patterns:
        if re.search(pattern, checklist, re.IGNORECASE):
            issues.append(
                f"Assumes need for payment gateway ({description}). "
                "Verify the vendor's setup first; a simpler payment option may be more appropriate."
            )

    if re.search(r"\binventory\s+(?:management\s+)?(?:software|system|app)\b",
                 checklist, re.IGNORECASE):
        issues.append(
            "Recommends inventory software without establishing the vendor's scale or need. "
            "Consider a simple digital product list first."
        )
    return issues


def _check_customer_behavior_claims(checklist: str) -> List[str]:
    patterns = [
        r"\b(?:most|many|majority of)\s+(?:the\s+)?(?:customers|buyers|people|users)\s+(?:prefer|expect|want|choose)\b",
        r"\bcustomers?\s+(?:are\s+looking|look|search)\s+for\b",
        r"\b(?:nowadays|today),?\s+(?:most|many|customers?|buyers?|people)\s+",
        r"\burban\s+buyers?\s+(?:prefer|opt|choose)\b",
        r"\bcustomers?\s+(?:demand|expect)\s+",
        r"\bgrowing\s+(?:trend|demand)\s+(?:for|in|of)\b",
        r"\bpeople\s+(?:increasingly|generally)\s+(?:prefer|choose|expect)\b",
    ]
    if any(re.search(p, checklist, re.IGNORECASE) for p in patterns):
        return ["Makes an unsupported customer behavior or trend claim. "
                "Do not assume customer preferences or behavior without evidence."]
    return []


def _check_outcome_guarantees(checklist: str) -> List[str]:
    patterns = [
        r"\bthis\s+will\s+increase\s+(?:sales|revenue|income|earnings|profit)\b",
        r"\bwill\s+increase\s+(?:your\s+)?(?:sales|revenue|income|earnings|profit)\b",
        r"\bwill\s+(?:attract|bring|get)\s+(?:more|new)\s+customers\b",
        r"\bguaranteed?\s+(?:to\s+)?(?:increase|improve|boost|generate)\b",
        r"\bwill\s+(?:boost|improve|grow|expand)\s+(?:your\s+)?(?:business|sales|revenue)\b",
        r"\bgenerate\s+(?:more\s+)?(?:leads?|sales|revenue)\b",
        r"\bwill\s+result\s+in\s+(?:more|increased|higher)\s+(?:sales|revenue|customers)\b",
    ]
    if any(re.search(p, checklist, re.IGNORECASE) for p in patterns):
        return ["Makes an unsupported outcome guarantee. "
                "Use possibility language rather than promising results."]
    return []


def _check_assumed_tools(checklist: str, declared_tools: set) -> List[str]:
    checks = [
        ({"whatsapp business", "whatsapp"}, r"\bon\s+whatsapp\s+business\b", "WhatsApp Business"),
        ({"google business profile", "google business"},
         r"\bupdate\s+(?:your|the)\s+google\s+business\s+profile\b", "Google Business Profile"),
        ({"social media", "facebook", "instagram"},
         r"\bpost\s+on\s+(?:your\s+)?(?:social\s+media|facebook|instagram)\b", "social media account"),
    ]
    issues = []
    for accepted, pattern, name in checks:
        if (re.search(pattern, checklist, re.IGNORECASE)
                and not (accepted & declared_tools)
                and not _is_conditional(checklist, pattern)):
            issues.append(
                f"Assumes {name} is already active without confirmation. "
                f"Use conditional phrasing, such as 'If you don't already have {name}...'."
            )
    return issues


def validate_checklist_quality(checklist: str, max_words_per_step: int = 55) -> Tuple[bool, List[str]]:
    """Require 5–7 concise steps with sequential numbering and limited repetition."""
    if not isinstance(checklist, str) or not checklist.strip():
        return False, ["Checklist is empty."]
    if not isinstance(max_words_per_step, int) or max_words_per_step < 1:
        return False, ["max_words_per_step must be a positive integer."]

    matches = list(re.finditer(r"^\s*(\d+)[.)]\s+(.+?)\s*$", checklist, re.MULTILINE))
    steps = [(int(m.group(1)), m.group(2).strip()) for m in matches]
    if not 5 <= len(steps) <= 7:
        return False, [f"Expected 5–7 steps, but received {len(steps)}."]

    issues = []
    numbers = [n for n, _ in steps]
    if numbers != list(range(1, len(steps) + 1)):
        issues.append(f"Steps must be numbered sequentially from 1 to {len(steps)}.")

    for index, (_, step) in enumerate(steps, 1):
        words = re.findall(r"\b[\w'-]+\b", step, re.UNICODE)
        if len(words) < 6:
            issues.append(f"Step {index} is too short to provide a useful instruction.")
            continue
        if len(words) > max_words_per_step:
            issues.append(
                f"Step {index} contains {len(words)} words. "
                f"Keep each step at or below {max_words_per_step} words."
            )
        normalized = [w.lower() for w in words]
        if len(normalized) >= 15:
            counts = {}
            for word in normalized:
                if len(word) > 3:
                    counts[word] = counts.get(word, 0) + 1
            if counts and max(counts.values()) > 6:
                issues.append(f"Step {index} contains excessive word repetition.")
        if len(normalized) >= 12:
            phrases = [tuple(normalized[i:i + 4]) for i in range(len(normalized) - 3)]
            if len(phrases) != len(set(phrases)):
                issues.append(f"Step {index} contains repeated phrases.")
    return len(issues) == 0, issues
