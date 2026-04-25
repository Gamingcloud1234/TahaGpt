import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io

# --- 1. THE ULTIMATE UI & CSS ---
st.set_page_config(page_title="TahaGpt Pro", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
        .stApp { background-color: #ffffff !important; color: #000000 !important; }
        [data-testid="stSidebar"] { background-color: #f8f9fa !important; border-right: 1px solid #eeeeee; }
        
        /* Circular Style for the '+' button */
        div[data-testid="column"] .stPopover button {
            border-radius: 50% !important;
            width: 45px !important;
            height: 45px !important;
            background-color: #f0f2f6 !important;
            border: 1px solid #ddd !important;
            font-size: 24px !important;
            margin-top: 5px;
        }

        .stChatInput { border-radius: 20px !important; }
        .stChatMessage { background-color: #f7f7f8; border-radius: 15px; margin-bottom: 10px; }
        
        .pro-header {
            background: linear-gradient(90deg, #FFD700, #FFFACD);
            color: #000; padding: 6px; border-radius: 8px;
            text-align: center; font-weight: bold; font-size: 15px;
            margin-bottom: 15px; border: 1px solid #E6B800;
        }
        .normal-header { text-align: center; font-size: 28px; font-weight: bold; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SESSION STATE SETUP ---
if "users" not in st.session_state:
    st.session_state.users = {"admin": "taha123"} # Default user
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = ""
if "is_pro" not in st.session_state: 
    st.session_state.is_pro = False
if "messages" not in st.session_state: 
    st.session_state.messages = []
if "page" not in st.session_state: 
    st.session_state.page = "Chat"

# --- 3. LOGIN & REGISTER SYSTEM ---
def login_page():
    st.markdown("<h1 style='text-align: center;'>🚀 TahaGpt Login</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        u = st.text_input("Username", key="login_u")
        p = st.text_input("Password", type="password", key="login_p")
        if st.button("Login", use_container_width=True):
            if u in st.session_state.users and st.session_state.users[u] == p:
                st.session_state.logged_in = True
                st.session_state.current_user = u
                st.rerun()
            else:
                st.error("Invalid username or password")

    with tab2:
        new_u = st.text_input("Choose Username", key="reg_u")
        new_p = st.text_input("Choose Password", type="password", key="reg_p")
        if st.button("Create Account", use_container_width=True):
            if new_u in st.session_state.users:
                st.warning("Username already exists!")
            elif new_u and new_p:
                st.session_state.users[new_u] = new_p
                st.success("Account created! Please login.")
            else:
                st.error("Fields cannot be empty")

# --- 4. MAIN APP LOGIC ---
if not st.session_state.logged_in:
    login_page()
else:
    # API SETUP
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("⚠️ KEY MISSING: Add GEMINI_API_KEY to your Streamlit Secrets.")
        st.stop()
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    TAHA_IDENTITY = f"Your name is TahaGpt. You are helping {st.session_state.current_user}. Created by Taha Farooq."

    # SIDEBAR
    with st.sidebar:
        st.image("https://raw.githubusercontent.com/Gamingcloud1234/TahaGpt/main/Taha.jpeg", width=100)
        st.markdown(f"**Welcome, {st.session_state.current_user}!**")
        
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

        # PRO SECTION
        if st.session_state.is_pro:
            st.markdown("<p style='color:#B8860B; font-weight:bold;'>💎 Pro Items</p>", unsafe_allow_html=True)
            if st.button("📄 Create a PDF", use_container_width=True): st.session_state.page = "PDF_Mode"; st.rerun()
            if st.button("💻 Create AI Code", use_container_width=True): st.session_state.page = "Code_Mode"; st.rerun()
            if st.button("❌ Logout", use_container_width=True): 
                st.session_state.logged_in = False
                st.rerun()
        else:
            with st.expander("💎 Become a Pro"):
                promo = st.text_input("Promo Code")
                if st.button("Activate"):
                    if promo == "TAHA2026": st.session_state.is_pro = True; st.rerun()
                if st.button("💳 Buy for 100 PKR", use_container_width=True): st.info("Demo Mode")
            if st.button("🚪 Logout"): 
                st.session_state.logged_in = False
                st.rerun()

    # HEADER
    if st.session_state.is_pro:
        st.markdown('<div class="pro-header">✨ PRO MODE ACTIVE ✨</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="normal-header">TahaGpt</div>', unsafe_allow_html=True)

    # PAGES
    if st.session_state.page == "Chat":
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
        # STABLE PLUS ICON LAYOUT
        input_container = st.container()
        with input_container:
            c1, c2 = st.columns([0.08, 0.92])
            with c1:
                with st.popover("＋"):
                    st.file_uploader("Upload", type=['png', 'jpg', 'pdf'])
                    st.button("Drive")
            with c2:
                if prompt := st.chat_input("Message TahaGpt..."):
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    with st.chat_message("user"): st.markdown(prompt)
                    res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                    st.session_state.messages.append({"role": "assistant", "content": res.text})
                    with st.chat_message("assistant"): st.markdown(res.text)

    elif st.session_state.page == "PDF_Mode":
        st.header("📄 PDF Maker")
        st.text_area("Content...")
        st.button("Generate")

    elif st.session_state.page == "Code_Mode":
        st.header("💻 Code Studio")
        st.text_input("What code do you need?")
        st.button("Write Code")

    elif st.session_state.page == "Draw":
        st.header("🎨 Image Gen")
        # Image gen code here...
