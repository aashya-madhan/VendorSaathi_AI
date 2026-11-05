"""Tests for government scheme answer validation.

All tests use mocked answers - no live Granite API calls.
"""
import pytest
from scheme_answer_validation import validate_scheme_answer


# Sample retrieved passages (realistic RAG output)
UDYAM_PASSAGES = [
    "The process for Udyam Registration is fully digitalized and Paperless. Registration Process is totally free. No Costs or Fees are to be paid to anyone.",
    "An enterprise shall be classified as a micro, small or medium enterprise on the basis of investment and turnover criteria.",
]

GEM_PASSAGES = [
    "To add a product on GeM: 1. Open the Catalog tab. 2. Select Add New Product from the dropdown menu.",
    "GeM seller registration requires Aadhaar and PAN for primary sellers.",
]

EMPTY_PASSAGES = []


class TestLegalClaimDetection:
    """Test detection of unsupported legal/regulatory claims."""
    
    def test_blocks_udyam_replaces_shops_act(self):
        answer = "Udyam registration replaces the Shops Act registration requirement."
        valid, issues = validate_scheme_answer(answer, "", UDYAM_PASSAGES)
        assert not valid
        assert any("replacement" in issue.lower() for issue in issues)
    
    def test_blocks_mandatory_registration_claim(self):
        answer = "Udyam registration is mandatory for all MSMEs under Section 7."
        valid, issues = validate_scheme_answer(answer, "", UDYAM_PASSAGES)
        assert not valid
        assert any("mandatory" in issue.lower() for issue in issues)
    
    def test_blocks_specific_legal_provision_citation(self):
        answer = "Under Section 27 of the Act, registration is compulsory."
        valid, issues = validate_scheme_answer(answer, "", UDYAM_PASSAGES)
        assert not valid
        assert any("legal provision" in issue.lower() for issue in issues)
    
    def test_allows_optional_registration_language(self):
        answer = "Udyam registration is available for MSMEs. It is voluntary."
        valid, issues = validate_scheme_answer(answer, "", UDYAM_PASSAGES)
        assert valid
        assert not issues


class TestBenefitFabricationDetection:
    """Test detection of fabricated benefits."""
    
    def test_blocks_automatic_insurance_claim(self):
        answer = "Udyam registration automatically provides insurance coverage."
        valid, issues = validate_scheme_answer(answer, "", UDYAM_PASSAGES)
        assert not valid
        assert any("insurance" in issue.lower() for issue in issues)
    
    def test_blocks_free_insurance_claim(self):
        answer = "You get free health insurance policy with Udyam registration."
        valid, issues = validate_scheme_answer(answer, "", UDYAM_PASSAGES)
        assert not valid
        assert any("insurance" in issue.lower() for issue in issues)
    
    def test_blocks_guaranteed_loan_claim(self):
        answer = "Udyam provides guaranteed loan access from banks."
        valid, issues = validate_scheme_answer(answer, "", UDYAM_PASSAGES)
        assert not valid
        assert any("guaranteed" in issue.lower() or "financing" in issue.lower() for issue in issues)
    
    def test_blocks_tax_exemption_claim(self):
        answer = "Udyam registration gives tax exemption to small businesses."
        valid, issues = validate_scheme_answer(answer, "", UDYAM_PASSAGES)
        assert not valid
        assert any("tax" in issue.lower() for issue in issues)
    
    def test_blocks_automatic_subsidy_claim(self):
        answer = "Registered enterprises automatically receive government subsidies."
        valid, issues = validate_scheme_answer(answer, "", UDYAM_PASSAGES)
        assert not valid
        assert any("subsidy" in issue.lower() or "automatic" in issue.lower() for issue in issues)


class TestRequirementFabricationDetection:
    """Test detection of invented requirements."""
    
    def test_blocks_specific_turnover_requirement(self):
        answer = "You must have a minimum turnover of Rs. 5 lakh to register."
        valid, issues = validate_scheme_answer(answer, "", UDYAM_PASSAGES)
        assert not valid
        assert any("turnover" in issue.lower() for issue in issues)
    
    def test_blocks_specific_fee_amount(self):
        answer = "The registration fee is ₹500 for micro enterprises."
        valid, issues = validate_scheme_answer(answer, "", UDYAM_PASSAGES)
        assert not valid
        assert any("fee" in issue.lower() for issue in issues)
    
    def test_allows_free_registration_when_sourced(self):
        answer = "Registration is free according to the official guidelines."
        valid, issues = validate_scheme_answer(answer, "", UDYAM_PASSAGES)
        assert valid
        assert not issues
    
    def test_allows_totally_free_language(self):
        """Test that 'totally free' phrasing is accepted when passages contain it."""
        answer = "The registration process is totally free. No costs or fees are to be paid."
        passages_with_totally_free = [
            "Registration Process is totally free. No Costs or Fees are to be paid to anyone."
        ]
        valid, issues = validate_scheme_answer(answer, "", passages_with_totally_free)
        assert valid
        assert not issues
    
    def test_allows_historical_qualified_free_statement(self):
        """Test that historically-qualified free registration statements are accepted."""
        answer = (
            "According to the February 2021 document, the Udyam registration process is "
            "totally free, and no costs or fees are to be paid. Please verify current fee "
            "information on the official Udyam portal."
        )
        passages_with_free_info = [
            "Registration Process is totally free. No Costs or Fees are to be paid to anyone."
        ]
        valid, issues = validate_scheme_answer(answer, "", passages_with_free_info)
        assert valid
        assert not issues
    
    def test_blocks_specific_processing_time(self):
        answer = "Registration approval takes 7 days after submission."
        valid, issues = validate_scheme_answer(answer, "", UDYAM_PASSAGES)
        assert not valid
        assert any("processing" in issue.lower() or "timeline" in issue.lower() for issue in issues)
    
    def test_blocks_specific_validity_period(self):
        answer = "The Udyam certificate is valid for 5 years."
        valid, issues = validate_scheme_answer(answer, "", UDYAM_PASSAGES)
        assert not valid
        assert any("validity" in issue.lower() for issue in issues)


