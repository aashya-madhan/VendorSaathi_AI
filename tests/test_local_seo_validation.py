import unittest

from local_seo_validation import (
    get_local_seo_warnings,
    validate_local_seo_output,
)


ROCKY_PROFILE = {
    "business_name": "Rocky Electronics",
    "vendor_type": "Electronics & Accessories",
    "location": "Porur, Chennai",
    "products": (
        "Smartphones & Tablets, Audio & Wearables, Computers & Accessories, "
        "Microcontrollers & Modules, Motors & Hardware"
    ),
}

TEXTILES_PROFILE = {
    "business_name": "Rocky Textiles",
    "vendor_type": "Clothing & Textiles",
    "location": "Porur, Chennai",
    "products": "Sarees, kurtis, western dresses, pants, shirts and palazzos",
}


class LocalSEOValidationTests(unittest.TestCase):
    def test_flags_unsupported_claims_products_and_services_in_sample(self):
        sample = """
        Rocky Electronics – Your Trusted Source for Electronics and Accessories in Chennai.
        We offer portable speakers, laptops, microcontroller boards and wristbands.
        We provide smartphone repair and wholesale electronics at competitive prices.
        Our store serves tech enthusiasts with reliable products and friendly service.
        Keywords: Buy tablets near me; best mobile gadgets Porur.
        Categories: Mobile Phone Repair Shop; Dealership (Electronics).
        """
        valid, issues = validate_local_seo_output(sample, ROCKY_PROFILE)
        self.assertFalse(valid)
        combined = " ".join(issues).lower()
        for expected in (
            "trust claim", "portable speakers", "laptops", "microcontroller",
            "wristbands", "phone repair", "wholesale", "pricing claim",
            "reliability claim", "service-quality", "superlative",
        ):
            self.assertIn(expected, combined)

    def test_allows_profile_supported_products_and_neutral_action_advice(self):
        sample = """
        ### Business description
        Rocky Electronics is an electronics and accessories business in Porur, Chennai.
        Products include smartphones and tablets, audio and wearables, computers and
        accessories, microcontrollers and modules, motors and hardware.

        ### Local visibility actions
        Verify business information, upload genuine storefront and product photos,
        respond to customer enquiries, and update listings when business details change.
        """
        valid, issues = validate_local_seo_output(sample, ROCKY_PROFILE)
        self.assertTrue(valid, issues)
        self.assertEqual(issues, [])

    def test_flags_only_specific_items_not_explicitly_in_profile(self):
        sample = "Computers, tablets, and portable speakers are available."
        valid, issues = validate_local_seo_output(sample, ROCKY_PROFILE)
        self.assertFalse(valid)
        self.assertTrue(any("portable speakers" in issue for issue in issues))
        self.assertFalse(any("tablets" in issue for issue in issues))

    def test_empty_output_is_rejected(self):
        valid, issues = validate_local_seo_output("  ", ROCKY_PROFILE)
        self.assertFalse(valid)
        self.assertTrue(issues)

    def test_flags_rocky_sample_brand_and_unverified_product_specifics(self):
        sample = """
        Rocky Electronics is your go-to shop at Porur, Chennai for all things tech.
        We offer a wide variety of smartphones and tablets. Our selection includes
        audio gear like headphones and speakers designed for reliable sound quality.
        We stock keyboards and mice, storage solutions, and Micromax components.
        Your one-stop-shop for gadgets in Chennai.
        """
        valid, issues = validate_local_seo_output(sample, ROCKY_PROFILE)
        self.assertFalse(valid)
        combined = " ".join(issues).lower()
        # Note: "wide variety" is now allowed since Rocky has 5+ products (Bug Fix #3)
        for expected in (
            "promotional positioning", "headphones", "speakers",
            "keyboards", "storage", "micromax", "breadth/positioning",
        ):
            self.assertIn(expected, combined)

    def test_near_me_and_long_sentence_are_non_blocking_warnings(self):
        sample = (
            "Clothing store near me in Porur, Chennai. "
            "Visit the listing to explore sarees, kurtis, western dresses, pants, shirts "
            "and palazzos, check the business location, review the available information, "
            "and contact the business directly for details before making your visit, checking current availability, confirming the exact address, and planning a convenient time to visit the shop."
        )
        valid, issues = validate_local_seo_output(sample, TEXTILES_PROFILE)
        self.assertTrue(valid, issues)
        self.assertEqual(issues, [])
        warnings = get_local_seo_warnings(sample)
        self.assertTrue(any("near me" in warning for warning in warnings))
        self.assertTrue(any("long" in warning for warning in warnings))

    def test_textiles_profile_allows_its_listed_products(self):
        sample = (
            "Rocky Textiles is a clothing business in Porur, Chennai. "
            "Products include sarees, kurtis, western dresses, pants, shirts and palazzos."
        )
        valid, issues = validate_local_seo_output(sample, TEXTILES_PROFILE)
        self.assertTrue(valid, issues)

    def test_unverified_quality_and_pricing_claims_still_block(self):
        sample = "Rocky Textiles offers quality products at competitive prices in Porur."
        valid, issues = validate_local_seo_output(sample, TEXTILES_PROFILE)
        self.assertFalse(valid)
        self.assertTrue(any("product-quality" in issue for issue in issues))
        self.assertTrue(any("pricing claim" in issue for issue in issues))

    def test_flags_unsupported_address_attributes_delivery_and_collection_claims(self):
        sample = """
        Rocky Textiles is located on Avadi Main Road in Porur, Chennai.
        Discover an extensive collection of clothing at our accessible store.
        We offer home delivery and free delivery across Chennai.
        """
        valid, issues = validate_local_seo_output(sample, TEXTILES_PROFILE)
        self.assertFalse(valid)
        combined = " ".join(issues).lower()
        # Note: "extensive collection" is now allowed since Textiles has 6 products (Bug Fix #3)
        for expected in (
            "street-level address", "accessibility claim",
            "delivery-service claim",
        ):
            self.assertIn(expected, combined)

    def test_allows_address_and_delivery_only_when_profile_explicitly_supports_them(self):
        profile = {
            **TEXTILES_PROFILE,
            "address": "12 Avadi Main Road",
            "services": "Home delivery",
        }
        sample = (
            "Rocky Textiles is located on Avadi Main Road. "
            "Home delivery is available."
        )
        valid, issues = validate_local_seo_output(sample, profile)
        self.assertTrue(valid, issues)

    def test_flags_unverified_pin_code(self):
        sample = "Rocky Textiles, Porur, Chennai 600116."
        valid, issues = validate_local_seo_output(sample, TEXTILES_PROFILE)
        self.assertFalse(valid)
        self.assertTrue(any("PIN code" in issue for issue in issues))

    def test_flags_unverified_gender_and_fabric_category_attributes(self):
        sample = "Categories: Women's Fashion Retailer; Fabric Shop."
        valid, issues = validate_local_seo_output(sample, TEXTILES_PROFILE)
        self.assertFalse(valid)
        combined = " ".join(issues).lower()
        self.assertIn("customer-demographic", combined)
        self.assertIn("fabric-retail", combined)

    def test_flags_excessively_long_action_plan_as_warning_not_blocker(self):
        sample = (
            "### Local visibility action plan\n"
            "Share high-quality images showcasing key items across your website and social "
            "media platforms so prospective clients can compare prices and features before "
            "visiting the store, thereby increasing conversions and improving the customer "
            "journey through several digital touchpoints in the local market."
        )
        valid, issues = validate_local_seo_output(sample, ROCKY_PROFILE)
        self.assertTrue(valid, issues)
        self.assertTrue(any("long" in warning for warning in get_local_seo_warnings(sample)))


if __name__ == "__main__":
    unittest.main()
