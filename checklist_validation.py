"""
Validation for digitalization checklist output.

Blocks recommendations that:
- Mention products not in vendor profile
- Assume delivery/online ordering without confirmation
- Assume payment systems without confirmation
- Make unsupported customer behavior claims
- Guarantee revenue/sales outcomes
"""

import re
from typing import Tuple, List


def validate_checklist_output(checklist: str, vendor: dict, declared_tools: list = None) -> Tuple[bool, List[str]]:
    """
    Validate checklist content against vendor profile.
    
    Args:
        checklist: Generated checklist text
        vendor: Vendor profile dict
        declared_tools: List of tools user declared they already have
        
    Returns:
        (is_valid, issues) where issues is a list of blocking problems
    """
    if not isinstance(checklist, str) or not checklist.strip():
        return False, ["Checklist is empty"]
    
    issues: List[str] = []
    checklist_lower = checklist.lower()
    
    # Get vendor's actual products
    vendor_products = vendor.get("products", "").lower().strip()
    if vendor_products:
        # Split by common delimiters
        actual_products = set()
        for product in re.split(r'[,;&]+|\band\b', vendor_products):
            product = product.strip()
            if len(product) > 2:  # Ignore very short fragments
                actual_products.add(product)
    else:
        actual_products = set()
    
    declared_tools = declared_tools or []
    declared_tools_lower = [t.lower() for t in declared_tools]
    
    # Check for invented products
    issues.extend(_check_invented_products(checklist_lower, actual_products, vendor))
    
    # Check for assumed services
    issues.extend(_check_assumed_services(checklist_lower, vendor, declared_tools_lower))
    
    # Check for customer behavior claims
    issues.extend(_check_customer_behavior_claims(checklist_lower))
    
    # Check for outcome guarantees
    issues.extend(_check_outcome_guarantees(checklist_lower))
    
    # Check for assumed tools/platforms
    issues.extend(_check_assumed_tools(checklist_lower, declared_tools_lower))
    
    return (len(issues) == 0, issues)


def _check_invented_products(checklist: str, actual_products: set, vendor: dict) -> List[str]:
    """Check if checklist mentions products not in vendor profile."""
    issues = []
    
    # Common product examples that might be invented
    # This is not exhaustive - the prompt should prevent invention
    potential_products = [
        'avocado', 'fig', 'dragonfruit', 'kiwi', 'pomegranate',
        'quinoa', 'chia', 'exotic', 'imported', 'organic',
        'premium', 'specialty', 'gourmet',
    ]
    
    for product in potential_products:
        if product in checklist and product not in vendor.get("products", "").lower():
            issues.append(
                f"Mentions '{product}' which is not in the vendor's saved product list. "
                f"Only reference products explicitly listed in the profile."
            )
    
    return issues


