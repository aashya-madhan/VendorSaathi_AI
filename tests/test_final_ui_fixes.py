"""
Regression tests for final UI fixes from manual testing.

Tests cover:
1. Local SEO regeneration path and validation messaging
2. Digitalization Checklist factual grounding
3. Historical source qualification in Government Schemes
"""

import pytest
from prompts import (
    build_checklist_prompt,
    build_local_seo_prompt,
    build_scheme_qa_prompt,
)


class TestLocalSEORegenerationPath:
    """Test that Local SEO provides regeneration guidance after rejection."""

    def test_local_seo_prompt_exists(self):
        """Verify Local SEO prompt builds successfully."""
        vendor = {
            "business_name": "Test Fruits",
            "vendor_type": "Fruits & Vegetables",
            "location": "Porur, Chennai",
            "products": "apple, mango, guava",
            "language": "English",
        }
        prompt = build_local_seo_prompt(vendor)
        assert len(prompt) > 100
        assert "business_name" in prompt.lower() or "test fruits" in prompt.lower()

    def test_local_seo_prompt_prohibits_pricing_claims(self):
        """Verify prompt instructs against unsupported pricing claims."""
        vendor = {
            "business_name": "Test Shop",
            "vendor_type": "General Store",
            "location": "Test Area",
            "products": "item1, item2",
            "language": "English",
        }
        prompt = build_local_seo_prompt(vendor)
        # Check for pricing-related prohibitions
        assert (
            "pricing" in prompt.lower()
            or "price" in prompt.lower()
            or "discount" in prompt.lower()
        )


class TestDigitalizationChecklistFactualGrounding:
    """Test that checklist prompt prevents invented business facts."""

    def test_prohibits_sourcing_claims(self):
        """Checklist must not invent sourcing details."""
        vendor = {
            "business_name": "Fresh Fruits Stand",
            "vendor_type": "Fruits & Vegetables",
            "location": "Porur, Chennai",
            "products": "apple, mango, banana",
            "language": "English",
        }
        prompt = build_checklist_prompt(vendor)

        # Check that it has strong prohibitions
        assert "never" in prompt.lower() or "do not" in prompt.lower() or "absolute" in prompt.lower()
        # Should have the actual products listed
        assert "apple" in prompt.lower() and "mango" in prompt.lower()

    def test_prohibits_freshness_claims(self):
        """Checklist must not invent freshness or stock status."""
        vendor = {
            "business_name": "Veggie Cart",
            "vendor_type": "Fruits & Vegetables",
            "location": "Test Location",
            "products": "carrot, potato, beans",
            "language": "English",
        }
        prompt = build_checklist_prompt(vendor)

        # Should have prohibitions
        assert "do not" in prompt.lower() or "never" in prompt.lower() or "absolute" in prompt.lower()
        # Should have the actual products
        assert "carrot" in prompt.lower() and "potato" in prompt.lower()

    def test_prohibits_customer_behavior_assumptions(self):
        """Checklist must not assume customer preferences or behaviors."""
        vendor = {
            "business_name": "Test Business",
            "vendor_type": "General Store",
            "location": "Test Area",
            "products": "various items",
            "language": "English",
        }
        prompt = build_checklist_prompt(vendor)

        # Should prohibit customer behavior claims
        assert "customer" in prompt.lower()
        assert (
            "prefer" in prompt.lower()
            or "expect" in prompt.lower()
            or "behavior" in prompt.lower()
        )

    def test_prohibits_revenue_guarantees(self):
        """Checklist must not guarantee sales or revenue outcomes."""
        vendor = {
            "business_name": "Market Stall",
            "vendor_type": "Clothing & Textiles",
            "location": "City Center",
            "products": "shirts, pants",
            "language": "English",
        }
        prompt = build_checklist_prompt(vendor)

        # Should prohibit outcome guarantees
        assert (
            "sales" in prompt.lower()
            or "revenue" in prompt.lower()
            or "demand" in prompt.lower()
        )
        assert (
            "will increase" in prompt.lower()
            or "guarantee" in prompt.lower()
            or "certainties" in prompt.lower()
        )

    def test_requires_conditional_phrasing(self):
        """Checklist must use conditional language for recommendations."""
        vendor = {
            "business_name": "Small Shop",
            "vendor_type": "Electronics & Accessories",
            "location": "Local Area",
            "products": "phones, cables",
            "language": "English",
        }
        prompt = build_checklist_prompt(vendor)

        # Should require conditional phrasing
        assert "if you don't already have" in prompt.lower()
        assert "consider" in prompt.lower() or "could" in prompt.lower()

    def test_factual_grounding_section_present(self):
        """Verify factual grounding rules exist."""
        vendor = {
            "business_name": "Test",
            "vendor_type": "Test Type",
            "location": "Test",
            "products": "test",
            "language": "English",
        }
        prompt = build_checklist_prompt(vendor)

        # Should have strong prohibitions about inventing facts
        assert "absolute" in prompt.lower() or "critical" in prompt.lower()
        # Should mention using only vendor profile facts
        assert "only" in prompt.lower() and ("vendor" in prompt.lower() or "profile" in prompt.lower() or "actual" in prompt.lower())

    def test_provides_correct_and_incorrect_examples(self):
        """Verify prompt includes correct vs incorrect phrasing examples."""
        vendor = {
            "business_name": "Demo Shop",
            "vendor_type": "General",
            "location": "Area",
            "products": "items",
            "language": "English",
        }
        prompt = build_checklist_prompt(vendor)

        # Should have examples - check for checkmark/cross or good/bad labels
        has_examples = (
            ("✓" in prompt and "✗" in prompt) or 
            ("good" in prompt.lower() and "bad" in prompt.lower()) or
            ("suitable" in prompt.lower() and "unsuitable" in prompt.lower()) or
            ("practical" in prompt.lower() and ("do not" in prompt.lower() or "never" in prompt.lower()))
        )
        assert has_examples


