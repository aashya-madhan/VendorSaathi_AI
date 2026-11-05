"""Regression tests for critical bug fixes from actual UI testing.

Tests the 5 critical bugs identified and fixed:
1. Business Profile validation import
2. Government Schemes false-positive for free registration
3. Local SEO validation for genuinely supported product lists
4. Promo Studio factual grounding
5. Digitalization Checklist conditional phrasing
"""
from business_profile_validation import validate_business_profile_output
from scheme_answer_validation import validate_scheme_answer
from local_seo_validation import validate_local_seo_output
from prompts import build_promo_prompt, build_checklist_prompt


# Test Bug Fix 1: Business Profile import (tested by import working above)

def test_business_profile_validator_importable():
    """Verify validate_business_profile_output can be imported (Bug Fix 1)."""
    # If this test runs, the import worked
    vendor = {"business_name": "Test", "vendor_type": "Food", "location": "Chennai", "products": "Snacks"}
    result, issues = validate_business_profile_output("Test is a Food business in Chennai.", vendor)
    assert isinstance(result, bool)
    assert isinstance(issues, list)


# Test Bug Fix 2: Government Schemes false-positive for free registration

def test_allows_free_registration_explanation():
    """Bug Fix 2: Allow answers explaining that registration is free (not mandatory)."""
    # This was previously blocked because "required" appeared near "Udyam"
    answer = (
        "According to the retrieved evidence from the Benefits of Udyam Registration document, "
        "the Udyam registration process is totally free. No costs or fees are required to be paid."
    )
    question = "Is Udyam registration free?"
    passages = [
        "Registration Process is totally free. No Costs or Fees are to be paid to anyone."
    ]
    
    valid, issues = validate_scheme_answer(answer, question, passages)
    assert valid, f"Should allow free registration explanation. Issues: {issues}"


def test_blocks_actual_mandatory_claim():
    """Bug Fix 2: Continue blocking genuine mandatory registration claims."""
    answer = "Udyam registration is mandatory for all MSMEs under the law."
    question = "Is Udyam registration mandatory?"
    passages = ["Udyam provides benefits to registered MSMEs."]
    
    valid, issues = validate_scheme_answer(answer, question, passages)
    assert not valid, "Should block unsupported mandatory claim"
    assert any("mandatory" in issue.lower() for issue in issues)


def test_blocks_must_register_claim():
    """Bug Fix 2: Block 'must register for Udyam' claims."""
    answer = "All MSMEs must register for Udyam to access government schemes."
    question = "Do I need Udyam registration?"
    passages = ["Udyam registration provides priority lending benefits."]
    
    valid, issues = validate_scheme_answer(answer, question, passages)
    assert not valid, "Should block 'must register' claim"


def test_allows_conditional_registration_language():
    """Bug Fix 2: Allow explanations that registration may be beneficial but not mandatory."""
    answer = (
        "Udyam registration is optional for MSMEs. The process is free and provides "
        "access to priority sector lending."
    )
    question = "Should I register for Udyam?"
    passages = [
        "Registration Process is totally free.",
        "Priority Sector Lending: Banks are mandated to lend to MSMEs. "
        "Udyam registered enterprises get priority access to credit."
    ]
    
    valid, issues = validate_scheme_answer(answer, question, passages)
    assert valid, f"Should allow conditional language. Issues: {issues}"


# Test Bug Fix 3: Local SEO validation for genuinely supported product lists

def test_allows_wide_range_with_multiple_products():
    """Bug Fix 3: Allow 'wide range' when vendor has 5+ distinct products listed."""
    vendor = {
        "business_name": "Rocky Textiles",
        "vendor_type": "Clothing & Textiles",
        "location": "Porur, Chennai",
        "products": "Sarees, kurtis, western dresses, pants, shirts, palazzos"  # 6 products
    }
    # SEO copy that mentions wide range
    seo_text = (
        "Rocky Textiles in Porur, Chennai offers a wide range of clothing including "
        "sarees, kurtis, western dresses, pants, shirts, and palazzos."
    )
    
    valid, issues = validate_local_seo_output(seo_text, vendor)
    # Should NOT block "wide range" because vendor genuinely has 6 products
    range_issues = [i for i in issues if "range/selection" in i.lower()]
    assert not range_issues, f"Should allow 'wide range' with 6 products. Issues: {range_issues}"


def test_blocks_wide_range_with_few_products():
    """Bug Fix 3: Block 'wide range' when vendor has few products."""
    vendor = {
        "business_name": "Small Shop",
        "vendor_type": "Food",
        "location": "Delhi",
        "products": "Samosas, Chai"  # Only 2 products
    }
    seo_text = "Small Shop offers a wide range of snacks and beverages."
    
    valid, issues = validate_local_seo_output(seo_text, vendor)
    # Should block because "wide range" is not supported by 2 products
    assert not valid or any("range/selection" in i.lower() for i in issues), \
        "Should block 'wide range' with only 2 products"


