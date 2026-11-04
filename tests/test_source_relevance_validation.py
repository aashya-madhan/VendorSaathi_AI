"""Test suite for source-relevance and evidence-grounding validation.

Ensures answers about Udyam use only Udyam sources, not BHIM/GeM/SVANidhi sources.
"""
import pytest
from scheme_answer_validation import validate_scheme_answer


def test_udyam_question_with_relevant_udyam_passages():
    """Valid case: Udyam question answered with Udyam evidence."""
    question = "What does Udyam documents say about registration?"
    answer = (
        "According to the Benefits of Udyam Registration document dated February 2021, "
        "Udyam Registration is totally free. There is no fee charged for the registration process. "
        "Verify current fee status on udyamregistration.gov.in."
    )
    passages = [
        "Udyam Registration is totally free. There is no fee charged for the registration process."
    ]
    hits = [
        {
            "source": "Benefits_of_Udyam_Registration.pdf",
            "page": 14,
            "text": passages[0],
            "score": 0.85,
        }
    ]
    
    is_valid, issues = validate_scheme_answer(answer, question, passages, hits)
    assert is_valid, f"Should accept Udyam answer with Udyam evidence: {issues}"


def test_udyam_question_with_bhim_passages_rejected():
    """Invalid case: Udyam question answered with BHIM evidence - must reject."""
    question = "What does Udyam documents say about registration?"
    answer = (
        "To register for Udyam, you need:\n"
        "- Aadhaar Card of business owner\n"
        "- Business PAN Card\n"
        "- Active bank account details\n"
        "Provisional registration is issued immediately, with final verification within 24 hours.\n"
        "Register at udyamregistration.gov.in"
    )
    passages = [
        "To register on BHIM, download the BHIM app and link your bank account. "
        "Set a UPI PIN to complete registration.",
        "For merchant QR code, you need to register as a merchant and generate your UPI QR code.",
    ]
    hits = [
        {
            "source": "BHIM_Official_FAQs.pdf",
            "page": 2,
            "text": passages[0],
            "score": 0.65,
        },
        {
            "source": "BHIM_UPI_Merchant_QR_Guidelines_2026.pdf",
            "page": 55,
            "text": passages[1],
            "score": 0.60,
        },
    ]
    
    is_valid, issues = validate_scheme_answer(answer, question, passages, hits)
    assert not is_valid, "Should reject Udyam question answered with BHIM evidence"
    
    # Check that source mismatch is detected
    source_mismatch_found = any("Source mismatch" in issue for issue in issues)
    assert source_mismatch_found, f"Should detect source mismatch, got: {issues}"
    
    # Check that it mentions BHIM in the error
    bhim_mentioned = any("BHIM" in issue for issue in issues)
    assert bhim_mentioned, f"Should mention BHIM in error, got: {issues}"


def test_udyam_question_with_mixed_irrelevant_passages():
    """Invalid case: Udyam question with GeM + SVANidhi evidence."""
    question = "What are Udyam registration requirements?"
    answer = "Udyam registration requires GST number and bank account details."
    passages = [
        "GeM seller registration requires valid GST number and PAN card.",
        "PM SVANidhi provides working capital loans to street vendors.",
    ]
    hits = [
        {"source": "seller-registration-pre-requisites-v1.2.pdf", "page": 1, "text": passages[0], "score": 0.5},
        {"source": "PM_SVANidhi_Scheme_Guidelines_2025.pdf", "page": 4, "text": passages[1], "score": 0.4},
    ]
    
    is_valid, issues = validate_scheme_answer(answer, question, passages, hits)
    assert not is_valid, "Should reject Udyam question with GeM/SVANidhi evidence"
    
    source_mismatch_found = any("Source mismatch" in issue for issue in issues)
    assert source_mismatch_found, f"Should detect source mismatch: {issues}"


def test_unsupported_aadhaar_pan_bank_claims():
    """Reject Aadhaar/PAN/bank requirements not in evidence."""
    question = "What documents are needed for Udyam?"
    answer = (
        "For Udyam registration, you must provide:\n"
        "1. Aadhaar Card of the business owner\n"
        "2. PAN Card of the business\n"
        "3. Bank account details"
    )
    passages = [
        "Udyam Registration is a simple online process for MSMEs in India."
    ]
    hits = [
        {"source": "Udyam_Official_Information.pdf", "page": 1, "text": passages[0], "score": 0.7}
    ]
    
    is_valid, issues = validate_scheme_answer(answer, question, passages, hits)
    assert not is_valid, "Should reject unsupported Aadhaar/PAN/bank claims"
    
    # Check specific patterns detected
    aadhaar_found = any("Aadhaar" in issue for issue in issues)
    pan_found = any("PAN" in issue for issue in issues)
    bank_found = any("bank account" in issue for issue in issues)
    
    assert aadhaar_found or pan_found or bank_found, f"Should detect document requirement fabrication: {issues}"


def test_unsupported_24_hour_processing_claims():
    """Reject 24-hour processing timeline not in evidence."""
    question = "How long does Udyam registration take?"
    answer = (
        "Udyam registration is processed within 24 hours. "
        "You receive provisional registration immediately, and final verification is completed within 24 hours."
    )
    passages = [
        "Udyam Registration can be completed online at udyamregistration.gov.in."
    ]
    hits = [
        {"source": "Udyam_Official_Information.pdf", "page": 1, "text": passages[0], "score": 0.6}
    ]
    
    is_valid, issues = validate_scheme_answer(answer, question, passages, hits)
    assert not is_valid, "Should reject unsupported 24-hour processing claim"
    
    timeline_found = any("24-hour" in issue or "processing timeline" in issue for issue in issues)
    assert timeline_found, f"Should detect timeline fabrication: {issues}"


