"""
Focused tests for multilingual Business Profile validation.

Covers:
- English: all identity checks remain strict (name, category, location required).
- Tamil:   identity checks are best-effort; unsupported English claims still blocked.
- Hindi:   same as Tamil.
- Missing business identity, category, location (English only — strict).
- Invented products and services (all languages).
- Unsupported marketing claims in English mixed into non-English output.

No live IBM Granite calls are made; all texts are hand-crafted representative
outputs as Granite would plausibly produce them.
"""

import pytest
from business_profile_validation import validate_business_profile_output


# ──────────────────────────────────────────────────────────────────────────────
# Shared vendor fixtures
# ──────────────────────────────────────────────────────────────────────────────

VENDOR_EN = {
    "business_name": "Rocky Textiles",
    "vendor_type": "Clothing & Textiles",
    "location": "Porur, Chennai",
    "products": "Sarees, kurtis, western dresses, pants, shirts and palazzos",
    "language": "English",
}

VENDOR_TA = {
    "business_name": "Rocky Textiles",
    "vendor_type": "Clothing & Textiles",
    "location": "Porur, Chennai",
    "products": "Sarees, kurtis, western dresses, pants, shirts and palazzos",
    "language": "Tamil",
}

VENDOR_HI = {
    "business_name": "Rocky Textiles",
    "vendor_type": "Clothing & Textiles",
    "location": "Porur, Chennai",
    "products": "Sarees, kurtis, western dresses, pants, shirts and palazzos",
    "language": "Hindi",
}

VENDOR_FOOD_EN = {
    "business_name": "Ramu Chaat Corner",
    "vendor_type": "Food & Beverages",
    "location": "T. Nagar, Chennai",
    "products": "Pani puri, bhel puri, samosa",
    "language": "English",
}

VENDOR_FOOD_TA = {
    "business_name": "Ramu Chaat Corner",
    "vendor_type": "Food & Beverages",
    "location": "T. Nagar, Chennai",
    "products": "Pani puri, bhel puri, samosa",
    "language": "Tamil",
}

VENDOR_FOOD_HI = {
    "business_name": "Ramu Chaat Corner",
    "vendor_type": "Food & Beverages",
    "location": "T. Nagar, Chennai",
    "products": "Pani puri, bhel puri, samosa",
    "language": "Hindi",
}


# ──────────────────────────────────────────────────────────────────────────────
# 1. English — valid profiles
# ──────────────────────────────────────────────────────────────────────────────

class TestEnglishValidProfiles:
    """English profiles must pass when all identity facts are present."""

    def test_neutral_english_profile_passes(self):
        text = (
            "Rocky Textiles is a Clothing & Textiles business located in "
            "Porur, Chennai. Products include sarees, kurtis, western dresses, "
            "pants, shirts and palazzos."
        )
        valid, issues = validate_business_profile_output(text, VENDOR_EN)
        assert valid, f"Should accept valid English profile. Issues: {issues}"
        assert issues == []

    def test_english_profile_with_category_rephrased(self):
        """'clothing and textiles' as a phrase instead of exact 'Clothing & Textiles'."""
        text = (
            "Rocky Textiles is a clothing and textiles business in Porur, Chennai. "
            "Products include sarees, kurtis, western dresses, pants, shirts and palazzos."
        )
        valid, issues = validate_business_profile_output(text, VENDOR_EN)
        assert valid, f"Rephrased category should be accepted. Issues: {issues}"

    def test_english_food_vendor_profile_passes(self):
        text = (
            "Ramu Chaat Corner is a Food & Beverages business located in "
            "T. Nagar, Chennai. Products include pani puri, bhel puri and samosa."
        )
        valid, issues = validate_business_profile_output(text, VENDOR_FOOD_EN)
        assert valid, f"Should accept valid food vendor profile. Issues: {issues}"


# ──────────────────────────────────────────────────────────────────────────────
# 2. Tamil — valid profiles (Granite translates; identity checks are best-effort)
# ──────────────────────────────────────────────────────────────────────────────