def test_allows_extensive_collection_with_multiple_products():
    """Bug Fix 3: Allow 'extensive collection' with genuinely large product list."""
    vendor = {
        "business_name": "Fashion Hub",
        "vendor_type": "Clothing",
        "location": "Mumbai",
        "products": "T-shirts, Jeans, Shirts, Jackets, Sweaters, Shorts, Skirts"  # 7 products
    }
    seo_text = "Fashion Hub has an extensive collection of clothing for all ages."
    
    valid, issues = validate_local_seo_output(seo_text, vendor)
    collection_issues = [i for i in issues if "range/selection" in i.lower() or "extensive" in i.lower()]
    assert not collection_issues, f"Should allow 'extensive collection' with 7 products. Issues: {collection_issues}"


# Test Bug Fix 4: Promo Studio factual grounding

def test_promo_prompt_prohibits_quality_claims():
    """Bug Fix 4: Verify promo prompt explicitly prohibits quality inventions."""
    vendor = {
        "business_name": "Test Shop",
        "vendor_type": "Clothing",
        "location": "Chennai",
        "products": "Sarees",
        "language": "English"
    }
    prompt = build_promo_prompt(vendor, "Weekend Special")
    
    # Check that prohibitions are in the prompt
    assert "do not invent product qualities" in prompt.lower() or "not allowed" in prompt.lower()
    assert "breathtaking" in prompt.lower() or "premium" in prompt.lower()  # Example of what NOT to do


def test_promo_prompt_shows_allowed_vs_not_allowed():
    """Bug Fix 4: Verify prompt provides clear allowed vs not-allowed examples."""
    vendor = {
        "business_name": "Rocky Textiles",
        "vendor_type": "Clothing",
        "location": "Porur",
        "products": "Sarees, kurtis",
        "language": "English"
    }
    prompt = build_promo_prompt(vendor)
    
    # Should contain guidance on what's allowed vs not allowed
    assert "allowed:" in prompt.lower()
    assert "not allowed:" in prompt.lower()


# Test Bug Fix 5: Digitalization Checklist conditional phrasing

def test_checklist_prompt_requires_conditional_language():
    """Bug Fix 5: Verify checklist prompt requires conditional phrasing."""
    vendor = {
        "business_name": "Test Stall",
        "vendor_type": "Food",
        "location": "Delhi",
        "products": "Snacks",
        "language": "English"
    }
    prompt = build_checklist_prompt(vendor, "Priority: Getting more customers")
    
    # Check for conditional phrasing requirements
    assert "never assume" in prompt.lower() or "do not assume" in prompt.lower()
    assert "if you don't already have" in prompt.lower() or "conditional" in prompt.lower()


def test_checklist_prompt_prohibits_guarantees():
    """Bug Fix 5: Verify checklist prompt prohibits outcome guarantees."""
    vendor = {
        "business_name": "Street Shop",
        "vendor_type": "Clothing",
        "location": "Mumbai",
        "products": "Clothes",
        "language": "English"
    }
    prompt = build_checklist_prompt(vendor)
    
    # Should prohibit guarantees - check for ABSOLUTE PROHIBITION section
    assert "absolute prohibition" in prompt.lower() or "never say" in prompt.lower()
    # Check reminder section mentions outcomes
    assert ("outcomes:" in prompt.lower() and ("could" in prompt.lower() or "might" in prompt.lower() or "may" in prompt.lower())) or ("will" in prompt.lower() and "not" in prompt.lower())


def test_checklist_prompt_requires_possibility_language():
    """Bug Fix 5: Verify checklist prompt requires 'could help' not 'will increase'."""
    vendor = {
        "business_name": "Vendor",
        "vendor_type": "Food",
        "location": "Chennai",
        "products": "Snacks",
        "language": "English"
    }
    prompt = build_checklist_prompt(vendor)
    
    # Should require possibility language - check reminder section
    assert ("could" in prompt.lower() or "might" in prompt.lower() or "may" in prompt.lower())
    # Check it has "not 'will'" guidance
    assert ('not "will"' in prompt.lower() or "use \"could" in prompt.lower() or "✓" in prompt)


def test_checklist_prompt_prohibits_platform_assumptions():
    """Bug Fix 5: Verify checklist doesn't assume WhatsApp Business is already set up."""
    vendor = {
        "business_name": "Small Vendor",
        "vendor_type": "Food",
        "location": "Bangalore",
        "products": "Snacks",
        "language": "English"
    }
    prompt = build_checklist_prompt(vendor)
    
    # Should not assume platforms are set up
    assert "whatsapp" in prompt.lower()  # Mentions WhatsApp
    assert "already in use" in prompt.lower() or "already have" in prompt.lower()  # But conditionally
