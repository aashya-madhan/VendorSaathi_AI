"""Reusable prompt builders for Street Vendor Growth Copilot.

Each builder returns a plain string ready to be passed to llm.generate().
"""
from typing import Dict, Optional


def _language_instruction(language: str) -> str:
    """Return a language directive to embed in every prompt."""
    return f"Respond entirely in {language}."


def _vendor_context(vendor: Dict) -> str:
    """Summarise vendor details as a compact context block."""
    return (
        f"Business name: {vendor.get('business_name') or 'Not provided'}\n"
        f"Vendor type: {vendor.get('vendor_type') or 'Not provided'}\n"
        f"Location: {vendor.get('location') or 'Not provided'}\n"
        f"Main products/services: {vendor.get('products') or 'Not provided'}"
    )


_SAFETY_NOTE = (
    "Important: Do NOT invent, assume, or fabricate any government scheme names, "
    "eligibility criteria, benefits, loan amounts, application deadlines, or official URLs. "
    "If you are uncertain about any official detail, say so clearly."
)


def build_profile_prompt(vendor: Dict) -> str:
    """
    Build a factual, profile-grounded digital business description.
    """
    language = vendor.get("language", "English")

    return f"""{_language_instruction(language)}

You write factual digital business profiles for small street vendors in India.

TASK:
Write a concise business profile of 30–50 words using only the
vendor details supplied below. Do not add sentences to reach a word count.
If the supplied facts support a shorter profile, keep it shorter.

STRICT ACCURACY RULES:
- Use only the saved business details.
- Preserve the exact business name, category, products and location.
- Describe the business in neutral, simple and natural language.
- Mention only products explicitly listed in the vendor profile.
- Do not infer product varieties, materials, brands or specializations.
- Do not invent product quality, pricing, promotions, popularity, reputation, customer satisfaction, selection size or expertise unless explicitly stated in the profile.
- Do not infer a narrower store format, retail subcategory or customer group.
- Do not invent addresses, landmarks, contact details, opening hours,
  delivery, online ordering or other services.
- Do not describe the locality with subjective or promotional adjectives.
- Do not add promotional filler or persuasive claims.
- Do not use superlatives.
- Do not repeat or paraphrase prohibited claim categories from these rules.

NEUTRAL LANGUAGE REQUIREMENT:
- Use simple connecting phrases such as "is a", "located in", "products include".
- NEVER use positioning words such as "specializes", "known for", "focuses on", "dedicated to", "committed to".
- NEVER use expertise claims such as "expert", "specialist", "experienced".
- NEVER use promotional verbs such as "offers", "provides", "serves", "caters to".
- Prefer neutral descriptive structure: [Name] is a [category] business located in [location]. Products include [product list].

CONTENT REQUIREMENTS:
1. State the exact business name and supplied business category.
2. Mention the supplied location without expanding it.
3. List the supplied products using their original wording.
4. Use only short factual connecting language.

If any information is missing, omit it rather than guessing.
Do not fill missing details with assumptions.

Vendor details:
{_vendor_context(vendor)}

Return only the completed business profile.
Do not display these instructions.

Respond entirely in {language}.
"""


def build_promo_prompt(vendor: Dict, occasion: Optional[str] = None) -> str:
    """Build a prompt for a WhatsApp / social-media promotional message."""
    language = vendor.get("language", "English")
    occasion_line = (
        f"Occasion or special offer: {occasion}"
        if occasion
        else "No specific occasion — write a general promotional message."
    )
    return f"""{_language_instruction(language)}

You are a marketing assistant for small street vendors in India.

Write a short, engaging promotional message (50–80 words) suitable for WhatsApp or
a social-media post. Include the stall name, highlight the products, and end with a
friendly call-to-action. Use simple, everyday language. Do not add prices, phone
numbers, or addresses that were not provided.

FACTUAL GROUNDING RULES:
- Use only the business name, location, and products listed in the vendor profile
- Do NOT invent product qualities (beautiful, stunning, breathtaking, premium, high-quality)
- Do NOT claim unique designs, exclusive collections, or special features unless stated in profile
- Do NOT invent discounts, offers, prices, or deals unless provided in the occasion
- Do NOT make claims about reputation, popularity, customer satisfaction, or awards
- Keep the message warm and inviting using neutral, factual descriptions
- Use engaging structure and calls-to-action without inventing facts

ALLOWED: "Visit [business name] for [products]! Located in [location]. [Call-to-action]"
NOT ALLOWED: "Visit [business name] for breathtaking sarees and unique designs!"

Vendor details:
{_vendor_context(vendor)}

{occasion_line}

Write the promotional message now:"""


