"""
prompts.py — Reusable prompt builders for Street Vendor Growth Copilot.

Each builder returns a plain string ready to be passed to llm.generate().
All prompts:
  - Include the user's chosen output language.
  - Explicitly instruct the model NOT to invent scheme eligibility criteria,
    benefits, application deadlines, or official URLs.
  - For scheme Q&A: require reliance on supplied context and honest admission
    when that context is insufficient.
"""

from typing import Dict, Optional


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 1. Business Profile
# ---------------------------------------------------------------------------

def build_profile_prompt(vendor: Dict) -> str:
    """
    Build a prompt that generates a short digital business profile
    (suitable for WhatsApp Business, Google Business, or online listings).
    """
    language = vendor.get("language", "English")
    return f"""{_language_instruction(language)}

You are a helpful business writing assistant for small street vendors in India.

Using the vendor details below, write a friendly and professional digital business profile
of 60–100 words. The profile should mention the stall name, what it sells, its location,
and invite customers to visit or reach out. Keep the tone warm and approachable.
Do not add contact details, prices, or operating hours that were not provided.

Vendor details:
{_vendor_context(vendor)}

Write the business profile now:"""


# ---------------------------------------------------------------------------
# 2. Promotional Content
# ---------------------------------------------------------------------------

def build_promo_prompt(vendor: Dict, occasion: Optional[str] = None) -> str:
    """
    Build a prompt for a WhatsApp / social-media promotional message.
    """
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

Vendor details:
{_vendor_context(vendor)}

{occasion_line}

Write the promotional message now:"""


# ---------------------------------------------------------------------------
# 3. Digitalization Checklist
# ---------------------------------------------------------------------------

def build_checklist_prompt(vendor: Dict, context: str = "") -> str:
    """
    Build a prompt that produces a numbered digitalization checklist.
    An optional `context` string may contain RAG-retrieved document chunks.
    """
    language = vendor.get("language", "English")
    vendor_type = vendor.get("vendor_type") or "street vendor"
    context_block = (
        f"\nRelevant reference information:\n{context}\n"
        if context.strip()
        else "\nNo additional reference documents were retrieved for this query.\n"
    )

    # Food-safety step is injected only for food/beverage businesses.
    food_note = (
        "- Because this is a food business, include one step about FSSAI basic "
        "registration (for vendors with turnover below ₹12 lakh per year). "
        "Do not apply this step to other business types.\n"
        if "food" in vendor_type.lower() or "beverage" in vendor_type.lower()
        else ""
    )

    # Per-language output-quality rules placed immediately before the generation cue.
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

    return f"""You are a digital-onboarding advisor for street vendors in India.

{_SAFETY_NOTE}

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
- Never output placeholder URLs such as [official portal URL],
  [relevant program website], or [Udyam Registration link].
- Do not invent or guess government scheme names, skill-development
  programs, portal links, or official authorities.
- Do not claim that a government registration, licence, or certificate
  is mandatory unless the supplied evidence explicitly establishes it.
- Do not claim that a registration guarantees credit, tenders,
  subsidies, or other benefits.
- If reliable evidence is unavailable, recommend checking with the
  relevant official authority without inventing a link.
- Present software, marketplaces, and digital-payment providers
  only as optional examples, never as compulsory requirements.
- Prefer practical, low-cost actions that a small vendor can take
  without assuming legal obligations.
{food_note}
{context_block}
Vendor details:
{_vendor_context(vendor)}

{language_quality_note}{_language_instruction(language)}
Write the digitalization checklist now:"""


# ---------------------------------------------------------------------------
# 4. Government Scheme Q&A
# ---------------------------------------------------------------------------


def build_scheme_qa_prompt(
    question: str,
    context: str = "",
    language: str = "English",
    vendor: Optional[Dict] = None,
) -> str:
    """Build a strictly evidence-grounded government-scheme Q&A prompt."""

    _scope_refusal = {
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
"{_scope_refusal}"

EVIDENCE RULES:
1. Use only facts explicitly stated in the retrieved source evidence.
2. Never infer a fact from implication, absence of information, or general knowledge.
3. An authorized registration portal does not establish that registration is free.
4. Do not invent fees, eligibility criteria, documents, procedures, deadlines,
   URLs, benefits, or platform features.
5. Do not add steps beyond those explicitly supported by the source.
6. If the source is incomplete, ambiguous, or insufficient, say so clearly.
7. Distinguish source statements from information the source does not establish.
8. Disclose historical source dates when available.
9. Never describe retrieval scores as confidence probabilities.
10. Keep the answer concise and relevant to the question.
11. Respond entirely in the requested language: {language}.

If the evidence is insufficient, respond in {language} that you do not have enough
verified information to answer reliably and recommend checking the relevant official
government portal. Do not guess.

{_SAFETY_NOTE}
{context_block}
{vendor_block}
Vendor's question: {question}

{_language_instruction(language)}
Answer:"""