def _check_assumed_services(checklist: str, vendor: dict, declared_tools: list) -> List[str]:
    """Check for assumptions about delivery, online ordering, website, etc."""
    issues = []
    
    # Check for delivery assumptions
    delivery_patterns = [
        (r'\bdelivery\s+(zone|area|time|schedule|service)', 'delivery zones/schedules'),
        (r'\bestimated\s+arrival', 'estimated arrival times'),
        (r'\bdelivery\s+radius', 'delivery radius'),
        (r'\bfree\s+delivery', 'free delivery claims'),
        (r'\bshipping\s+(option|method|cost)', 'shipping options'),
        (r'\border\s+tracking', 'order tracking'),
    ]
    
    for pattern, description in delivery_patterns:
        if re.search(pattern, checklist):
            issues.append(
                f"Assumes delivery service exists ({description}). "
                f"Do not recommend delivery-specific features without confirming the vendor offers delivery."
            )
    
    # Check for online ordering assumptions
    ordering_patterns = [
        (r'\bonline\s+ordering\s+(system|platform|portal)', 'online ordering system'),
        (r'\baccept\s+(online|direct)\s+orders', 'accepting online orders'),
        (r'\border\s+management\s+(system|software)', 'order management system'),
        (r'\bcustomer\s+order\s+portal', 'customer order portal'),
    ]
    
    for pattern, description in ordering_patterns:
        if re.search(pattern, checklist):
            # Only flag if not a conditional recommendation
            if not _is_conditional(checklist, pattern):
                issues.append(
                    f"Assumes online ordering capability exists ({description}). "
                    f"Use conditional phrasing: 'If you plan to accept online orders...'"
                )
    
    # Check for website assumptions
    website_patterns = [
        (r'\bupdate\s+(your|the)\s+website', 'website updates'),
        (r'\bwebsite\s+(content|design|layout)', 'website content'),
        (r'\badd\s+.{0,20}\s+to\s+(your|the)\s+website', 'adding to website'),
    ]
    
    for pattern, description in website_patterns:
        if re.search(pattern, checklist):
            issues.append(
                f"Assumes website exists ({description}). "
                f"Use conditional phrasing: 'If you have a website...'"
            )
    
    # Check for payment gateway assumptions
    payment_patterns = [
        (r'\bintegrate\s+.{0,15}payment\s+gateway', 'payment gateway integration'),
        (r'\bpayment\s+gateway\s+(integration|setup)', 'payment gateway setup'),
        (r'\bonline\s+payment\s+processing', 'online payment processing'),
        (r'\bmerchant\s+account\s+with\s+payment', 'merchant account setup'),
    ]
    
    for pattern, description in payment_patterns:
        if re.search(pattern, checklist):
            issues.append(
                f"Assumes need for payment gateway ({description}). "
                f"This is unsuitable for a small street vendor without verifying their setup. "
                f"Prefer simpler options like UPI QR codes."
            )
    
    # Check for inventory software assumptions
    if re.search(r'\binventory\s+(management\s+)?(software|system|app)', checklist):
        issues.append(
            "Recommends inventory software without establishing the vendor's scale or need. "
            "For small vendors, suggest simpler methods like maintaining a digital product list."
        )
    
    return issues


def _check_customer_behavior_claims(checklist: str) -> List[str]:
    """Check for unsupported claims about customer preferences or behaviors."""
    issues = []
    
    behavior_patterns = [
        (r'\b(most|many|majority of)\s+(customers|buyers|people|users)\s+(prefer|expect|want|choose)', 
         'customer preference claims'),
        (r'\bcustomers?\s+(are\s+looking|look|search)\s+for', 'customer search behavior'),
        (r'\b(nowadays|today),?\s+(most|many|customers?|buyers?|people)\s+', 'generalized behavior claims'),
        (r'\burban\s+buyers?\s+(prefer|opt|choose)', 'urban buyer behavior'),
        (r'\bcustomers?\s+(demand|expect)\s+', 'customer demand claims'),
        (r'\bgrowing\s+(trend|demand)\s+(for|in|of)', 'trend claims without evidence'),
    ]
    
    for pattern, description in behavior_patterns:
        if re.search(pattern, checklist):
            issues.append(
                f"Makes unsupported customer behavior claim ({description}). "
                f"Do not assume customer preferences, expectations, or behaviors without evidence."
            )
    
    return issues


def _check_outcome_guarantees(checklist: str) -> List[str]:
    """Check for guaranteed outcomes about sales, revenue, customers."""
    issues = []
    
    # Strong outcome guarantees
    guarantee_patterns = [
        (r'\bthis\s+will\s+increase\s+(sales|revenue|income|earnings|profit)', 'guaranteed sales increase'),
        (r'\bwill\s+increase\s+(your\s+)?(sales|revenue|income|earnings|profit)', 'guaranteed sales increase'),
        (r'\bwill\s+(attract|bring|get)\s+(more|new)\s+customers', 'guaranteed customer acquisition'),
        (r'\bguaranteed?\s+(to\s+)?(increase|improve|boost|generate)', 'explicit guarantee'),
        (r'\bwill\s+(boost|improve|grow|expand)\s+(your\s+)?(business|sales|revenue)', 'guaranteed business growth'),
        (r'\bgenerate\s+(more\s+)?(leads?|sales|revenue)', 'guaranteed lead generation'),
        (r'\bwill\s+result\s+in\s+(more|increased|higher)\s+(sales|revenue|customers)', 'guaranteed results'),
    ]
    
    for pattern, description in guarantee_patterns:
        if re.search(pattern, checklist):
            issues.append(
                f"Makes unsupported outcome guarantee ({description}). "
                f"Use possibility language: 'could help attract customers' not 'will increase sales'."
            )
    
    return issues