class TestCategoryTransformationDetection:
    """Test detection of unsupported business category claims."""
    
    def test_blocks_boutique_claim(self):
        answer = "This boutique business should register under Udyam."
        question = "What is Udyam registration?"
        valid, issues = validate_scheme_answer(answer, question, UDYAM_PASSAGES)
        assert not valid
        assert any("boutique" in issue.lower() for issue in issues)
    
    def test_allows_boutique_if_in_question(self):
        answer = "This boutique business should register under Udyam."
        question = "Can my boutique register for Udyam?"
        valid, issues = validate_scheme_answer(answer, question, UDYAM_PASSAGES)
        assert valid  # Category from user question is acceptable
    
    def test_blocks_fabric_store_claim(self):
        answer = "Fabric stores can benefit from Udyam registration."
        question = "What is Udyam?"
        valid, issues = validate_scheme_answer(answer, question, UDYAM_PASSAGES)
        assert not valid
        # Should fail either for category claim or insufficient evidence
        assert len(issues) > 0
    
    def test_blocks_wholesale_claim(self):
        answer = "Wholesale businesses must register separately."
        question = "What is Udyam?"
        valid, issues = validate_scheme_answer(answer, question, UDYAM_PASSAGES)
        assert not valid
        assert any("wholesale" in issue.lower() for issue in issues)


class TestInsufficientEvidenceDetection:
    """Test detection of answers making claims beyond retrieved evidence."""
    
    def test_blocks_benefit_claims_without_benefit_passages(self):
        answer = "Udyam provides several benefits including priority lending and subsidies."
        passages_no_benefits = ["Udyam is a registration portal for MSMEs."]
        valid, issues = validate_scheme_answer(answer, "", passages_no_benefits)
        assert not valid
        assert any("evidence" in issue.lower() or "supported" in issue.lower() for issue in issues)
    
    def test_allows_benefit_claims_with_benefit_passages(self):
        answer = "Benefits of Udyam registration include digital certification."
        passages_with_benefits = [
            "Benefits of taking Udyam Registration: An e-certificate shall be issued online.",
        ]
        valid, issues = validate_scheme_answer(answer, "", passages_with_benefits)
        assert valid
        assert not issues
    
    def test_blocks_fee_claims_without_fee_passages(self):
        answer = "Registration is free of cost."
        passages_no_fee_info = ["Udyam is the official registration system."]
        valid, issues = validate_scheme_answer(answer, "", passages_no_fee_info)
        assert not valid
    
    def test_allows_fee_claims_with_fee_passages(self):
        answer = "Registration is totally free. No costs are to be paid."
        valid, issues = validate_scheme_answer(answer, "", UDYAM_PASSAGES)
        assert valid
        assert not issues


class TestValidAnswers:
    """Test that properly grounded answers pass validation."""
    
    def test_accepts_procedural_answer(self):
        answer = "To add a product on GeM, open the Catalog tab and select Add New Product."
        valid, issues = validate_scheme_answer(answer, "", GEM_PASSAGES)
        assert valid
        assert not issues
    
    def test_accepts_classification_answer(self):
        answer = "Enterprises are classified based on investment and turnover criteria."
        valid, issues = validate_scheme_answer(answer, "", UDYAM_PASSAGES)
        assert valid
        assert not issues
    
    def test_accepts_insufficient_evidence_acknowledgment(self):
        answer = "The retrieved source does not establish specific eligibility criteria. Please verify on the official portal."
        valid, issues = validate_scheme_answer(answer, "", EMPTY_PASSAGES)
        assert valid
        assert not issues
    
    def test_accepts_source_qualified_statement(self):
        answer = "According to the retrieved passage, registration is free. No costs or fees are to be paid."
        valid, issues = validate_scheme_answer(answer, "", UDYAM_PASSAGES)
        assert valid
        assert not issues


class TestEmptyAnswerDetection:
    """Test validation of empty or whitespace-only answers."""
    
    def test_rejects_empty_answer(self):
        valid, issues = validate_scheme_answer("", "", UDYAM_PASSAGES)
        assert not valid
        assert any("empty" in issue.lower() for issue in issues)
    
    def test_rejects_whitespace_only_answer(self):
        valid, issues = validate_scheme_answer("   \n\n   ", "", UDYAM_PASSAGES)
        assert not valid
        assert any("empty" in issue.lower() for issue in issues)
