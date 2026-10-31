"""
VendorSaathi AI — redesigned Streamlit interface.
The existing IBM watsonx.ai/Granite, prompt builders and local RAG modules are retained.
"""
import re
import streamlit as st
from llm import generate, is_configured, configuration_message
from rag import LocalRetriever
from prompts import (
    build_profile_prompt, build_promo_prompt,
    build_checklist_prompt, build_scheme_qa_prompt,
)

st.set_page_config(
    page_title="VendorSaathi AI | Street Vendor Growth Copilot",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------- Visual system ------------------------------
# VendorSaathi uses a single, consistent dark theme.
C = {
    "page": "#0d1713", "surface": "#182720", "surface_alt": "#22372c",
    "ink": "#edf5ef", "muted": "#a8bbb0", "line": "#30463a",
    "green": "#23865a", "green_hover": "#1b704a", "soft_text": "#8fe0b2",
    "input": "#17251e", "sidebar": "#111f18",
}
css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
:root {
 --page: #0d1713; --surface: #182720; --surface-alt: #22372c;
 --ink: #edf5ef; --muted: #a8bbb0; --line: #30463a;
 --green: #23865a; --green-hover: #1b704a; --soft-text: #8fe0b2;
 --input: #17251e; --sidebar: #111f18;
 color-scheme: dark;
}
html, body, [class*="css"] {font-family:'DM Sans',sans-serif}
.stApp {background:var(--page);color:var(--ink)}
.block-container {width:100%;max-width:1580px;padding:2rem clamp(1.2rem,3vw,3rem) 3.5rem}
[data-testid="stSidebar"] {background:var(--sidebar);border-right:1px solid var(--line)}
[data-testid="stSidebar"] .block-container {padding:1.5rem 1.1rem 2rem}
[data-testid="stSidebar"] * {color:var(--ink)}
.brand {display:flex;align-items:center;gap:11px;padding:8px 4px 24px}
.brandmark {width:42px;height:42px;background:#176b45;border-radius:14px;color:white!important;display:grid;place-items:center;font-size:22px}
.brandname {font-family:Manrope,sans-serif;font-size:19px;font-weight:800;letter-spacing:-.6px}
.brandtag {font-size:9px;letter-spacing:1.4px;color:var(--muted)!important;font-weight:700}
.eyebrow {font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:var(--soft-text)!important;font-weight:800}
.page-title {font-family:Manrope,sans-serif;font-size:32px;font-weight:800;letter-spacing:-1px;margin:4px 0;color:var(--ink)!important}
.subtle {color:var(--muted)!important;font-size:14px}
.hero {background:linear-gradient(115deg,#145b3a,#237b50 68%,#329260);border-radius:22px;padding:32px clamp(22px,3vw,38px);color:#fff;margin:18px 0 22px;width:100%;box-sizing:border-box}
.hero h2 {font-family:Manrope,sans-serif;font-size:27px;letter-spacing:-.7px;margin:7px 0 10px;color:#fff!important}
.hero p {color:#e4f1e8!important;max-width:760px;line-height:1.65;margin:0 0 16px}
.hero-tag {font-size:10px;letter-spacing:1.5px;color:#e2f477!important;font-weight:800}
.metric,.panel {background:var(--surface);color:var(--ink);border:1px solid var(--line);box-shadow:0 5px 18px rgba(0,0,0,.12);box-sizing:border-box}
.metric {border-radius:16px;padding:20px 21px;min-height:122px;height:100%}
.metric-label {color:var(--muted)!important;font-size:12px;font-weight:600}
.metric-value {font-family:Manrope,sans-serif;color:var(--ink)!important;font-size:29px;font-weight:800;letter-spacing:-1px;margin:9px 0 3px}
.metric-note {font-size:11px;color:var(--soft-text)!important;font-weight:700;line-height:1.45}
.panel {border-radius:18px;padding:22px 24px;margin-bottom:16px;width:100%}
.panel h3 {font-family:Manrope,sans-serif;font-size:17px;font-weight:800;margin:0 0 7px;color:var(--ink)!important}
.panel-caption {font-size:12px;color:var(--muted)!important;margin-bottom:14px;line-height:1.5}
.step {display:flex;align-items:center;gap:13px;padding:13px 0;border-bottom:1px solid var(--line)}
.step:last-child {border-bottom:0}
.step-icon {height:38px;width:38px;flex:0 0 38px;border-radius:11px;background:var(--surface-alt);color:var(--soft-text);display:grid;place-items:center;font-size:17px}
.step-title {font-size:13px;font-weight:700;color:var(--ink)!important;line-height:1.4}
.step-caption {font-size:11px;color:var(--muted)!important;line-height:1.5;margin-top:3px}
.pill {display:inline-block;border-radius:20px;padding:5px 10px;background:var(--surface-alt);color:var(--soft-text)!important;font-size:10px;font-weight:800}
.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5,.stApp strong {color:var(--ink)}
.stApp p,.stApp li,.stApp label,.stApp [data-testid="stMarkdownContainer"] {color:var(--ink)}
.stCaption,.stCaption *,[data-testid="stCaptionContainer"] {color:var(--muted)!important}
div.stButton>button[kind="primary"],.stDownloadButton>button {background:var(--green);border:1px solid var(--green);color:#fff!important;border-radius:10px;font-weight:700;padding:.65rem 1.1rem;min-height:42px}
div.stButton>button[kind="primary"]:hover,.stDownloadButton>button:hover {background:var(--green-hover);border-color:var(--green-hover);color:#fff!important}
div.stButton>button[kind="secondary"] {border-radius:10px;border-color:var(--line);color:var(--ink)!important;background:var(--surface)}
.stTextInput input,.stTextArea textarea,[data-baseweb="select"]>div {border-radius:10px!important;background:var(--input)!important;color:var(--ink)!important;border-color:var(--line)!important;min-height:42px}
input,textarea,[data-baseweb="select"] input {color:var(--ink)!important}
[data-baseweb="select"] *,[role="listbox"],[role="option"] {color:var(--ink)!important}
[data-baseweb="popover"],[data-baseweb="menu"] {background:var(--surface)!important}
[data-testid="stForm"],[data-testid="stExpander"] {border:1px solid var(--line)!important;border-radius:14px!important;background:var(--surface)!important}
[data-testid="stVerticalBlockBorderWrapper"] {background:var(--surface)!important;border:1px solid var(--line)!important;border-radius:18px!important;padding:1.15rem 1.25rem!important}
[data-testid="stForm"] {padding:16px!important}
[data-testid="stExpander"] summary,[data-testid="stExpander"] details {color:var(--ink)!important}
[data-testid="stAlert"] {border-radius:12px}
[data-testid="stMetric"] label,[data-testid="stMetricValue"] {color:var(--ink)!important}
[data-testid="stDataFrame"],[data-testid="stTable"] {background:var(--surface)}
[data-testid="stHorizontalBlock"] {gap:1rem;align-items:stretch}
[data-testid="column"] {min-width:0}
hr {border-color:var(--line)}
.stRadio label,.stCheckbox label {color:var(--ink)!important}
footer {visibility:hidden}
@media(max-width:900px) {
 .block-container {padding:1.3rem 1rem 2.5rem}
 .page-title {font-size:27px}
 .hero {padding:24px}
 .hero h2 {font-size:23px}
}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

@st.cache_resource
def get_retriever():
    try:
        return LocalRetriever()
    except (FileNotFoundError, ValueError, OSError) as exc:
        st.warning(f"Local source retrieval is unavailable: {exc}")
        return None

retriever = get_retriever()

def run_generation(prompt: str):
    if not is_configured():
        st.error("IBM watsonx.ai is not configured. " + configuration_message())
        return None
    with st.spinner("VendorSaathi is thinking with IBM Granite…"):
        result, error = generate(prompt)
    if error:
        st.error(f"Generation failed: {error}")
        return None
    return result

def validate_checklist(text: str):
    pattern = re.compile(r"^\s*(\d+)[.)]\s+\S", re.MULTILINE)
    matches = list(pattern.finditer(text))
    count = len(matches)
    if count < 5 or count > 7:
        return False, f"Expected 5–7 steps; received {count}. Please regenerate."
    last = text[matches[-1].start():].strip()
    if re.search(r"\b(and|or|but|with|for|the|to|in|of|on|as|by|at|is|are|that|which)\s*$", last, re.I) or re.search(r"[,:(]\s*$", last):
        return False, "The final step appears incomplete. Please regenerate."
    return True, ""

def get_safe_scheme_answer(question, hits):
    q = question.lower()
    evidence = " ".join(hit["text"] for hit in hits).lower()
    asks_udyam_fee = "udyam" in q and any(t in q for t in ("free","fee","charge","cost","price"))
    if asks_udyam_fee and not any(p in evidence for p in ("registration is free","registration fee is nil","no registration fee","without any fee","free of charge","no fee is charged")):
        return ("The retrieved source identifies the official Udyam Registration Portal as an authorized registration channel. However, it does not explicitly establish whether registration is free. Please verify current fee information on the official Udyam portal.")
    asks_gem_add = "gem" in q and "product" in q and any(t in q for t in ("add","adding","create","creating","list","listing","catalog"))
    if asks_gem_add and "catalog" in evidence and "add new product" in evidence:
        return ("According to the retrieved GeM seller-manual passage:\\n\\n1. Open the Catalog tab.\\n2. Select Add New Product from the dropdown menu.\\n\\nThe available passage does not establish subsequent submission or approval steps. Verify the current workflow on GeM.")
    asks_gem_docs = "gem" in q and any(t in q for t in ("document","documents","requirement","requirements","aadhaar","gstin","pan"))
    if asks_gem_docs:
        return ("The retrieved GeM seller manual excerpt contains a table of contents referring to primary and secondary seller registration. It does not establish the required documents. Please check the official GeM portal for current requirements.")
    return None

# ------------------------------ Sidebar -----------------------------------
with st.sidebar:
    st.markdown("""
    <div class="brand"><div class="brandmark">✦</div><div>
    <div class="brandname">VendorSaathi <span style="color:#238454">AI</span></div>
    <div class="brandtag">YOUR DIGITAL BUSINESS PARTNER</div></div></div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">WORKSPACE</div>', unsafe_allow_html=True)
    page = st.radio(
        "Navigation",
        ["Overview","AI Copilot","Business Profile","Promo Studio","Digitalization Checklist","Government Schemes","Knowledge Sources"],
        label_visibility="collapsed",
        format_func=lambda x: {
            "Overview":"⌂   Overview",
            "AI Copilot":"✧   AI Copilot",
            "Business Profile":"▣   Business Profile",
            "Promo Studio":"✎   Promo Studio",
            "Digitalization Checklist":"✓   Digitalization Checklist",
            "Government Schemes":"⌂   Government Schemes",
            "Knowledge Sources":"▤   Knowledge Sources",
        }[x],
    )
    st.divider()
    st.markdown('<div class="eyebrow">YOUR BUSINESS</div>', unsafe_allow_html=True)
    with st.form("vendor_form"):
        business_name = st.text_input("Business / Stall Name", value=st.session_state.get("vendor",{}).get("business_name",""), placeholder="e.g. Ramu Chaat Corner")
        vendor_type = st.selectbox("Business type", ["Food & Beverages","Clothing & Textiles","Fruits & Vegetables","Electronics & Accessories","Handicrafts & Artifacts","Other"], index=["Food & Beverages","Clothing & Textiles","Fruits & Vegetables","Electronics & Accessories","Handicrafts & Artifacts","Other"].index(st.session_state.get("vendor",{}).get("vendor_type","Food & Beverages")) if st.session_state.get("vendor",{}).get("vendor_type","Food & Beverages") in ["Food & Beverages","Clothing & Textiles","Fruits & Vegetables","Electronics & Accessories","Handicrafts & Artifacts","Other"] else 0)
        location = st.text_input("City / Area", value=st.session_state.get("vendor",{}).get("location",""), placeholder="e.g. T. Nagar, Chennai")
        products = st.text_area("Products / Services", value=st.session_state.get("vendor",{}).get("products",""), placeholder="What do you sell?", height=70)
        language = st.selectbox("Output language", ["English","Tamil","Hindi"], index=["English","Tamil","Hindi"].index(st.session_state.get("vendor",{}).get("language","English")) if st.session_state.get("vendor",{}).get("language","English") in ["English","Tamil","Hindi"] else 0)
        saved = st.form_submit_button("Save business details", use_container_width=True, type="primary")
    if saved:
        st.session_state["vendor"] = {"business_name":business_name.strip(),"vendor_type":vendor_type,"location":location.strip(),"products":products.strip(),"language":language}
        st.success("Business details saved.")
    st.markdown("---")
    st.caption("AI engine")
    if is_configured():
        st.markdown('<span class="pill">● IBM Granite connected by configuration</span>', unsafe_allow_html=True)
    else:
        st.warning("watsonx.ai credentials not configured")
    st.caption("Keep API keys in server-side environment variables. Never commit .env.")

vendor = st.session_state.get("vendor", {})
def vendor_summary():
    if not vendor: return "No business profile saved yet"
    return " · ".join(x for x in [vendor.get("business_name"),vendor.get("vendor_type"),vendor.get("location")] if x)
def guard_vendor():
    if not vendor or not vendor.get("business_name"):
        st.warning("Add and save your business details in the sidebar to use this feature.")
        return False
    return True

# ------------------------------ Header ------------------------------------
c1,c2=st.columns([4,1])
with c1:
    st.markdown('<div class="eyebrow">STREET BUSINESS, BIGGER POSSIBILITIES</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="page-title">{page}</div>',unsafe_allow_html=True)
    st.markdown('<div class="subtle">Simple digital tools and AI guidance for India’s street vendors.</div>',unsafe_allow_html=True)
with c2:
    st.markdown('<div style="text-align:right;padding-top:12px"><span class="pill">POWERED BY IBM GRANITE</span></div>',unsafe_allow_html=True)

if not is_configured():
    with st.expander("IBM watsonx.ai setup status", expanded=False):
        st.warning(configuration_message())
        st.caption("AI generation is disabled until credentials are configured on the server.")

# ------------------------------- Pages ------------------------------------
if page == "Overview":
    st.markdown(f"""
    <div class="hero">
      <div class="hero-tag">✦ YOUR AI-POWERED GROWTH PARTNER</div>
      <h2>Take your street business digital.</h2>
      <p>Build your business profile, create customer-ready promotions and understand digital onboarding — with practical guidance in your preferred language.</p>
      <div style="font-size:12px;color:#e0f0e5">Currently viewing: <b>{vendor_summary()}</b></div>
    </div>""",unsafe_allow_html=True)
    m=st.columns(4)
    metrics=[("AI features","4","Profile · Promo · Checklist · Scheme Q&A"),("Knowledge files","5","Government reference PDFs"),("Languages","3","English · Tamil · Hindi"),("AI foundation","Granite","IBM watsonx.ai")]
    for col,(label,value,note) in zip(m,metrics):
        with col:
            st.markdown(f'<div class="metric"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>',unsafe_allow_html=True)
    left,right=st.columns([1.08,.92],gap="large")
    with left:
        with st.container(border=True):
            st.markdown("### Your digital growth checklist")
            st.caption("A practical path to strengthen your online presence.")
            items=[("▣","Create a business profile","A short description for digital listings."),("✎","Prepare a customer promotion","A message ready to share on WhatsApp."),("✓","Review your digitalization steps","A tailored checklist for your business."),("⌂","Explore government information","Ask questions grounded in your uploaded references.")]
            for icon,title,desc in items:
                st.markdown(f'<div class="step"><div class="step-icon">{icon}</div><div><div class="step-title">{title}</div><div class="step-caption">{desc}</div></div></div>',unsafe_allow_html=True)
    with right:
        with st.container(border=True):
            st.markdown("### Built for practical support")
            st.caption("The existing project capabilities, now in a clearer workspace.")
            st.markdown("**IBM Granite**  \\nGenerates vendor-specific content and answers.")
            st.markdown("**Retrieval-Augmented Generation**  \\nFinds relevant passages from the provided government PDFs.")
            st.markdown("**Responsible responses**  \\nScheme answers are restricted to retrieved evidence; missing information is stated rather than guessed.")
            if retriever:
                st.success(f"Knowledge retrieval ready · {len(retriever.passages)} passages indexed")
            else:
                st.warning("Knowledge retrieval is unavailable. Check source PDFs and dependencies.")

elif page == "Business Profile":
    st.markdown('<div class="panel"><h3>Turn your stall details into a digital business profile</h3><div class="panel-caption">Create a warm, professional description for WhatsApp Business and online listings.</div>',unsafe_allow_html=True)
    if st.button("✦ Generate business profile",type="primary"):
        if guard_vendor():
            result=run_generation(build_profile_prompt(vendor))
            if result:
                st.session_state["profile_result"]=result
    if st.session_state.get("profile_result"):
        st.markdown("#### Your generated profile")
        st.write(st.session_state["profile_result"])
        st.download_button("Download profile",st.session_state["profile_result"],"vendor_business_profile.txt")
    st.markdown('</div>',unsafe_allow_html=True)

elif page == "Promo Studio":
    st.markdown('<div class="panel"><h3>Create a promotion customers will notice</h3><div class="panel-caption">Generate a short WhatsApp or social-media message in your preferred language.</div>',unsafe_allow_html=True)
    occasion=st.text_input("Occasion, offer or new arrival (optional)",placeholder="e.g. Weekend special, festive offer, fresh stock")
    if st.button("✦ Create promotional message",type="primary"):
        if guard_vendor():
            result=run_generation(build_promo_prompt(vendor,occasion=occasion.strip()))
            if result: st.session_state["promo_result"]=result
    if st.session_state.get("promo_result"):
        st.markdown("#### Ready-to-share message")
        st.write(st.session_state["promo_result"])
        st.download_button("Download promotion",st.session_state["promo_result"],"vendor_promotion.txt")
    st.markdown('</div>',unsafe_allow_html=True)

elif page == "Digitalization Checklist":
    st.markdown('<div class="panel"><h3>Your step-by-step digitalization plan</h3><div class="panel-caption">Practical suggestions tailored to your business type. Verify regulatory requirements with official authorities.</div>',unsafe_allow_html=True)
    st.info("This is general AI-generated guidance, not legal or financial advice. Applicability of registrations and licences depends on your circumstances.")
    if st.button("✦ Generate my checklist",type="primary"):
        if guard_vendor():
            result=run_generation(build_checklist_prompt(vendor,context=""))
            if result:
                valid,reason=validate_checklist(result)
                if valid: st.session_state["checklist_result"]=result
                else: st.warning(reason)
    if st.session_state.get("checklist_result"):
        st.markdown("#### Your personalized checklist")
        st.markdown(st.session_state["checklist_result"])
        st.download_button("Download checklist",st.session_state["checklist_result"],"digitalization_checklist.txt")
    st.markdown('</div>',unsafe_allow_html=True)

elif page == "Government Schemes":
    st.markdown('<div class="panel"><h3>Government scheme & registration assistant</h3><div class="panel-caption">Ask about topics covered by the reference documents. Answers are grounded in retrieved passages.</div>',unsafe_allow_html=True)
    st.info("Available knowledge includes Udyam information and GeM seller registration resources. The uploaded sources may be historical; verify current requirements on official portals.")
    question=st.text_area("What would you like to know?",placeholder="e.g. What does the Udyam document say about registration?",height=100)
    qa_language=vendor.get("language","English")
    if st.button("Ask VendorSaathi",type="primary"):
        if not question.strip():
            st.warning("Enter a question first.")
        elif retriever is None:
            st.warning("Source retrieval is unavailable. No answer was generated.")
        else:
            hits=retriever.search(question.strip(),top_k=1)
            if not hits:
                st.warning("No sufficiently relevant evidence was found in the available documents. No AI answer was generated.")
            else:
                context=retriever.format_context(question.strip(),top_k=1)
                st.markdown("#### Retrieved evidence")
                for i,hit in enumerate(hits,1):
                    with st.expander(f"Source {i}: {hit['source']} · PDF page {hit['page']}",expanded=False):
                        st.write(hit["text"])
                        st.caption(f"Retrieval relevance score: {hit['score']} — not a confidence probability. {hit['date_note']}")
                safe=get_safe_scheme_answer(question.strip(),hits)
                answer=safe if safe is not None else run_generation(build_scheme_qa_prompt(question.strip(),context,qa_language,vendor))
                if answer:
                    st.markdown("#### Answer")
                    st.write(answer)
                    st.download_button("Download answer",answer,"scheme_information_answer.txt")
    st.markdown('</div>',unsafe_allow_html=True)

elif page == "AI Copilot":
    st.markdown('<div class="panel"><h3>Ask your digital business copilot</h3><div class="panel-caption">This chat interface routes questions to the existing grounded scheme assistant. Other tasks can be opened from the workspace.</div>',unsafe_allow_html=True)
    st.caption("For this first redesign, the copilot uses the existing Government Scheme RAG workflow. Profile, promotion and checklist remain dedicated tools.")
    q=st.text_area("Your question",placeholder="How can I understand Udyam registration? / GeM seller registration requirements?",height=110,key="copilot_question")
    if st.button("Send to IBM Granite",type="primary"):
        if not q.strip(): st.warning("Type a question first.")
        elif retriever is None: st.warning("Knowledge retrieval is unavailable.")
        else:
            hits=retriever.search(q.strip(),top_k=1)
            if not hits: st.warning("I couldn't find relevant evidence in the available source documents, so I won't guess.")
            else:
                for hit in hits:
                    st.caption(f"Retrieved: {hit['source']} · PDF page {hit['page']}")
                safe=get_safe_scheme_answer(q.strip(),hits)
                ans=safe if safe is not None else run_generation(build_scheme_qa_prompt(q.strip(),retriever.format_context(q.strip(),top_k=1),vendor.get("language","English"),vendor))
                if ans: st.markdown("**VendorSaathi**"); st.write(ans)
    st.markdown('</div>',unsafe_allow_html=True)

elif page == "Knowledge Sources":
    st.markdown('<div class="panel"><h3>Knowledge base</h3><div class="panel-caption">The documents currently used by the local retrieval pipeline.</div>',unsafe_allow_html=True)
    if retriever:
        st.success(f"{len(retriever.passages)} readable passages loaded.")
        counts={}
        for passage in retriever.passages: counts[passage.source]=counts.get(passage.source,0)+1
        for name,count in counts.items():
            st.markdown(f"**{name}** — {count} passages")
    else:
        st.warning("No passages were loaded. Confirm that the PDF files are in data/government_docs.")
    st.markdown('</div>',unsafe_allow_html=True)
    st.caption("Source coverage is limited to the documents bundled with this project. The system does not claim live policy updates.")

st.markdown("<div style='padding:20px 0 0;color:var(--muted);font-size:11px;text-align:center'>VendorSaathi AI · Street Vendor Growth Copilot · IBM watsonx.ai & IBM Granite</div>",unsafe_allow_html=True)
