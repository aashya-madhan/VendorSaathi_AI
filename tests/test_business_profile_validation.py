from business_profile_validation import validate_business_profile_output


VENDOR = {
    "business_name": "Rocky Textiles",
    "vendor_type": "Clothing & Textiles",
    "location": "Porur, Chennai",
    "products": "Sarees, kurtis, western dresses, pants, shirts and palazzos",
}


def test_accepts_neutral_profile_using_saved_facts():
    text = (
        "Rocky Textiles is a Clothing & Textiles business located in Porur, Chennai. "
        "Products listed include sarees, kurtis, western dresses, pants, shirts and palazzos."
    )
    assert validate_business_profile_output(text, VENDOR) == (True, [])


def test_blocks_specialization_and_selection_claims():
    text = (
        "Rocky Textiles specializes in clothing and textiles in Porur, Chennai. "
        "It offers a diverse selection of products."
    )
    valid, issues = validate_business_profile_output(text, VENDOR)
    assert not valid
    assert any("specialization" in issue for issue in issues)
    assert any("selection-size" in issue for issue in issues)


def test_blocks_customer_sentiment_and_unverified_store_type():
    text = (
        "Rocky Textiles is a boutique in Porur, Chennai, known for satisfied customers. "
        "Category: Clothing & Textiles."
    )
    valid, issues = validate_business_profile_output(text, VENDOR)
    assert not valid
    assert any("business-category" in issue for issue in issues)
    assert any("customer-sentiment" in issue for issue in issues)


def test_blocks_unverified_pricing_and_delivery():
    text = (
        "Rocky Textiles, Clothing & Textiles, Porur, Chennai offers affordable prices "
        "and home delivery."
    )
    valid, issues = validate_business_profile_output(text, VENDOR)
    assert not valid
    assert any("pricing" in issue for issue in issues)
    assert any("service" in issue for issue in issues)


def test_rejects_missing_profile_identity():
    valid, issues = validate_business_profile_output("A shop selling clothes.", VENDOR)
    assert not valid
    assert len(issues) == 3


# ---------------------------------------------------------------------------
# Real-world dirty-input cases: whitespace normalisation
# ---------------------------------------------------------------------------

# Simulates a vendor who typed extra spaces or a space before the comma when
# saving their profile; Granite normalises those in its output.
_VENDOR_DIRTY = {
    "business_name": "Rocky  textiles",      # double space
    "vendor_type": "Clothing & Textiles",
    "location": "Porur , Chennai",            # space before comma
    "products": "Sarees, kurtis, western dresses, pants, shirts and palazzos",
}

_GRANITE_OUTPUT = (
    "Rocky Textiles is a clothing store located in Porur, Chennai, "
    "offering sarees, kurtis, western dresses, pants, shirts, and palazzos."
)


def test_accepts_granite_output_when_name_has_extra_spaces():
    """double-space in saved name must not cause a false-positive rejection."""
    valid, issues = validate_business_profile_output(_GRANITE_OUTPUT, _VENDOR_DIRTY)
    name_issues = [i for i in issues if "business name" in i]
    assert not name_issues, f"Name check raised a false positive: {name_issues}"


def test_accepts_granite_output_when_location_has_space_before_comma():
    """Space before comma in saved location must not cause a false-positive rejection."""
    valid, issues = validate_business_profile_output(_GRANITE_OUTPUT, _VENDOR_DIRTY)
    location_issues = [i for i in issues if "location" in i]
    assert not location_issues, f"Location check raised a false positive: {location_issues}"


def test_category_token_check_accepts_rephrased_category():
    """Granite rephrasing 'Clothing & Textiles' as 'clothing store' must pass
    because 'clothing' appears as a standalone word outside the business name."""
    valid, issues = validate_business_profile_output(_GRANITE_OUTPUT, _VENDOR_DIRTY)
    category_issues = [i for i in issues if "category" in i]
    assert not category_issues, f"Category check raised a false positive: {category_issues}"


def test_category_check_still_blocks_completely_absent_category():
    """When no category token appears outside the business name, the check must fail.

    'Rocky Textiles is located in Porur, Chennai.' — 'textiles' only appears inside
    the business name; 'clothing' is absent entirely.  After stripping the name,
    no category word remains, so a category issue must be raised.
    """
    text = "Rocky Textiles is located in Porur, Chennai."
    valid, issues = validate_business_profile_output(text, _VENDOR_DIRTY)
    assert any("category" in i for i in issues), (
        "Category check should have failed when no category word appears outside the business name."
    )


def test_category_check_blocks_name_only_category_word():
    """Category word appearing only inside the business name must not satisfy the check.

    This is the core edge case: category = 'Clothing & Textiles', text = 'Rocky
    Textiles sells food items.'  After the name is stripped, 'textiles' is gone and
    'clothing' is absent — so the check must raise a category issue.
    """
    vendor = {
        "business_name": "Rocky Textiles",
        "vendor_type": "Clothing & Textiles",
        "location": "Porur, Chennai",
        "products": "Sarees, kurtis",
    }
    text = "Rocky Textiles sells food items in Porur, Chennai."
    valid, issues = validate_business_profile_output(text, vendor)
    assert any("category" in i for i in issues), (
        "Category check should have failed when the only occurrence of a category word "
        "is inside the business name, not in the descriptive text."
    )
