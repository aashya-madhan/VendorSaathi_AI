"""Deterministic validation for government scheme Q&A answers.

Blocks unsupported legal claims, fabricated benefits, invented requirements,
hallucinated regulatory details, and source-question mismatches.
"""
import re
from typing import Tuple, List, Dict, Any


# Patterns for processing time/timeline fabrication
_TIMELINE_FABRICATION_PATTERNS = (
    (r"\b(within|in|takes?).{0,20}(24|twenty[\s-]four)\s*hours?\b", "24-hour processing claim"),
    (r"\b(within|in|takes?).{0,20}(48|forty[\s-]eight)\s*hours?\b", "48-hour processing claim"),
    (r"\b(within|in|takes?).{0,20}\d+\s*(days?|weeks?|months?)\b", "specific processing timeline claim"),
    (r"\bimmediate(ly)?\s+(issued|provided|granted|approved)\b", "immediate processing claim"),
    (r"\binstant(ly)?\s+(approved|issued|granted)\b", "instant processing claim"),
    (r"\bprovisional\s+registration\b", "provisional registration claim"),
    (r"\bfinal\s+(verification|approval).{0,30}(24|48)\s*hours?\b", "final verification timeline"),
)

# Patterns for malformed/incorrect portal URLs
_URL_VALIDATION_PATTERNS = (
    (r"\budaym(?:registration)?\.gov\.in\b", "malformed Udyam URL (udaym instead of udyam)"),
    (r"www\.udyam\.(?:com|in|org)\b", "incorrect Udyam domain (should be udyamregistration.gov.in)"),
    (r"\budyam\.in\b", "incomplete Udyam domain (should be udyamregistration.gov.in)"),
)

# Patterns for unsupported legal/regulatory claims
_LEGAL_CLAIM_PATTERNS = (
    (r"\b(replaces?|replaced|replacing)\b.*(shops? act|trade licen[cs]e|municipal|local registration)", "unverified replacement of existing registration"),
    (r"\budyam\b.*(replaces?|instead of|in place of).*(shops? act|trade licen[cs]e)", "Udyam replacement claim"),
    # Match mandatory claims only when they are making the claim, not when quoting evidence about free/optional registration
    # Exclude cases where the sentence explains it's NOT mandatory or discusses whether it's mandatory
    (r"\budyam\s+(is|registration\s+is)\s+(mandatory|compulsory|legally\s+required|required\s+by\s+law)\b", "mandatory registration claim"),
    (r"\bmust\s+register\s+(for|with|under)\s+udyam\b", "mandatory registration claim"),
    (r"\budyam\b.{0,20}(legal\s+requirement|legal\s+obligation)\b", "mandatory registration claim"),
    (r"\bunder (section|act|provision|law) \d+", "specific legal provision citation"),
    (r"\bas per (section|act|provision) \d+", "specific legal provision citation"),
)

# Patterns for fabricated benefits
_BENEFIT_FABRICATION_PATTERNS = (
    (r"\b(automatic|automatically).{0,30}(insurance|coverage|policy|protection)", "automatic insurance benefit claim"),
    (r"\b(provides?|gives?|includes?).{0,30}(insurance|coverage|policy)", "insurance provision claim"),
    (r"\b(free|subsidized).{0,20}(insurance|health|medical|accident).{0,20}(coverage|policy)", "insurance benefit claim"),
    (r"\b(guaranteed|assured|automatic).{0,20}(loan|credit|funding)", "guaranteed financing claim"),
    (r"\b(priority|preferential).{0,20}(treatment|access|consideration).{0,30}(bank|loan|credit)", "priority lending claim without source"),
    (r"\btax\s+(exemption|waiver|relief|benefit)", "tax benefit claim"),
    (r"\b(subsidies|subsidy|grant).{0,30}automatic", "automatic subsidy claim"),
    (r"\breceive.{0,20}(subsidies|subsidy)", "subsidy receipt claim"),
)

# Patterns for invented eligibility/requirements
_REQUIREMENT_FABRICATION_PATTERNS = (
    (r"\b(must have|requires?|need to have).{0,40}(minimum|at least).{0,40}(turnover|revenue|sales|income).{0,40}(rs|₹|rupees)[\s.]*\d+", "specific turnover requirement"),
    (r"\b(eligibility|eligible).{0,40}(turnover|revenue|sales).{0,40}(below|under|less than|up to).{0,40}(rs|₹|rupees)[\s.]*\d+", "specific turnover threshold"),
    (r"\b(fee|fees|charges?|cost)\s+(is|are|of).{0,20}(rs|₹|rupees)[\s.]*\d+", "specific fee amount"),
    (r"\b(processing time|takes?|within).{0,30}\d+\s*(days?|weeks?|months?)", "specific processing timeline"),
    (r"\b(valid for|validity|expires? after).{0,20}\d+\s*(years?|months?)", "specific validity period"),
    (r"\b(required documents?|must submit|need to provide):\s*\d+\.", "numbered document requirement list"),
)

