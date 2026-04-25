import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io

# --- 1. THE PINNED BOTTOM CSS ---
st.set_page_config(page_title="TahaGpt Pro", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
        .stApp { background-color: #ffffff !important; color: #000000 !important; }
        [data-testid="stSidebar"] { background-color: #f8f9fa !important; border-right: 1px solid #eeeeee; }
        
        /* PIN THE INPUT ROW TO THE BOTTOM */
        div[data-testid="stVerticalBlock"] > div:has(div.stPopover) {
            position: fixed;
            bottom: 30px;
            width: 75%; /* Matches the wide layout width */
            background: white;
            z-index: 1000;
            padding-top: 10px;
        }

        /* Styling the '+' button to be a circular icon */
        div[data-testid="column"] .stPopover button {
            border-radius: 50% !important;
            width: 45px !important;
            height: 45px !important;
            background-color: #f0f2f6 !important;
            border: 1px solid #ddd !important;
            font-size: 24px !important;
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

# --- 3. AUTH LOGIC ---
def login_page():
    st.markdown("<h1 style='text-align: center;'>🚀 TahaGpt Login</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        u = st.text_input("Username", key="l_u")
        p = st.text_input("Password", type="password", key="l_p")
        if st.button("Login", use_container_width=True):
            if u in st.session_state.users and st.session_state.users[u] == p:
                st.session_state.logged_in = True
                st.session_state.current_user = u
                st.rerun()
            else: st.error("Invalid Login")
    with tab2:
        nu = st.text_input("New Username")
        np = st.text_input("New Password", type="password")
        if st.button("Register", use_container_width=True):
            st.session_state.users[nu] = np
            st.success("Account Ready!")

# --- 4. APP CONTENT ---
if not st.session_state.logged_in:
    login_page()
else:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    TAHA_IDENTITY = f"Your name is TahaGpt. Created by Taha Farooq."

    with st.sidebar:
        st.image("https://raw.githubusercontent.com/Gamingcloud1234/TahaGpt/main/Taha.jpeg", width=100)
        st.markdown(f"**Hi, {st.session_state.current_user}!**")
        if st.button("➕ New Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.page = "Chat"
            st.rerun()
        st.divider()
        app_mode = st.radio("Menu", ["💬 Chatbot", "🎨 Pic Generate", "🖼️ See & Explain"])
        if app_mode == "💬 Chatbot": st.session_state.page = "Chat"
        elif app_mode == "🎨 Pic Generate": st.session_state.page = "Draw"
        elif app_mode == "🖼️ See & Explain": st.session_state.page = "See"
        st.divider()
        st.caption("🚀 Karachi Edition | 2026")
        
        if st.session_state.is_pro:
            st.markdown("<p style='color:#B8860B; font-weight:bold;'>💎 Pro Items</p>", unsafe_allow_html=True)
            if st.button("📄 PDF Maker", use_container_width=True): st.session_state.page = "PDF_Mode"; st.rerun()
            if st.button("💻 AI Code", use_container_width=True): st.session_state.page = "Code_Mode"; st.rerun()
            if st.button("🚪 Logout", use_container_width=True): st.session_state.logged_in = False; st.rerun()
        else:
            with st.expander("💎 Become a Pro"):
                if st.button("Activate TAHA2026"): st.session_state.is_pro = True; st.rerun()
            if st.button("🚪 Logout"): st.session_state.logged_in = False; st.rerun()

    # HEADER
    if st.session_state.is_pro:
        st.markdown('<div class="pro-header">✨ PRO MODE ACTIVE ✨</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="normal-header">TahaGpt</div>', unsafe_allow_html=True)

    # PAGES
    if st.session_state.page == "Chat":
        # Padding for chat history so it doesn't hide behind the pinned bar
        st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)
        
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
        # Pinned Input Section
        input_col1, input_col2 = st.columns([0.08, 0.92])
        with input_col1:
            with st.popover("＋"):
                st.file_uploader("Device", type=['png', 'jpg', 'pdf'])
        with input_col2:
            if prompt := st.chat_input("Message TahaGpt..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"): st.markdown(prompt)
                res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                st.session_state.messages.append({"role": "assistant", "content": res.text})
                with st.chat_message("assistant"): st.markdown(res.text)
                st.rerun()

    elif st.session_state.page == "PDF_Mode":
        st.header("📄 PDF Assistant")
        st.text_area("Write something...")
        
    elif st.session_state.page == "Code_Mode":
        st.header("💻 Code Studio")
        st.text_input("Coding prompt...")
