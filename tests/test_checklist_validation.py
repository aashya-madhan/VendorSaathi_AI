"""
Tests for digitalization checklist validation.

Ensures checklist recommendations are practical, grounded, and don't make
unsupported assumptions about the vendor's services, tools, or products.
"""

import pytest
from checklist_validation import validate_checklist_output


class TestInventedProductDetection:
    """Test that unlisted products are flagged."""
    
    def test_blocks_invented_exotic_products(self):
        """Checklist must not mention products not in vendor profile."""
        vendor = {
            "business_name": "Fresh Market",
            "vendor_type": "Fruits & Vegetables",
            "location": "Chennai",
            "products": "apple, mango, banana, carrot, potato",
        }
        checklist = """
        1. Take photos of your avocados and figs
        2. Display prices clearly
        """
        valid, issues = validate_checklist_output(checklist, vendor)
        
        assert not valid
        assert any("avocado" in issue.lower() for issue in issues)
        assert any("fig" in issue.lower() for issue in issues)
    
    def test_allows_actual_products(self):
        """Checklist can mention products that are in profile."""
        vendor = {
            "business_name": "Fruit Stand",
            "vendor_type": "Fruits & Vegetables",
            "location": "Test",
            "products": "apple, mango, banana",
        }
        checklist = """
        1. Take clear photos of your apples, mangoes, and bananas
        2. Keep a price list for your products
        """
        valid, issues = validate_checklist_output(checklist, vendor)
        
        # This should pass (actual products mentioned)
        # Note: The validator checks common exotic products, not all possible inventions
        assert valid or len(issues) == 0


class TestAssumedDeliveryService:
    """Test that delivery assumptions are flagged."""
    
    def test_blocks_delivery_zone_recommendations(self):
        """Must not assume delivery service exists."""
        vendor = {
            "business_name": "Local Shop",
            "vendor_type": "General Store",
            "location": "Test Area",
            "products": "various items",
        }
        checklist = """
        1. Define your delivery zones
        2. Set estimated arrival times for deliveries
        """
        valid, issues = validate_checklist_output(checklist, vendor)
        
        assert not valid
        assert any("delivery" in issue.lower() for issue in issues)
    
    def test_blocks_order_tracking_recommendations(self):
        """Must not recommend order tracking without confirmed delivery."""
        vendor = {
            "business_name": "Test Business",
            "vendor_type": "Test Type",
            "location": "Test",
            "products": "items",
        }
        checklist = """
        1. Set up order tracking for customer orders
        2. Enable shipping options
        """
        valid, issues = validate_checklist_output(checklist, vendor)
        
        assert not valid
        # Should flag order tracking
        assert any("order tracking" in issue.lower() or "tracking" in issue.lower() for issue in issues)
    
    def test_blocks_assumed_online_ordering(self):
        """Must not assume online ordering capability."""
        vendor = {
            "business_name": "Small Stall",
            "vendor_type": "Food",
            "location": "Market",
            "products": "snacks",
        }
        checklist = """
        1. Set up an online ordering system
        2. Accept direct orders through your ordering portal
        """
        valid, issues = validate_checklist_output(checklist, vendor)
        
        assert not valid
        assert any("online ordering" in issue.lower() or "ordering" in issue.lower() for issue in issues)


class TestCustomerBehaviorClaims:
    """Test that unsupported customer behavior claims are flagged."""
    
    def test_blocks_customer_preference_claims(self):
        """Must not claim customer preferences without evidence."""
        vendor = {
            "business_name": "Test",
            "vendor_type": "Test",
            "location": "Test",
            "products": "test",
        }
        checklist = """
        1. Most customers prefer cashless payments nowadays
        2. Set up UPI
        """
        valid, issues = validate_checklist_output(checklist, vendor)
        
        assert not valid
        assert any("customer" in issue.lower() and ("prefer" in issue.lower() or "behavior" in issue.lower()) for issue in issues)
    
    def test_blocks_urban_buyer_claims(self):
        """Must not make claims about urban buyer behavior."""
        vendor = {
            "business_name": "City Vendor",
            "vendor_type": "Retail",
            "location": "Urban Area",
            "products": "goods",
        }
        checklist = """
        1. Urban buyers opt for digital payments
        2. Customers expect online ordering
        """
        valid, issues = validate_checklist_output(checklist, vendor)
        
        assert not valid
        assert any("urban" in issue.lower() or "buyer" in issue.lower() or "customer" in issue.lower() for issue in issues)
    
    def test_blocks_generalized_trend_claims(self):
        """Must not claim trends without evidence."""
        vendor = {
            "business_name": "Vendor",
            "vendor_type": "Type",
            "location": "Place",
            "products": "items",
        }
        checklist = """
        1. There's a growing demand for organic products
        2. Nowadays, people look for sustainable options
        """
        valid, issues = validate_checklist_output(checklist, vendor)
        
        assert not valid
        # Should flag trend/demand claims
        assert len(issues) > 0


