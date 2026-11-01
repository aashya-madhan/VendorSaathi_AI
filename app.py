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
 --bg:#07110b; --bg2:#0b1710; --panel:#101d14; --panel2:#14251a;
 --panel3:#1a3020; --line:#233b2a; --line2:#31523a;
 --text:#f1f7f0; --muted:#9aab9d; --green:#35d36b;
 --green2:#159447; --lime:#a4f35b; --input:#101d14;
 color-scheme:dark;
}
html,body,[class*="css"] {font-family:'DM Sans',sans-serif}
.stApp {background:radial-gradient(ellipse at 70% -15%,rgba(33,111,54,.17),transparent 42%),var(--bg);color:var(--text)}
[data-testid="stHeader"] {background:rgba(7,17,11,.96);height:2.8rem}
[data-testid="stToolbar"] {right:1rem}
.block-container {max-width:1600px;width:100%;padding:1.05rem clamp(1rem,2.1vw,2rem) 2.4rem}
[data-testid="stSidebar"] {background:#09150d;border-right:1px solid #1c3323}
[data-testid="stSidebar"] .block-container {padding:1.05rem .9rem 1.6rem}
[data-testid="stSidebar"] * {color:var(--text)}
.brand {display:flex;align-items:center;gap:10px;padding:9px 5px 22px}
.brandmark {width:39px;height:39px;flex:0 0 39px;border-radius:12px;background:linear-gradient(145deg,#8df34f,#16a45b);display:grid;place-items:center;color:#07110b!important;font-size:21px;font-weight:900;box-shadow:0 0 22px rgba(53,211,107,.18)}
.brandname {font-family:Manrope,sans-serif;font-size:18px;font-weight:800;letter-spacing:-.5px;color:#f4fbf4}
.brandtag {font-size:8px;letter-spacing:1.35px;font-weight:800;color:#829989!important;margin-top:1px}
.eyebrow {font-size:9px;letter-spacing:1.55px;text-transform:uppercase;color:var(--green)!important;font-weight:800}
.page-title {font-family:Manrope,sans-serif;font-size:29px;font-weight:800;letter-spacing:-.9px;line-height:1.2;margin:1px 0 4px;color:var(--text)!important}
.subtle {font-size:13px;color:var(--muted)!important;line-height:1.5}
.topbar {display:flex;align-items:center;justify-content:space-between;gap:14px;margin:0 0 17px;padding:8px 0 13px;border-bottom:1px solid rgba(49,82,58,.45)}
.topbar-left {display:flex;align-items:center;gap:10px}
.topbar-tag {padding:7px 11px;border-radius:20px;background:#102519;border:1px solid #24442d;color:#91e6a7!important;font-size:10px;font-weight:800;letter-spacing:.5px}
.hero {position:relative;overflow:hidden;background:linear-gradient(110deg,#102c1b 0%,#123c25 56%,#17633a 100%);border:1px solid #28623b;border-radius:17px;padding:25px 27px;margin:14px 0 16px;box-shadow:0 12px 35px rgba(0,0,0,.16)}
.hero:after {content:"";position:absolute;width:270px;height:270px;border-radius:50%;right:-70px;top:-135px;background:radial-gradient(circle,rgba(126,255,121,.18),transparent 68%);pointer-events:none}
.hero h2 {font-family:Manrope,sans-serif;font-size:25px;line-height:1.22;letter-spacing:-.7px;margin:8px 0;color:#f5fff5!important}
.hero p {font-size:13px;line-height:1.6;max-width:690px;color:#c5dfcb!important;margin:0 0 11px}
.hero-tag {font-size:9px;letter-spacing:1.6px;font-weight:900;color:var(--lime)!important}
.metric {height:100%;min-height:105px;padding:15px 16px;border:1px solid var(--line);border-radius:13px;background:linear-gradient(145deg,#14251a,#0d1a12);box-shadow:0 7px 20px rgba(0,0,0,.13)}
.metric-label {font-size:10px;color:var(--muted)!important;font-weight:600}
.metric-value {font-family:Manrope,sans-serif;font-size:26px;font-weight:800;letter-spacing:-.8px;color:#f4fbf4!important;margin:8px 0 1px}
.metric-note {font-size:9px;line-height:1.4;color:#78dc91!important;font-weight:700}
.panel,.feature-card {background:linear-gradient(145deg,#111f16,#0d1911);border:1px solid var(--line);border-radius:15px;padding:18px 19px;margin:10px 0 14px;box-shadow:0 8px 24px rgba(0,0,0,.12)}
.panel h3,.feature-card h3 {font-family:Manrope,sans-serif;font-size:16px;font-weight:800;margin:0 0 6px;color:var(--text)!important}
.panel-caption {font-size:11px;line-height:1.55;color:var(--muted)!important;margin:0 0 12px}
.card-heading {display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:12px}
.card-heading span {font-size:13px;font-weight:800;color:var(--text)}
.card-chip {font-size:9px;color:#8ce7a1;background:#153321;border:1px solid #275438;border-radius:20px;padding:4px 8px}
.step {display:flex;align-items:center;gap:11px;padding:10px 0;border-bottom:1px solid rgba(49,82,58,.5)}
.step:last-child {border-bottom:0}
.step-icon {height:34px;width:34px;flex:0 0 34px;border-radius:10px;background:#193524;border:1px solid #2b5036;color:#8cf0a5;display:grid;place-items:center;font-size:15px}
.step-title {font-size:11px;font-weight:700;color:var(--text)!important;line-height:1.4}
.step-caption {font-size:10px;color:var(--muted)!important;line-height:1.45;margin-top:2px}
.pill {display:inline-block;border-radius:20px;padding:6px 10px;background:#143321;border:1px solid #285438;color:#8fe9a5!important;font-size:9px;font-weight:900;letter-spacing:.45px}
.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5,.stApp strong {color:var(--text)}
.stApp p,.stApp li,.stApp label {color:var(--text)}
.stCaption,.stCaption *,[data-testid="stCaptionContainer"] {color:var(--muted)!important}
[data-testid="stMarkdownContainer"] {color:var(--text)}
div.stButton>button[kind="primary"],.stDownloadButton>button {background:linear-gradient(110deg,#22a653,#39d56c);border:1px solid #3bd66e;color:#06130a!important;border-radius:9px;font-weight:800;padding:.58rem 1rem;min-height:40px;box-shadow:0 4px 14px rgba(28,190,83,.13)}
div.stButton>button[kind="primary"]:hover,.stDownloadButton>button:hover {background:linear-gradient(110deg,#35c765,#8ae95b);border-color:#8ae95b;color:#06130a!important}
div.stButton>button[kind="secondary"] {background:#122219;border:1px solid #2a4832;color:var(--text)!important;border-radius:9px}
.stTextInput input,.stTextArea textarea,[data-baseweb="select"]>div {background:#0c1911!important;border:1px solid #294532!important;border-radius:9px!important;color:var(--text)!important;min-height:42px}
.stTextArea textarea {line-height:1.55}
input,textarea,[data-baseweb="select"] input {color:var(--text)!important}
[data-baseweb="select"] *,[role="listbox"],[role="option"] {color:var(--text)!important}
[data-baseweb="popover"],[data-baseweb="menu"] {background:#122219!important}
[data-testid="stForm"],[data-testid="stExpander"] {border:1px solid var(--line)!important;border-radius:13px!important;background:#101d14!important}
[data-testid="stVerticalBlockBorderWrapper"] {background:#101d14!important;border:1px solid var(--line)!important;border-radius:13px!important;padding:1rem 1.05rem!important}
[data-testid="stForm"] {padding:13px!important}
[data-testid="stExpander"] summary,[data-testid="stExpander"] details {color:var(--text)!important}
[data-testid="stAlert"] {border-radius:10px}
[data-testid="stMetric"] label,[data-testid="stMetricValue"] {color:var(--text)!important}
[data-testid="stHorizontalBlock"] {gap:.8rem;align-items:stretch}
[data-testid="column"] {min-width:0}
[data-testid="stRadio"] [role="radiogroup"] {gap:4px}
[data-testid="stRadio"] label {border-radius:8px;padding:6px 8px;margin:1px 0;color:#b7c8ba!important;font-size:12px}
[data-testid="stRadio"] label:has(input:checked) {background:linear-gradient(90deg,#173c25,#102719);border:1px solid #2c7442;color:#9df2ae!important}
[data-testid="stRadio"] label p {font-size:12px}
hr {border-color:#233b2a}
footer {visibility:hidden}
[data-testid="stChatMessage"] {background:#101e15;border:1px solid #253e2c;border-radius:13px;padding:12px 14px}
[data-testid="stChatInput"] textarea {background:#101e15!important}
@media(max-width:900px) {
 .block-container {padding:1rem .9rem 2rem}
 .page-title {font-size:26px}
 .hero {padding:22px}
 .hero h2 {font-size:22px}
}
@media(max-width:640px) {
 .block-container {padding:.7rem .65rem 1.5rem}
 .page-title {font-size:23px}
 .subtle {font-size:12px}
 .topbar {align-items:flex-start;flex-direction:column}
 .hero {padding:18px 16px;border-radius:13px}
 .hero h2 {font-size:20px}
 .metric {min-height:0;padding:13px}
 .metric-value {font-size:23px}
 .panel,.feature-card {padding:15px 13px}
 [data-testid="stHorizontalBlock"] {flex-wrap:wrap!important;gap:.55rem!important}
 [data-testid="stHorizontalBlock"]>[data-testid="column"] {flex:1 1 100%!important;width:100%!important;min-width:100%!important}
 [data-testid="stSidebar"] .block-container {padding:.8rem .7rem 1.2rem}
 div.stButton>button,.stDownloadButton>button {width:100%;white-space:normal}
}

/* Public landing and account screens */
.auth-shell {max-width:1180px;margin:2.4rem auto 1rem;padding:0 1rem}
.auth-nav {display:flex;align-items:center;justify-content:space-between;padding:13px 17px;border:1px solid #294532;border-radius:16px;background:rgba(9,22,13,.88);margin-bottom:38px}
.auth-brand {display:flex;align-items:center;gap:10px;font-family:Manrope,sans-serif;font-weight:800;font-size:18px}
.auth-logo {height:38px;width:38px;border-radius:12px;display:grid;place-items:center;background:linear-gradient(140deg,#a4f35b,#1aa45a);color:#07110b;font-size:20px}
.auth-nav-note {font-size:10px;letter-spacing:1.1px;color:#9ab59f;text-transform:uppercase;font-weight:800}
.landing-hero {padding:clamp(28px,5vw,62px);border:1px solid #2b633b;border-radius:24px;background:radial-gradient(circle at 83% 30%,rgba(112,239,93,.18),transparent 27%),linear-gradient(115deg,#102819,#0d1a11 68%,#153a20);box-shadow:0 20px 65px rgba(0,0,0,.24);position:relative;overflow:hidden}
.landing-kicker {font-size:10px;letter-spacing:2px;color:#a4f35b;font-weight:900;text-transform:uppercase}
.landing-hero h1 {font-family:Manrope,sans-serif;font-size:clamp(34px,5vw,58px);line-height:1.08;letter-spacing:-2px;max-width:760px;margin:18px 0 15px;color:#f4fff4!important}
.landing-hero p {font-size:15px;line-height:1.75;color:#b9cfbd!important;max-width:650px}
.landing-orb {position:absolute;right:8%;top:22%;width:170px;height:170px;border-radius:50%;border:1px solid rgba(128,242,113,.5);box-shadow:0 0 35px rgba(49,211,90,.17),inset 0 0 35px rgba(49,211,90,.1)}
.landing-orb:before,.landing-orb:after {content:"";position:absolute;inset:17px;border:1px solid rgba(128,242,113,.38);border-radius:50%}
.landing-orb:after {inset:35px;border-color:rgba(128,242,113,.26)}
.landing-grid {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:18px}
.landing-tile {padding:20px;border:1px solid #263f2d;border-radius:15px;background:linear-gradient(145deg,#122219,#0c1810)}
.landing-tile-icon {height:36px;width:36px;border-radius:11px;background:#1b3825;color:#9af0a9;display:grid;place-items:center;margin-bottom:13px;font-size:17px}
.landing-tile h3 {font-size:14px;margin:0 0 6px;color:#f1f8f1!important}
.landing-tile p {font-size:11px;line-height:1.6;color:#9aab9d!important;margin:0}
.auth-card {max-width:520px;margin:2.5rem auto;padding:clamp(20px,4vw,34px);border:1px solid #2a4b32;border-radius:20px;background:linear-gradient(145deg,#122219,#0b1710);box-shadow:0 18px 55px rgba(0,0,0,.24)}
.auth-card h1 {font-family:Manrope,sans-serif;font-size:28px;margin:7px 0;color:#f4fff4!important}
.auth-card p {font-size:12px;color:#9aab9d!important;line-height:1.6}
.auth-foot {text-align:center;color:#8fa394;font-size:11px;margin-top:18px}
.overview-welcome {display:flex;justify-content:space-between;gap:20px;align-items:center;padding:23px 25px;border:1px solid #2b633b;border-radius:17px;background:linear-gradient(110deg,#102b1a,#143d24 65%,#17613a);margin:8px 0 18px}
.overview-welcome h2 {font-family:Manrope,sans-serif;font-size:24px;line-height:1.2;margin:7px 0;color:#f5fff5!important}
.overview-welcome p {font-size:12px;color:#c4dec9!important;margin:0;line-height:1.6}
.overview-user {border:1px solid #41794b;border-radius:12px;background:rgba(5,20,10,.3);padding:11px 14px;min-width:130px}
.overview-user small {display:block;color:#9bdca8;font-size:9px;text-transform:uppercase;letter-spacing:1px}
.overview-user strong {font-size:13px;color:#fff}
.overview-section-title {font-family:Manrope,sans-serif;font-size:15px;font-weight:800;margin:20px 0 10px;color:#f1f8f1}
.quick-card {height:100%;padding:17px;border-radius:14px;border:1px solid #2a4932;background:linear-gradient(145deg,#13251a,#0d1911)}
.quick-card .q-icon {font-size:19px;color:#a4f35b;margin-bottom:12px}
.quick-card h3 {font-size:13px;margin:0 0 6px;color:#f2faf2!important}
.quick-card p {font-size:10px;line-height:1.55;color:#9aab9d!important;min-height:32px}
.status-row {display:flex;align-items:center;justify-content:space-between;padding:11px 0;border-bottom:1px solid #243c2b;font-size:11px}
.status-row:last-child {border-bottom:0}
@media(max-width:760px) {
 .auth-shell {margin:1rem auto}
 .auth-nav {margin-bottom:18px}
 .landing-orb {opacity:.28;right:-45px;top:20px;width:125px;height:125px}
 .landing-grid {grid-template-columns:1fr}
 .overview-welcome {align-items:flex-start;flex-direction:column}
 .overview-user {width:100%}
}


/* Refined visual pass: charcoal surfaces, restrained emerald accents, tighter rhythm */
:root {
 --bg:#0b100d; --bg2:#0e1511; --panel:#141c17; --panel2:#19231c;
 --line:#29382e; --line2:#3a5140; --text:#edf3ed; --muted:#a4b2a7;
 --green:#2fbd68; --green2:#209653; --lime:#a9df72; --input:#111a14;
}
.stApp {
 background:
   radial-gradient(ellipse at 82% 0%,rgba(46,132,75,.10),transparent 34%),
   #0b100d !important;
 font-size:14px;
}
.block-container {padding-top:1rem!important;padding-bottom:1.5rem!important}
[data-testid="stSidebar"] {background:#0e1511!important;border-right:1px solid #26342b!important}
[data-testid="stSidebar"] .block-container {padding:.8rem .75rem 1.2rem!important}
.brand {padding:5px 4px 15px!important}
.topbar {margin-bottom:12px!important;padding:5px 0 10px!important}
.page-title {font-size:27px!important}
.subtle {font-size:13px!important}
.hero {padding:21px 24px!important;margin:10px 0 12px!important;border-radius:15px!important}
.metric {min-height:90px!important;padding:12px 14px!important;border-radius:11px!important}
.metric-value {font-size:23px!important;margin:6px 0 1px!important}
.panel,.feature-card {padding:15px 16px!important;margin:8px 0 11px!important;border-radius:12px!important}
.step {padding:8px 0!important}
.step-icon {height:31px!important;width:31px!important;flex-basis:31px!important}
.landing-hero {padding:clamp(25px,4vw,48px)!important;border-radius:20px!important}
.landing-grid {gap:12px!important;margin-top:15px!important}
.landing-tile {padding:16px!important;border-radius:13px!important}
.landing-tile p {font-size:12px!important}
.auth-nav {padding:10px 14px!important;margin-bottom:25px!important}
.auth-shell {margin:1.7rem auto .8rem!important}
.overview-welcome {padding:19px 21px!important;margin:6px 0 14px!important}
.quick-card {padding:14px!important}
.quick-card p {font-size:11px!important;min-height:28px!important}
[data-testid="stForm"] {
 background:#121a15!important;border:1px solid #2a3b30!important;
 border-radius:12px!important;padding:15px!important;
}
.stTextInput input,.stTextArea textarea,[data-baseweb="select"]>div {
 min-height:39px!important;border-radius:8px!important;
 background:#101812!important;border-color:#2b3c31!important;
}
.stTextArea textarea {min-height:90px!important}
div.stButton>button,
button[kind="primary"],
button[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-primary"] {
 min-height:38px!important;padding:.48rem .85rem!important;
 border-radius:8px!important;font-size:13px!important;
}
div.stButton>button[kind="primary"],
button[kind="primary"],
button[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-primary"] {
 background:linear-gradient(110deg,#239b55,#35bd68)!important;
 border:1px solid #39c875!important;color:#07120b!important;
 box-shadow:0 3px 12px rgba(36,173,91,.13)!important;
}
div.stButton>button[kind="primary"]:hover,
button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover {
 background:linear-gradient(110deg,#2eaf61,#55cf7d)!important;
 border-color:#65db8b!important;
}
div.stButton>button[kind="secondary"],
button[kind="secondary"],
button[data-testid="stBaseButton-secondary"] {
 background:#17221a!important;border:1px solid #304638!important;
 color:#e8f1e9!important;
}
[data-testid="stChatInput"] {border-color:#304638!important}
[data-testid="stChatMessage"] {background:#141e17!important;border-color:#2b3c30!important}
@media(max-width:760px) {
 .block-container {padding:.7rem .65rem 1.2rem!important}
 .auth-shell {margin:1rem auto!important}
 .auth-nav {margin-bottom:16px!important}
 .hero {padding:17px 15px!important}
 .metric {padding:12px!important}
}


button[kind*="primary"],
[data-testid="stFormSubmitButton"] button,
[data-testid="stForm"] button[kind] {
 background:linear-gradient(110deg,#239b55,#35bd68)!important;
 border:1px solid #39c875!important;color:#07120b!important;
}
[data-testid="stFormSubmitButton"] button:hover,
[data-testid="stForm"] button[kind]:hover {
 background:linear-gradient(110deg,#2eaf61,#55cf7d)!important;
 border-color:#65db8b!important;
}


/* Landing page alignment correction */
.public-header-shell {margin-top:1.15rem!important;margin-bottom:0!important}
.public-header-shell .auth-nav {
  min-height:58px!important;height:auto!important;box-sizing:border-box;
  padding:9px 15px!important;margin-bottom:0!important;overflow:visible!important;
}
.auth-logo {width:34px!important;height:34px!important;flex:0 0 34px!important}
.home-main {max-width:1180px!important;margin:2.1rem auto 1rem!important;padding:0 1rem!important}
.home-main .landing-hero {
  min-height:0!important;padding:42px 46px!important;border-radius:20px!important;
  display:flex;align-items:center;box-sizing:border-box;
}
.home-main .landing-copy {position:relative;z-index:1;max-width:700px}
.home-main .landing-hero h1 {
  font-size:clamp(35px,4.1vw,51px)!important;line-height:1.09!important;
  letter-spacing:-1.7px!important;max-width:690px!important;margin:17px 0 14px!important;
}
.home-main .landing-hero h1 span {color:#a9df72!important;display:inline}
.home-main .landing-hero p {font-size:14px!important;line-height:1.65!important;max-width:650px!important;margin-bottom:0!important}
.home-main .landing-orb {width:142px!important;height:142px!important;right:7%!important;top:25%!important;opacity:.75}
.home-feature-grid {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:16px}
.home-feature-grid .landing-tile {min-width:0;padding:16px!important;min-height:145px;box-sizing:border-box}
.home-feature-grid .landing-tile-icon {width:32px;height:32px;margin-bottom:10px}
.home-feature-grid .landing-tile h3 {font-size:13px!important;line-height:1.35!important}
.home-feature-grid .landing-tile p {font-size:11px!important;line-height:1.5!important}
.home-footer {text-align:center;color:#718878;font-size:9px;letter-spacing:.35px;margin:17px 0 0}
div[data-testid="stHorizontalBlock"]:has(button[key="home_signup"]) {max-width:1180px;margin:0 auto!important}
@media(max-width:760px) {
 .public-header-shell {margin-top:.7rem!important}
 .home-main {margin:1.1rem auto .7rem!important;padding:0 .65rem!important}
 .home-main .landing-hero {padding:25px 20px!important;min-height:0!important}
 .home-main .landing-hero h1 {font-size:34px!important;max-width:100%!important}
 .home-main .landing-hero p {font-size:13px!important}
 .home-main .landing-orb {width:90px!important;height:90px!important;right:5%!important;top:8%!important;opacity:.35}
 .home-feature-grid {grid-template-columns:1fr;gap:9px}
 .home-feature-grid .landing-tile {min-height:0;padding:14px!important}
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
        conn.commit()


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
    <div class="auth-shell public-header-shell">
      <div class="auth-nav">
        <div class="auth-brand"><div class="auth-logo">✦</div><span>VendorSaathi <span style="color:#a9df72">AI</span></span></div>
        <div class="auth-nav-note">Your digital business partner</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

def render_home():
    show_public_nav()

    st.markdown("""
    <div class="auth-shell home-main">
      <section class="landing-hero">
        <div class="landing-orb"></div>
        <div class="landing-copy">
          <div class="landing-kicker">✦ BUILT FOR INDIA'S STREET VENDORS</div>
          <h1>Take your street business <span>one step further.</span></h1>
          <p>Create a digital business profile, make promotions customers notice, understand digital onboarding and explore government information — with an AI assistant designed around your everyday business.</p>
        </div>
      </section>
      <div class="home-feature-grid">
        <article class="landing-tile">
          <div class="landing-tile-icon">▣</div>
          <h3>Build your business profile</h3>
          <p>Turn your stall details into a clear profile for customers and online listings.</p>
        </article>
        <article class="landing-tile">
          <div class="landing-tile-icon">✦</div>
          <h3>Create customer promotions</h3>
          <p>Prepare short promotional messages in your preferred language.</p>
        </article>
        <article class="landing-tile">
          <div class="landing-tile-icon">⌂</div>
          <h3>Understand digital services</h3>
          <p>Explore digitalization steps and ask questions grounded in government reference PDFs.</p>
        </article>
      </div>
      <div class="home-footer">POWERED BY IBM WATSONX.AI · IBM GRANITE</div>
    </div>
    """, unsafe_allow_html=True)

    # Keep the two account actions aligned with the same content width as the hero.
    left, action_col, right = st.columns([1, 8, 1], gap="small")
    with action_col:
        signup_col, login_col = st.columns(2, gap="small")
        with signup_col:
            if st.button("Get started · Create account", type="primary", use_container_width=True, key="home_signup"):
                st.session_state["auth_view"] = "Signup"
                st.rerun()
        with login_col:
            if st.button("I already have an account · Sign in", use_container_width=True, key="home_login"):
                st.session_state["auth_view"] = "Login"
                st.rerun()

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
                full_name = st.text_input("Your name", placeholder="e.g. Aashya")
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

# ------------------------------ Navigation callbacks ----------------------
def navigate_to(page_name: str):
    """Update the radio widget value before the next script run creates it."""
    st.session_state["selected_page"] = page_name


# ------------------------------ Sidebar -----------------------------------
with st.sidebar:
    st.markdown("""
    <div class="brand"><div class="brandmark">✦</div><div>
    <div class="brandname">VendorSaathi <span style="color:#238454">AI</span></div>
    <div class="brandtag">YOUR DIGITAL BUSINESS PARTNER</div></div></div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">WORKSPACE NAVIGATION</div>', unsafe_allow_html=True)
    nav_pages = ["Overview","AI Copilot","Business Profile","Promo Studio","Digitalization Checklist","Government Schemes","Knowledge Sources"]
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
        st.session_state.pop("checklist_result", None)
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
    business_label = vendor.get("business_name") or "Set up your stall profile"
    source_count = len({p.source for p in retriever.passages}) if retriever else 0

    st.markdown(f"""
    <section class="overview-welcome">
      <div>
        <div class="eyebrow">YOUR BUSINESS WORKSPACE</div>
        <h2>Good to see you, {escape(display_name.split()[0])}.</h2>
        <p>Everything you need to take your street business digital, in one place.</p>
      </div>
      <div class="overview-user"><small>YOUR STALL</small><strong>{escape(business_label)}</strong></div>
    </section>
    """, unsafe_allow_html=True)

    st.markdown('<div class="overview-section-title">Your VendorSaathi toolkit</div>', unsafe_allow_html=True)
    tool_cols = st.columns(4)
    tool_cards = [
        ("▣","Business Profile","Create a digital identity for your stall.","Business Profile"),
        ("✦","Promo Studio","Prepare WhatsApp and social promotions.","Promo Studio"),
        ("✓","Digital Checklist","Plan your next digital steps.","Digitalization Checklist"),
        ("⌂","Government Help","Explore information from reference PDFs.","Government Schemes"),
    ]
    for col, (ico, title, desc, target) in zip(tool_cols, tool_cards):
        with col:
            st.markdown(f'<div class="quick-card"><div class="q-icon">{ico}</div><h3>{title}</h3><p>{desc}</p></div>', unsafe_allow_html=True)
            st.button(
                "Open tool →",
                key=f"overview_{target}",
                use_container_width=True,
                on_click=navigate_to,
                args=(target,),
            )

    st.markdown('<div class="overview-section-title">Workspace snapshot</div>', unsafe_allow_html=True)
    stats = st.columns(4)
    stat_values = [
        ("AI TOOLS","4","Profile · Promotion · Checklist · Scheme Q&A"),
        ("REFERENCE LIBRARY",str(source_count),"PDF sources indexed"),
        ("LANGUAGES","3","English · Tamil · Hindi"),
        ("AI ENGINE","Granite","IBM watsonx.ai"),
    ]
    for col, (label, value, note) in zip(stats, stat_values):
        with col:
            st.markdown(f'<div class="metric"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>', unsafe_allow_html=True)

    left, right = st.columns([1.2,.8], gap="medium")
    with left:
        with st.container(border=True):
            st.markdown('<div class="card-heading"><span>Start with these steps</span><span class="card-chip">QUICK GUIDE</span></div>', unsafe_allow_html=True)
            steps = [
                ("01","Add your business details","Save your stall name, category, location and products in the sidebar."),
                ("02","Create your digital profile","Generate a description customers can use to discover your business."),
                ("03","Share a promotion","Prepare a short message for WhatsApp or social media."),
            ]
            for number, title, desc in steps:
                st.markdown(f'<div class="step"><div class="step-icon">{number}</div><div><div class="step-title">{title}</div><div class="step-caption">{desc}</div></div></div>', unsafe_allow_html=True)
    with right:
        with st.container(border=True):
            st.markdown('<div class="card-heading"><span>System status</span><span class="card-chip">LIVE CONFIG</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="status-row"><span>IBM Granite configuration</span><strong style="color:{"#78e69a" if is_configured() else "#f0c36b"}">{"Configured" if is_configured() else "Needs setup"}</strong></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="status-row"><span>Government PDF retrieval</span><strong style="color:{"#78e69a" if retriever else "#f0c36b"}">{"Ready" if retriever else "Unavailable"}</strong></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="status-row"><span>Indexed passages</span><strong>{len(retriever.passages) if retriever else 0}</strong></div>', unsafe_allow_html=True)
            st.caption("Scheme answers are limited to evidence retrieved from the documents bundled with this project.")

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
                result = run_generation(build_profile_prompt(vendor))
                if result:
                    st.session_state["profile_result"] = result
    else:
        st.info("Add your business details above to create a customer-ready profile.")

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
        promo_col1, promo_col2, promo_col3 = st.columns([1, 1, 1])
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
    if checklist_submitted:
        if guard_vendor():
            context = "Vendor priority: " + priority + ".\nTools already used: " + (", ".join(current_tools) if current_tools else "Not specified") + ".\nAdditional context: " + (extra_context.strip() or "Not provided")
            result = run_generation(build_checklist_prompt(vendor, context=context))
            if result:
                valid, reason = validate_checklist(result)
                if valid:
                    st.session_state["checklist_result"] = result
                    st.session_state["checklist_priority"] = priority
                    st.session_state["checklist_completed"] = [False] * len(parse_checklist_steps(result))
                else:
                    st.warning(reason)
    if st.session_state.get("checklist_result"):
        st.markdown('<div class="card-heading"><span>Your personalized action plan</span><span class="card-chip">5–7 STEPS</span></div>', unsafe_allow_html=True)
        st.caption("Priority: " + st.session_state.get("checklist_priority", "Your business"))
        checklist_steps = parse_checklist_steps(st.session_state["checklist_result"])
        if "checklist_completed" not in st.session_state or len(st.session_state["checklist_completed"]) != len(checklist_steps):
            st.session_state["checklist_completed"] = [False] * len(checklist_steps)
        with st.container(border=True):
            completed_count = sum(st.session_state["checklist_completed"])
            total_count = len(checklist_steps)
            st.progress(completed_count / total_count if total_count else 0)
            st.caption(f"{completed_count} of {total_count} steps completed")
            for step_index, step_text in enumerate(checklist_steps):
                checked = st.checkbox(
                    step_text,
                    value=st.session_state["checklist_completed"][step_index],
                    key=f"checklist_step_{step_index}",
                )
                st.session_state["checklist_completed"][step_index] = checked
            completed_count = sum(st.session_state["checklist_completed"])
            st.progress(completed_count / total_count if total_count else 0)
            st.caption(f"Progress: {completed_count}/{total_count} completed")
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
                safe = get_safe_scheme_answer(question.strip(), hits)
                answer = safe if safe is not None else run_generation(build_scheme_qa_prompt(question.strip(), context, qa_language, vendor))
                if answer:
                    st.session_state["scheme_answer"] = answer
                    st.session_state["scheme_hits"] = hits
                    st.session_state["scheme_question"] = question.strip()
    if st.session_state.get("scheme_answer"):
        st.markdown('<div class="card-heading"><span>Answer</span><span class="card-chip">GROUNDED RESPONSE</span></div>', unsafe_allow_html=True)
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

    if "copilot_messages" not in st.session_state:
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
                st.markdown(message["content"])
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
                    source_note = f"Source: {hits[0]['source']} · PDF page {hits[0]['page']}"
                    safe = get_safe_scheme_answer(question.strip(), hits)
                    answer = safe if safe is not None else run_generation(
                        build_scheme_qa_prompt(
                            question.strip(),
                            retriever.format_context(question.strip(), top_k=1),
                            vendor.get("language","English"),
                            vendor,
                        )
                    ) or "I couldn't generate an answer. Please check the IBM watsonx.ai connection and try again."
            st.session_state["copilot_messages"].append({"role":"assistant","content":answer,"source":source_note})
            st.rerun()

    with history_col:
        with st.container(border=True):
            st.markdown('<div class="card-heading"><span>Chat history</span><span class="card-chip">SESSION</span></div>', unsafe_allow_html=True)
            st.caption(f"{len(st.session_state['copilot_messages']) // 2} exchanges in this session")
            if st.button("＋ New chat", use_container_width=True):
                st.session_state["copilot_messages"] = []
                st.rerun()
            if st.session_state["copilot_messages"]:
                for idx, message in enumerate(st.session_state["copilot_messages"]):
                    if message["role"] == "user":
                        st.markdown(f'<div class="step"><div class="step-icon">◉</div><div><div class="step-title">{escape(message["content"][:58])}</div><div class="step-caption">This session</div></div></div>', unsafe_allow_html=True)
            else:
                st.caption("Your recent questions will appear here.")
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