class TestTamilValidProfiles:
    """Tamil profiles must not be rejected solely because saved English values
    are absent from the non-Latin output."""

    def test_tamil_profile_with_latin_name_retained(self):
        """Granite keeps 'Rocky Textiles' in Latin inside the Tamil sentence."""
        # Representative output: business name in Latin, rest in Tamil script.
        text = (
            "Rocky Textiles என்பது Porur, Chennai இல் அமைந்துள்ள "
            "ஆடை மற்றும் ஜவுளி வணிகம். தயாரிப்புகளில் சேலைகள், "
            "குர்திகள், மேற்கத்திய ஆடைகள், பேண்ட், சேர்ட்டுகள் மற்றும் "
            "பலாஸோக்கள் அடங்கும்."
        )
        valid, issues = validate_business_profile_output(text, VENDOR_TA)
        assert valid, f"Tamil profile with Latin name should pass. Issues: {issues}"

    def test_tamil_profile_with_transliterated_name(self):
        """Granite transliterates 'Rocky Textiles' into Tamil script.
        The saved Latin form is absent; validation must still pass."""
        text = (
            "ராக்கி டெக்ஸ்டைல்ஸ் என்பது புரூர், சென்னையில் அமைந்துள்ள "
            "ஆடை மற்றும் ஜவுளி வணிகம். சேலைகள், குர்திகள், மேற்கத்திய "
            "ஆடைகள், பேண்ட், சேர்ட்டுகள் மற்றும் பலாஸோக்கள் உள்ளன."
        )
        valid, issues = validate_business_profile_output(text, VENDOR_TA)
        assert valid, (
            "Tamil profile with transliterated name (no Latin) should pass "
            f"because identity absence is acceptable for non-English. Issues: {issues}"
        )

    def test_tamil_profile_fully_translated(self):
        """All parts including location fully rendered in Tamil script."""
        text = (
            "ராக்கி டெக்ஸ்டைல்ஸ் என்பது புரூர், சென்னையில் உள்ள "
            "ஆடை வணிகம் ஆகும். இதன் பொருட்களில் சேலை, குர்தி, "
            "பேண்ட், சேர்ட் ஆகியவை அடங்கும்."
        )
        valid, issues = validate_business_profile_output(text, VENDOR_TA)
        assert valid, (
            "Fully translated Tamil profile must not be rejected. "
            f"Issues: {issues}"
        )

    def test_tamil_food_vendor_profile_passes(self):
        """Food vendor profile in Tamil must pass."""
        text = (
            "Ramu Chaat Corner என்பது T. Nagar, Chennai இல் உள்ள உணவு "
            "மற்றும் பானங்கள் வணிகம். பணிபூரி, பேல்பூரி, சமோசா ஆகியவை "
            "கிடைக்கின்றன."
        )
        valid, issues = validate_business_profile_output(text, VENDOR_FOOD_TA)
        assert valid, f"Tamil food vendor profile should pass. Issues: {issues}"


# ──────────────────────────────────────────────────────────────────────────────
# 3. Hindi — valid profiles
# ──────────────────────────────────────────────────────────────────────────────

class TestHindiValidProfiles:
    """Hindi profiles follow the same best-effort rule as Tamil."""

    def test_hindi_profile_with_latin_name_retained(self):
        """Granite keeps 'Rocky Textiles' in Latin inside the Hindi sentence."""
        text = (
            "Rocky Textiles एक कपड़ा और वस्त्र व्यवसाय है जो Porur, Chennai में "
            "स्थित है। उत्पादों में साड़ियाँ, कुर्तियाँ, वेस्टर्न ड्रेस, पैंट, "
            "शर्ट और पलाज़ो शामिल हैं।"
        )
        valid, issues = validate_business_profile_output(text, VENDOR_HI)
        assert valid, f"Hindi profile with Latin name should pass. Issues: {issues}"

    def test_hindi_profile_with_transliterated_name(self):
        """Granite transliterates 'Rocky Textiles' into Devanagari script."""
        text = (
            "रॉकी टेक्सटाइल्स एक कपड़े और वस्त्र का व्यवसाय है, जो पोरुर, "
            "चेन्नई में स्थित है। साड़ियाँ, कुर्तियाँ, पैंट और शर्ट बेचे जाते हैं।"
        )
        valid, issues = validate_business_profile_output(text, VENDOR_HI)
        assert valid, (
            "Hindi profile with Devanagari-script name should pass "
            f"(identity absence is acceptable). Issues: {issues}"
        )

    def test_hindi_food_vendor_profile_passes(self):
        text = (
            "Ramu Chaat Corner T. Nagar, Chennai में स्थित एक खाद्य और पेय "
            "व्यवसाय है। पानी पूरी, भेल पूरी और समोसा उपलब्ध हैं।"
        )
        valid, issues = validate_business_profile_output(text, VENDOR_FOOD_HI)
        assert valid, f"Hindi food vendor profile should pass. Issues: {issues}"


