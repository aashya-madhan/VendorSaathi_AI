"""Deterministic safety checks for generated Local SEO copy.

Blocking checks catch known unsupported claims, address details, business
attributes, delivery claims, and over-specific product/service mentions.
Non-blocking checks identify SEO/readability improvements. These checks are
not a semantic fact-checker and do not rewrite generated text.
"""
import re
from typing import Dict, List, Tuple


_UNSUPPORTED_CLAIM_PATTERNS = (
    (r"\byour trusted source\b|\btrusted (?:seller|store|source|provider)\b", "unverified trust claim"),
    (r"\breliable (?:products?|selection|range|goods?)\b", "unverified reliability claim"),
    (r"\bquality (?:products?|goods?)\b", "unverified product-quality claim"),
    (r"\bcompetitive prices?\b|\baffordable prices?\b", "unverified pricing claim"),
    (r"\bbest (?:mobile|electronics|computer|gadget|phone)[\w -]*", "unverified superlative claim"),
    (r"\bcutting[- ]edge\b", "unverified product-feature claim"),
    (r"\bfriendly service\b|\bexcellent service\b", "unverified service-quality claim"),
    (r"\bcommitment to (?:excellent|quality|reliable)\b", "unverified business-quality claim"),
    (r"\bspeciali[sz]es in providing\b", "unverified specialization claim"),
    (r"\bwide (?:variety|range) of\b|\bwide selection\b|\bextensive (?:selection|collection|range)\b|\b(?:large|huge|vast) (?:collection|selection|range)\b", "unverified range/selection claim"),
    (r"\ball your tech needs\b|\bone[- ]stop[- ]shop\b", "unverified breadth/positioning claim"),
    (r"\bgo[- ]to shop\b", "unverified promotional positioning claim"),
    (r"\btech enthusiasts\b", "unverified target-customer claim"),
    (r"\bpopular products?\b|\bsatisfied customers?\b", "unverified popularity/customer-satisfaction claim"),
    (r"\bone of the (?:best|leading|top)\b", "unverified ranking claim"),
)

# Broad profile labels do not prove that each specific SKU or product type is sold.
_SPECIFIC_PRODUCT_PATTERNS = (
    (r"\bportable speakers?\b", "portable speakers"),
    (r"\bspeakers?\b", "speakers"),
    (r"\bheadphones?\b|\bearbuds?\b", "headphones/earbuds"),
    (r"\baudio systems?\b", "audio systems"),
    (r"\bwristbands?\b|\bsmartwatches?\b", "wristbands/smartwatches"),
    (r"\bmicrocontroller boards?\b|\bdevelopment boards?\b", "microcontroller/development boards"),
    (r"\blaptops?\b", "laptops"),
    (r"\bcomputer parts?\b", "computer parts"),
    (r"\bkeyboards?\b|\bmice\b|\bcomputer mice\b", "keyboards/mice"),
    (r"\bstorage solutions?\b|\b(ssd|hard drives?)\b", "storage devices"),
    (r"\bmicromax\b", "Micromax-branded products"),
)

_UNSUPPORTED_SERVICE_PATTERNS = (
    (r"\bsmartphone repair\b|\bmobile phone repair\b|\bphone repair\b", "phone repair"),
    (r"\bcomputer repair\b|\blaptop repair\b", "computer/laptop repair"),
    (r"\belectronics wholesale\b|\bwholesale (?:electronics|store|retailer|sales)\b", "wholesale sales"),
    (r"\bdealership\b|\bauthorized dealer\b|\baudio equipment dealer\b", "dealership/authorized-dealer status"),
)

# These are factual business attributes/services, not generic SEO wording.
_UNSUPPORTED_ATTRIBUTE_PATTERNS = (
    (r"\baccessible store\b|\bwheelchair[- ]accessible\b", "accessibility claim"),
    (r"\bwomen['’]s (?:fashion )?retailer\b|\bmen['’]s (?:fashion )?retailer\b|\bkids['’] (?:fashion )?store\b", "customer-demographic/business-attribute claim"),
    (r"\bfabric shop\b|\bfabric store\b", "fabric-retail category claim"),
    (r"\b(?:clothing )?boutique\b", "boutique category claim"),
    (r"\bopen 24 hours\b|\b24[- ]hour service\b", "opening-hours claim"),
)

_UNSUPPORTED_DELIVERY_PATTERNS = (
    (r"\bhome delivery\b|\bdoorstep delivery\b|\bsame[- ]day delivery\b|\bfree delivery\b", "delivery-service claim"),
    (r"\bwe deliver\b|\bdelivery available\b|\bdelivers? to your door\b", "delivery-service claim"),
    (r"\bshipping available\b|\bships? nationwide\b|\bonline orders?\b", "shipping/online-order claim"),
)

