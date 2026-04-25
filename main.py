import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io

# --- 1. THE ULTIMATE CSS HACK ---
st.set_page_config(page_title="TahaGpt Pro", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
        .stApp { background-color: #ffffff !important; }
        
        /* This moves the popover button to look like it's inside the chat bar */
        div[data-testid="stVerticalBlock"] > div:has(div.stPopover) {
            position: fixed;
            bottom: 38px;
            left: 50px;
            z-index: 1000;
        }

        /* Styling the '+' button to be a small circle */
        .stPopover button {
            border-radius: 50% !important;
            width: 35px !important;
            height: 35px !important;
            background-color: #f0f2f6 !important;
            border: 1px solid #ddd !important;
            font-size: 20px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding-bottom: 5px !important;
        }

        /* Adjusting chat input padding to make room for the button */
        .stChatInput textarea {
            padding-left: 50px !important;
        }

        .stChatMessage { background-color: #f7f7f8; border-radius: 15px; }
        .pro-header {
            background: linear-gradient(90deg, #FFD700, #FFFACD);
            color: #000; padding: 5px; border-radius: 8px;
            text-align: center; font-weight: bold; font-size: 14px;
            margin-bottom: 15px;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SESSION STATE ---
if "is_pro" not in st.session_state: st.session_state.is_pro = False
if "messages" not in st.session_state: st.session_state.messages = []
if "page" not in st.session_state: st.session_state.page = "Chat"

# --- 3. API SETUP ---
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
TAHA_IDENTITY = "Your name is TahaGpt. You were created by M. Taha Farooq."

# --- 4. SIDEBAR ---
with st.sidebar:
    st.image("https://raw.githubusercontent.com/Gamingcloud1234/TahaGpt/main/Taha.jpeg", width=100)
    st.markdown("**M. Taha Farooq** (Owner)")
    
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.page = "Chat"
        st.rerun()
    
    st.divider()
    app_mode = st.radio("Main Menu", ["💬 Chatbot", "🎨 Pic Generate", "🖼️ See & Explain"])
    st.divider()
    st.caption("🚀 Karachi Edition | 2026")

    if st.session_state.is_pro:
        st.markdown("<p style='color:#B8860B; font-weight:bold;'>💎 Pro Items</p>", unsafe_allow_html=True)
        if st.button("📄 Create a PDF", use_container_width=True): st.session_state.page = "PDF_Mode"; st.rerun()
        if st.button("💻 Create AI Code", use_container_width=True): st.session_state.page = "Code_Mode"; st.rerun()
        if st.button("❌ Remove Pro", use_container_width=True): st.session_state.is_pro = False; st.rerun()
    else:
        with st.expander("💎 Become a Pro"):
            promo = st.text_input("Promo Code")
            if st.button("Activate"):
                if promo == "TAHA2026": st.session_state.is_pro = True; st.rerun()
            st.button("💳 Buy for 100 PKR", use_container_width=True)

# --- 5. TOP HEADER ---
if st.session_state.is_pro:
    st.markdown('<div class="pro-header">✨ PRO MODE ACTIVE ✨</div>', unsafe_allow_html=True)
else:
    st.markdown('<h2 style="text-align:center;">TahaGpt</h2>', unsafe_allow_html=True)

# --- 6. THE CHAT INTERFACE ---
if st.session_state.page == "Chat":
    # Show History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    # THE FLOATING "+" BUTTON
    # This sits exactly over the left side of the input bar
    with st.popover("＋"):
        st.write("📤 **Upload Options**")
        st.file_uploader("This device", type=['png', 'jpg', 'pdf', 'txt'])
        st.button("Google Drive")
        st.button("Link")

    # THE INPUT BAR
    if prompt := st.chat_input("Message TahaGpt..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                config=types.GenerateContentConfig(system_instruction=TAHA_IDENTITY),
                contents=prompt
            )
            with st.chat_message("assistant"): st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e: st.error(e)

# (Keep your PDF_Mode and Code_Mode sections same as before)