def build_checklist_prompt(vendor: Dict, context: str = "") -> str:
    """Build a numbered digitalization checklist."""
    language = vendor.get("language", "English")
    vendor_type = vendor.get("vendor_type") or "street vendor"
    
    # Extract actual products for explicit reference
    vendor_products = vendor.get("products", "").strip()
    if vendor_products:
        products_note = f"\nVendor's ACTUAL products: {vendor_products}\n"
    else:
        products_note = "\nVendor has not listed specific products yet.\n"
    
    context_block = (
        f"\nRelevant reference information:\n{context}\n"
        if context.strip()
        else "\nNo additional reference documents were retrieved for this query.\n"
    )
    
    food_note = (
        "- Because this is a food business, include one step about FSSAI basic "
        "registration (for vendors with turnover below ₹12 lakh per year). "
        "Do not apply this step to other business types.\n"
        if "food" in vendor_type.lower() or "beverage" in vendor_type.lower()
        else ""
    )
    
    if language == "Tamil":
        language_quality_note = (
            "LANGUAGE RULES (must follow):\n"
            "- Write every step in clear, natural Tamil (Unicode Tamil script only).\n"
            "- Do not mix English words into Tamil sentences.\n"
            "- Do not transliterate English into Tamil phonetics.\n"
            "- Do not produce garbled characters, broken Unicode, or mixed-script text.\n"
            "- Each numbered step must be a complete Tamil sentence.\n"
        )
    elif language == "Hindi":
        language_quality_note = (
            "LANGUAGE RULES (must follow):\n"
            "- Write every step in clear, natural Hindi (Devanagari script only).\n"
            "- Do not mix English words or Roman script into Hindi sentences.\n"
            "- Every numbered step must be a complete Hindi sentence — "
            "do not end mid-sentence or leave Markdown unfinished.\n"
        )
    else:
        language_quality_note = ""

    return f"""You are a digital-onboarding advisor for small street vendors in India.

{_SAFETY_NOTE}

CRITICAL — READ THESE RULES FIRST:

PRODUCTS — ABSOLUTE RULE:
{products_note}
- If you mention ANY product in the checklist, it MUST be from this exact list above
- Do NOT invent products (avocados, figs, exotic items, etc.)
- Do NOT assume products from the vendor type (e.g., "Fruits & Vegetables" does NOT mean you can mention all fruits)
- Use the EXACT product names from the list, or don't mention specific products at all
- Generic recommendations are fine ("your products", "your offerings") without naming specific items

SERVICES — ABSOLUTE RULE:
- Do NOT assume the vendor has:
  * Delivery service
  * Online ordering capability  
  * A website
  * Social media accounts (unless user confirmed in context)
  * WhatsApp Business (unless user confirmed in context)
  * Google Business Profile (unless user confirmed in context)
  * Inventory software
  * Payment gateway
  
- If recommending any of these, use CONDITIONAL phrasing:
  * "If you plan to offer delivery in the future, consider..."
  * "If you don't already have WhatsApp Business, you could set it up to..."
  * "When you're ready to create a website, you might..."

DELIVERY-SPECIFIC RULES:
- NEVER recommend: delivery zones, estimated arrival times, delivery radius, shipping options, order tracking
- These are only suitable IF the vendor already confirmed they offer delivery
- Check the context: if delivery is not confirmed, do NOT include delivery-specific recommendations

CUSTOMER BEHAVIOR — ABSOLUTE PROHIBITION:
- NEVER claim: "most customers prefer...", "buyers nowadays...", "urban customers opt for..."
- NEVER assume customer preferences, payment habits, or search behaviors
- NEVER claim growing trends or demand without evidence

OUTCOME GUARANTEES — ABSOLUTE PROHIBITION:
- NEVER say: "will increase sales", "will attract customers", "will boost revenue"
- ALWAYS use: "could help attract", "may increase visibility", "might improve"
- Recommendations are suggestions, NOT guaranteed results

PLATFORM ASSUMPTIONS — CONDITIONAL PHRASING REQUIRED:
- Check user's declared tools in the context
- If WhatsApp Business not declared: "If you don't already have WhatsApp Business, consider..."
- If Google Business Profile not declared: "If you want to be found on Google, you could create..."
- If social media not declared: "If you use social media, you might..."
- NEVER assume these platforms are active without confirmation

PRACTICAL RECOMMENDATIONS (GOOD):
✓ "Consider setting up a UPI QR code through your bank's mobile app"
✓ "Take clear photos of your products to share with interested customers"
✓ "Keep a simple digital record of your products and prices"
✓ "If you don't already have WhatsApp Business, it's a free tool that could help with customer communication"
✓ "When customers ask for your business details, having them written down can help"
✓ "Consider displaying your UPI QR code clearly at your stall"

UNSUITABLE RECOMMENDATIONS (BAD):
✗ "Set up delivery zones and estimated arrival times" (assumes delivery service)
✗ "Integrate a payment gateway for online transactions" (too complex for street vendor)
✗ "Update your website content" (assumes website exists)
✗ "Most customers nowadays prefer cashless payment" (unsupported behavior claim)
✗ "This will increase your sales and revenue" (outcome guarantee)
✗ "Post photos on your social media daily" (assumes social media without confirmation)
✗ "Add avocados and figs to your product photos" (invents products not in profile)
✗ "Install inventory management software" (assumes need/scale without confirmation)
✗ "Set up order tracking for customer orders" (assumes online ordering system)

STEP-BY-STEP VALIDATION BEFORE WRITING:
1. Does this step mention a specific product? → Is it in the vendor's actual product list?
2. Does this step assume delivery/website/ordering? → Is it confirmed or phrased conditionally?
3. Does this step make customer behavior claims? → Remove it
4. Does this step guarantee outcomes? → Change to possibility language
5. Does this step assume a platform/tool? → Check if declared, otherwise use conditional phrasing
6. Is this practical for a SMALL STREET VENDOR? → If it requires complex software/systems, reconsider

Additional rules for this response:
- Produce exactly 5 to 7 numbered steps. Do not produce fewer than 5 or more than 7.
- Every step must be a complete sentence. Do not leave any step unfinished.
- Tailor every step specifically to a {vendor_type} business.
- Do not include food-safety or FSSAI requirements unless this is a food business.
- Do not include trade-specific advice that applies only to unrelated business types.
- Do not invent URLs, domain names, app names, or document names.
- Do not make claims about registration benefits, government subsidies, loan amounts,
  or guaranteed outcomes. If you are uncertain whether a requirement applies, tell the
  vendor to verify it with the relevant official authority.
- Do not recommend specific paid third-party services or vendors.
- Do not present municipal registration, trade licences, GST registration,
  or any other government registration as mandatory for every vendor.
- When applicability depends on turnover, location, business type, sales channel,
  or other conditions, tell the vendor to check whether the requirement applies.
- Do not invent mandatory documents, fees, eligibility conditions, or deadlines.
- Clearly distinguish optional digitalization suggestions from legal or
  government requirements. Recommend verification through the relevant
  official authority before taking regulatory action.
- Never output placeholder URLs or invented government scheme names.
- Present software, marketplaces, and digital-payment providers
  only as optional examples, never as compulsory requirements.
- Prefer practical, low-cost actions that a small vendor can take
  without assuming legal obligations.

{food_note}
{context_block}
Vendor details:
{_vendor_context(vendor)}

{language_quality_note}{_language_instruction(language)}

REMINDER — Before writing each step, verify:
- Products: Only from the actual list, or use generic terms
- Services: Don't assume delivery/ordering/website unless confirmed
- Customers: No behavior claims
- Outcomes: Use "could/might/may" not "will"
- Tools: Use conditional phrasing unless declared

Write the digitalization checklist now:"""


