from prompts import build_local_seo_prompt


def _prompt(products="Sarees, kurtis, western dresses, pants, shirts and palazzos"):
    return build_local_seo_prompt({
        "business_name": "Rocky Textiles",
        "vendor_type": "Clothing & Textiles",
        "location": "Porur, Chennai",
        "products": products,
        "language": "English",
    })


def test_local_seo_prompt_blocks_unsupported_marketing_claims_without_listing_examples():
    prompt = _prompt()
    assert "neutral, descriptive language" in prompt
    assert "Do not make unsupported claims about product quality, pricing" in prompt
    assert "customer sentiment" in prompt
    assert "Do not add filler claims" in prompt

    for phrase in (
        '"quality products"', '"quality product"', '"competitive prices"',
        '"friendly service"', '"wide selection"', '"satisfied customers"',
    ):
        assert phrase not in prompt

    assert 'Do not use "near me" as a keyword' in prompt
    assert "Porur, Chennai" in prompt


def test_local_seo_prompt_requires_neutral_profile_grounded_copy():
    prompt = _prompt("Sarees and kurtis")
    assert "neutral, descriptive language" in prompt
    assert "Use only the business details supplied in the vendor profile" in prompt
    assert "Do not invent nearby landmarks or other localities" in prompt
    assert "Never invent street addresses, road names, landmarks, PIN codes" in prompt


def test_local_seo_prompt_preserves_exact_product_and_category_details():
    prompt = _prompt()
    assert "Preserve the exact business name, spelling, products, category" in prompt
    assert "Reproduce product names and categories using the exact wording" in prompt
    assert "Rocky Textiles" in prompt
    assert "Clothing & Textiles" in prompt
    assert "Sarees, kurtis, western dresses, pants, shirts and palazzos" in prompt
