"""Regression tests for digitalization checklist validation."""
import pytest
from checklist_validation import validate_checklist_output, validate_checklist_quality


def vendor(products="apple, mango, banana, carrot, potato"):
    return {"business_name": "Test Vendor", "vendor_type": "Retail",
            "location": "Test Area", "products": products}


class TestInventedProductDetection:
    def test_blocks_unlisted_known_products(self):
        valid, issues = validate_checklist_output(
            "1. Take photos of your avocados and figs.", vendor())
        assert not valid
        assert any("avocado" in issue.lower() for issue in issues)
        assert any("fig" in issue.lower() for issue in issues)

    def test_allows_listed_products_and_plural_forms(self):
        valid, issues = validate_checklist_output(
            "1. Take photos of your apples, mangoes, and bananas.", vendor())
        assert valid, issues

    def test_empty_product_list_does_not_crash(self):
        valid, issues = validate_checklist_output(
            "1. Take clear photos of your products.", vendor(products=""))
        assert valid, issues


class TestAssumedServices:
    @pytest.mark.parametrize("phrase", [
        "Define your delivery zones.", "Set estimated arrival times.",
        "Set up order tracking for customer orders.", "Enable shipping options.",
    ])
    def test_blocks_delivery_assumptions(self, phrase):
        valid, issues = validate_checklist_output(f"1. {phrase}", vendor())
        assert not valid
        assert any("delivery" in issue.lower() for issue in issues)

    def test_blocks_online_ordering_without_condition(self):
        valid, issues = validate_checklist_output(
            "1. Set up an online ordering system.", vendor())
        assert not valid
        assert any("online ordering" in issue.lower() for issue in issues)

    def test_allows_conditional_online_ordering(self):
        valid, issues = validate_checklist_output(
            "1. If you plan to accept online orders, consider a simple order form.", vendor())
        assert valid, issues

    def test_blocks_website_assumption(self):
        valid, issues = validate_checklist_output(
            "1. Update your website with current product information.", vendor())
        assert not valid
        assert any("website" in issue.lower() for issue in issues)

    def test_allows_conditional_website_recommendation(self):
        valid, issues = validate_checklist_output(
            "1. If you have a website, update its contact information.", vendor())
        assert valid, issues

    def test_blocks_payment_gateway(self):
        valid, issues = validate_checklist_output(
            "1. Integrate a payment gateway for online payments.", vendor())
        assert not valid
        assert any("payment gateway" in issue.lower() for issue in issues)

    def test_blocks_inventory_software(self):
        valid, issues = validate_checklist_output(
            "1. Install inventory management software to track stock.", vendor())
        assert not valid
        assert any("inventory" in issue.lower() for issue in issues)


class TestCustomerBehaviorClaims:
    @pytest.mark.parametrize("claim", [
        "Most customers prefer cashless payments nowadays.",
        "Urban buyers opt for digital payments.",
        "There is growing demand for organic products.",
        "Customers expect online ordering.",
    ])
    def test_blocks_unsupported_behavior_claims(self, claim):
        valid, issues = validate_checklist_output(f"1. {claim}", vendor())
        assert not valid
        assert any("customer" in issue.lower() or "behavior" in issue.lower()
                   or "trend" in issue.lower() for issue in issues)


class TestOutcomeGuarantees:
    @pytest.mark.parametrize("claim", [
        "This will increase your sales.", "This will attract more customers.",
        "This will boost your revenue.", "This will grow your business.",
    ])
    def test_blocks_guarantees(self, claim):
        valid, issues = validate_checklist_output(f"1. {claim}", vendor())
        assert not valid
        assert any("guarantee" in issue.lower() for issue in issues)


class TestAssumedTools:
    def test_blocks_whatsapp_without_declaration(self):
        valid, issues = validate_checklist_output(
            "1. Post on WhatsApp Business daily.", vendor(), declared_tools=[])
        assert not valid
        assert any("whatsapp" in issue.lower() for issue in issues)

    def test_allows_whatsapp_when_declared_case_insensitively(self):
        valid, issues = validate_checklist_output(
            "1. Post on WhatsApp Business daily.", vendor(),
            declared_tools=["WHATSAPP BUSINESS"])
        assert valid, issues

    def test_allows_conditional_whatsapp_recommendation(self):
        valid, issues = validate_checklist_output(
            "1. If you don't already have WhatsApp Business, consider setting it up.", vendor())
        assert valid, issues

    def test_blocks_google_profile_update_without_declaration(self):
        valid, issues = validate_checklist_output(
            "1. Update your Google Business Profile with new hours.", vendor())
        assert not valid
        assert any("google" in issue.lower() for issue in issues)


class TestConditionalContext:
    def test_unrelated_condition_does_not_excuse_assumption(self):
        checklist = ("1. If you have time, arrange the counter. "
                     "Update your website with current prices.")
        valid, issues = validate_checklist_output(checklist, vendor())
        assert not valid
        assert any("website" in issue.lower() for issue in issues)


class TestChecklistQuality:
    def test_accepts_five_concise_sequential_steps(self):
        checklist = """\
1. Take clear photos of your products and save them on your phone.
2. Display your UPI QR code where customers can easily see it.
3. Maintain a simple digital list of your products and prices.
4. Create a business profile with your location and contact details.
5. Ask customers for feedback to understand their experience.
"""
        valid, issues = validate_checklist_quality(checklist)
        assert valid
        assert issues == []

    def test_rejects_excessively_long_step(self):
        steps = [
            "1. Take clear photos of your products and save them.",
            "2. Display your UPI QR code clearly.",
            "3. Keep a simple digital price list.",
            "4. Record daily sales in a simple notebook.",
            "5. " + " ".join(["systematic advancement"] * 40),
        ]
        valid, issues = validate_checklist_quality("\n".join(steps))
        assert not valid
        assert any("words" in issue.lower() for issue in issues)

    def test_rejects_repeated_phrases(self):
        repeated = " ".join(["keep your business details updated"] * 5)
        checklist = "\n".join([
            "1. Take photos of your products and save them.",
            "2. Display your QR code clearly to customers.",
            "3. Maintain a simple record of your daily sales.",
            "4. Keep a list of your products and prices.",
            f"5. {repeated}",
        ])
        valid, issues = validate_checklist_quality(checklist)
        assert not valid
        assert issues

    def test_rejects_nonsequential_numbering(self):
        checklist = "\n".join([
            "1. Take clear photos of all your products.",
            "2. Display your QR code near the counter.",
            "3. Maintain a simple list of current prices.",
            "5. Record daily sales in a small notebook.",
            "6. Ask customers for feedback about service.",
        ])
        valid, issues = validate_checklist_quality(checklist)
        assert not valid
        assert any("sequentially" in issue.lower() for issue in issues)

    def test_rejects_empty_checklist(self):
        valid, issues = validate_checklist_quality("")
        assert not valid
        assert any("empty" in issue.lower() for issue in issues)

    def test_rejects_wrong_number_of_steps(self):
        valid, issues = validate_checklist_quality(
            "1. Take clear photos of your products and save them.")
        assert not valid
        assert "5–7" in issues[0]