def test_unsupported_provisional_registration_claim():
    """Reject provisional registration claim not in evidence."""
    question = "How does Udyam registration work?"
    answer = "After submitting your application, you receive provisional registration immediately."
    passages = [
        "Udyam Registration is an online registration process for MSMEs."
    ]
    hits = [
        {"source": "Benefits_of_Udyam_Registration.pdf", "page": 2, "text": passages[0], "score": 0.65}
    ]
    
    is_valid, issues = validate_scheme_answer(answer, question, passages, hits)
    assert not is_valid, "Should reject provisional registration claim"
    
    provisional_found = any("provisional registration" in issue for issue in issues)
    assert provisional_found, f"Should detect provisional registration claim: {issues}"


def test_incorrect_udyam_portal_urls():
    """Reject malformed Udyam portal URLs."""
    test_cases = [
        ("udaymregistration.gov.in", "malformed (udaym instead of udyam)"),
        ("www.udyam.com", "incorrect domain (.com instead of .gov.in)"),
        ("udyam.in", "incomplete domain"),
    ]
    
    for bad_url, description in test_cases:
        question = "What is the Udyam portal?"
        answer = f"You can register at {bad_url}"
        passages = ["The official Udyam portal provides registration services."]
        hits = [
            {"source": "Udyam_Official_Information.pdf", "page": 1, "text": passages[0], "score": 0.8}
        ]
        
        is_valid, issues = validate_scheme_answer(answer, question, passages, hits)
        assert not is_valid, f"Should reject {description}: {bad_url}"
        
        url_error_found = any("URL" in issue or "malformed" in issue for issue in issues)
        assert url_error_found, f"Should detect URL error for {bad_url}: {issues}"


def test_valid_udyam_free_registration_response():
    """Existing valid Udyam free-registration response must still pass."""
    question = "Is Udyam registration free?"
    answer = (
        "According to the Benefits of Udyam Registration document dated February 2021, "
        "Udyam Registration is described as 'totally free.' There is no registration fee charged. "
        "Historical evidence from February 2021 indicates registration was free at that time. "
        "Verify current fee status on the official portal: udyamregistration.gov.in"
    )
    passages = [
        "Udyam Registration is totally free. No registration fee is charged for the entire process."
    ]
    hits = [
        {
            "source": "Benefits_of_Udyam_Registration.pdf",
            "page": 14,
            "text": passages[0],
            "score": 0.90,
        }
    ]
    
    is_valid, issues = validate_scheme_answer(answer, question, passages, hits)
    assert is_valid, f"Should accept valid free-registration response: {issues}"


def test_bhim_question_with_bhim_evidence_valid():
    """Valid case: BHIM question answered with BHIM evidence."""
    question = "How do I link my bank account in BHIM?"
    answer = (
        "According to BHIM Official FAQs: "
        "To link your bank account, open the BHIM app, select your bank from the list, "
        "and verify your mobile number registered with the bank."
    )
    passages = [
        "To link a bank account in BHIM, open the app, select your bank, "
        "and verify using your bank-registered mobile number."
    ]
    hits = [
        {
            "source": "BHIM_Official_FAQs.pdf",
            "page": 2,
            "text": passages[0],
            "score": 0.85,
        }
    ]
    
    is_valid, issues = validate_scheme_answer(answer, question, passages, hits)
    assert is_valid, f"Should accept BHIM answer with BHIM evidence: {issues}"


def test_gem_question_with_gem_evidence_valid():
    """Valid case: GeM question answered with GeM evidence."""
    question = "What are GeM seller registration requirements?"
    answer = (
        "According to the GeM seller registration prerequisites document, "
        "sellers need a valid PAN card and GST registration to complete the registration process."
    )
    passages = [
        "GeM seller registration requires valid PAN card, GST registration number, "
        "and bank account details for payment processing."
    ]
    hits = [
        {
            "source": "seller-registration-pre-requisites-v1.2.pdf",
            "page": 1,
            "text": passages[0],
            "score": 0.88,
        }
    ]
    
    is_valid, issues = validate_scheme_answer(answer, question, passages, hits)
    assert is_valid, f"Should accept GeM answer with GeM evidence: {issues}"


def test_svanidhi_question_with_svanidhi_evidence_valid():
    """Valid case: SVANidhi question answered with SVANidhi evidence."""
    question = "What are the loan amounts under PM SVANidhi?"
    answer = (
        "According to PM SVANidhi Scheme Guidelines dated September 2025, "
        "the scheme provides working capital loans in three tranches: "
        "₹15,000, ₹25,000, and ₹50,000."
    )
    passages = [
        "PM SVANidhi provides working capital term loans in three tranches: "
        "first tranche of ₹15,000, second tranche of ₹25,000, and third tranche of ₹50,000."
    ]
    hits = [
        {
            "source": "PM_SVANidhi_Scheme_Guidelines_2025.pdf",
            "page": 4,
            "text": passages[0],
            "score": 0.92,
        }
    ]
    
    is_valid, issues = validate_scheme_answer(answer, question, passages, hits)
    assert is_valid, f"Should accept SVANidhi answer with SVANidhi evidence: {issues}"


def test_correct_udyam_url_accepted():
    """Accept correct Udyam portal URL."""
    question = "Where can I register for Udyam?"
    answer = "You can register at the official portal: udyamregistration.gov.in"
    passages = ["Udyam Registration can be completed at the official portal."]
    hits = [
        {"source": "Udyam_Official_Information.pdf", "page": 1, "text": passages[0], "score": 0.8}
    ]
    
    is_valid, issues = validate_scheme_answer(answer, question, passages, hits)
    assert is_valid, f"Should accept correct udyamregistration.gov.in URL: {issues}"
