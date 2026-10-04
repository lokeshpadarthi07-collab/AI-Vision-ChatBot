import json
import os
import smtplib
from email.mime.text import MIMEText
import urllib.parse
import streamlit as st
from google import genai
from google.genai import types
from twilio.rest import Client as TwilioClient
from prompts import SUMMARY_REQUEST_PROMPT, SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE

# Configure Streamlit page
st.set_page_config(
    page_title="MacroSnap - AI Nutrition Buddy",
    page_icon="🥗",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Model configuration (gemini-flash-latest)
MODEL_NAME = "gemini-flash-latest"

# Helper to retrieve configuration from st.secrets or os.environ
def get_secret(key, default=""):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, default)

GEMINI_API_KEY = get_secret("GEMINI_API_KEY", "")
TWILIO_ACCOUNT_SID = get_secret("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = get_secret("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = get_secret("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
TWILIO_CONTENT_SID = get_secret("TWILIO_CONTENT_SID", "")
GMAIL_ADDRESS = get_secret("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = get_secret("GMAIL_APP_PASSWORD", "")

# Custom CSS for rich aesthetics and clean UI
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #10B981, #06B6D4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    .sub-caption {
        color: #94A3B8;
        font-size: 0.95rem;
        margin-bottom: 1.2rem;
    }
    .user-badge {
        display: inline-flex;
        align-items: center;
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.3);
        color: #34D399;
        padding: 5px 14px;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 500;
        margin-bottom: 1rem;
    }
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
    }
    .sample-pill {
        display: inline-block;
        padding: 6px 12px;
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 20px;
        font-size: 0.82rem;
        color: #E2E8F0;
        margin-right: 6px;
        margin-bottom: 8px;
        cursor: pointer;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Optional sidebar for API key configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    st.markdown("MacroSnap reads credentials from `.streamlit/secrets.toml`. You can also configure them below:")
    sidebar_gemini_key = st.text_input(
        "Gemini API Key",
        value="" if GEMINI_API_KEY.startswith("your-") else GEMINI_API_KEY,
        type="password",
        help="Get a free Gemini API key from https://aistudio.google.com",
    )
    if sidebar_gemini_key:
        GEMINI_API_KEY = sidebar_gemini_key

    with st.expander("Twilio WhatsApp Settings (Option A)"):
        sidebar_twilio_sid = st.text_input("Account SID", value="" if TWILIO_ACCOUNT_SID.startswith("your-") else TWILIO_ACCOUNT_SID)
        sidebar_twilio_token = st.text_input("Auth Token", value="" if TWILIO_AUTH_TOKEN.startswith("your-") else TWILIO_AUTH_TOKEN, type="password")
        sidebar_twilio_from = st.text_input("WhatsApp From", value=TWILIO_WHATSAPP_FROM)
        sidebar_content_sid = st.text_input("Content Template SID (HX...)", value="" if TWILIO_CONTENT_SID.startswith("your-") else TWILIO_CONTENT_SID)
        if sidebar_twilio_sid:
            TWILIO_ACCOUNT_SID = sidebar_twilio_sid
        if sidebar_twilio_token:
            TWILIO_AUTH_TOKEN = sidebar_twilio_token
        if sidebar_twilio_from:
            TWILIO_WHATSAPP_FROM = sidebar_twilio_from
        if sidebar_content_sid:
            TWILIO_CONTENT_SID = sidebar_content_sid

    with st.expander("Gmail SMTP Settings (Option B - Free)"):
        sidebar_gmail = st.text_input("Gmail Address", value="" if GMAIL_ADDRESS.startswith("your-") else GMAIL_ADDRESS)
        sidebar_gmail_pass = st.text_input("App Password (16-char)", value="" if GMAIL_APP_PASSWORD.startswith("your-") else GMAIL_APP_PASSWORD, type="password")
        if sidebar_gmail:
            GMAIL_ADDRESS = sidebar_gmail
        if sidebar_gmail_pass:
            GMAIL_APP_PASSWORD = sidebar_gmail_pass

    st.markdown("---")
    if st.button("🔄 Reset Session / Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.markdown("🥗 **MacroSnap** · Powered by Google Gemini & Twilio WhatsApp.")


@st.cache_resource
def get_gemini_client(api_key: str):
    if not api_key or api_key.startswith("your-"):
        return None
    return genai.Client(api_key=api_key)


@st.cache_resource
def get_twilio_client(account_sid: str, auth_token: str):
    if not account_sid or not auth_token or account_sid.startswith("your-"):
        return None
    try:
        return TwilioClient(account_sid, auth_token)
    except Exception:
        return None


gemini_client = get_gemini_client(GEMINI_API_KEY)
twilio_client = get_twilio_client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def render_message(message):
    with st.chat_message(message["role"]):
        if message["kind"] == "text":
            st.write(message["content"])
        elif message["kind"] == "image":
            st.image(message["content"])


def add_message(role, kind, content):
    st.session_state.messages.append({"role": role, "kind": kind, "content": content})
    render_message(st.session_state.messages[-1])


def ask_gemini(parts):
    try:
        active_key = st.session_state.get("api_key") or GEMINI_API_KEY
        client = get_gemini_client(active_key)
        if client is None:
            return "⚠️ Gemini API key is missing. Please provide it in secrets or on the onboarding screen."
        
        if "chat" not in st.session_state or st.session_state.chat is None:
            st.session_state.chat = client.chats.create(
                model=st.session_state.get("model_used", "gemini-flash-latest"),
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
            )
            
        try:
            return st.session_state.chat.send_message(parts).text
        except Exception as send_err:
            # If client was closed, recreate chat from cached client and retry
            if "closed" in str(send_err).lower():
                st.session_state.chat = client.chats.create(
                    model=st.session_state.get("model_used", "gemini-flash-latest"),
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                )
                return st.session_state.chat.send_message(parts).text
            raise send_err
    except Exception as error:
        return f"Sorry, something went wrong: {error}"


def clean_whatsapp_text(text):
    if not text:
        return "No nutrition summary available."
    text = " ".join(text.split())  # collapse whitespace/newlines
    return text[:1500] + "..." if len(text) > 1500 else text


def send_whatsapp(to_number, user_name, summary):
    # Content template expects {{1}} = name, {{2}} = summary.
    try:
        if not twilio_client or not TWILIO_CONTENT_SID or TWILIO_CONTENT_SID.startswith("your-"):
            return False, "Twilio WhatsApp credentials or Content SID not configured."
        content_variables = json.dumps(
            {"1": user_name, "2": clean_whatsapp_text(summary)}, ensure_ascii=False
        )
        message = twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=f"whatsapp:{to_number}",
            content_sid=TWILIO_CONTENT_SID,
            content_variables=content_variables,
        )
        return True, message.sid
    except Exception as error:
        return False, str(error)


def send_email(to_address, subject, body):
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD or GMAIL_ADDRESS.startswith("your-"):
        return False, "Gmail credentials not configured in secrets.toml."
    try:
        message = MIMEText(body)
        message["Subject"] = subject
        message["From"] = GMAIL_ADDRESS
        message["To"] = to_address
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(message)
        return True, "Email sent successfully!"
    except Exception as error:
        return False, str(error)


# Step 1: Onboarding
if "onboarded" not in st.session_state:
    st.markdown('<div class="main-header">🥗 MacroSnap</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-caption">Snap it. Track it. Text yourself the results.</div>', unsafe_allow_html=True)

    with st.form("onboarding_form"):
        name = st.text_input("Your name", placeholder="e.g. Alex")
        whatsapp_number = st.text_input(
            "WhatsApp number (with country code)",
            placeholder="+91XXXXXXXXXX",
            help="This is the number MacroSnap will text your summary to.",
        )
        email_address = st.text_input(
            "Email address (Optional - for email summaries)",
            placeholder="you@example.com",
            help="Optional: Receive your nutrition summary via Email as well.",
        )
        
        # Prominent API Key input on the form
        default_key_val = "" if GEMINI_API_KEY.startswith("your-") else GEMINI_API_KEY
        form_api_key = st.text_input(
            "Google Gemini API Key",
            value=default_key_val,
            type="password",
            placeholder="AIzaSy...",
            help="Get your free key from https://aistudio.google.com/apikey",
        )
        
        submitted = st.form_submit_button("Let's go 🚀")
        if submitted:
            active_key = (form_api_key or GEMINI_API_KEY).strip().strip('"').strip("'")
            if not name.strip() or not whatsapp_number.strip():
                st.warning("Please fill in both your name and WhatsApp number.")
            elif not active_key or active_key.startswith("your-") or len(active_key) < 10:
                st.error("⚠️ Please enter a valid Gemini API key. Get one for free at https://aistudio.google.com/apikey")
            else:
                st.session_state.name = name.strip()
                st.session_state.whatsapp_number = whatsapp_number.strip()
                st.session_state.email_address = email_address.strip() if email_address else ""
                st.session_state.api_key = active_key
                
                # Test the key and initialize Gemini chat session using cached client
                try:
                    client = get_gemini_client(active_key)
                    if client is None:
                        st.error("Invalid API key provided.")
                        st.stop()
                    # Initialize chat with gemini-flash-latest
                    st.session_state.chat = client.chats.create(
                        model="gemini-flash-latest",
                        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                    )
                    st.session_state.model_used = "gemini-flash-latest"
                    
                    st.session_state.messages = []
                    st.session_state.onboarded = True
                    st.rerun()
                except Exception as ex:
                    st.error(f"❌ Could not connect with this Gemini API key: {ex}\n\nPlease make sure you copied the full key from https://aistudio.google.com/apikey")
    st.stop()


# Step 2: Chat Interface
header_col, btn_wa_col, btn_mail_col = st.columns([4, 2, 2], vertical_alignment="center")
with header_col:
    st.markdown('<div class="main-header">🥗 MacroSnap</div>', unsafe_allow_html=True)

send_disabled = len(st.session_state.messages) <= 2

with btn_wa_col:
    if st.button("📤 WhatsApp", disabled=send_disabled, use_container_width=True, help="Send summary to WhatsApp"):
        with st.spinner("Summarizing your day..."):
            summary = ask_gemini([SUMMARY_REQUEST_PROMPT])
            success, info = send_whatsapp(st.session_state.whatsapp_number, st.session_state.name, summary)
            if success:
                st.success("Sent! Check your WhatsApp 📲")
            else:
                st.warning(f"Twilio: {info}")
                # Direct WhatsApp click-to-chat fallback
                clean_phone = "".join(filter(str.isdigit, st.session_state.whatsapp_number))
                wa_url = f"https://api.whatsapp.com/send?phone={clean_phone}&text={urllib.parse.quote(summary)}"
                st.markdown(
                    f"""<a href="{wa_url}" target="_blank" style="text-decoration: none;">
                        <button style="width: 100%; background: #25D366; color: white; border: none; padding: 7px 12px; border-radius: 8px; font-weight: bold; cursor: pointer; margin-top: 4px;">
                            📲 Open WhatsApp Web
                        </button>
                    </a>""",
                    unsafe_allow_html=True,
                )

with btn_mail_col:
    if st.session_state.get("email_address"):
        if st.button("📧 Email", disabled=send_disabled, use_container_width=True, help="Send summary to Email"):
            with st.spinner("Generating email summary..."):
                summary = ask_gemini([SUMMARY_REQUEST_PROMPT])
                mail_ok, mail_info = send_email(
                    st.session_state.email_address,
                    f"🥗 MacroSnap Daily Summary for {st.session_state.name}",
                    summary,
                )
                if mail_ok:
                    st.success("Summary emailed! 📬")
                else:
                    st.error(f"Email error: {mail_info}")
    else:
        st.button("📧 Email", disabled=True, use_container_width=True, help="Provide an email during login to enable")

badge_text = f"👤 <strong>{st.session_state.name}</strong> · WhatsApp: {st.session_state.whatsapp_number}"
if st.session_state.get("email_address"):
    badge_text += f" · Email: {st.session_state.email_address}"
st.markdown(f'<div class="user-badge">{badge_text}</div>', unsafe_allow_html=True)

# Display chat history
if not st.session_state.messages:
    add_message("assistant", "text", WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.name))