def build_scheme_qa_prompt(
    question: str,
    context: str = "",
    language: str = "English",
    vendor: Optional[Dict] = None,
) -> str:
    """Build a strictly evidence-grounded government-scheme Q&A prompt."""
    scope_refusal = {
        "Tamil": (
            "இந்தக் கேள்வி என் பணியின் எல்லைக்கு வெளியே உள்ளது. "
            "தெரு வியாபாரிகளுக்கான இந்திய அரசு திட்டங்கள் பற்றி மட்டுமே "
            "உதவ முடியும்."
        ),
        "Hindi": (
            "यह प्रश्न मेरे दायरे से बाहर है। मैं केवल भारतीय सरकारी "
            "योजनाओं के बारे में सहायता कर सकता हूँ जो सड़क विक्रेताओं "
            "के लिए प्रासंगिक हैं।"
        ),
    }.get(
        language,
        "This question is outside my scope. I can only help with Indian government "
        "schemes and registrations relevant to street vendors.",
    )
    if context.strip():
        context_block = (
            "\nRETRIEVED SOURCE EVIDENCE (the only factual source you may use):\n"
            f"{context}\n"
        )
    else:
        context_block = (
            "\nNO VERIFIED SOURCE EVIDENCE WAS RETRIEVED.\n"
            "Do not answer from memory or training data. Explain that verified "
            "information is unavailable and direct the user to the relevant "
            "official government portal.\n"
        )
    vendor_block = (
        f"\nVendor context (use only to personalize wording, never as evidence):\n"
        f"{_vendor_context(vendor)}\n"
        if vendor
        else ""
    )
    return f"""You are a government-scheme information assistant for street vendors in India.
Help users understand relevant Indian government schemes and registrations.
You are not an official government representative and do not provide official legal
or financial advice.

IN-SCOPE TOPICS:
PM SVANidhi, Udyam registration, GeM seller registration and product
listing, FSSAI basic registration for food vendors, DigiLocker,
Jan Dhan Yojana, digital-payment onboarding (UPI/BHIM), and similar
Indian government initiatives for street vendors and micro-enterprises.

SCOPE RULE:
If the question is unrelated to these topics, including personal loans, private
bank products, investment advice, or unrelated government schemes, respond with
exactly this message (translated into {language} if needed):
"{scope_refusal}"

EVIDENCE RULES:
1. Use only facts explicitly stated in the retrieved source evidence.
2. Never infer a fact from implication, absence of information, or general knowledge.
3. An authorized registration portal does not establish that registration is free.
4. Do not invent fees, eligibility criteria, documents, procedures, deadlines,
   URLs, benefits, or platform features.
5. Do not add steps beyond those explicitly supported by the source.
6. If the source is incomplete, ambiguous, or insufficient, say so clearly.
7. Distinguish source statements from information the source does not establish.
8. ALWAYS cite the source document name and date when providing factual information.
9. When source evidence is historical (dated before 2024), explicitly state:
   "According to [document name] dated [date], [fact]. Verify current requirements on [official portal]."
10. Do NOT claim historical documents verify current official requirements.
11. Never describe retrieval scores as confidence probabilities.
12. Keep the answer concise and relevant to the question.
13. Respond entirely in the requested language: {language}.

HISTORICAL SOURCE HANDLING (CRITICAL):
- Source date notes indicate when information was published
- Documents dated 2021, 2020, or earlier are HISTORICAL EVIDENCE
- Never claim "current requirements are" or "official rules state" based solely on historical sources
- Use phrasing like: "Historical evidence from [date] indicates..." OR "According to [document dated X]..."
- ALWAYS direct users to verify current status on official government portals
- Example: "According to the Benefits of Udyam Registration document dated February 2021, 
  registration was described as totally free. Verify current fee status on udyamregistration.gov.in."

If the evidence is insufficient, respond in {language} that you do not have enough
verified information to answer reliably and recommend checking the relevant official
government portal. Do not guess.

{_SAFETY_NOTE}
{context_block}
{vendor_block}
Vendor's question: {question}

{_language_instruction(language)}
Answer:"""