# ──────────────────────────────────────────────────────────────────────────────
# 4. English — missing identity fields (must reject)
# ──────────────────────────────────────────────────────────────────────────────

class TestEnglishMissingIdentity:
    """English profiles must be rejected when identity facts are absent."""

    def test_missing_business_name_rejected(self):
        text = (
            "This is a Clothing & Textiles business located in Porur, Chennai. "
            "Products include sarees and kurtis."
        )
        valid, issues = validate_business_profile_output(text, VENDOR_EN)
        assert not valid
        assert any("business name" in i for i in issues), (
            f"Expected 'business name' issue. Got: {issues}"
        )

    def test_missing_category_rejected(self):
        """Profile contains the name and location but no category word."""
        text = (
            "Rocky Textiles is located in Porur, Chennai. "
            "Products include sarees and kurtis."
        )
        valid, issues = validate_business_profile_output(text, VENDOR_EN)
        assert not valid
        assert any("category" in i for i in issues), (
            f"Expected 'category' issue. Got: {issues}"
        )

    def test_missing_location_rejected(self):
        text = (
            "Rocky Textiles is a Clothing & Textiles business. "
            "Products include sarees, kurtis and western dresses."
        )
        valid, issues = validate_business_profile_output(text, VENDOR_EN)
        assert not valid
        assert any("location" in i for i in issues), (
            f"Expected 'location' issue. Got: {issues}"
        )

    def test_all_three_missing_gives_three_issues(self):
        text = "A shop selling clothes near a busy market area."
        valid, issues = validate_business_profile_output(text, VENDOR_EN)
        assert not valid
        assert len(issues) == 3, (
            f"Expected exactly 3 issues (name, category, location). Got: {issues}"
        )

    def test_empty_text_rejected_for_all_languages(self):
        for language, vendor in [
            ("English", VENDOR_EN),
            ("Tamil",   VENDOR_TA),
            ("Hindi",   VENDOR_HI),
        ]:
            valid, issues = validate_business_profile_output("   ", vendor)
            assert not valid, f"Empty text should be rejected for {language}"
            assert any("empty" in i.lower() for i in issues)


# ──────────────────────────────────────────────────────────────────────────────
# 5. Unsupported marketing claims — blocked for all languages
# ──────────────────────────────────────────────────────────────────────────────

class TestUnsupportedClaimsAllLanguages:
    """English promotional phrases must be blocked even when they appear
    alongside non-English (Tamil/Hindi) content."""

    def test_english_specialization_blocked_in_english(self):
        text = (
            "Rocky Textiles specializes in clothing in Porur, Chennai. "
            "Products include sarees and kurtis."
        )
        valid, issues = validate_business_profile_output(text, VENDOR_EN)
        assert not valid
        assert any("specialization" in i for i in issues)

    def test_english_quality_claim_blocked_in_english(self):
        text = (
            "Rocky Textiles offers quality products in Porur, Chennai. "
            "Category: Clothing & Textiles."
        )
        valid, issues = validate_business_profile_output(text, VENDOR_EN)
        assert not valid
        assert any("product-quality" in i for i in issues)

    def test_english_pricing_claim_blocked_in_english(self):
        text = (
            "Rocky Textiles, Clothing & Textiles, Porur, Chennai. "
            "Affordable prices on all products."
        )
        valid, issues = validate_business_profile_output(text, VENDOR_EN)
        assert not valid
        assert any("pricing" in i for i in issues)

    def test_english_delivery_claim_blocked_in_english(self):
        text = (
            "Rocky Textiles is a Clothing & Textiles business in Porur, Chennai "
            "offering home delivery on sarees and kurtis."
        )
        valid, issues = validate_business_profile_output(text, VENDOR_EN)
        assert not valid
        assert any("service" in i for i in issues)

    def test_stray_english_quality_claim_blocked_in_tamil_output(self):
        """If Granite inserts an English quality phrase into Tamil text,
        it must still be caught."""
        text = (
            "Rocky Textiles என்பது Porur, Chennai இல் உள்ள ஆடை வணிகம். "
            "quality products கிடைக்கும்."
        )
        valid, issues = validate_business_profile_output(text, VENDOR_TA)
        assert not valid, (
            "English quality claim inside Tamil output must be blocked."
        )
        assert any("product-quality" in i for i in issues)

    def test_stray_english_delivery_claim_blocked_in_hindi_output(self):
        """If Granite inserts an English delivery phrase into Hindi text,
        it must still be caught."""
        text = (
            "Rocky Textiles Porur, Chennai में स्थित है। "
            "Home delivery उपलब्ध है।"
        )
        valid, issues = validate_business_profile_output(text, VENDOR_HI)
        assert not valid, (
            "English delivery claim inside Hindi output must be blocked."
        )
        assert any("service" in i for i in issues)

    def test_boutique_category_claim_blocked_in_english(self):
        text = (
            "Rocky Textiles is a boutique located in Porur, Chennai. "
            "Clothing & Textiles."
        )
        valid, issues = validate_business_profile_output(text, VENDOR_EN)
        assert not valid
        assert any("business-category" in i for i in issues)

    def test_selection_size_claim_blocked_in_english(self):
        text = (
            "Rocky Textiles offers a wide selection of clothing in "
            "Porur, Chennai."
        )
        valid, issues = validate_business_profile_output(text, VENDOR_EN)
        assert not valid
        assert any("selection-size" in i for i in issues)


