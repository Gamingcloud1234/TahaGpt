import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io

# --- 1. PINNED BOTTOM CSS ---
st.set_page_config(page_title="TahaGpt Pro", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
        .stApp { background-color: #ffffff !important; color: #000000 !important; }
        
        /* PIN THE ENTIRE INPUT SECTION TO THE BOTTOM */
        [data-testid="stVerticalBlock"] > div:has(div.stChatInput) {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background-color: white;
            padding: 10px 10% 20px 10%; /* Adjust padding to match wide layout */
            z-index: 1000;
            border-top: 1px solid #eeeeee;
        }

        /* Style the Popover Button */
        .stPopover button {
            border-radius: 50% !important;
            width: 42px !important;
            height: 42px !important;
            background-color: #f0f2f6 !important;
            border: 1px solid #ddd !important;
            font-size: 20px !important;
        }

        .stChatInput { border-radius: 20px !important; }
        .stChatMessage { margin-bottom: 20px; border-radius: 15px; }
        
        /* Header Styling */
        .pro-header {
            background: linear-gradient(90deg, #FFD700, #FFFACD);
            color: #000; padding: 6px; border-radius: 8px;
            text-align: center; font-weight: bold; font-size: 15px;
        }
        .normal-header { text-align: center; font-size: 28px; font-weight: bold; }
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
            else: st.error("Access Denied")
    with t2:
        nu = st.text_input("New Username")
        np = st.text_input("New Password", type="password")
        if st.button("Create Account", use_container_width=True):
            st.session_state.users[nu] = np
            st.success("User Registered!")

# --- 4. MAIN APP ---
if not st.session_state.logged_in:
    login_page()
else:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    with st.sidebar:
        st.image("https://raw.githubusercontent.com/Gamingcloud1234/TahaGpt/main/Taha.jpeg", width=100)
        st.markdown(f"**Dev: {st.session_state.current_user}**")
        if st.button("➕ New Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        st.divider()
        app_mode = st.radio("Navigation", ["💬 Chatbot", "🎨 Pic Generate", "🖼️ See & Explain"])
        st.divider()
        st.caption("🚀 Karachi Edition | 2026")
        
        if st.session_state.is_pro:
            st.markdown("<p style='color:#B8860B; font-weight:bold;'>💎 Pro Features</p>", unsafe_allow_html=True)
            if st.button("📄 Create PDF", use_container_width=True): st.session_state.page = "PDF_Mode"; st.rerun()
            if st.button("💻 AI Code", use_container_width=True): st.session_state.page = "Code_Mode"; st.rerun()
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # TOP LOGO/HEADER
    if st.session_state.is_pro:
        st.markdown('<div class="pro-header">✨ PRO MODE ACTIVE ✨</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="normal-header">TahaGpt</div>', unsafe_allow_html=True)

    # PAGE: CHAT
    if st.session_state.page == "Chat" or app_mode == "💬 Chatbot":
        # Extra space for messages so they don't get hidden by the sticky bar
        st.write("") 
        
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])

        # STICKY BOTTOM BAR (Always Locked)
        input_col1, input_col2 = st.columns([0.07, 0.93])
        with input_col1:
            with st.popover("＋"):
                st.write("📤 **Upload Files**")
                st.file_uploader("Upload Image", type=['png', 'jpg'])
                st.button("Google Drive")
        with input_col2:
            if prompt := st.chat_input("Message TahaGpt..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"): st.markdown(prompt)
                
                res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                st.session_state.messages.append({"role": "assistant", "content": res.text})
                with st.chat_message("assistant"): st.markdown(res.text)
                st.rerun()
        
        # Spacer for the sticky bar
        st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)

    # PAGE: PDF & CODE
    elif st.session_state.page == "PDF_Mode":
        st.header("📄 PDF Maker Studio")
        st.text_area("Write content here...")
    elif st.session_state.page == "Code_Mode":
        st.header("💻 AI Coding Studio")
        st.text_input("Describe your script...")