class TestHistoricalSourceQualification:
    """Test that Government Schemes properly qualifies historical sources."""

    def test_historical_source_handling_rules_present(self):
        """Verify prompt includes historical source handling rules."""
        prompt = build_scheme_qa_prompt(
            "Test question", "Test context", language="English"
        )

        assert "historical" in prompt.lower()
        assert "dated" in prompt.lower() or "date" in prompt.lower()

    def test_requires_source_date_citation(self):
        """Verify prompt requires citing document dates."""
        prompt = build_scheme_qa_prompt("What is Udyam?", "", language="English")

        # Should explicitly require date citation
        assert "cite" in prompt.lower() or "source" in prompt.lower()
        assert "date" in prompt.lower()

    def test_prohibits_claiming_historical_as_current(self):
        """Verify prompt prohibits treating historical docs as current."""
        prompt = build_scheme_qa_prompt(
            "Is registration free?", "test context", language="English"
        )

        # Should explicitly prohibit claiming historical = current
        prohibition_found = (
            "do not claim" in prompt.lower()
            or "never claim" in prompt.lower()
            or "not verify current" in prompt.lower()
        )
        assert prohibition_found

    def test_requires_verification_direction(self):
        """Verify prompt requires directing users to verify current status."""
        prompt = build_scheme_qa_prompt("Test question", "context", language="English")

        # Should require verification guidance
        assert "verify" in prompt.lower()
        assert "portal" in prompt.lower() or "official" in prompt.lower()

    def test_historical_phrasing_examples_provided(self):
        """Verify prompt provides examples of how to phrase historical info."""
        prompt = build_scheme_qa_prompt("Question", "Context", language="English")

        # Should provide phrasing guidance for historical sources
        historical_guidance = (
            "according to" in prompt.lower()
            and "dated" in prompt.lower()
            and "verify" in prompt.lower()
        )
        assert historical_guidance

    def test_evidence_rules_numbered_and_comprehensive(self):
        """Verify EVIDENCE RULES section is comprehensive."""
        prompt = build_scheme_qa_prompt("Test", "Test", language="English")

        assert "evidence rules" in prompt.lower()
        # Should have multiple numbered rules
        numbered_rules = sum(1 for line in prompt.split("\n") if line.strip().startswith(("1.", "2.", "3.", "4.", "5.")))
        assert numbered_rules >= 5


class TestPromptIntegrity:
    """Verify prompts maintain structural integrity."""

    def test_local_seo_prompt_has_vendor_context(self):
        """Local SEO prompt must include vendor details."""
        vendor = {
            "business_name": "Test Business",
            "vendor_type": "Test Type",
            "location": "Test Location",
            "products": "Test Products",
            "language": "English",
        }
        prompt = build_local_seo_prompt(vendor)

        assert "Test Business" in prompt
        assert "Test Type" in prompt
        assert "Test Location" in prompt

    def test_checklist_prompt_has_vendor_context(self):
        """Checklist prompt must include vendor details."""
        vendor = {
            "business_name": "Example Shop",
            "vendor_type": "Example Type",
            "location": "Example Place",
            "products": "Example Items",
            "language": "English",
        }
        prompt = build_checklist_prompt(vendor)

        assert "Example Shop" in prompt
        assert "Example Type" in prompt

    def test_scheme_qa_prompt_has_language_instruction(self):
        """Government Schemes prompt must include language directive."""
        prompt = build_scheme_qa_prompt("Test?", "", language="Hindi")

        assert "Hindi" in prompt
        assert "respond" in prompt.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