# ──────────────────────────────────────────────────────────────────────────────
# 6. Regression: existing English edge cases must still pass
# ──────────────────────────────────────────────────────────────────────────────

class TestEnglishRegressions:
    """These tests mirror the original test_business_profile_validation.py
    cases to confirm nothing regressed."""

    _VENDOR_DIRTY = {
        "business_name": "Rocky  textiles",   # double space
        "vendor_type": "Clothing & Textiles",
        "location": "Porur , Chennai",         # space before comma
        "products": "Sarees, kurtis, western dresses, pants, shirts and palazzos",
        "language": "English",
    }

    _GRANITE_OUTPUT = (
        "Rocky Textiles is a clothing store located in Porur, Chennai, "
        "offering sarees, kurtis, western dresses, pants, shirts, and palazzos."
    )

    def test_whitespace_normalisation_name(self):
        valid, issues = validate_business_profile_output(
            self._GRANITE_OUTPUT, self._VENDOR_DIRTY
        )
        name_issues = [i for i in issues if "business name" in i]
        assert not name_issues, f"Name check raised a false positive: {name_issues}"

    def test_whitespace_normalisation_location(self):
        valid, issues = validate_business_profile_output(
            self._GRANITE_OUTPUT, self._VENDOR_DIRTY
        )
        location_issues = [i for i in issues if "location" in i]
        assert not location_issues, (
            f"Location check raised a false positive: {location_issues}"
        )

    def test_rephrased_category_accepted(self):
        """'clothing store' must satisfy the 'Clothing & Textiles' category check."""
        valid, issues = validate_business_profile_output(
            self._GRANITE_OUTPUT, self._VENDOR_DIRTY
        )
        category_issues = [i for i in issues if "category" in i]
        assert not category_issues, (
            f"Category check raised a false positive: {category_issues}"
        )

    def test_category_absent_outside_name_rejected(self):
        """Category word that only appears inside the business name must fail."""
        vendor = {
            "business_name": "Rocky Textiles",
            "vendor_type": "Clothing & Textiles",
            "location": "Porur, Chennai",
            "products": "Sarees, kurtis",
            "language": "English",
        }
        text = "Rocky Textiles sells food items in Porur, Chennai."
        valid, issues = validate_business_profile_output(text, vendor)
        assert any("category" in i for i in issues), (
            "Category check should fail when no category word appears outside the name."
        )

    def test_vendor_without_language_key_treated_as_english(self):
        """A vendor dict without 'language' must default to English behaviour."""
        vendor_no_lang = {
            "business_name": "Rocky Textiles",
            "vendor_type": "Clothing & Textiles",
            "location": "Porur, Chennai",
            "products": "Sarees, kurtis",
            # no "language" key
        }
        # Profile missing the business name — must be rejected (English rules apply).
        text = "A clothing and textiles store in Porur, Chennai."
        valid, issues = validate_business_profile_output(text, vendor_no_lang)
        assert not valid
        assert any("business name" in i for i in issues)