# Explicit street-level details are not established by a city/area-only profile.
_STREET_ADDRESS_PATTERN = re.compile(
    r"\b(?:on|at|located on|situated on)\s+"
    r"((?:[a-z0-9][a-z0-9.'’-]*\s+){0,5}"
    r"(?:road|rd\.?|street|st\.?|avenue|ave\.?|lane|ln\.?|"
    r"main road|highway|hwy\.?|cross street|1st cross|2nd cross))\b",
    re.IGNORECASE,
)
_PIN_CODE_PATTERN = re.compile(r"\b(?:pin(?:code)?\s*[:#-]?\s*)?[1-9][0-9]{5}\b", re.IGNORECASE)


def _normalise(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def _profile_supports(pattern: str, profile_text: str) -> bool:
    return bool(re.search(pattern, profile_text, re.IGNORECASE))


def get_local_seo_warnings(text: str) -> List[str]:
    """Return non-blocking SEO/readability suggestions for a non-empty draft."""
    if not isinstance(text, str) or not text.strip():
        return []

    warnings: List[str] = []
    if re.search(r"\bnear me\b", text, re.IGNORECASE):
        warnings.append(
            "The keyword 'near me' is generic. Add the saved city/area to the keyword, "
            "for example, 'clothing store in Porur, Chennai'."
        )

    for sentence in re.split(r"(?<=[.!?])\s+", text):
        words = re.findall(r"\b[\w'-]+\b", sentence)
        if len(words) > 35:
            warnings.append(
                f"A sentence is long ({len(words)} words); consider splitting it for readability."
            )
            break

    return warnings


def validate_local_seo_output(text: str, vendor: Dict) -> Tuple[bool, List[str]]:
    """Return (is_valid, blocking_issues); SEO/readability suggestions do not block."""
    if not isinstance(text, str) or not text.strip():
        return False, ["The generated Local SEO draft is empty."]

    vendor = vendor or {}
    products = _normalise(vendor.get("products", ""))
    profile_text = _normalise(" ".join(
        str(vendor.get(key, "") or "")
        for key in ("business_name", "vendor_type", "location", "products", "services", "address")
    ))
    content = _normalise(text)
    issues: List[str] = []

    # Count distinct products in the saved profile
    # Split by commas, "and", "&" to get individual product names
    product_list = re.split(r'[,&]|\band\b', products)
    distinct_products = [p.strip() for p in product_list if p.strip() and len(p.strip()) > 2]
    has_multiple_products = len(distinct_products) >= 5

    for pattern, description in _UNSUPPORTED_CLAIM_PATTERNS:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            # Special handling for range/selection claims - allow if genuinely supported
            if "range/selection claim" in description and has_multiple_products:
                # Vendor has 5+ distinct products, allow "wide range" description
                continue
            issues.append(
                f"Remove or verify the {description}. Matched wording: '{match.group(0)}'."
            )

    for pattern, item in _SPECIFIC_PRODUCT_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE) and not re.search(pattern, products, re.IGNORECASE):
            issues.append(f"'{item}' is not explicitly listed in the saved products/services profile.")

    for pattern, service in _UNSUPPORTED_SERVICE_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE) and not re.search(pattern, products, re.IGNORECASE):
            issues.append(f"'{service}' is not listed as a service in the saved profile.")

    for pattern, description in _UNSUPPORTED_ATTRIBUTE_PATTERNS:
        match = re.search(pattern, content, re.IGNORECASE)
        if match and not _profile_supports(pattern, profile_text):
            issues.append(
                f"Remove or verify the {description}. Matched wording: '{match.group(0)}'."
            )

    for pattern, description in _UNSUPPORTED_DELIVERY_PATTERNS:
        match = re.search(pattern, content, re.IGNORECASE)
        if match and not _profile_supports(pattern, profile_text):
            issues.append(
                f"Remove or verify the {description}. Matched wording: '{match.group(0)}'."
            )

    for match in _STREET_ADDRESS_PATTERN.finditer(content):
        street_detail = _normalise(match.group(1))
        if street_detail not in profile_text:
            issues.append(
                f"Street-level address '{match.group(1).strip()}' is not present in the saved business profile."
            )

    for match in _PIN_CODE_PATTERN.finditer(content):
        pin = match.group(0)
        if pin not in profile_text:
            issues.append(f"PIN code '{pin}' is not present in the saved business profile.")

    if re.search(r"\[(?:insert|business name|location|product|keyword)[^\]]*\]", text, re.IGNORECASE):
        issues.append("The draft contains an unresolved placeholder.")

    unique_issues = list(dict.fromkeys(issues))
    return not unique_issues, unique_issues