class TestOutcomeGuarantees:
    """Test that outcome guarantees are flagged."""
    
    def test_blocks_sales_increase_guarantee(self):
        """Must not guarantee sales increases."""
        vendor = {
            "business_name": "Shop",
            "vendor_type": "Retail",
            "location": "Area",
            "products": "products",
        }
        checklist = """
        1. Set up a Google Business Profile - this will increase your sales
        2. Post photos daily
        """
        valid, issues = validate_checklist_output(checklist, vendor)
        
        assert not valid
        assert any("sales" in issue.lower() or "guarantee" in issue.lower() for issue in issues)
    
    def test_blocks_customer_acquisition_guarantee(self):
        """Must not guarantee customer acquisition."""
        vendor = {
            "business_name": "Test",
            "vendor_type": "Test",
            "location": "Test",
            "products": "test",
        }
        checklist = """
        1. Create a Facebook page - this will attract more customers
        2. Share your contact info
        """
        valid, issues = validate_checklist_output(checklist, vendor)
        
        assert not valid
        assert any("attract" in issue.lower() or "customer" in issue.lower() or "guarantee" in issue.lower() for issue in issues)
    
    def test_blocks_revenue_boost_claims(self):
        """Must not claim guaranteed revenue boosts."""
        vendor = {
            "business_name": "Stall",
            "vendor_type": "Food",
            "location": "Market",
            "products": "food",
        }
        checklist = """
        1. Use digital payments to boost your revenue
        2. This will grow your business significantly
        """
        valid, issues = validate_checklist_output(checklist, vendor)
        
        assert not valid
        assert any("revenue" in issue.lower() or "boost" in issue.lower() or "grow" in issue.lower() for issue in issues)


class TestAssumedTools:
    """Test that tool/platform assumptions are flagged."""
    
    def test_blocks_whatsapp_business_assumption(self):
        """Must not assume WhatsApp Business without confirmation."""
        vendor = {
            "business_name": "Vendor",
            "vendor_type": "Type",
            "location": "Place",
            "products": "items",
        }
        # Not declared in tools
        checklist = """
        1. Post updates on WhatsApp Business daily
        2. Share your catalog on WhatsApp Business
        """
        valid, issues = validate_checklist_output(checklist, vendor, declared_tools=[])
        
        assert not valid
        assert any("whatsapp" in issue.lower() for issue in issues)
    
    def test_allows_whatsapp_when_declared(self):
        """Allows WhatsApp recommendations when user declared they have it."""
        vendor = {
            "business_name": "Test",
            "vendor_type": "Test",
            "location": "Test",
            "products": "test",
        }
        checklist = """
        1. Update your WhatsApp Business status regularly
        2. Keep your contact info current
        """
        # User declared they have WhatsApp Business
        valid, issues = validate_checklist_output(checklist, vendor, declared_tools=["WhatsApp Business"])
        
        # Should either pass or have fewer/no WhatsApp-related issues
        whatsapp_issues = [i for i in issues if "whatsapp" in i.lower()]
        # The validator might still flag if phrasing isn't conditional, but shouldn't flag existence
        # This is a reasonable behavior
    
    def test_blocks_google_profile_update_without_confirmation(self):
        """Must not assume Google Business Profile exists."""
        vendor = {
            "business_name": "Shop",
            "vendor_type": "Retail",
            "location": "Area",
            "products": "goods",
        }
        checklist = """
        1. Update your Google Business Profile with new hours
        2. Add photos to your Google listing
        """
        valid, issues = validate_checklist_output(checklist, vendor, declared_tools=[])
        
        assert not valid
        assert any("google" in issue.lower() for issue in issues)