def _check_assumed_tools(checklist: str, declared_tools: list) -> List[str]:
    """Check for assumptions about tools/platforms vendor already uses."""
    issues = []
    
    # Tools that should not be assumed unless declared
    tool_checks = [
        ('whatsapp business', r'\bon\s+whatsapp\s+business', 'WhatsApp Business'),
        ('google business profile', r'\bupdate\s+(your|the)\s+google\s+business\s+profile', 'Google Business Profile'),
        ('social media', r'\bpost\s+on\s+(your\s+)?(social\s+media|facebook|instagram)', 'social media account'),
    ]
    
    for tool_key, pattern, tool_name in tool_checks:
        if re.search(pattern, checklist):
            if tool_key not in declared_tools:
                # Check if it's phrased conditionally
                if not _is_conditional(checklist, pattern):
                    issues.append(
                        f"Assumes {tool_name} is already active without confirmation. "
                        f"Use conditional phrasing: 'If you don't already have {tool_name}...'"
                    )
    
    return issues


def _is_conditional(text: str, pattern: str) -> bool:
    """Check if a pattern appears in a conditional context."""
    # Find the match
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return False
    
    # Get surrounding context (up to 100 chars before)
    start = max(0, match.start() - 100)
    context = text[start:match.end()]
    
    # Check for conditional phrases
    conditional_markers = [
        r'\bif\s+you\b',
        r'\bif\s+you\s+(don\'?t|do\s+not)\b',
        r'\bconsider\b',
        r'\byou\s+(could|can|may|might)\b',
        r'\bwhen\s+you\b',
        r'\bonce\s+you\b',
    ]
    
    for marker in conditional_markers:
        if re.search(marker, context, re.IGNORECASE):
            return True
    
    return False


if __name__ == "__main__":
    # Quick self-test
    vendor = {
        "business_name": "Fresh Fruits",
        "vendor_type": "Fruits & Vegetables",
        "location": "Porur, Chennai",
        "products": "apple, mango, banana, carrot, potato",
    }
    
    # Test case 1: Invented product
    bad_checklist_1 = """
    1. Take clear photos of your apples, mangoes, avocados and figs
    2. Set up a Google Business Profile
    """
    valid, issues = validate_checklist_output(bad_checklist_1, vendor)
    print(f"Test 1 (invented products): valid={valid}, issues={len(issues)}")
    for issue in issues:
        print(f"  - {issue}")
    
    # Test case 2: Assumed delivery
    bad_checklist_2 = """
    1. Define your delivery zones and estimated arrival times
    2. Set up order tracking for customers
    """
    valid, issues = validate_checklist_output(bad_checklist_2, vendor)
    print(f"\nTest 2 (assumed delivery): valid={valid}, issues={len(issues)}")
    for issue in issues:
        print(f"  - {issue}")
    
    # Test case 3: Customer behavior
    bad_checklist_3 = """
    1. Most customers prefer cashless payments nowadays
    2. Urban buyers opt for online ordering
    """
    valid, issues = validate_checklist_output(bad_checklist_3, vendor)
    print(f"\nTest 3 (customer behavior): valid={valid}, issues={len(issues)}")
    for issue in issues:
        print(f"  - {issue}")
    
    # Test case 4: Good checklist
    good_checklist = """
    1. If you don't already have a UPI QR code, consider setting one up through your bank's app
    2. Take clear photos of your products (apples, mangoes, bananas, carrots, potatoes)
    3. Consider creating a simple digital price list that you could share with customers
    """
    valid, issues = validate_checklist_output(good_checklist, vendor)
    print(f"\nTest 4 (good checklist): valid={valid}, issues={len(issues)}")
