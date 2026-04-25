import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io

# --- 1. UI SETTINGS ---
st.set_page_config(page_title="TahaGpt Pro", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
        /* Modern White Theme */
        .stApp { background-color: #ffffff !important; color: #000000 !important; }
        [data-testid="stSidebar"] { background-color: #f8f9fa !important; border-right: 1px solid #eeeeee; }
        
        /* Chat Styling */
        .stChatInput { border-radius: 20px !important; }
        .stChatMessage { border-radius: 15px; margin-bottom: 10px; border: 1px solid #f0f0f0; }
        
        /* Pro Golden Bar */
        .pro-header {
            background: linear-gradient(90deg, #FFD700, #FFFACD);
            color: #000; padding: 8px; border-radius: 10px;
            text-align: center; font-weight: bold; font-size: 16px;
            margin-bottom: 20px; border: 1px solid #E6B800;
        }
        .normal-header { text-align: center; font-size: 32px; font-weight: bold; margin-bottom: 20px; color: #1a1a1a; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SESSION STATE (Database & Auth) ---
if "users" not in st.session_state:
    st.session_state.users = {"admin": "taha123"} # Default Account
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
def auth_screen():
    st.markdown("<div class='normal-header'>TahaGpt</div>", unsafe_allow_html=True)
    
    # Center the login box
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])
        
        with tab1:
            u = st.text_input("Username", key="l_user")
            p = st.text_input("Password", type="password", key="l_pass")
            if st.button("Login", use_container_width=True):
                if u in st.session_state.users and st.session_state.users[u] == p:
                    st.session_state.logged_in = True
                    st.session_state.current_user = u
                    st.rerun()
                else:
                    st.error("Invalid username or password")

        with tab2:
            new_u = st.text_input("Choose Username", key="r_user")
            new_p = st.text_input("Choose Password", type="password", key="r_pass")
            if st.button("Create Account", use_container_width=True):
                if new_u and new_p:
                    if new_u in st.session_state.users:
                        st.warning("User already exists!")
                    else:
                        st.session_state.users[new_u] = new_p
                        st.success("Account created! Go to Login tab.")
                else:
                    st.error("Please fill all fields")

# --- 4. MAIN APPLICATION ---
if not st.session_state.logged_in:
    auth_screen()
else:
    # Gemini Setup
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    TAHA_IDENTITY = f"Your name is TahaGpt. Created by M. Taha Farooq for {st.session_state.current_user}."

    # Sidebar UI
    with st.sidebar:
        # User Profile
        st.image("https://raw.githubusercontent.com/Gamingcloud1234/TahaGpt/main/Taha.jpeg", width=100)
        st.markdown(f"👤 **{st.session_state.current_user}**")
        
        if st.button("➕ New Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.page = "Chat"
            st.rerun()
        
        st.divider()
        # Main Navigation
        app_mode = st.radio("Navigation", ["💬 Chatbot", "🎨 Pic Generate", "🖼️ See & Explain"])
        
        st.divider()
        st.caption("🚀 Karachi Edition | 2026")

        # Pro Section (Fixed below Karachi Edition)
        if st.session_state.is_pro:
            st.markdown("<p style='color:#B8860B; font-weight:bold; margin-top:10px;'>💎 Pro Items</p>", unsafe_allow_html=True)
            if st.button("📄 Create a PDF", use_container_width=True):
                st.session_state.page = "PDF_Mode"
                st.rerun()
            if st.button("💻 Create AI Code", use_container_width=True):
                st.session_state.page = "Code_Mode"
                st.rerun()
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.logged_in = False
                st.rerun()
        else:
            with st.expander("💎 Become a Pro"):
                st.write("Price: 100 PKR")
                promo = st.text_input("Enter Promo Code")
                if st.button("Activate"):
                    if promo == "TAHA2026":
                        st.session_state.is_pro = True
                        st.rerun()
                st.button("💳 Buy via EasyPaisa", use_container_width=True)
            
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.logged_in = False
                st.rerun()

    # Dynamic Header
    if st.session_state.is_pro:
        st.markdown('<div class="pro-header">✨ PRO MODE ACTIVE ✨</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="normal-header">TahaGpt</div>', unsafe_allow_html=True)

    # PAGE LOGIC
    if app_mode == "💬 Chatbot" and st.session_state.page == "Chat":
        # Display Messages
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat Input (Locked to bottom by Streamlit)
        if prompt := st.chat_input("Message TahaGpt..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    config=types.GenerateContentConfig(system_instruction=TAHA_IDENTITY),
                    contents=prompt
                )
                with st.chat_message("assistant"):
                    st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"API Error: {e}")

    elif st.session_state.page == "PDF_Mode":
        st.header("📄 PDF Generation Studio")
        st.write("Enter the text you want to convert into a professional PDF document.")
        st.text_area("Document Content", height=300)
        st.button("Download PDF")

    elif st.session_state.page == "Code_Mode":
        st.header("💻 AI Code Assistant")
        st.write("Generate clean code for Python, Minecraft, or Web Apps.")
        code_input = st.text_input("What code should I write?")
        if st.button("Generate Code"):
            st.code("# TahaGpt Pro Code Output\nprint('Hello Karachi!')")

    elif app_mode == "🎨 Pic Generate":
        st.header("🎨 AI Artist")
        # Add your image generation logic here...

    elif app_mode == "🖼️ See & Explain":
        st.header("🖼️ Visual Intelligence")
        # Add your image analysis logic here...
