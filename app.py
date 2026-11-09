"""
VendorSaathi AI — redesigned Streamlit interface.
The existing IBM watsonx.ai/Granite, prompt builders and local RAG modules are retained.
"""
import re
import sqlite3
import hashlib
import secrets
import hmac
from pathlib import Path
from html import escape
import streamlit as st
from llm import generate, is_configured, configuration_message
from rag import LocalRetriever
from prompts import (
    build_profile_prompt,
    build_promo_prompt,
    build_checklist_prompt,
    build_scheme_qa_prompt,
    build_local_seo_prompt,
)
from business_profile_validation import validate_business_profile_output
from local_seo_validation import validate_local_seo_output
from scheme_answer_validation import validate_scheme_answer
from checklist_validation import (
    validate_checklist_output,
    validate_checklist_quality,
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
/* ─── Fonts ─────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');

/* ─── Design tokens ─────────────────────────────────────────────────── */
:root {
  --bg:     #0b100d;
  --panel:  #141c17;
  --line:   #29382e;
  --text:   #edf3ed;
  --muted:  #a4b2a7;
  --green:  #35d36b;
  --lime:   #a9df72;
  --input:  #111a14;
}

/* ─── Base ───────────────────────────────────────────────────────────── */
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp {
  background: radial-gradient(ellipse at 82% 0%, rgba(46,132,75,.10), transparent 34%), var(--bg) !important;
  font-size: 14px;
  color: var(--text);
}
[data-testid="stHeader"]  { background: rgba(7,17,11,.96); height: 2.8rem; }
[data-testid="stToolbar"] { right: 1rem; }
.block-container { max-width:1600px; width:100%; padding: 1rem clamp(1rem,2.1vw,2rem) 1.5rem; }

/* ─── Sidebar ────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] { background: #0e1511 !important; border-right: 1px solid #26342b !important; }
[data-testid="stSidebar"] .block-container { padding: .8rem .75rem 1.2rem !important; }

/* ─── Branding ───────────────────────────────────────────────────────── */
.brand      { display:flex; align-items:center; gap:10px; padding:5px 4px 15px; }
.brandmark  { width:39px; height:39px; flex:0 0 39px; border-radius:12px; background:linear-gradient(145deg,#8df34f,#16a45b); display:grid; place-items:center; color:#07110b !important; font-size:21px; font-weight:900; box-shadow:0 0 22px rgba(53,211,107,.18); }
.brandname  { font-family:Manrope,sans-serif; font-size:18px; font-weight:800; letter-spacing:-.5px; color:#f4fbf4; }
.brandtag   { font-size:8px; letter-spacing:1.35px; font-weight:800; color:#829989 !important; margin-top:1px; }
/* Public landing header: keep the project name below Streamlit's fixed toolbar. */
.public-brand {
  display:flex; align-items:center; gap:11px; min-height:58px;
  margin:2.2rem 0 1rem; padding:8px 0 12px;
  overflow:visible !important; box-sizing:border-box;
}
.public-brand-mark {
  width:40px; height:40px; flex:0 0 40px; display:grid; place-items:center;
  border-radius:12px; background:linear-gradient(140deg,#a4f35b,#1aa45a);
  color:#07110b !important; font-size:21px; font-weight:900;
}
.public-brand-copy {
  min-width:0; display:flex; flex-direction:column; justify-content:center;
  overflow:visible !important;
}
.public-brand-name {
  display:block; margin:0; padding:0; color:#f4fbf4 !important;
  font-family:Manrope,sans-serif; font-size:19px; font-weight:800;
  line-height:1.4 !important; letter-spacing:-.35px; white-space:nowrap;
}
.public-brand-name span { color:#a9df72 !important; }
.public-brand-tag {
  display:block; margin-top:2px; color:#a5b9aa !important;
  font-size:9px; font-weight:800; line-height:1.5 !important;
  letter-spacing:1.15px;
}
.eyebrow    { font-size:9px; letter-spacing:1.55px; text-transform:uppercase; color:var(--green) !important; font-weight:800; }
.page-title { font-family:Manrope,sans-serif; font-size:27px; font-weight:800; letter-spacing:-.9px; line-height:1.2; margin:1px 0 4px; color:var(--text) !important; }
.subtle     { font-size:13px; color:var(--muted) !important; line-height:1.5; }
.topbar     { display:flex; align-items:center; justify-content:space-between; gap:14px; margin:0 0 12px; padding:5px 0 10px; border-bottom:1px solid rgba(49,82,58,.45); }
.topbar-left { display:flex; align-items:center; gap:10px; }
.topbar-tag  { padding:7px 11px; border-radius:20px; background:#102519; border:1px solid #24442d; color:#91e6a7 !important; font-size:10px; font-weight:800; letter-spacing:.5px; }

/* ─── Hero card ──────────────────────────────────────────────────────── */
.hero { position:relative; overflow:hidden; background:linear-gradient(110deg,#102c1b 0%,#123c25 56%,#17633a 100%); border:1px solid #28623b; border-radius:15px; padding:21px 24px; margin:10px 0 12px; box-shadow:0 12px 35px rgba(0,0,0,.16); }
.hero:after { content:""; position:absolute; width:270px; height:270px; border-radius:50%; right:-70px; top:-135px; background:radial-gradient(circle,rgba(126,255,121,.18),transparent 68%); pointer-events:none; }
.hero h2 { font-family:Manrope,sans-serif; font-size:25px; line-height:1.22; letter-spacing:-.7px; margin:8px 0; color:#f5fff5 !important; }
.hero p  { font-size:13px; line-height:1.6; max-width:690px; color:#c5dfcb !important; margin:0 0 11px; }

/* ─── Metric cards ───────────────────────────────────────────────────── */
.metric       { height:100%; min-height:90px; padding:12px 14px; border:1px solid var(--line); border-radius:11px; background:linear-gradient(145deg,#14251a,#0d1a12); box-shadow:0 7px 20px rgba(0,0,0,.13); }
.metric-label { font-size:10px; color:var(--muted) !important; font-weight:600; }
.metric-value { font-family:Manrope,sans-serif; font-size:23px; font-weight:800; letter-spacing:-.8px; color:#f4fbf4 !important; margin:6px 0 1px; }
.metric-note  { font-size:9px; line-height:1.4; color:#78dc91 !important; font-weight:700; }

/* ─── Panel / feature card ───────────────────────────────────────────── */
.panel, .feature-card { background:linear-gradient(145deg,#111f16,#0d1911); border:1px solid var(--line); border-radius:12px; padding:15px 16px; margin:8px 0 11px; box-shadow:0 8px 24px rgba(0,0,0,.12); }
.panel h3, .feature-card h3 { font-family:Manrope,sans-serif; font-size:16px; font-weight:800; margin:0 0 6px; color:var(--text) !important; }
.panel-caption { font-size:11px; line-height:1.55; color:var(--muted) !important; margin:0 0 12px; }

/* ─── Card heading / chip ────────────────────────────────────────────── */
.card-heading      { display:flex; justify-content:space-between; align-items:center; gap:8px; margin-bottom:12px; }
.card-heading span { font-size:13px; font-weight:800; color:var(--text); }
.card-chip { font-size:9px; color:#8ce7a1; background:#153321; border:1px solid #275438; border-radius:20px; padding:4px 8px; }

/* ─── Step list ──────────────────────────────────────────────────────── */
.step         { display:flex; align-items:center; gap:11px; padding:8px 0; border-bottom:1px solid rgba(49,82,58,.5); }
.step:last-child { border-bottom:0; }
.step-icon    { height:31px; width:31px; flex:0 0 31px; border-radius:10px; background:#193524; border:1px solid #2b5036; color:#8cf0a5; display:grid; place-items:center; font-size:15px; }
.step-title   { font-size:11px; font-weight:700; color:var(--text) !important; line-height:1.4; }
.step-caption { font-size:10px; color:var(--muted) !important; line-height:1.45; margin-top:2px; }

/* ─── Misc ───────────────────────────────────────────────────────────── */
.pill { display:inline-block; border-radius:20px; padding:6px 10px; background:#143321; border:1px solid #285438; color:#8fe9a5 !important; font-size:9px; font-weight:900; letter-spacing:.45px; }
.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5,.stApp strong { color:var(--text); }
.stCaption, .stCaption *, [data-testid="stCaptionContainer"] { color:var(--muted) !important; }
[data-testid="stMarkdownContainer"] { color:var(--text); }
hr     { border-color:#233b2a; }
footer { visibility:hidden; }

/* ─── Forms & expanders ──────────────────────────────────────────────── */
[data-testid="stForm"] {
  background: #121a15 !important;
  border: 1px solid #2a3b30 !important;
  border-radius: 12px !important;
  padding: 15px !important;
}
[data-testid="stExpander"] { border:1px solid var(--line) !important; border-radius:12px !important; background:#121a15 !important; }
[data-testid="stVerticalBlockBorderWrapper"] { background:#121a15 !important; border:1px solid var(--line) !important; border-radius:12px !important; padding:1rem 1.05rem !important; }

/* ─── Buttons ────────────────────────────────────────────────────────── */
div.stButton > button,
button[kind="primary"],
button[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-primary"],
[data-testid="stFormSubmitButton"] button,
button[kind*="primary"] {
  min-height: 38px !important;
  padding: .48rem .85rem !important;
  border-radius: 8px !important;
  font-size: 13px !important;
}
div.stButton > button[kind="primary"],
button[kind="primary"],
button[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-primary"],
[data-testid="stFormSubmitButton"] button {
  background: linear-gradient(110deg,#239b55,#35bd68) !important;
  border: 1px solid #39c875 !important;
  color: #07120b !important;
  box-shadow: 0 3px 12px rgba(36,173,91,.13) !important;
}
div.stButton > button[kind="primary"]:hover,
button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover,
[data-testid="stFormSubmitButton"] button:hover {
  background: linear-gradient(110deg,#2eaf61,#55cf7d) !important;
  border-color: #65db8b !important;
}
div.stButton > button[kind="secondary"],
button[kind="secondary"],
button[data-testid="stBaseButton-secondary"] {
  background: #17221a !important;
  border: 1px solid #304638 !important;
  color: #e8f1e9 !important;
}
.stDownloadButton > button {
  background: linear-gradient(110deg,#239b55,#35bd68) !important;
  border: 1px solid #39c875 !important;
  color: #07120b !important;
  border-radius: 8px !important;
  font-weight: 800;
}

/* ─── Sidebar radio nav ──────────────────────────────────────────────── */
[data-testid="stRadio"] [role="radiogroup"] { gap:4px; }
[data-testid="stRadio"] label { border-radius:8px; padding:6px 8px; margin:1px 0; color:#b7c8ba !important; font-size:12px; }
[data-testid="stRadio"] label:has(input:checked) { background:linear-gradient(90deg,#173c25,#102719); border:1px solid #2c7442; color:#9df2ae !important; }
[data-testid="stRadio"] label p { font-size:12px; }

/* ─── Alerts / metrics ───────────────────────────────────────────────── */
[data-testid="stAlert"]        { border-radius:10px; }
[data-testid="stMetric"] label,
[data-testid="stMetricValue"]  { color:var(--text) !important; }

/* ─── Grid helpers ───────────────────────────────────────────────────── */
[data-testid="stHorizontalBlock"] { gap:.8rem; align-items:stretch; }
[data-testid="column"]            { min-width:0; }

/* ─── Chat ───────────────────────────────────────────────────────────── */
[data-testid="stChatMessage"] { background:#141e17 !important; border:1px solid #2b3c30 !important; border-radius:13px; padding:12px 14px; }
[data-testid="stChatInput"]   { border-color:#304638 !important; }

/* ─── Public / landing screens ───────────────────────────────────────── */
.auth-shell  { max-width:1180px; margin:1.7rem auto .8rem !important; padding:0 1rem !important; }
.auth-nav    { display:flex; align-items:center; justify-content:space-between; padding:10px 14px !important; border:1px solid #294532; border-radius:16px; background:rgba(9,22,13,.88); margin-bottom:25px !important; }
.auth-brand  { display:flex; align-items:center; gap:10px; font-family:Manrope,sans-serif; font-weight:800; font-size:18px; }
.auth-logo   { height:34px !important; width:34px !important; flex:0 0 34px !important; border-radius:12px; display:grid; place-items:center; background:linear-gradient(140deg,#a4f35b,#1aa45a); color:#07110b; font-size:20px; }
.auth-nav-note { font-size:10px; letter-spacing:1.1px; color:#9ab59f; text-transform:uppercase; font-weight:800; }
.landing-hero { padding:clamp(25px,4vw,48px) !important; border:1px solid #2b633b; border-radius:20px !important; background:radial-gradient(circle at 83% 30%,rgba(112,239,93,.18),transparent 27%),linear-gradient(115deg,#102819,#0d1a11 68%,#153a20); box-shadow:0 20px 65px rgba(0,0,0,.24); position:relative; overflow:hidden; }
.landing-kicker { font-size:10px; letter-spacing:2px; color:#a4f35b; font-weight:900; text-transform:uppercase; }
.landing-hero h1 { font-family:Manrope,sans-serif; font-size:clamp(34px,5vw,58px); line-height:1.08; letter-spacing:-2px; max-width:760px; margin:18px 0 15px; color:#f4fff4 !important; }
.landing-hero p  { font-size:15px; line-height:1.75; color:#b9cfbd !important; max-width:650px; }
.landing-orb { position:absolute; right:8%; top:22%; width:170px; height:170px; border-radius:50%; border:1px solid rgba(128,242,113,.5); box-shadow:0 0 35px rgba(49,211,90,.17),inset 0 0 35px rgba(49,211,90,.1); }
.landing-orb:before,.landing-orb:after { content:""; position:absolute; inset:17px; border:1px solid rgba(128,242,113,.38); border-radius:50%; }
.landing-orb:after { inset:35px; border-color:rgba(128,242,113,.26); }
.landing-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px !important; margin-top:15px !important; }
.landing-tile { padding:16px !important; border:1px solid #263f2d; border-radius:13px !important; background:linear-gradient(145deg,#122219,#0c1810); }
.landing-tile-icon { height:36px; width:36px; border-radius:11px; background:#1b3825; color:#9af0a9; display:grid; place-items:center; margin-bottom:13px; font-size:17px; }
.landing-tile h3 { font-size:13px !important; line-height:1.35 !important; margin:0 0 6px; color:#f1f8f1 !important; }
.landing-tile p  { font-size:11px !important; line-height:1.5 !important; color:#9aab9d !important; margin:0; }
.auth-card { max-width:520px; margin:2.5rem auto; padding:clamp(20px,4vw,34px); border:1px solid #2a4b32; border-radius:20px; background:linear-gradient(145deg,#122219,#0b1710); box-shadow:0 18px 55px rgba(0,0,0,.24); }
.auth-card h1 { font-family:Manrope,sans-serif; font-size:28px; margin:7px 0; color:#f4fff4 !important; }
.auth-card p  { font-size:12px; color:#9aab9d !important; line-height:1.6; }
.auth-foot    { text-align:center; color:#8fa394; font-size:11px; margin-top:18px; }

/* ─── Landing Page Navigation Bar ───────────────────────────────────── */
.landing-navbar {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: rgba(13, 23, 19, 0.95);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid rgba(43, 99, 59, 0.3);
  padding: 12px 0;
}
.navbar-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
}
.navbar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 0 0 auto;
}
.navbar-links {
  display: flex;
  gap: 2rem;
  align-items: center;
  flex: 1;
}
.navbar-links a {
  font-size: 13px;
  color: #c5e8cc;
  text-decoration: none;
  font-weight: 600;
  transition: color 0.2s;
}
.navbar-links a:hover {
  color: #a9df72;
}
.navbar-actions {
  display: flex;
  gap: 1rem;
  align-items: center;
  flex: 0 0 auto;
}
.navbar-signin {
  background: transparent;
  border: 1px solid #35d36b;
  color: #35d36b;
  padding: 7px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.navbar-signin:hover {
  background: rgba(53, 211, 107, 0.1);
}
.navbar-cta {
  background: linear-gradient(110deg, #239b55, #35bd68);
  color: #07120b;
  border: 1px solid #39c875;
  padding: 8px 18px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}
.navbar-cta:hover {
  background: linear-gradient(110deg, #2eaf61, #55cf7d);
  border-color: #65db8b;
}

/* ─── Landing Page Container ────────────────────────────────────────── */
.landing-container {
  background: #0b100d;
}

/* ─── Hero Section ──────────────────────────────────────────────────── */
.landing-hero-section {
  max-width: 1400px;
  margin: 0 auto;
  padding: 4rem 2rem;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4rem;
  align-items: center;
}
.hero-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}
.hero-eyebrow {
  font-size: 11px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #a9df72;
  font-weight: 800;
}
.hero-title {
  font-family: Manrope, sans-serif;
  font-size: clamp(36px, 5vw, 56px);
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -1.8px;
  color: #f4fbf4;
  margin: 0;
}
.hero-subtitle {
  font-size: 16px;
  line-height: 1.7;
  color: #b9cfbd;
  max-width: 600px;
  margin: 0;
}
.hero-cta-buttons {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}
.btn-primary {
  background: linear-gradient(110deg, #239b55, #35bd68);
  color: #07120b;
  border: 1px solid #39c875;
  padding: 11px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-primary:hover {
  background: linear-gradient(110deg, #2eaf61, #55cf7d);
  border-color: #65db8b;
  box-shadow: 0 6px 20px rgba(35, 155, 85, 0.2);
}
.btn-secondary {
  background: transparent;
  color: #a9df72;
  border: 1px solid #a9df72;
  padding: 10px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-secondary:hover {
  background: rgba(169, 223, 114, 0.1);
}
.btn-large {
  padding: 14px 32px;
  font-size: 16px;
}

.hero-visual {
  display: flex;
  align-items: center;
  justify-content: center;
}
.dashboard-mockup {
  background: linear-gradient(145deg, #141c17, #0d1911);
  border: 1px solid #2b4932;
  border-radius: 12px;
  padding: 20px;
  width: 100%;
  max-width: 500px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}
.mockup-header {
  display: flex;
  gap: 6px;
  margin-bottom: 20px;
}
.mockup-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #2a4932;
}
.mockup-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.mockup-section {
  background: rgba(19, 37, 26, 0.4);
  border: 1px solid #1f3428;
  border-radius: 8px;
  padding: 12px;
}
.mockup-label {
  font-size: 10px;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: #8fe0b2;
  font-weight: 700;
  margin-bottom: 8px;
}
.mockup-item, .mockup-feature, .mockup-stat {
  font-size: 12px;
  color: #c5e8cc;
  padding: 4px 0;
  display: flex;
  align-items: center;
}
.stat-number {
  font-size: 18px;
  font-weight: 800;
  color: #a9df72;
  margin-right: 6px;
}

/* ─── Features Section ──────────────────────────────────────────────── */
.landing-features-section {
  max-width: 1400px;
  margin: 0 auto;
  padding: 5rem 2rem;
  background: linear-gradient(180deg, rgba(11, 16, 13, 0), rgba(17, 26, 22, 0.5));
}
.section-header {
  text-align: center;
  margin-bottom: 3rem;
}
.section-header h2 {
  font-family: Manrope, sans-serif;
  font-size: clamp(32px, 4vw, 48px);
  font-weight: 800;
  line-height: 1.1;
  color: #f4fbf4;
  margin: 0 0 1rem;
}
.section-header p {
  font-size: 16px;
  color: #b9cfbd;
  max-width: 600px;
  margin: 0 auto;
}
.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 2rem;
}
.feature-card {
  background: linear-gradient(145deg, #111f16, #0d1911);
  border: 1px solid #2b4932;
  border-radius: 12px;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  transition: all 0.3s;
}
.feature-card:hover {
  border-color: #35d36b;
  box-shadow: 0 12px 40px rgba(53, 211, 107, 0.1);
  transform: translateY(-4px);
}
.feature-card.clickable-card {
  cursor: pointer;
}
.feature-card.clickable-card:active {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(53, 211, 107, 0.15);
}
.feature-icon {
  font-size: 32px;
  width: 50px;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(169, 223, 114, 0.1);
  border-radius: 10px;
}
.feature-card h3 {
  font-family: Manrope, sans-serif;
  font-size: 18px;
  font-weight: 700;
  color: #f4fbf4;
  margin: 0;
}
.feature-card p {
  font-size: 14px;
  color: #b9cfbd;
  line-height: 1.6;
  margin: 0;
}

/* ─── How It Works Section ──────────────────────────────────────────── */
.landing-how-section {
  max-width: 1400px;
  margin: 0 auto;
  padding: 5rem 2rem;
  background: #0b100d;
}
.steps-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 2rem;
  margin-top: 3rem;
}
.step-card {
  background: linear-gradient(145deg, #141c17, #0d1911);
  border: 1px solid #2b4932;
  border-radius: 12px;
  padding: 2.5rem 2rem;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}
.step-card.clickable-card {
  cursor: pointer;
  transition: all 0.3s;
}
.step-card.clickable-card:hover {
  border-color: #35d36b;
  box-shadow: 0 12px 40px rgba(53, 211, 107, 0.1);
  transform: translateY(-4px);
}
.step-card.clickable-card:active {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(53, 211, 107, 0.15);
}
.step-number {
  font-family: Manrope, sans-serif;
  font-size: 48px;
  font-weight: 800;
  color: #a9df72;
  line-height: 1;
}
.step-card h3 {
  font-family: Manrope, sans-serif;
  font-size: 20px;
  font-weight: 700;
  color: #f4fbf4;
  margin: 0;
}
.step-card p {
  font-size: 14px;
  color: #b9cfbd;
  line-height: 1.6;
  margin: 0;
}

/* ─── Why VendorSaathi Section ──────────────────────────────────────── */
.landing-why-section {
  max-width: 1400px;
  margin: 0 auto;
  padding: 5rem 2rem;
  background: linear-gradient(180deg, rgba(11, 16, 13, 0), rgba(17, 26, 22, 0.5));
}
.why-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 2rem;
  margin-top: 3rem;
}
.why-card {
  background: linear-gradient(145deg, #111f16, #0d1911);
  border: 1px solid #2b4932;
  border-radius: 12px;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  align-items: center;
  text-align: center;
}
.why-card.clickable-card {
  cursor: pointer;
  transition: all 0.3s;
}
.why-card.clickable-card:hover {
  border-color: #35d36b;
  box-shadow: 0 12px 40px rgba(53, 211, 107, 0.1);
  transform: translateY(-4px);
}
.why-card.clickable-card:active {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(53, 211, 107, 0.15);
}
.why-icon {
  font-size: 40px;
}
.why-card h3 {
  font-family: Manrope, sans-serif;
  font-size: 18px;
  font-weight: 700;
  color: #f4fbf4;
  margin: 0;
}
.why-card p {
  font-size: 14px;
  color: #b9cfbd;
  line-height: 1.6;
  margin: 0;
}

/* ─── CTA Section ───────────────────────────────────────────────────── */
.landing-cta-section {
  max-width: 1400px;
  margin: 0 auto;
  padding: 4rem 2rem;
  text-align: center;
  background: linear-gradient(110deg, #102c1b, #0d1a11);
  border-radius: 16px;
  margin: 5rem 2rem;
}
.landing-cta-section h2 {
  font-family: Manrope, sans-serif;
  font-size: clamp(28px, 4vw, 42px);
  font-weight: 800;
  color: #f4fbf4;
  margin: 0 0 1rem;
}
.landing-cta-section p {
  font-size: 16px;
  color: #b9cfbd;
  max-width: 600px;
  margin: 0 auto 2rem;
}

/* ─── Footer ────────────────────────────────────────────────────────── */
.landing-footer {
  background: #0a0f0c;
  border-top: 1px solid #1f3428;
  padding: 4rem 2rem 2rem;
}
.footer-content {
  max-width: 1400px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 3rem;
  margin-bottom: 2rem;
}
.footer-brand {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.footer-logo {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(140deg, #a4f35b, #1aa45a);
  color: #07110b;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 900;
  margin-bottom: 0.5rem;
}
.footer-title {
  font-family: Manrope, sans-serif;
  font-size: 16px;
  font-weight: 800;
  color: #f4fbf4;
}
.footer-subtitle {
  font-size: 12px;
  color: #8fa394;
}
.footer-links {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}
.footer-section h4 {
  font-size: 13px;
  font-weight: 800;
  color: #f4fbf4;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem;
}
.footer-section a {
  display: block;
  font-size: 13px;
  color: #8fa394;
  text-decoration: none;
  margin-bottom: 0.5rem;
  transition: color 0.2s;
}
.footer-section a:hover {
  color: #a9df72;
}
.footer-attribution {
  max-width: 1400px;
  margin: 0 auto;
  padding-top: 2rem;
  border-top: 1px solid #1f3428;
  text-align: center;
}
.footer-tech {
  font-size: 12px;
  color: #8fa394;
  margin-bottom: 0.5rem;
}
.footer-copy {
  font-size: 11px;
  color: #5a6b63;
}

/* ─── Home page layout ───────────────────────────────────────────────── */
.home-main { max-width:1180px !important; margin:2.1rem auto 1rem !important; padding:0 1rem !important; }
.home-main .landing-hero { min-height:0 !important; padding:42px 46px !important; border-radius:20px !important; display:flex; align-items:center; box-sizing:border-box; }
.home-main .landing-copy { position:relative; z-index:1; max-width:700px; }
.home-main .landing-hero h1 { font-size:clamp(35px,4.1vw,51px) !important; line-height:1.09 !important; letter-spacing:-1.7px !important; max-width:690px !important; margin:17px 0 14px !important; }
.home-main .landing-hero h1 span { color:#a9df72 !important; display:inline; }
.home-main .landing-hero p { font-size:14px !important; line-height:1.65 !important; max-width:650px !important; margin-bottom:0 !important; }
.home-main .landing-orb { width:142px !important; height:142px !important; right:7% !important; top:25% !important; opacity:.75; }
.home-feature-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin-top:16px; }
.home-feature-grid .landing-tile { min-width:0; padding:16px !important; min-height:145px; box-sizing:border-box; }
.home-feature-grid .landing-tile-icon { width:32px; height:32px; margin-bottom:10px; }
.home-footer { text-align:center; color:#718878; font-size:9px; letter-spacing:.35px; margin:17px 0 0; }
div[data-testid="stHorizontalBlock"]:has(button[key="home_signup"]) { max-width:1180px; margin:0 auto !important; }

/* ─── Overview page ──────────────────────────────────────────────────── */
.overview-welcome   { display:flex; justify-content:space-between; gap:20px; align-items:center; padding:19px 21px; border:1px solid #2b633b; border-radius:17px; background:linear-gradient(110deg,#102b1a,#143d24 65%,#17613a); margin:6px 0 14px; }
.overview-welcome h2 { font-family:Manrope,sans-serif; font-size:24px; line-height:1.2; margin:7px 0; color:#f5fff5 !important; }
.overview-welcome p  { font-size:12px; color:#c4dec9 !important; margin:0; line-height:1.6; }
.overview-user       { border:1px solid #41794b; border-radius:12px; background:rgba(5,20,10,.3); padding:11px 14px; min-width:130px; }
.overview-user small { display:block; color:#9bdca8; font-size:9px; text-transform:uppercase; letter-spacing:1px; }
.overview-user strong { font-size:13px; color:#fff; }
.overview-section-title { font-family:Manrope,sans-serif; font-size:15px; font-weight:800; margin:20px 0 10px; color:#f1f8f1; }
.quick-card     { height:100%; padding:14px; border-radius:14px; border:1px solid #2a4932; background:linear-gradient(145deg,#13251a,#0d1911); }
.quick-card .q-icon { font-size:19px; color:#a4f35b; margin-bottom:12px; }
.quick-card h3  { font-size:13px; margin:0 0 6px; color:#f2faf2 !important; }
.quick-card p   { font-size:11px !important; line-height:1.55; color:#9aab9d !important; min-height:28px; }
.status-row     { display:flex; align-items:center; justify-content:space-between; padding:11px 0; border-bottom:1px solid #243c2b; font-size:11px; }
.status-row:last-child { border-bottom:0; }

/* ─── Responsive ─────────────────────────────────────────────────────── */
@media(max-width:1024px) {
  .landing-hero-section {
    grid-template-columns: 1fr;
    padding: 3rem 2rem;
    gap: 2rem;
  }
  .navbar-links {
    display: none;
  }
}
@media(max-width:900px) {
  .block-container { padding:1rem .9rem 2rem; }
  .page-title { font-size:26px; }
  .hero { padding:22px; }
  .hero h2 { font-size:22px; }
  .navbar-container {
    padding: 0 1.5rem;
  }
  .navbar-actions {
    gap: 0.5rem;
  }
  .navbar-cta, .navbar-signin {
    padding: 6px 12px;
    font-size: 12px;
  }
  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media(max-width:768px) {
  .landing-hero-section {
    padding: 2rem 1.5rem;
  }
  .dashboard-mockup {
    max-width: 100%;
  }
  .navbar-container {
    gap: 1rem;
  }
  .hero-title {
    font-size: 32px;
  }
  .section-header h2 {
    font-size: 28px;
  }
  .features-grid, .steps-grid, .why-grid {
    grid-template-columns: 1fr;
  }
  .footer-content {
    grid-template-columns: 1fr;
    gap: 2rem;
  }
}
@media(max-width:760px) {
  .auth-shell { margin:1rem auto !important; }
  .auth-nav   { margin-bottom:16px !important; }
  .landing-orb { opacity:.28; right:-45px; top:20px; width:125px; height:125px; }
  .landing-grid { grid-template-columns:1fr; }
  .overview-welcome { align-items:flex-start; flex-direction:column; }
  .overview-user { width:100%; }
  .public-header-shell { margin-top:.7rem !important; }
  .home-main { margin:1.1rem auto .7rem !important; padding:0 .65rem !important; }
  .home-main .landing-hero { padding:25px 20px !important; min-height:0 !important; }
  .home-main .landing-hero h1 { font-size:34px !important; max-width:100% !important; }
  .home-main .landing-hero p  { font-size:13px !important; }
  .home-main .landing-orb { width:90px !important; height:90px !important; right:5% !important; top:8% !important; opacity:.35; }
  .home-feature-grid { grid-template-columns:1fr; gap:9px; }
  .home-feature-grid .landing-tile { min-height:0; padding:14px !important; }
  .hero { padding:17px 15px !important; }
  .metric { padding:12px !important; }
  .landing-navbar {
    padding: 8px 0;
  }
  .navbar-container {
    padding: 0 1rem;
    gap: 0.5rem;
  }
  .navbar-brand {
    font-size: 14px;
  }
  .navbar-links {
    display: none !important;
  }
  .navbar-actions {
    width: 100%;
  }
  .landing-cta-section {
    margin: 3rem 1rem;
    padding: 2rem 1.5rem;
  }
}
@media(max-width:640px) {
  .block-container { padding:.7rem .65rem 1.5rem; }
  .page-title { font-size:23px; }
  .subtle     { font-size:12px; }
  .topbar     { align-items:flex-start; flex-direction:column; }
  .hero       { border-radius:13px; }
  .hero h2    { font-size:20px; }
  .metric     { min-height:0; }
  .metric-value { font-size:23px; }
  [data-testid="stHorizontalBlock"] { flex-wrap:wrap !important; gap:.55rem !important; }
  [data-testid="stHorizontalBlock"] > [data-testid="column"] { flex:1 1 100% !important; width:100% !important; min-width:100% !important; }
  [data-testid="stSidebar"] .block-container { padding:.8rem .7rem 1.2rem; }
  div.stButton > button, .stDownloadButton > button { width:100%; white-space:normal; }
  .hero-title {
    font-size: 28px;
  }
  .hero-subtitle {
    font-size: 14px;
  }
  .hero-cta-buttons {
    flex-direction: column;
  }
  .btn-primary, .btn-secondary {
    width: 100%;
    text-align: center;
  }
  .section-header h2 {
    font-size: 24px;
  }
  .step-number {
    font-size: 36px;
  }
}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ---------------------- Local account prototype --------------------------
# Passwords are salted and hashed with PBKDF2; raw passwords are never stored.
# For public production deployment, replace this local auth layer with a managed
# identity provider and HTTPS-backed session management.
AUTH_DB = Path(__file__).with_name("vendor_users.db")

def init_auth_db():
    with sqlite3.connect(AUTH_DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                salt BLOB NOT NULL,
                password_hash BLOB NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS business_profiles (
                email      TEXT PRIMARY KEY REFERENCES users(email) ON DELETE CASCADE,
                business_name TEXT NOT NULL,
                vendor_type   TEXT NOT NULL,
                location      TEXT,
                products      TEXT,
                language      TEXT NOT NULL DEFAULT 'English',
                updated_at    TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id         INTEGER PRIMARY KEY,
                email      TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_sessions_email ON chat_sessions(email)"
        )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id         INTEGER PRIMARY KEY,
                session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                source     TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS saved_promotions (
                id         INTEGER PRIMARY KEY,
                email      TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                occasion   TEXT NOT NULL DEFAULT '',
                platform   TEXT NOT NULL DEFAULT '',
                tone       TEXT NOT NULL DEFAULT '',
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_saved_promotions_email ON saved_promotions(email)"
        )
        conn.commit()


def save_promotion(email: str, occasion: str, platform: str, tone: str, content: str) -> int:
    """Insert a saved promotion and return its integer id."""
    with sqlite3.connect(AUTH_DB) as conn:
        cur = conn.execute(
            "INSERT INTO saved_promotions(email, occasion, platform, tone, content) VALUES (?,?,?,?,?)",
            (email, occasion, platform, tone, content),
        )
        conn.commit()
        return cur.lastrowid


def load_saved_promotions(email: str, limit: int = 10) -> list:
    """Return the most-recent `limit` saved promotions for a user (newest first)."""
    with sqlite3.connect(AUTH_DB) as conn:
        rows = conn.execute(
            """
            SELECT id, occasion, platform, tone, content, created_at
            FROM saved_promotions
            WHERE email = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (email, limit),
        ).fetchall()
    return [
        {
            "id": r[0],
            "occasion": r[1],
            "platform": r[2],
            "tone": r[3],
            "content": r[4],
            "created_at": r[5],
        }
        for r in rows
    ]


def load_promotion_by_id(promo_id: int, email: str):
    """Return the full promotion row only if it belongs to `email`, else None."""
    with sqlite3.connect(AUTH_DB) as conn:
        row = conn.execute(
            "SELECT id, occasion, platform, tone, content, created_at "
            "FROM saved_promotions WHERE id = ? AND email = ?",
            (promo_id, email),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "occasion": row[1],
        "platform": row[2],
        "tone": row[3],
        "content": row[4],
        "created_at": row[5],
    }


def get_promotion_owner(promo_id: int):
    """Return the email that owns the promotion, or None if not found."""
    with sqlite3.connect(AUTH_DB) as conn:
        row = conn.execute(
            "SELECT email FROM saved_promotions WHERE id = ?", (promo_id,)
        ).fetchone()
    return row[0] if row else None


def delete_promotion(promo_id: int, email: str) -> bool:
    """Delete a promotion only if it belongs to `email`. Returns True if deleted."""
    with sqlite3.connect(AUTH_DB) as conn:
        cur = conn.execute(
            "DELETE FROM saved_promotions WHERE id = ? AND email = ?",
            (promo_id, email),
        )
        conn.commit()
    return cur.rowcount > 0


def create_chat_session(email: str) -> int:
    """Insert a new chat_sessions row and return its integer id."""
    with sqlite3.connect(AUTH_DB) as conn:
        cur = conn.execute(
            "INSERT INTO chat_sessions(email) VALUES (?)", (email,)
        )
        conn.commit()
        return cur.lastrowid


def append_chat_messages(
    session_id: int,
    user_content: str,
    assistant_content: str,
    source: str,
) -> None:
    """Persist a user+assistant exchange in a single transaction."""
    with sqlite3.connect(AUTH_DB) as conn:
        conn.execute(
            "INSERT INTO chat_messages(session_id, role, content, source) VALUES (?,?,?,?)",
            (session_id, "user", user_content, ""),
        )
        conn.execute(
            "INSERT INTO chat_messages(session_id, role, content, source) VALUES (?,?,?,?)",
            (session_id, "assistant", assistant_content, source),
        )
        conn.commit()


def load_chat_session_messages(session_id: int) -> list:
    """Return all messages for a session in chronological order."""
    with sqlite3.connect(AUTH_DB) as conn:
        rows = conn.execute(
            "SELECT role, content, source FROM chat_messages WHERE session_id=? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
    return [{"role": r[0], "content": r[1], "source": r[2]} for r in rows]


def load_latest_chat_session(email: str):
    """Return (session_id, messages) for the user's newest session, or None."""
    with sqlite3.connect(AUTH_DB) as conn:
        row = conn.execute(
            "SELECT id FROM chat_sessions WHERE email=? ORDER BY id DESC LIMIT 1",
            (email,),
        ).fetchone()
    if not row:
        return None
    session_id = row[0]
    return session_id, load_chat_session_messages(session_id)


def load_recent_chat_sessions(email: str, limit: int = 5) -> list:
    """Return up to `limit` recent sessions with id, created_at, first_question."""
    with sqlite3.connect(AUTH_DB) as conn:
        rows = conn.execute(
            """
            SELECT cs.id, cs.created_at,
                   (SELECT cm.content FROM chat_messages cm
                    WHERE cm.session_id = cs.id AND cm.role = 'user'
                    ORDER BY cm.id ASC LIMIT 1) AS first_question
            FROM chat_sessions cs
            WHERE cs.email = ?
            ORDER BY cs.id DESC
            LIMIT ?
            """,
            (email, limit),
        ).fetchall()
    return [{"id": r[0], "created_at": r[1], "first_question": r[2]} for r in rows]


def get_chat_session_owner(session_id: int):
    """Return the email that owns the session, or None if not found."""
    with sqlite3.connect(AUTH_DB) as conn:
        row = conn.execute(
            "SELECT email FROM chat_sessions WHERE id=?", (session_id,)
        ).fetchone()
    return row[0] if row else None


def load_business_profile(email: str) -> dict:
    with sqlite3.connect(AUTH_DB) as conn:
        row = conn.execute(
            "SELECT business_name, vendor_type, location, products, language "
            "FROM business_profiles WHERE email=?",
            (email,),
        ).fetchone()
    if not row:
        return {}
    return {
        "business_name": row[0],
        "vendor_type": row[1],
        "location": row[2] or "",
        "products": row[3] or "",
        "language": row[4],
    }


def upsert_business_profile(email: str, vendor: dict) -> None:
    with sqlite3.connect(AUTH_DB) as conn:
        conn.execute(
            """
            INSERT INTO business_profiles(email, business_name, vendor_type, location, products, language, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(email) DO UPDATE SET
                business_name = excluded.business_name,
                vendor_type   = excluded.vendor_type,
                location      = excluded.location,
                products      = excluded.products,
                language      = excluded.language,
                updated_at    = CURRENT_TIMESTAMP
            """,
            (
                email,
                vendor.get("business_name", ""),
                vendor.get("vendor_type", ""),
                vendor.get("location", ""),
                vendor.get("products", ""),
                vendor.get("language", "English"),
            ),
        )
        conn.commit()

def password_digest(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240000)

def create_account(full_name: str, email: str, password: str):
    normalized_email = email.strip().lower()
    salt = secrets.token_bytes(16)
    digest = password_digest(password, salt)
    try:
        with sqlite3.connect(AUTH_DB) as conn:
            conn.execute(
                "INSERT INTO users(email, full_name, salt, password_hash) VALUES(?,?,?,?)",
                (normalized_email, full_name.strip(), salt, digest),
            )
            conn.commit()
        return True, "Account created. You can now sign in."
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."

def verify_account(email: str, password: str):
    normalized_email = email.strip().lower()
    with sqlite3.connect(AUTH_DB) as conn:
        row = conn.execute(
            "SELECT full_name, salt, password_hash FROM users WHERE email=?",
            (normalized_email,),
        ).fetchone()
    if not row:
        return None
    full_name, salt, stored_hash = row
    if hmac.compare_digest(password_digest(password, salt), stored_hash):
        return {"email": normalized_email, "full_name": full_name}
    return None

init_auth_db()

if "auth_view" not in st.session_state:
    st.session_state["auth_view"] = "Home"
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def show_public_nav():
    st.markdown("""
    <div class="public-brand">
      <div class="public-brand-mark" aria-hidden="true">✦</div>
      <div class="public-brand-copy">
        <span class="public-brand-name">VendorSaathi <span>AI</span></span>
        <span class="public-brand-tag">YOUR DIGITAL BUSINESS PARTNER</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_home():
    show_public_nav()

    # ── Hero ─────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="hero" style="margin-bottom:18px;">
      <div class="landing-kicker">✦ BUILT FOR INDIA'S STREET VENDORS</div>
      <h2 style="font-family:Manrope,sans-serif;font-size:clamp(26px,3.5vw,40px);
                 font-weight:800;letter-spacing:-1px;margin:10px 0 10px;color:#f5fff5;">
        Take Your Street Business Digital
      </h2>
      <p style="font-size:14px;line-height:1.7;color:#b9cfbd;max-width:640px;margin:0;">
        VendorSaathi AI helps you create professional business profiles, reach more customers,
        craft engaging promotions, and access government schemes — all powered by IBM Granite AI.
      </p>
      <div class="landing-orb"></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Feature pills ─────────────────────────────────────────────────────
    st.markdown("""
    <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px;">
      <span class="pill">✧ AI Copilot</span>
      <span class="pill">▣ Business Profile</span>
      <span class="pill">⌖ Local SEO</span>
      <span class="pill">✎ Promo Studio</span>
      <span class="pill">✓ Digitalization Checklist</span>
      <span class="pill">⌂ Government Schemes</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Sign in / Sign up cards side by side ──────────────────────────────
    login_col, signup_col = st.columns(2, gap="large")

    with login_col:
        with st.container(border=True):
            st.markdown('<div class="eyebrow">EXISTING USER</div>', unsafe_allow_html=True)
            st.markdown("### Sign in")
            st.caption("Access your vendor workspace and saved data.")
            with st.form("home_login_form"):
                email_l = st.text_input("Email address", placeholder="you@example.com", key="hl_email")
                password_l = st.text_input("Password", type="password", placeholder="Your password", key="hl_pass")
                submitted_l = st.form_submit_button("Sign in →", type="primary", use_container_width=True)
            if submitted_l:
                account = verify_account(email_l, password_l)
                if account:
                    st.session_state["authenticated"] = True
                    st.session_state["account"] = account
                    st.session_state["auth_view"] = "App"
                    st.rerun()
                else:
                    st.error("Email or password is incorrect.")

    with signup_col:
        with st.container(border=True):
            st.markdown('<div class="eyebrow">NEW USER</div>', unsafe_allow_html=True)
            st.markdown("### Create account")
            st.caption("Free to use — set up in under 2 minutes.")
            with st.form("home_signup_form"):
                full_name_s = st.text_input("Your name", placeholder="e.g. ABC", key="hs_name")
                email_s = st.text_input("Email address", placeholder="you@example.com", key="hs_email")
                password_s = st.text_input("Password (min 8 chars)", type="password", key="hs_pass")
                confirm_s = st.text_input("Confirm password", type="password", key="hs_confirm")
                submitted_s = st.form_submit_button("Create account →", type="primary", use_container_width=True)
            if submitted_s:
                if not full_name_s.strip() or not email_s.strip() or not password_s:
                    st.error("Please complete all fields.")
                elif "@" not in email_s or "." not in email_s.split("@")[-1]:
                    st.error("Enter a valid email address.")
                elif len(password_s) < 8:
                    st.error("Password must be at least 8 characters.")
                elif password_s != confirm_s:
                    st.error("Passwords do not match.")
                else:
                    ok, message = create_account(full_name_s, email_s, password_s)
                    if ok:
                        st.success("Account created! Sign in on the left.")
                    else:
                        st.error(message)

    st.markdown('<div class="home-footer">Powered by IBM watsonx.ai · IBM Granite · © 2025 VendorSaathi</div>', unsafe_allow_html=True)


def render_login():
    show_public_nav()
    left, center, right = st.columns([1, 1.12, 1], gap="small")
    with center:
        with st.container(border=True):
            st.markdown('<div class="eyebrow">WELCOME BACK</div><h1 style="font-family:Manrope,sans-serif;font-size:25px;margin:6px 0;color:#edf3ed">Sign in to VendorSaathi</h1><p style="font-size:12px;color:#a4b2a7;margin:0 0 13px">Continue managing your digital business with your AI assistant.</p>', unsafe_allow_html=True)
            with st.form("login_form"):
                email = st.text_input("Email address", placeholder="you@example.com")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
            if submitted:
                account = verify_account(email, password)
                if account:
                    st.session_state["authenticated"] = True
                    st.session_state["account"] = account
                    st.session_state["auth_view"] = "App"
                    st.rerun()
                else:
                    st.error("Email or password is incorrect.")
            if st.button("← Back to home", key="login_back"):
                st.session_state["auth_view"] = "Home"
                st.rerun()
            st.markdown('<div class="auth-foot">New to VendorSaathi? Create an account from the home page.</div>', unsafe_allow_html=True)

def render_signup():
    show_public_nav()
    left, center, right = st.columns([1, 1.12, 1], gap="small")
    with center:
        with st.container(border=True):
            st.markdown('<div class="eyebrow">JOIN VENDORSAATHI</div><h1 style="font-family:Manrope,sans-serif;font-size:25px;margin:6px 0;color:#edf3ed">Create your account</h1><p style="font-size:12px;color:#a4b2a7;margin:0 0 13px">Set up your account to access your vendor workspace.</p>', unsafe_allow_html=True)
            with st.form("signup_form"):
                full_name = st.text_input("Your name", placeholder="e.g. ABC")
                email = st.text_input("Email address", placeholder="you@example.com")
                password = st.text_input("Create password", type="password", help="Use at least 8 characters.")
                confirm = st.text_input("Confirm password", type="password")
                submitted = st.form_submit_button("Create account", type="primary", use_container_width=True)
            if submitted:
                if not full_name.strip() or not email.strip() or not password:
                    st.error("Please complete all fields.")
                elif "@" not in email or "." not in email.split("@")[-1]:
                    st.error("Enter a valid email address.")
                elif len(password) < 8:
                    st.error("Use a password with at least 8 characters.")
                elif password != confirm:
                    st.error("The passwords do not match.")
                else:
                    ok, message = create_account(full_name, email, password)
                    if ok:
                        st.success(message)
                        st.session_state["auth_view"] = "Login"
                    else:
                        st.error(message)
            if st.button("← Back to home", key="signup_back"):
                st.session_state["auth_view"] = "Home"
                st.rerun()
            st.markdown('<div class="auth-foot">Your password is stored as a salted hash in the local account database.</div>', unsafe_allow_html=True)


if not st.session_state["authenticated"]:
    view = st.session_state["auth_view"]
    if view == "Login":
        render_login()
    elif view == "Signup":
        render_signup()
    else:
        render_home()
    st.stop()

# Load the authenticated user's business profile once per session (covers login rerun
# and browser refresh while already authenticated).
if st.session_state.get("authenticated") and "vendor" not in st.session_state:
    _email = st.session_state.get("account", {}).get("email", "")
    if _email:
        st.session_state["vendor"] = load_business_profile(_email)

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

def parse_checklist_steps(text: str):
    """Return the numbered action items from a generated checklist."""
    return [
        match.group(1).strip()
        for match in re.finditer(r"^\s*\d+[.)]\s+(.+?)\s*$", text, re.MULTILINE)
        if match.group(1).strip()
    ]


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
    
    # Udyam fee question with explicit free-registration evidence
    asks_udyam_fee = "udyam" in q and any(t in q for t in ("free","fee","charge","cost","price"))
    if asks_udyam_fee:
        # Check for multiple variations of "registration is free" statement
        has_free_evidence = any(p in evidence for p in (
            "totally free",
            "registration is free",
            "registration fee is nil",
            "no registration fee",
            "without any fee",
            "free of charge",
            "no fee is charged",
            "no costs or fees",
            "no cost or fee",
        ))
        
        if not has_free_evidence:
            return (
                "The retrieved source identifies the official Udyam Registration Portal as an authorized "
                "registration channel. However, it does not explicitly establish whether registration is free. "
                "Please verify current fee information on the official Udyam portal."
            )
    
    asks_gem_add = "gem" in q and "product" in q and any(t in q for t in ("add","adding","create","creating","list","listing","catalog"))
    if asks_gem_add and "catalog" in evidence and "add new product" in evidence:
        return (
            "According to the retrieved GeM seller-manual passage:\n\n"
            "1. Open the Catalog tab.\n"
            "2. Select Add New Product from the dropdown menu.\n\n"
            "The available passage does not establish subsequent submission or approval steps. "
            "Verify the current workflow on GeM."
        )
    asks_gem_docs = "gem" in q and any(t in q for t in ("document","documents","requirement","requirements","aadhaar","gstin","pan"))
    if asks_gem_docs:
        return (
            "The retrieved GeM seller manual excerpt contains a table of contents referring to "
            "primary and secondary seller registration. It does not establish the required documents. "
            "Please check the official GeM portal for current requirements."
        )
    return None

# ------------------------------ Navigation callbacks ----------------------
def navigate_to(page_name: str):
    """Update the radio widget value before the next script run creates it."""
    st.session_state["selected_page"] = page_name


def _clean_response(text: str) -> str:
    """Normalise escape sequences in LLM responses so they render correctly.

    Granite sometimes returns literal backslash-n sequences (the two characters
    '\\' and 'n') instead of real newlines. This function converts them to real
    newlines so that st.markdown renders paragraphs, numbered lists, etc.
    """
    if not isinstance(text, str):
        return text
    # Replace literal \n  (backslash + n) with a real newline.
    # Use a careful approach: only replace \\n that are NOT already a real newline.
    # Python stores the literal two-char sequence as '\\n' in a string variable.
    cleaned = text.replace("\\n", "\n")
    # Collapse sequences of 3+ newlines to a maximum of two (one blank line).
    import re as _re
    cleaned = _re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


# ------------------------------ Sidebar -----------------------------------
with st.sidebar:
    st.markdown("""
    <div class="brand"><div class="brandmark">✦</div><div>
    <div class="brandname">VendorSaathi <span style="color:#238454">AI</span></div>
    <div class="brandtag">YOUR DIGITAL BUSINESS PARTNER</div></div></div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">WORKSPACE NAVIGATION</div>', unsafe_allow_html=True)
    nav_pages = ["Overview","AI Copilot","Business Profile","Local SEO", "Promo Studio","Digitalization Checklist","Government Schemes","Knowledge Sources"]
    if "selected_page" not in st.session_state:
        st.session_state["selected_page"] = "Overview"
    page = st.radio(
        "Navigation",
        nav_pages,
        key="selected_page",
        label_visibility="collapsed",
        format_func=lambda x: {
            "Overview":"⌂   Overview",
            "AI Copilot":"✧   AI Copilot",
            "Business Profile":"▣   Business Profile",
            "Local SEO": "⌖   Local SEO",
            "Promo Studio":"✎   Promo Studio",
            "Digitalization Checklist":"✓   Digitalization Checklist",
            "Government Schemes":"⌂   Government Schemes",
            "Knowledge Sources":"▤   Knowledge Sources",
        }[x],
    )
    st.divider()
    st.markdown('<div class="eyebrow">VENDOR PROFILE</div>', unsafe_allow_html=True)
    sidebar_vendor = st.session_state.get("vendor", {})
    if sidebar_vendor.get("business_name"):
        st.markdown(
            f'<div class="panel" style="padding:12px;margin:7px 0">'
            f'<div style="font-weight:800;font-size:13px">{escape(sidebar_vendor.get("business_name", ""))}</div>'
            f'<div class="step-caption">{escape(sidebar_vendor.get("vendor_type", "Business type not set"))}</div>'
            f'<div class="step-caption">{escape(sidebar_vendor.get("location") or "Location not added")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("No business profile saved yet.")
    st.button(
        "✎ Edit business profile",
        use_container_width=True,
        key="sidebar_edit_profile",
        on_click=navigate_to,
        args=("Business Profile",),
    )
    st.markdown("---")
    st.caption("AI engine")
    if is_configured():
        st.markdown('<span class="pill">● IBM Granite connected by configuration</span>', unsafe_allow_html=True)
    else:
        st.warning("watsonx.ai credentials not configured")
    st.caption("Keep API keys in server-side environment variables. Never commit .env.")
    st.markdown("---")
    if st.button("↪ Sign out", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["account"] = {}
        st.session_state["auth_view"] = "Home"
        st.session_state.pop("vendor", None)
        st.session_state.pop("profile_result", None)
        st.session_state.pop("promo_result", None)
        st.session_state.pop("promo_settings", None)
        st.session_state.pop("checklist_result", None)
        st.session_state.pop("copilot_messages", None)
        st.session_state.pop("_copilot_session_id", None)
        st.rerun()

vendor = st.session_state.get("vendor", {})
def vendor_summary():
    if not vendor: return "No business profile saved yet"
    return " · ".join(escape(str(x)) for x in [vendor.get("business_name"),vendor.get("vendor_type"),vendor.get("location")] if x)
def guard_vendor():
    if not vendor or not vendor.get("business_name"):
        st.warning("Add and save your business details in the sidebar to use this feature.")
        return False
    return True

# ------------------------------ Header ------------------------------------
st.markdown(f"""
<div class="topbar">
  <div class="topbar-left">
    <div>
      <div class="eyebrow">VENDORSAATHI AI · STREET VENDOR WORKSPACE</div>
      <div class="page-title">{escape(page)}</div>
      <div class="subtle">Practical digital tools and AI guidance for your business.</div>
    </div>
  </div>
  <div class="topbar-tag">✦ POWERED BY IBM GRANITE</div>
</div>
""", unsafe_allow_html=True)

if not is_configured():
    with st.expander("IBM watsonx.ai setup status", expanded=False):
        st.warning(configuration_message())
        st.caption("AI generation is disabled until credentials are configured on the server.")

# ------------------------------- Pages ------------------------------------
if page == "Overview":
    account = st.session_state.get("account", {})
    display_name = account.get("full_name", "Vendor")
    source_count = len({p.source for p in retriever.passages}) if retriever else 0

    # ── Welcome bar ──────────────────────────────────────────────────────
    st.markdown(f"""
    <section class="overview-welcome">
      <div>
        <div class="eyebrow">WELCOME TO VENDORSAATHI AI</div>
        <h2>Hello, {escape(display_name.split()[0])}.</h2>
        <p>Your AI-powered workspace for digitizing and growing your street business.</p>
      </div>
    </section>
    """, unsafe_allow_html=True)

    # ── Business profile summary ─────────────────────────────────────────
    st.markdown('<div class="overview-section-title">Your business profile</div>', unsafe_allow_html=True)
    if vendor.get("business_name"):
        prof_cols = st.columns([2, 2, 2, 1], gap="small")
        with prof_cols[0]:
            st.markdown(
                f'<div class="metric"><div class="metric-label">BUSINESS NAME</div>'
                f'<div style="font-weight:800;font-size:15px;margin-top:8px;color:#f4fbf4">'
                f'{escape(vendor.get("business_name",""))}</div></div>',
                unsafe_allow_html=True,
            )
        with prof_cols[1]:
            st.markdown(
                f'<div class="metric"><div class="metric-label">CATEGORY</div>'
                f'<div style="font-weight:700;font-size:13px;margin-top:8px;color:#c5e8cc">'
                f'{escape(vendor.get("vendor_type",""))}</div></div>',
                unsafe_allow_html=True,
            )
        with prof_cols[2]:
            st.markdown(
                f'<div class="metric"><div class="metric-label">LOCATION</div>'
                f'<div style="font-weight:700;font-size:13px;margin-top:8px;color:#c5e8cc">'
                f'{escape(vendor.get("location") or "Not set")}</div></div>',
                unsafe_allow_html=True,
            )
        with prof_cols[3]:
            st.button(
                "Edit profile",
                key="dash_edit_profile",
                use_container_width=True,
                on_click=navigate_to,
                args=("Business Profile",),
            )
    else:
        with st.container(border=True):
            st.markdown(
                '<div class="card-heading">'
                '<span>No business profile saved yet</span>'
                '<span class="card-chip">ACTION NEEDED</span>'
                '</div>',
                unsafe_allow_html=True,
            )
            st.caption("Add your business name, category, location and products to unlock all AI tools.")
            st.button(
                "✎ Create your business profile",
                type="primary",
                key="dash_create_profile",
                on_click=navigate_to,
                args=("Business Profile",),
            )

    # ── Feature navigation cards ─────────────────────────────────────────
    st.markdown('<div class="overview-section-title">Tools</div>', unsafe_allow_html=True)

    _tool_cards = [
        ("✧", "AI Copilot",
         "Ask free-form questions about your business and get AI-powered guidance.",
         "AI Copilot"),
        ("▣", "Business Profile",
         "Build a factual digital description for your stall that customers can read.",
         "Business Profile"),
        ("⌖", "Local SEO",
         "Generate keywords, listing text and visibility actions for local search.",
         "Local SEO"),
        ("✎", "Promo Studio",
         "Create ready-to-share WhatsApp and social media promotional messages.",
         "Promo Studio"),
        ("✓", "Digitalization Checklist",
         "Get a practical step-by-step plan for taking your business digital.",
         "Digitalization Checklist"),
        ("⌂", "Government Schemes",
         "Ask questions grounded in official PDF documents on PM SVANidhi, Udyam, GeM and BHIM.",
         "Government Schemes"),
        ("▤", "Knowledge Sources",
         "Browse and inspect the government PDFs indexed as reference material.",
         "Knowledge Sources"),
    ]

    # Render cards in rows of 4 then 3 to avoid awkward single-card rows
    row1, row2 = _tool_cards[:4], _tool_cards[4:]
    for row in (row1, row2):
        cols = st.columns(len(row), gap="small")
        for col, (ico, title, desc, target) in zip(cols, row):
            with col:
                st.markdown(
                    f'<div class="quick-card">'
                    f'<div class="q-icon">{ico}</div>'
                    f'<h3>{title}</h3>'
                    f'<p>{desc}</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.button(
                    "Open →",
                    key=f"dash_{target}",
                    use_container_width=True,
                    on_click=navigate_to,
                    args=(target,),
                )

    # ── System status ────────────────────────────────────────────────────
    st.markdown('<div class="overview-section-title">System status</div>', unsafe_allow_html=True)
    stat_cols = st.columns([1.6, 1, 1, 1], gap="small")
    with stat_cols[0]:
        ai_color = "#78e69a" if is_configured() else "#f0c36b"
        ai_label = "IBM Granite — configured" if is_configured() else "IBM Granite — not configured"
        st.markdown(
            f'<div class="metric"><div class="metric-label">AI ENGINE</div>'
            f'<div style="font-size:12px;font-weight:700;margin-top:8px;color:{ai_color}">'
            f'{ai_label}</div></div>',
            unsafe_allow_html=True,
        )
    with stat_cols[1]:
        rag_color = "#78e69a" if retriever else "#f0c36b"
        rag_label = "Ready" if retriever else "Unavailable"
        st.markdown(
            f'<div class="metric"><div class="metric-label">REFERENCE LIBRARY</div>'
            f'<div class="metric-value" style="color:{rag_color}">{rag_label}</div>'
            f'<div class="metric-note">{source_count} PDF sources indexed</div></div>',
            unsafe_allow_html=True,
        )
    with stat_cols[2]:
        st.markdown(
            '<div class="metric"><div class="metric-label">LANGUAGES</div>'
            '<div class="metric-value">3</div>'
            '<div class="metric-note">English · Tamil · Hindi</div></div>',
            unsafe_allow_html=True,
        )
    with stat_cols[3]:
        passage_count = len(retriever.passages) if retriever else 0
        st.markdown(
            f'<div class="metric"><div class="metric-label">INDEXED PASSAGES</div>'
            f'<div class="metric-value">{passage_count}</div>'
            f'<div class="metric-note">Deduplicated chunks</div></div>',
            unsafe_allow_html=True,
        )

elif page == "Business Profile":
    st.markdown('<div class="feature-card"><div class="eyebrow">BUSINESS IDENTITY</div><h3>Build your digital business profile</h3><div class="panel-caption">Add the details customers need to understand what you sell and where to find you. Your saved details are used by the AI tools across VendorSaathi.</div></div>', unsafe_allow_html=True)

    current_vendor = st.session_state.get("vendor", {})
    with st.container(border=True):
        st.markdown('<div class="card-heading"><span>Business details</span><span class="card-chip">EDIT PROFILE</span></div>', unsafe_allow_html=True)
        with st.form("business_profile_editor"):
            edit_name = st.text_input("Business / stall name", value=current_vendor.get("business_name", ""), placeholder="e.g. Ramu Chaat Corner")
            type_options = ["Food & Beverages", "Clothing & Textiles", "Fruits & Vegetables", "Electronics & Accessories", "Handicrafts & Artifacts", "Other"]
            saved_type = current_vendor.get("vendor_type", "Food & Beverages")
            edit_type = st.selectbox("Business category", type_options, index=type_options.index(saved_type) if saved_type in type_options else 0)
            edit_location = st.text_input("City / area", value=current_vendor.get("location", ""), placeholder="e.g. T. Nagar, Chennai")
            edit_products = st.text_area("Products or services", value=current_vendor.get("products", ""), placeholder="List your main products or services", height=85)
            language_options = ["English", "Tamil", "Hindi"]
            saved_language = current_vendor.get("language", "English")
            edit_language = st.selectbox("Profile language", language_options, index=language_options.index(saved_language) if saved_language in language_options else 0)
            save_profile = st.form_submit_button("Save business details", type="primary", use_container_width=True)
        if save_profile:
            if not edit_name.strip():
                st.error("Enter your business or stall name before saving.")
            else:
                st.session_state["vendor"] = {
                    "business_name": edit_name.strip(), "vendor_type": edit_type,
                    "location": edit_location.strip(), "products": edit_products.strip(),
                    "language": edit_language,
                }
                upsert_business_profile(
                    st.session_state["account"]["email"],
                    st.session_state["vendor"],
                )
                st.success("Business details saved. You can now generate your profile.")
                st.rerun()

    vendor = st.session_state.get("vendor", {})
    st.markdown('<div class="card-heading"><span>Profile preview</span><span class="card-chip">AI-GENERATED</span></div>', unsafe_allow_html=True)
    if vendor.get("business_name"):
        pcols = st.columns(3)
        with pcols[0]:
            st.markdown(f'<div class="metric"><div class="metric-label">BUSINESS</div><div style="font-weight:800;margin-top:8px">{escape(vendor.get("business_name", ""))}</div></div>', unsafe_allow_html=True)
        with pcols[1]:
            st.markdown(f'<div class="metric"><div class="metric-label">CATEGORY</div><div style="font-weight:800;margin-top:8px">{escape(vendor.get("vendor_type", ""))}</div></div>', unsafe_allow_html=True)
        with pcols[2]:
            st.markdown(f'<div class="metric"><div class="metric-label">LOCATION</div><div style="font-weight:800;margin-top:8px">{escape(vendor.get("location") or "Not added")}</div></div>', unsafe_allow_html=True)
        st.caption("Products / services: " + (vendor.get("products") or "Not added yet"))
        if st.button("✦ Generate business profile", type="primary", key="generate_business_profile"):
            if guard_vendor():
                st.session_state.pop("profile_result", None)
                st.session_state.pop("profile_validation_issues", None)
                result = run_generation(build_profile_prompt(vendor))
                if result:
                    is_valid, issues = validate_business_profile_output(result, vendor)
                    if is_valid:
                        st.session_state["profile_result"] = result
                    else:
                        st.session_state["profile_validation_issues"] = issues
    else:
        st.info("Add your business details above to create a customer-ready profile.")

    if st.session_state.get("profile_validation_issues"):
        st.warning(
            "This profile was not saved, displayed or made downloadable because "
            "it contains claims or details not confirmed by your Business Profile. "
            "Please regenerate after checking your saved details."
        )
        for issue in st.session_state["profile_validation_issues"]:
            st.write(f"- {issue}")

    if st.session_state.get("profile_result"):
        st.markdown("#### Your generated profile")
        with st.container(border=True):
            st.markdown(st.session_state["profile_result"])
        st.download_button("Download profile", st.session_state["profile_result"], "vendor_business_profile.txt", key="download_profile")

elif page == "Promo Studio":
    st.markdown('<div class="feature-card"><div class="eyebrow">CUSTOMER ENGAGEMENT</div><h3>Create a promotion customers will notice</h3><div class="panel-caption">Prepare a clear, ready-to-share message for WhatsApp or social media. The message uses your saved business details and preferred language.</div></div>', unsafe_allow_html=True)
    vendor = st.session_state.get("vendor", {})
    with st.container(border=True):
        st.markdown('<div class="card-heading"><span>Promotion details</span><span class="card-chip">MESSAGE BUILDER</span></div>', unsafe_allow_html=True)
        with st.form("promo_builder_form"):
            occasion = st.text_input("Offer, occasion or new arrival", placeholder="e.g. Weekend special, festive offer, fresh stock")
            platform = st.selectbox("Where will you share this?", ["WhatsApp", "Instagram", "Facebook", "General social media"])
            tone = st.selectbox("Message style", ["Friendly and welcoming", "Festive and energetic", "Simple and informative", "Special offer focused"])
            promo_submitted = st.form_submit_button("✦ Create promotional message", type="primary", use_container_width=True)
    if promo_submitted:
        if guard_vendor():
            prompt = build_promo_prompt(vendor, occasion=occasion.strip())
            prompt += f"\n\nChannel: {platform}. Tone: {tone}. Adapt the format to this channel. Do not invent prices, discounts, contact details or claims."
            result = run_generation(prompt)
            if result:
                st.session_state["promo_result"] = result
                st.session_state["promo_settings"] = {
                    "occasion": occasion.strip(), "platform": platform, "tone": tone
                }
    if st.session_state.get("promo_result"):
        st.markdown('<div class="card-heading"><span>Ready-to-share message</span><span class="card-chip">YOUR DRAFT</span></div>', unsafe_allow_html=True)
        with st.container(border=True):
            # st.code provides a built-in copy control and preserves line breaks.
            st.code(st.session_state["promo_result"], language=None)
        promo_col1, promo_col2, promo_col3, promo_col4 = st.columns([1, 1, 1, 1])
        with promo_col1:
            st.download_button(
                "Download promotion", st.session_state["promo_result"],
                "vendor_promotion.txt", key="download_promo", use_container_width=True
            )
        with promo_col2:
            if st.button("↻ Regenerate message", key="regenerate_promo", use_container_width=True):
                settings = st.session_state.get("promo_settings", {})
                if guard_vendor():
                    prompt = build_promo_prompt(
                        vendor, occasion=settings.get("occasion", "")
                    )
                    prompt += (
                        f"\\n\\nChannel: {settings.get('platform', 'WhatsApp')}. "
                        f"Tone: {settings.get('tone', 'Friendly and welcoming')}. "
                        "Adapt the format to this channel. Do not invent prices, "
                        "discounts, contact details or claims."
                    )
                    regenerated = run_generation(prompt)
                    if regenerated:
                        st.session_state["promo_result"] = regenerated
                        st.rerun()
        with promo_col3:
            if st.button("Clear draft", key="clear_promo", use_container_width=True):
                st.session_state.pop("promo_result", None)
                st.session_state.pop("promo_settings", None)
                st.rerun()
        with promo_col4:
            _promo_content = st.session_state.get("promo_result", "")
            _promo_settings = st.session_state.get("promo_settings", {})
            _promo_saved_key = f"_promo_saved_{hash(_promo_content)}"
            _already_saved = st.session_state.get(_promo_saved_key, False)
            if _already_saved:
                st.success("Promotion saved successfully!")
            elif st.button("★ Save to library", key="save_promo", use_container_width=True):
                if _promo_content.strip():
                    _promo_email = st.session_state["account"]["email"]
                    save_promotion(
                        _promo_email,
                        _promo_settings.get("occasion", ""),
                        _promo_settings.get("platform", ""),
                        _promo_settings.get("tone", ""),
                        _promo_content,
                    )
                    st.session_state[_promo_saved_key] = True
                    st.rerun()

        # Saved promotions library (collapsed by default)
        _lib_email = st.session_state["account"]["email"]
        _saved = load_saved_promotions(_lib_email, limit=10)
        with st.expander(f"★ Saved promotions ({len(_saved)} saved)", expanded=False):
            if _saved:
                for _promo in _saved:
                    _p_occasion = _promo["occasion"] or "No occasion"
                    _p_date = (_promo["created_at"] or "")[:10]
                    _p_platform = _promo["platform"] or ""
                    st.markdown(
                        f'<div class="step"><div class="step-icon">◎</div>'
                        f'<div><div class="step-title">{escape(_p_occasion[:55])} · {escape(_p_platform)}</div>'
                        f'<div class="step-caption">{escape(_p_date)}</div></div></div>',
                        unsafe_allow_html=True,
                    )
                    _lib_col1, _lib_col2 = st.columns([1, 1])
                    with _lib_col1:
                        if st.button("Load", key=f"load_promo_{_promo['id']}", use_container_width=True):
                            _loaded = load_promotion_by_id(_promo["id"], _lib_email)
                            if _loaded:
                                st.session_state["promo_result"] = _loaded["content"]
                                st.session_state["promo_settings"] = {
                                    "occasion": _loaded["occasion"],
                                    "platform": _loaded["platform"],
                                    "tone": _loaded["tone"],
                                }
                                st.rerun()
                    with _lib_col2:
                        if st.button("Delete", key=f"delete_promo_{_promo['id']}", use_container_width=True):
                            delete_promotion(_promo["id"], _lib_email)
                            st.rerun()
            else:
                st.caption("No saved promotions yet. Generate a message and click ★ Save to library.")


elif page == "Local SEO":
    st.markdown(
        '<div class="feature-card"><div class="eyebrow">'
        'LOCAL BUSINESS VISIBILITY</div><h3>Help nearby customers '
        'discover your business</h3><div class="panel-caption">'
        'Generate location-aware keywords, business listing content '
        'and practical local visibility suggestions.</div></div>',
        unsafe_allow_html=True,
    )

    vendor = st.session_state.get("vendor", {})

    st.info(
        "Suggestions are AI-generated. Keywords are not verified "
        "search-volume data, and no search ranking is guaranteed."
    )

    if not vendor.get("business_name"):
        st.warning("Please complete your Business Profile first.")
    elif not vendor.get("location", "").strip():
        st.warning("Add your city and area to your Business Profile first.")
    elif not vendor.get("products", "").strip():
        st.warning("Add your products or services to your Business Profile first.")
    else:
        st.markdown("#### Business details")
        st.write(
            f"**Business:** {vendor['business_name']}  \n"
            f"**Category:** {vendor.get('vendor_type', 'Not specified')}  \n"
            f"**Location:** {vendor['location']}  \n"
            f"**Products:** {vendor['products']}"
        )

        if st.button(
            "Generate local SEO kit",
            type="primary",
            key="generate_local_seo",
        ):
            # Do not leave an older draft visible if this generation fails validation.
            st.session_state.pop("local_seo_result", None)
            st.session_state.pop("local_seo_validation_issues", None)
            st.session_state.pop("local_seo_rejected_draft", None)

            MAX_AUTO_RETRIES = 2
            result = run_generation(build_local_seo_prompt(vendor))
            if result:
                is_valid, issues = validate_local_seo_output(result, vendor)
                # Auto-retry loop: pass the exact validation errors back to the model
                _attempts = 0
                while not is_valid and _attempts < MAX_AUTO_RETRIES:
                    _attempts += 1
                    issues_text = "\n".join(f"- {issue}" for issue in issues)
                    correction_prompt = build_local_seo_prompt(vendor)
                    correction_prompt += (
                        f"\n\n---\nCORRECTION REQUIRED (attempt {_attempts} of {MAX_AUTO_RETRIES}):\n"
                        f"The previous draft was rejected because it contained unsupported claims.\n"
                        f"Specific problems found:\n{issues_text}\n\n"
                        "Write a new SEO kit that fixes every problem listed above. "
                        "Replace every rejected phrase with a factual description using only "
                        "the actual business name, vendor type, location, and exact products "
                        "from the vendor profile. "
                        "Do NOT use trust claims, satisfaction claims, popularity claims, "
                        "experience claims, superiority claims, or any form of unverified "
                        "promotional language. Describe the business plainly and factually.\n"
                        "---\n"
                    )
                    corrected = run_generation(correction_prompt)
                    if corrected:
                        result = corrected
                        is_valid, issues = validate_local_seo_output(result, vendor)
                    else:
                        break  # generation failed, stop retrying

                if is_valid:
                    st.session_state["local_seo_result"] = result
                else:
                    st.session_state["local_seo_validation_issues"] = issues
                    st.session_state["local_seo_rejected_draft"] = result

        if st.session_state.get("local_seo_validation_issues"):
            st.error(
                "❌ **Draft rejected** — The generated content still contains unsupported claims "
                "after automatic correction attempts. The AI could not remove all prohibited phrases."
            )
            st.markdown("**Remaining issues:**")
            for issue in st.session_state["local_seo_validation_issues"]:
                st.write(f"- {issue}")

            st.info(
                "**What you can do:**\n\n"
                "1. Click **'Regenerate with corrections'** below — this sends the exact issues to the AI for another attempt.\n"
                "2. If a claim is actually true for your business (e.g. you do have many years of experience), "
                "add that information to your **Business Profile** first, then generate again.\n"
                "3. The validation rules are intentional — they prevent fabricated claims from appearing in your SEO content."
            )
            
            if st.button("🔄 Regenerate with corrections", type="primary", key="regenerate_local_seo_corrected"):
                # Build a correction-focused prompt with explicit forbidden phrase list
                issues_text = "\n".join(f"- {issue}" for issue in st.session_state["local_seo_validation_issues"])
                correction_prompt = build_local_seo_prompt(vendor)
                correction_prompt += (
                    f"\n\n---\nCORRECTION REQUIRED:\n"
                    f"The previous draft was rejected because it contained unsupported claims.\n"
                    f"Specific problems found:\n{issues_text}\n\n"
                    "Write a new SEO kit that fixes every problem listed above. "
                    "Replace every rejected phrase with a factual description using only "
                    "the actual business name, vendor type, location, and exact products "
                    "from the vendor profile. "
                    "Do NOT use trust claims, satisfaction claims, popularity claims, "
                    "experience claims, superiority claims, or any form of unverified "
                    "promotional language. Describe the business plainly and factually.\n"
                    "---\n"
                )

                st.session_state.pop("local_seo_validation_issues", None)
                st.session_state.pop("local_seo_rejected_draft", None)
                result = run_generation(correction_prompt)
                if result:
                    is_valid, issues = validate_local_seo_output(result, vendor)
                    if is_valid:
                        st.session_state["local_seo_result"] = result
                        st.rerun()
                    else:
                        st.session_state["local_seo_validation_issues"] = issues
                        st.session_state["local_seo_rejected_draft"] = result
                        st.rerun()

        if st.session_state.get("local_seo_result"):
            st.markdown("#### Your local SEO kit")
            with st.container(border=True):
                st.markdown(st.session_state["local_seo_result"])

            st.download_button(
                "Download local SEO kit",
                st.session_state["local_seo_result"],
                "vendor_local_seo_kit.txt",
                key="download_local_seo",
            )


elif page == "Digitalization Checklist":
    st.markdown('<div class="feature-card"><div class="eyebrow">YOUR NEXT STEPS</div><h3>Your step-by-step digitalization plan</h3><div class="panel-caption">Get practical next steps based on your business type and the areas you want to improve.</div></div>', unsafe_allow_html=True)
    st.info("This is general AI-generated guidance, not legal or financial advice. Applicability of registrations and licences depends on your circumstances.")
    with st.container(border=True):
        st.markdown('<div class="card-heading"><span>Personalize your checklist</span><span class="card-chip">QUICK ASSESSMENT</span></div>', unsafe_allow_html=True)
        with st.form("checklist_options_form"):
            priority = st.selectbox("What would you most like to improve?", ["Getting more customers", "Accepting digital payments", "Creating an online presence", "Understanding registrations", "Managing and growing my business"])
            current_tools = st.multiselect("Which of these do you already use?", ["UPI / QR payments", "WhatsApp Business", "Google Business Profile", "Social media page", "Online marketplace"], help="Select all that apply. It is okay to leave this blank.")
            extra_context = st.text_area("Anything else we should consider? (optional)", placeholder="e.g. I run my stall alone and have limited time", height=70)
            checklist_submitted = st.form_submit_button("✦ Generate my checklist", type="primary", use_container_width=True)
    
    if st.session_state.get("checklist_validation_issues"):
        st.error(
            "❌ **Checklist rejected** — The generated checklist contains unsuitable recommendations "
            "or unsupported claims."
        )
        st.markdown("**Specific issues found:**")
        for issue in st.session_state["checklist_validation_issues"]:
            st.write(f"- {issue}")
        
        st.info(
            "**What happened:**\n\n"
            "The AI generated recommendations that don't match your business profile or made assumptions "
            "about services/tools you haven't confirmed. Click 'Generate my checklist' again for a new attempt."
        )
    
    
    if checklist_submitted:
        if guard_vendor():
            declared_tools = current_tools if current_tools else []

            context = (
                "Vendor priority: " + priority + ".\n"
                "Tools already used: "
                + (", ".join(current_tools) if current_tools else "Not specified")
                + ".\nAdditional context: "
                + (extra_context.strip() or "Not provided")
            )

            # Clear previous results before generating again.
            st.session_state.pop("checklist_result", None)
            st.session_state.pop("checklist_validation_issues", None)
            st.session_state.pop("checklist_completed", None)

            prompt = build_checklist_prompt(vendor, context=context)
            final_issues = []

            # Initial generation + maximum two correction attempts.
            for attempt in range(3):
                result = run_generation(prompt)

                if not result:
                    final_issues = [
                        "IBM Granite did not return a usable response. "
                        "Please try again."
                    ]
                    break

                format_valid, format_reason = validate_checklist(result)

                attempt_issues = []

                if not format_valid:
                    attempt_issues.append(format_reason)

                else:
                    content_valid, content_issues = (
                        validate_checklist_output(
                            result,
                            vendor,
                            declared_tools,
                        )
                    )

                    quality_valid, quality_issues = (
                        validate_checklist_quality(result)
                    )

                    if not content_valid:
                        attempt_issues.extend(content_issues)

                    if not quality_valid:
                        attempt_issues.extend(quality_issues)

                # Accept only if every validation layer passes.
                if not attempt_issues:
                    st.session_state["checklist_result"] = result
                    st.session_state["checklist_priority"] = priority
                    st.session_state["checklist_completed"] = [
                        False
                    ] * len(parse_checklist_steps(result))

                    final_issues = []
                    break

                final_issues = attempt_issues

                # Ask Granite to correct the rejected output.
                if attempt < 2:
                    prompt = (
                        build_checklist_prompt(vendor, context=context)
                        + "\n\nIMPORTANT CORRECTION REQUIRED:\n"
                        + "\n".join(
                            "- " + issue for issue in attempt_issues
                        )
                        + "\n\nRegenerate the entire checklist. "
                        "Write exactly 5–7 concise, meaningful, "
                        "business-specific and actionable steps. "
                        "Keep each step below 55 words. "
                        "Do not use filler, repeated phrases, "
                        "unrelated terminology or incomplete sentences. "
                        "Follow all original factual and safety instructions."
                    )

        # Never display rejected AI output as a successful checklist.
        if final_issues:
            st.session_state["checklist_validation_issues"] = (
                final_issues
            )
 
    if st.session_state.get("checklist_result"):
        st.markdown('<div class="card-heading"><span>Your personalized action plan</span><span class="card-chip">5–7 STEPS</span></div>', unsafe_allow_html=True)
        st.caption("Priority: " + st.session_state.get("checklist_priority", "Your business"))
        checklist_steps = parse_checklist_steps(st.session_state["checklist_result"])
        if "checklist_completed" not in st.session_state or len(st.session_state["checklist_completed"]) != len(checklist_steps):
            st.session_state["checklist_completed"] = [False] * len(checklist_steps)
        
        with st.container(border=True):
            total_count = len(checklist_steps)

            # Render each checkbox using its saved completion state.
            for step_index, step_text in enumerate(checklist_steps):
                checked = st.checkbox(
                    step_text,
                    value=st.session_state["checklist_completed"][step_index],
                    key=f"checklist_step_{step_index}",
                )

                st.session_state["checklist_completed"][step_index] = checked

            # Calculate progress only after all checkbox values are updated.
            completed_count = sum(
                st.session_state["checklist_completed"]
            ) 

            progress = (
                completed_count / total_count
                if total_count else 0
            )

            st.progress(progress)
            st.caption(
                f"Progress: {completed_count}/{total_count} steps completed"
            )

        st.download_button(
            "Download checklist", st.session_state["checklist_result"],
            "digitalization_checklist.txt", key="download_checklist"
        )

elif page == "Government Schemes":
    st.markdown('<div class="feature-card"><div class="eyebrow">GROUNDED GOVERNMENT INFORMATION</div><h3>Government scheme & registration assistant</h3><div class="panel-caption">Ask about topics covered by the reference documents. Answers are grounded in retrieved passages, and source limitations are shown clearly.</div></div>', unsafe_allow_html=True)
    st.info("Available knowledge includes Udyam information and GeM seller registration resources. The uploaded sources may be historical; verify current requirements on official portals.")
    with st.container(border=True):
        st.markdown('<div class="card-heading"><span>Ask a question</span><span class="card-chip">DOCUMENT-BASED Q&A</span></div>', unsafe_allow_html=True)
        with st.form("scheme_question_form"):
            question = st.text_area("What would you like to know?", placeholder="e.g. What does the Udyam document say about registration?", height=95)
            qa_language = st.selectbox("Answer language", ["English", "Tamil", "Hindi"], index=["English", "Tamil", "Hindi"].index(vendor.get("language", "English")) if vendor.get("language", "English") in ["English", "Tamil", "Hindi"] else 0)
            scheme_submitted = st.form_submit_button("Ask VendorSaathi", type="primary", use_container_width=True)
    if scheme_submitted:
        if not question.strip():
            st.warning("Enter a question first.")
        elif retriever is None:
            st.warning("Source retrieval is unavailable. No answer was generated.")
        else:
            hits = retriever.search(question.strip(), top_k=3)
            if not hits:
                st.warning("No sufficiently relevant evidence was found in the available documents. No AI answer was generated.")
            else:
                context = retriever.format_context(question.strip(), top_k=3)
                retrieved_passages = [hit["text"] for hit in hits]
                safe = get_safe_scheme_answer(question.strip(), hits)
                answer = safe if safe is not None else run_generation(build_scheme_qa_prompt(question.strip(), context, qa_language, vendor))
                if answer:
                    # Validate the generated answer for unsupported claims
                    is_valid, validation_issues = validate_scheme_answer(answer, question.strip(), retrieved_passages, hits)
                    if is_valid:
                        st.session_state["scheme_answer"] = answer
                        st.session_state["scheme_hits"] = hits
                        st.session_state["scheme_question"] = question.strip()
                        st.session_state.pop("scheme_validation_issues", None)  # Clear any old issues
                    else:
                        # Clear old answer to prevent displaying stale successful answer
                        st.session_state.pop("scheme_answer", None)
                        st.session_state.pop("scheme_question", None)
                        st.warning(
                            "The generated answer was not saved or displayed because "
                            "it contains claims not supported by the retrieved evidence. "
                            "Please try rephrasing your question or check the evidence sources below."
                        )
                        st.session_state["scheme_validation_issues"] = validation_issues
                        st.session_state["scheme_hits"] = hits
    if st.session_state.get("scheme_validation_issues"):
        st.error("Validation issues detected in the generated answer:")
        for issue in st.session_state["scheme_validation_issues"]:
            st.write(f"- {issue}")
        st.caption("The answer was blocked because it does not meet accuracy requirements.")
    
    if st.session_state.get("scheme_answer"):
        st.markdown('<div class="card-heading"><span>Answer</span><span class="card-chip">GROUNDED RESPONSE</span></div>', unsafe_allow_html=True)
        if st.session_state.get("scheme_question"):
            st.caption(f"Question: {st.session_state['scheme_question']}")
        with st.container(border=True):
            st.markdown(st.session_state["scheme_answer"])
        st.download_button("Download answer", st.session_state["scheme_answer"], "scheme_information_answer.txt", key="download_scheme_answer")
        with st.expander("Evidence used for this answer", expanded=False):
            st.caption("These are the retrieved passages supplied to the answer generator. Relevance scores are retrieval-ranking signals, not confidence probabilities.")
            for i, hit in enumerate(st.session_state.get("scheme_hits", []), 1):
                with st.container(border=True):
                    st.markdown(f"**Evidence {i} · {escape(hit['source'])} · PDF page {hit['page']}**")
                    st.write(hit["text"])
                    st.caption(f"Retrieval relevance: {hit['score']} · {hit['date_note']}")

elif page == "AI Copilot":
    st.markdown("""
    <div class="hero" style="margin-top:8px">
      <div class="hero-tag">✦ VENDORSAATHI AI ASSISTANT</div>
      <h2>Your digital business copilot</h2>
      <p>Ask about government registration and schemes. Answers are grounded in your uploaded reference PDFs and existing IBM Granite workflow.</p>
    </div>
    """, unsafe_allow_html=True)

    _copilot_email = st.session_state["account"]["email"]
    if "copilot_messages" not in st.session_state:
        # Guard runs exactly once per Streamlit session initialisation.
        # Normal reruns skip this block because the key already exists.
        _latest = load_latest_chat_session(_copilot_email)
        if _latest:
            st.session_state["_copilot_session_id"], st.session_state["copilot_messages"] = _latest
        else:
            st.session_state["_copilot_session_id"] = create_chat_session(_copilot_email)
            st.session_state["copilot_messages"] = []

    chat_col, history_col = st.columns([2.15, .85], gap="medium")
    with chat_col:
        st.markdown('<div class="card-heading"><span>Conversation</span><span class="card-chip">GROUNDED RAG</span></div>', unsafe_allow_html=True)
        if not st.session_state["copilot_messages"]:
            with st.container(border=True):
                st.markdown("### Welcome to VendorSaathi")
                st.caption("Start with a question about Udyam, GeM seller registration or the information in your government reference documents.")
                suggestions = [
                    "What does the Udyam document say about registration?",
                    "What GeM seller registration information is available?",
                    "How do I add a product to a GeM catalogue?",
                ]
                for idx, suggestion in enumerate(suggestions):
                    if st.button("✦  " + suggestion, key=f"copilot_suggest_{idx}", use_container_width=True):
                        st.session_state["copilot_pending"] = suggestion
                        st.rerun()

        for message in st.session_state["copilot_messages"]:
            with st.chat_message(message["role"]):
                st.markdown(_clean_response(message["content"]))
                if message.get("source"):
                    st.caption(message["source"])

        pending = st.session_state.pop("copilot_pending", None)
        question = st.chat_input("Ask VendorSaathi about your business or government information…")
        if pending:
            question = pending

        if question:
            st.session_state["copilot_messages"].append({"role":"user","content":question})
            if retriever is None:
                answer = "Knowledge retrieval is unavailable. Please check that the government reference PDFs and retrieval dependencies are installed."
                source_note = ""
            else:
                hits = retriever.search(question.strip(), top_k=1)
                if not hits:
                    answer = "I couldn't find sufficiently relevant evidence in the available reference documents, so I won't guess. Try asking about a topic covered by the uploaded PDFs."
                    source_note = ""
                else:
                    retrieved_passages = [hits[0]["text"]]
                    source_note = f"Source: {hits[0]['source']} · PDF page {hits[0]['page']}"
                    safe = get_safe_scheme_answer(question.strip(), hits)
                    if safe is not None:
                        answer = _clean_response(safe)
                    else:
                        generated_answer = run_generation(
                            build_scheme_qa_prompt(
                                question.strip(),
                                retriever.format_context(question.strip(), top_k=1),
                                vendor.get("language","English"),
                                vendor,
                            )
                        )
                        if generated_answer:
                            # Validate generated answer for unsupported claims
                            is_valid, validation_issues = validate_scheme_answer(
                                generated_answer, question.strip(), retrieved_passages
                            )
                            if is_valid:
                                answer = _clean_response(generated_answer)
                            else:
                                # Return a safe insufficient-evidence message
                                answer = (
                                    "I found some relevant information but cannot generate a reliable answer "
                                    "from the retrieved passages without making unsupported claims. "
                                    "Please verify the information on the official portal or rephrase your question."
                                )
                                source_note = f"Validation blocked · {source_note}"
                        else:
                            answer = "I couldn't generate an answer. Please check the IBM watsonx.ai connection and try again."
            st.session_state["copilot_messages"].append({"role":"assistant","content":answer,"source":source_note})
            append_chat_messages(
                st.session_state["_copilot_session_id"],
                question,
                answer,
                source_note,
            )
            st.rerun()

    with history_col:
        with st.container(border=True):
            st.markdown('<div class="card-heading"><span>Chat history</span><span class="card-chip">SAVED</span></div>', unsafe_allow_html=True)
            st.caption(f"{len(st.session_state['copilot_messages']) // 2} exchanges · saved")
            if st.button("＋ New chat", use_container_width=True):
                _new_sid = create_chat_session(_copilot_email)
                st.session_state["_copilot_session_id"] = _new_sid
                st.session_state["copilot_messages"] = []
                st.rerun()
            _recent_sessions = load_recent_chat_sessions(_copilot_email, limit=5)
            
            if _recent_sessions:
                for _sess in _recent_sessions:
                    _is_active = (
                        _sess["id"] == st.session_state.get("_copilot_session_id")
                    )
                    _fq = _sess["first_question"]
                    _title = _fq[:55] if _fq else "New conversation"
                    _date = (_sess["created_at"] or "")[:10]

                    if _is_active:
                        st.button(
                            f"● {_title}",
                            key=f"active_session_{_sess['id']}",
                            use_container_width=True,
                            disabled=True,
                        )
                    else:
                        if st.button(
                            f"○ {_title}",
                            key=f"load_session_{_sess['id']}",
                            use_container_width=True,
                        ):
                            _owner = get_chat_session_owner(_sess["id"])
                            if _owner == _copilot_email:
                                st.session_state["_copilot_session_id"] = _sess["id"]
                                st.session_state["copilot_messages"] = (
                                    load_chat_session_messages(_sess["id"])
                                )
                                st.rerun()
                    st.caption(_date)
            else:
                st.caption("No saved conversations yet.")

        with st.container(border=True):
            st.markdown("**Knowledge assistant**")
            st.caption("Responses use the local government-PDF retrieval pipeline.")
            if retriever:
                st.success(f"{len(retriever.passages)} passages indexed")
            else:
                st.warning("Retrieval is unavailable")

elif page == "Knowledge Sources":
    st.markdown('<div class="feature-card"><div class="eyebrow">REFERENCE LIBRARY</div><h3>Knowledge base</h3><div class="panel-caption">The documents currently used by the local retrieval pipeline.</div></div>',unsafe_allow_html=True)
    if retriever:
        st.success(f"{len(retriever.passages)} readable passages loaded.")
        counts={}
        for passage in retriever.passages: counts[passage.source]=counts.get(passage.source,0)+1
        for name,count in counts.items():
            st.markdown(f'<div class="step"><div class="step-icon">▤</div><div><div class="step-title">{escape(name)}</div><div class="step-caption">{count} indexed passages</div></div><span class="card-chip">INDEXED</span></div>',unsafe_allow_html=True)
    else:
        st.warning("No passages were loaded. Confirm that the PDF files are in data/government_docs.")
    st.markdown('</div>',unsafe_allow_html=True)
    st.caption("Source coverage is limited to the documents bundled with this project. The system does not claim live policy updates.")

st.markdown("<div style='padding:20px 0 0;color:var(--muted);font-size:11px;text-align:center'>VendorSaathi AI · Street Vendor Growth Copilot · IBM watsonx.ai & IBM Granite</div>",unsafe_allow_html=True)
