import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io

# --- 1. CLEAN UI ---
st.set_page_config(page_title="TahaGpt Pro", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
        .stApp { background-color: #ffffff !important; color: #000000 !important; }
        [data-testid="stSidebar"] { background-color: #f8f9fa !important; border-right: 1px solid #eeeeee; }
        
        /* Floating '+' button style */
        .stPopover button {
            border-radius: 20px !important;
            background-color: #f0f2f6 !important;
            border: 1px solid #ddd !important;
            font-weight: bold;
        }

        .stChatInput { border-radius: 20px !important; }
        .stChatMessage { background-color: #f7f7f8; border-radius: 15px; margin-bottom: 10px; }
        
        .pro-header {
            background: linear-gradient(90deg, #FFD700, #FFFACD);
            color: #000; padding: 6px; border-radius: 8px;
            text-align: center; font-weight: bold; font-size: 15px;
            margin-bottom: 15px;
        }
        .normal-header { text-align: center; font-size: 28px; font-weight: bold; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SESSION STATE ---
if "users" not in st.session_state: st.session_state.users = {"admin": "taha123"}
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "current_user" not in st.session_state: st.session_state.current_user = ""
if "is_pro" not in st.session_state: st.session_state.is_pro = False
if "messages" not in st.session_state: st.session_state.messages = []
if "page" not in st.session_state: st.session_state.page = "Chat"

# --- 3. LOGIN PAGE ---
def login_page():
    st.markdown("<h1 style='text-align: center;'>🚀 TahaGpt Login</h1>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["Login", "Register"])
    with t1:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login", use_container_width=True):
            if u in st.session_state.users and st.session_state.users[u] == p:
                st.session_state.logged_in = True
                st.session_state.current_user = u
                st.rerun()
            else: st.error("Wrong details")
    with t2:
        nu = st.text_input("New Username")
        np = st.text_input("New Password", type="password")
        if st.button("Register", use_container_width=True):
            st.session_state.users[nu] = np
            st.success("Account Created!")

# --- 4. MAIN APP ---
if not st.session_state.logged_in:
    login_page()
else:
    # API SETUP
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    TAHA_IDENTITY = f"Your name is TahaGpt. Created by Taha Farooq for {st.session_state.current_user}."

    with st.sidebar:
        st.image("https://raw.githubusercontent.com/Gamingcloud1234/TahaGpt/main/Taha.jpeg", width=100)
        st.markdown(f"**User: {st.session_state.current_user}**")
        if st.button("➕ New Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.page = "Chat"
            st.rerun()
        st.divider()
        app_mode = st.radio("Menu", ["💬 Chatbot", "🎨 Pic Generate", "🖼️ See & Explain"])
        st.divider()
        st.caption("🚀 Karachi Edition | 2026")
        
        if st.session_state.is_pro:
            st.markdown("<p style='color:#B8860B; font-weight:bold;'>💎 Pro Items</p>", unsafe_allow_html=True)
            if st.button("📄 PDF Maker", use_container_width=True): st.session_state.page = "PDF_Mode"; st.rerun()
            if st.button("💻 AI Code", use_container_width=True): st.session_state.page = "Code_Mode"; st.rerun()
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # HEADER
    if st.session_state.is_pro:
        st.markdown('<div class="pro-header">✨ PRO MODE ACTIVE ✨</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="normal-header">TahaGpt</div>', unsafe_allow_html=True)

    # PAGE: CHAT
    if st.session_state.page == "Chat":
        # Chat Messages Area
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])

        # THE FIX: Bottom Attachment Bar
        # Ye chat input ke bilkul upar hamesha rahega
        st.write("") # Spacer
        with st.popover("➕ Attach Files"):
            st.write("📤 **Select Source**")
            st.file_uploader("This Device", type=['png', 'jpg', 'pdf'])
            st.button("Google Drive")
            st.button("Web Link")

        # THE INPUT BAR (Pinned by Streamlit naturally)
        if prompt := st.chat_input("Message TahaGpt..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            try:
                res = client.models.generate_content(
                    model="gemini-2.0-flash",
                    config=types.GenerateContentConfig(system_instruction=TAHA_IDENTITY),
                    contents=prompt
                )
                st.session_state.messages.append({"role": "assistant", "content": res.text})
                with st.chat_message("assistant"): st.markdown(res.text)
                st.rerun()
            except Exception as e: st.error(e)

    # PAGE: PDF
    elif st.session_state.page == "PDF_Mode":
        st.header("📄 PDF Assistant")
        st.text_area("Content for PDF...")

    # PAGE: CODE
    elif st.session_state.page == "Code_Mode":
        st.header("💻 Code Studio")
        st.text_input("Coding prompt...")