# Patterns for category/business-type transformations
_CATEGORY_TRANSFORMATION_PATTERNS = (
    (r"\bboutique\b", "boutique business-type claim", True),  # (pattern, description, check_question)
    (r"\bfabric\s+(shops?|stores?)\b", "fabric retail claim", True),
    (r"\bwholesale\b", "wholesale business claim", False),  # Always block, not query-dependent
    (r"\bmanufacturer\b", "manufacturer claim", False),
    (r"\be-commerce\b", "e-commerce business claim", False),
)


def _has_insufficient_evidence(answer: str, retrieved_passages: List[str]) -> bool:
    """Return True if answer makes claims about benefits/fees not supported by passages.
    
    This checks if the answer discusses specific benefits or fee structures that
    aren't mentioned in the evidence, not just document names or source citations.
    """
    answer_lower = answer.lower()
    passages_text = " ".join(retrieved_passages).lower()
    
    # Check for benefit CLAIMS (not just document names containing "benefit")
    # Look for patterns like "provides benefits", "benefit is", "benefits include"
    # But EXCLUDE document citations like "from the Benefits of Udyam document"
    benefit_claim_match = re.search(
        r"\b(provides?|gives?|offers?|includes?|grants?)\s+\w*\s*benefits?\b|"
        r"\bbenefits?\s+(are|is|include)",
        answer_lower
    )
    
    # Exclude citations: if "benefit" appears near citation words like "document", "from", "according to"
    is_document_citation = bool(re.search(
        r"(from|in|according to|retrieved from|evidence from)\s+.{0,30}benefits?\s+of",
        answer_lower
    ))
    
    claims_benefits = bool(benefit_claim_match) and not is_document_citation
    passages_describe_benefits = "benefit" in passages_text or "advantage" in passages_text
    
    # Only flag if answer CLAIMS benefits but passages don't discuss benefits
    if claims_benefits and not passages_describe_benefits:
        return True
    
    # For fee/cost questions: Only flag if answer discusses specific fees but passages mention nothing about costs
    # Allow explanations of "free" registration when evidence confirms "free"
    # Catch patterns like "fee is X", "cost of", "free of cost", etc.
    discusses_fees = bool(re.search(
        r"\b(fee|fees|cost|costs|charge|charges)\s+(is|are|of)|"
        r"\bfree\s+of\s+(cost|charge)",
        answer_lower
    ))
    passages_describe_fees = any(term in passages_text for term in ("fee", "cost", "charge", "free", "paid", "payment"))
    
    if discusses_fees and not passages_describe_fees:
        return True
    
    return False