def build_local_seo_prompt(vendor: Dict) -> str:
    """Generate practical, location-aware local SEO content for a street vendor."""
    language = vendor.get("language", "English")
    return f"""{_language_instruction(language)}

You are a local business visibility advisor for small street vendors in India.

Use the vendor details below to create a practical local SEO kit.

Produce these four sections:

1. BUSINESS DESCRIPTION
Write a clear, customer-friendly description of 60–90 words.
Mention the actual business name, products, category and location.

2. LOCAL SEARCH KEYWORDS
Suggest 8–12 relevant search phrases.
Include combinations of the actual products and the vendor's stated locality.
Do not claim these phrases have verified search volume or ranking potential.

3. ONLINE BUSINESS LISTING
Suggest:
- One concise listing title.
- One search-friendly business description.
- A short list of relevant business categories or attributes.

4. LOCAL VISIBILITY ACTION PLAN
Give 5 practical, low-cost actions to improve local discoverability.
Prioritize accurate business details, genuine product photos,
customer communication, encouraging honest customer feedback
without pressure, and keeping online listings updated.
Do not invent offers, reviews or completed actions.

STRICT ACCURACY RULES:
- Use only the business details supplied in the vendor profile.
- Write in neutral, descriptive language rather than promotional language.
- Do not add filler claims to make the description persuasive.
- Do not make unsupported claims about product quality, pricing,
  discounts, service standards, selection size, customer sentiment,
  popularity, expertise or review outcomes.
- Do not describe the business as having a broad selection or range
  unless the profile explicitly establishes that fact.
- Preserve the exact business name, spelling, products, category
  and location.
- Never invent addresses, contact details, opening hours, prices,
  offers, discounts, reviews, ratings, business history or services.
- Never infer specific products from broad categories.
- Never invent customer segments, target audiences or use cases.
- Keywords must use only the supplied business name, products,
  category, locality and city.
- Treat keywords as suggestions, not verified search-volume or ranking data.
- Do not use "near me" as a keyword. Use the saved locality and city instead.
- Listing categories must reflect only the stated vendor type/category.
- Do not infer narrower store formats, retail subcategories,
  customer demographics, product specializations or business attributes.
- If no additional category is clearly supported, provide only
  the supplied vendor type/category.
- Label suggested categories as options to verify on Google Business Profile.

CATEGORY USAGE RULE — CRITICAL:
- NEVER transform the saved vendor category into a narrower business type.
- For example: "Clothing & Textiles" must NOT become "boutique", "fabric shop", or "clothing store".
- Use ONLY the exact saved vendor type/category or neutral equivalent phrases like "clothing and textiles business".
- In the listing category section, output ONLY the saved vendor type/category.
- Do not invent specific retail formats, store types, or subcategories.

- Business attributes may be included only when explicitly present
  in the vendor profile.
- Never invent street addresses, road names, landmarks, PIN codes,
  delivery areas or service coverage.
- Never imply that a listing, promotion, review or online business profile exists.
- Use the current platform name "Google Business Profile".
- Do not suggest publishing customer photographs without consent.
- Encourage honest customer feedback without pressure or filtering.
- Keep recommendations practical, low-cost and ethical.
- Reproduce product names and categories using the exact wording
  supplied in the vendor profile.
- Do not invent nearby landmarks or other localities.

NON-REPRODUCTION RULE — HIGHEST PRIORITY:
- The instructions above may mention examples of prohibited claims or categories.
  Those examples are instructions only; they are not content to include in the SEO kit.
- Never quote, repeat, list, paraphrase, or use prohibited example phrases in the
  generated business description, keywords, listing title, listing description,
  category list, or action plan.
- Do not output phrases merely because they appear in these instructions.
- For the listing category section, output only the exact vendor type/category from
  the saved profile unless a directly equivalent neutral category is unquestionably
  supported. If uncertain, output the saved category alone.
- For review guidance, say only: "Invite customers to share honest feedback about
  their own experience." Do not make claims about customer sentiment or outcomes.

FINAL OUTPUT VALIDATION:
Before returning the kit, silently check every section.
1. Verify every business fact against the vendor profile.
2. Remove invented products, services, audiences, addresses, attributes and claims.
3. Ensure keywords are relevant and grounded in supplied data.
4. Ensure listing titles, descriptions and categories are factual.
5. Ensure action steps are understandable, practical and ethical.
6. If required information is missing, explicitly tell the vendor to update
   their profile instead of guessing.
7. If a category cannot be confidently supported by the supplied vendor type,
   omit it rather than guessing.
8. Remove any use of unsupported store-format or demographic-specific
   retailer labels unless those exact attributes appear in the profile.
9. Do not copy or repeat prohibited wording from these prompt instructions.
10. Use only the saved vendor category in the category list when no equivalent
    category is certain.

Return only the completed SEO kit. Do not display these rules.

Vendor details:
{_vendor_context(vendor)}

Respond entirely in {language}.
Use clear headings and simple language.
"""