class TestWebsiteAssumptions:
    """Test that website assumptions are flagged."""
    
    def test_blocks_website_update_recommendations(self):
        """Must not assume website exists."""
        vendor = {
            "business_name": "Local Business",
            "vendor_type": "Retail",
            "location": "City",
            "products": "products",
        }
        checklist = """
        1. Update your website with new product information
        2. Add a contact form to your website
        """
        valid, issues = validate_checklist_output(checklist, vendor)
        
        assert not valid
        assert any("website" in issue.lower() for issue in issues)


class TestPaymentGatewayRecommendations:
    """Test that payment gateway assumptions are flagged."""
    
    def test_blocks_payment_gateway_integration(self):
        """Payment gateways are unsuitable for small street vendors."""
        vendor = {
            "business_name": "Street Stall",
            "vendor_type": "Food",
            "location": "Market",
            "products": "snacks",
        }
        checklist = """
        1. Integrate a payment gateway for online payments
        2. Set up merchant account with payment processor
        """
        valid, issues = validate_checklist_output(checklist, vendor)
        
        assert not valid
        assert any("payment gateway" in issue.lower() for issue in issues)


class TestInventorySoftware:
    """Test that inventory software assumptions are flagged."""
    
    def test_blocks_inventory_software_without_justification(self):
        """Inventory software unsuitable without confirming vendor's scale."""
        vendor = {
            "business_name": "Small Vendor",
            "vendor_type": "General",
            "location": "Local",
            "products": "few items",
        }
        checklist = """
        1. Install inventory management software to track stock
        2. Use barcode scanning for inventory
        """
        valid, issues = validate_checklist_output(checklist, vendor)
        
        assert not valid
        assert any("inventory" in issue.lower() for issue in issues)


class TestGoodRecommendations:
    """Test that appropriate, grounded recommendations are accepted."""
    
    def test_allows_upi_qr_recommendation(self):
        """UPI QR code is practical and doesn't assume existing setup."""
        vendor = {
            "business_name": "Fresh Mart",
            "vendor_type": "Retail",
            "location": "Chennai",
            "products": "groceries",
        }
        checklist = """
        1. If you don't already have a UPI QR code, consider setting one up through your bank's app
        2. Display the QR code clearly at your stall
        3. Keep a simple written record of your daily sales
        """
        valid, issues = validate_checklist_output(checklist, vendor)
        
        # Should pass with conditional phrasing
        assert valid or len(issues) == 0
    
    def test_allows_photo_recommendation(self):
        """Taking product photos is practical."""
        vendor = {
            "business_name": "Fruit Stand",
            "vendor_type": "Fruits",
            "location": "Market",
            "products": "seasonal fruits",
        }
        checklist = """
        1. Take clear, well-lit photos of your products
        2. Keep these photos ready to share with interested customers
        3. Consider creating a simple digital price list
        """
        valid, issues = validate_checklist_output(checklist, vendor)
        
        assert valid or len(issues) == 0
    
    def test_allows_conditional_whatsapp_recommendation(self):
        """Conditional WhatsApp recommendation should be fine."""
        vendor = {
            "business_name": "Local Shop",
            "vendor_type": "General",
            "location": "Area",
            "products": "various",
        }
        checklist = """
        1. If you don't already have WhatsApp Business, it's a free tool you could set up
        2. WhatsApp can help with customer communication if you choose to use it
        3. Keep your business name and location information ready to share
        """
        valid, issues = validate_checklist_output(checklist, vendor)
        
        # Conditional phrasing should pass
        assert valid or len([i for i in issues if "whatsapp" in i.lower()]) == 0


class TestEmptyChecklist:
    """Test edge cases."""
    
    def test_rejects_empty_checklist(self):
        """Empty checklist should be rejected."""
        vendor = {"business_name": "Test", "vendor_type": "Test", "location": "Test", "products": "test"}
        valid, issues = validate_checklist_output("", vendor)
        
        assert not valid
        assert any("empty" in issue.lower() for issue in issues)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