else:
    for message in st.session_state.messages:
        render_message(message)

# Quick sample meal suggestions for instant testing
st.markdown("<div style='font-size: 0.85rem; color: #94A3B8; margin-top: 10px; margin-bottom: 4px;'>💡 Quick test suggestions:</div>", unsafe_allow_html=True)
col_s1, col_s2, col_s3 = st.columns(3)
with col_s1:
    if st.button("🥗 Chicken Salad & Rice", use_container_width=True):
        quick_text = "I had a bowl of grilled chicken salad with brown rice and olive oil dressing."
        add_message("user", "text", quick_text)
        with st.spinner("Crunching the numbers..."):
            ans = ask_gemini([quick_text])
            add_message("assistant", "text", ans)
        st.rerun()

with col_s2:
    if st.button("🥑 Avocado Toast + Egg", use_container_width=True):
        quick_text = "I ate 2 slices of avocado toast with 2 poached eggs and a black coffee."
        add_message("user", "text", quick_text)
        with st.spinner("Crunching the numbers..."):
            ans = ask_gemini([quick_text])
            add_message("assistant", "text", ans)
        st.rerun()

with col_s3:
    if st.button("🍕 Pepperoni Pizza Slice", use_container_width=True):
        quick_text = "I ate 2 large slices of cheesy pepperoni pizza and a can of diet coke."
        add_message("user", "text", quick_text)
        with st.spinner("Crunching the numbers..."):
            ans = ask_gemini([quick_text])
            add_message("assistant", "text", ans)
        st.rerun()

# Chat input with multimodal file upload support
user_input = st.chat_input(
    "Ask a question, or attach a photo of your meal...",
    accept_file=True,
    file_type=["jpg", "jpeg", "png"],
)

if user_input:
    photo = user_input.files[0] if user_input.files else None
    text = user_input.text
    parts = []
    
    if photo is not None:
        photo_bytes = photo.getvalue()
        add_message("user", "image", photo_bytes)
        parts.append(types.Part.from_bytes(data=photo_bytes, mime_type=photo.type))
    
    if text:
        add_message("user", "text", text)
        parts.append(text)
    elif photo is not None:
        parts.append("What is this meal? Give me the calories and macros.")

    with st.spinner("Crunching the numbers..."):
        answer = ask_gemini(parts)
        add_message("assistant", "text", answer)