def _check_source_relevance(answer: str, question: str, retrieved_hits: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Check if retrieved sources match the question topic.
    
    Returns (is_relevant, error_message).
    If sources are relevant: (True, "")
    If sources are mismatched: (False, "descriptive error")
    """
    if not retrieved_hits:
        return True, ""  # Empty results already handled elsewhere
    
    q_lower = question.lower()
    
    # Define topic keywords and their required sources
    topic_checks = [
        {
            "name": "Udyam",
            "question_keywords": ["udyam"],
            "required_source_keywords": ["udyam"],
            "excluded_source_keywords": ["bhim", "upi", "svanidhi", "gem"],
        },
        {
            "name": "GeM",
            "question_keywords": ["gem", "government e-marketplace", "government e marketplace"],
            "required_source_keywords": ["seller", "gem", "catalog"],
            "excluded_source_keywords": ["bhim", "upi", "svanidhi", "udyam registration"],
        },
        {
            "name": "PM SVANidhi",
            "question_keywords": ["svanidhi", "sva nidhi", "street vendor loan"],
            "required_source_keywords": ["svanidhi"],
            "excluded_source_keywords": ["bhim", "upi", "gem"],
        },
        {
            "name": "BHIM/UPI",
            "question_keywords": ["bhim", "upi", "merchant qr", "payment"],
            "required_source_keywords": ["bhim", "upi", "qr"],
            "excluded_source_keywords": ["gem seller", "udyam registration", "svanidhi loan"],
        },
    ]
    
    # Check each topic
    for topic in topic_checks:
        # Does the question ask about this topic?
        asks_topic = any(kw in q_lower for kw in topic["question_keywords"])
        
        if not asks_topic:
            continue
        
        # Check all retrieved passages
        sources_text = " ".join(
            f"{hit.get('source', '')} {hit.get('text', '')}".lower()
            for hit in retrieved_hits
        )
        
        # Do sources contain the required keywords?
        has_required = any(kw in sources_text for kw in topic["required_source_keywords"])
        
        # Do sources contain excluded (wrong-topic) keywords?
        has_excluded = any(kw in sources_text for kw in topic["excluded_source_keywords"])
        
        # If question is about this topic but sources are from wrong topics
        if has_excluded and not has_required:
            retrieved_sources = set(hit.get("source", "unknown") for hit in retrieved_hits)
            return False, (
                f"Source mismatch: Question asks about {topic['name']}, but retrieved "
                f"passages are from: {', '.join(sorted(retrieved_sources))}. "
                f"These sources do not contain {topic['name']} information."
            )
    
    return True, ""


# Patterns for Aadhaar/PAN/bank account requirement fabrication
_DOCUMENT_REQUIREMENT_PATTERNS = (
    (r"\b(aadhaar|aadhar)\s+(card|number)\b", "Aadhaar requirement"),
    (r"\bpan\s+(card|number)\b", "PAN card requirement"),
    (r"\bbank\s+account\b.{0,30}\b(required|mandatory|needed|must have)", "bank account requirement"),
    (r"\b(must|need to|required to)\s+(submit|provide|have).{0,30}\b(aadhaar|aadhar|pan)\b", "document submission requirement"),
)


def validate_scheme_answer(
    answer: str, 
    question: str, 
    retrieved_passages: List[str],
    retrieved_hits: List[Dict[str, Any]] = None
) -> Tuple[bool, List[str]]:
    """
    Return (is_valid, blocking_issues).
    
    Args:
        answer: Generated answer text
        question: Original user question
        retrieved_passages: List of passage text strings used as context
        retrieved_hits: List of hit dicts with source/page/text metadata (optional but recommended)
        
    Returns:
        (True, []) if valid
        (False, [issue1, issue2, ...]) if invalid
    """
    if not isinstance(answer, str) or not answer.strip():
        return False, ["The generated answer is empty."]
    
    issues: List[str] = []
    answer_lower = answer.lower()
    
    # CRITICAL: Check source-question relevance FIRST
    if retrieved_hits:
        is_relevant, relevance_error = _check_source_relevance(answer, question, retrieved_hits)
        if not is_relevant:
            issues.append(relevance_error)
            # Return immediately - no point checking other patterns if sources are completely wrong
            return False, issues
    
    # Check for unsupported document requirements (Aadhaar, PAN, bank)
    for pattern, description in _DOCUMENT_REQUIREMENT_PATTERNS:
        match = re.search(pattern, answer_lower, re.IGNORECASE)
        if match:
            # Check if the requirement is actually in the evidence
            evidence_text = " ".join(retrieved_passages).lower()
            if not re.search(pattern, evidence_text, re.IGNORECASE):
                issues.append(
                    f"Unsupported {description}. Matched: '{match.group(0)}'. "
                    "Document requirements must be explicitly stated in retrieved sources."
                )
    
    # Check for timeline/processing fabrication
    for pattern, description in _TIMELINE_FABRICATION_PATTERNS:
        match = re.search(pattern, answer_lower, re.IGNORECASE)
        if match:
            # Check if the timeline is in the evidence
            evidence_text = " ".join(retrieved_passages).lower()
            if not re.search(pattern, evidence_text, re.IGNORECASE):
                issues.append(
                    f"Unsupported {description}. Matched: '{match.group(0)}'. "
                    "Processing timelines must be explicitly stated in retrieved sources."
                )
    
    # Check for malformed URLs
    for pattern, description in _URL_VALIDATION_PATTERNS:
        match = re.search(pattern, answer_lower, re.IGNORECASE)
        if match:
            issues.append(
                f"Malformed or incorrect URL detected: {description}. Matched: '{match.group(0)}'. "
                "Portal URLs must be accurate and verified."
            )
    
    # Check for unsupported legal/regulatory claims
    for pattern, description in _LEGAL_CLAIM_PATTERNS:
        match = re.search(pattern, answer_lower, re.IGNORECASE)
        if match:
            issues.append(
                f"Unsupported {description}. Matched: '{match.group(0)}'. "
                "Legal requirements must be explicitly stated in retrieved sources."
            )
    
    # Check for fabricated benefits
    for pattern, description in _BENEFIT_FABRICATION_PATTERNS:
        match = re.search(pattern, answer_lower, re.IGNORECASE)
        if match:
            issues.append(
                f"Unsupported {description}. Matched: '{match.group(0)}'. "
                "Benefits must be explicitly listed in retrieved sources."
            )
    
    # Check for invented requirements
    for pattern, description in _REQUIREMENT_FABRICATION_PATTERNS:
        match = re.search(pattern, answer_lower, re.IGNORECASE)
        if match:
            issues.append(
                f"Unsupported {description}. Matched: '{match.group(0)}'. "
                "Requirements must be explicitly stated in retrieved sources."
            )
    
    # Check for category transformations from vendor context
    for item in _CATEGORY_TRANSFORMATION_PATTERNS:
        pattern, description, check_question = item
        match = re.search(pattern, answer_lower, re.IGNORECASE)
        if match:
            # Category claims are acceptable if they appear in the question (for query-dependent patterns)
            if check_question and re.search(pattern, question.lower(), re.IGNORECASE):
                continue  # User asked about this category, so it's acceptable
            issues.append(
                f"Unsupported {description}. Matched: '{match.group(0)}'. "
                "Do not infer business categories from vendor context."
            )
    
    # Check for insufficient evidence (answer makes claims passages don't support)
    if _has_insufficient_evidence(answer, retrieved_passages):
        issues.append(
            "The answer appears to make claims not supported by the retrieved passages. "
            "Verify all statements are grounded in the provided evidence."
        )
    
    return not issues, issues
