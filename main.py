import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io

# --- 1. UI STYLING ---
st.set_page_config(page_title="TahaGpt Pro", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
        .stApp { background-color: #ffffff !important; color: #000000 !important; }
        [data-testid="stSidebar"] { background-color: #f8f9fa !important; border-right: 1px solid #eeeeee; }
        
        /* Styling the Chat Input to look modern */
        .stChatInput { border-radius: 20px !important; border: 1px solid #ddd !important; }
        .stChatMessage { background-color: #f7f7f8; border-radius: 15px; margin-bottom: 10px; }
        
        /* Slim Pro Bar */
        .pro-header {
            background: linear-gradient(90deg, #FFD700, #FFFACD);
            color: #000; padding: 5px; border-radius: 8px;
            text-align: center; font-weight: bold; font-size: 14px;
            margin-bottom: 15px; border: 1px solid #E6B800;
        }
        .normal-header { text-align: center; font-size: 28px; font-weight: bold; margin-bottom: 15px; }
        
        /* Make the popover button look like a circle '+' button */
        button[kind="secondary"] {
            border-radius: 50% !important;
            width: 40px !important;
            height: 40px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
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

    # PRO SECTION AT THE VERY BOTTOM
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

# --- 5. MAIN PAGE LOGIC ---
if st.session_state.is_pro:
    st.markdown('<div class="pro-header">✨ PRO MODE ACTIVE ✨</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="normal-header">TahaGpt</div>', unsafe_allow_html=True)

# --- MODE: CHAT ---
if st.session_state.page == "Chat":
    # Show history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    # FIXED ATTACHMENT AREA
    # We use a container to keep it right above the chat bar
    with st.container():
        c1, c2 = st.columns([0.07, 0.93])
        with c1:
            # This is the "+" icon
            with st.popover("➕"):
                st.write("📤 **Upload Files**")
                st.file_uploader("Device", type=['png', 'jpg', 'pdf'], key="file_up")
                st.text_input("Drive Link", placeholder="Paste URL here...")
        with c2:
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

# (Keep your PDF_Mode and Code_Mode sections here as well)
