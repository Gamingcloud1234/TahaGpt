import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io

# --- 1. PREMIUM WHITE THEME ---
st.set_page_config(page_title="TahaGpt Pro", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
        .stApp { background-color: #ffffff !important; color: #000000 !important; }
        [data-testid="stSidebar"] { background-color: #f8f9fa !important; border-right: 1px solid #eeeeee; }
        .stChatInput { border-radius: 20px !important; border: 1px solid #ddd !important; }
        .stChatMessage { background-color: #f7f7f8; border-radius: 15px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API SETUP ---
if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ Add GEMINI_API_KEY to Streamlit Secrets!")
    st.stop()

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
TAHA_IDENTITY = "Your name is TahaGpt. You were created by M. Taha Farooq, a 9th-grade developer from Karachi."

# --- 3. SIDEBAR WITH YOUR PIC & FAMILY SECTION ---
with st.sidebar:
    # --- USER PROFILE ---
    MY_PIC_URL = "PASTE_YOUR_RAW_GITHUB_LINK_HERE" # Update this link!
    try:
        st.image(MY_PIC_URL, width=110)
    except:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
    
    st.markdown("### M. Taha Farooq")
    st.caption("Developer & Admin")
    
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()

    # --- NEW: BECOME A PRO (FAMILY SECTION) ---
    with st.expander("💎 Become a Pro"):
        st.write("Special Family Upgrade")
        
        # Option 1: Promo Code
        promo = st.text_input("Enter Promo Code", placeholder="Family Code...")
        if st.button("Apply Code", use_container_width=True):
            if promo == "TAHA2026": # You can change this secret code
                st.success("Pro Activated!")
            else:
                st.error("Invalid Code")

        st.markdown("<p style='text-align: center;'>OR</p>", unsafe_allow_html=True)

        # Option 2: Buy for 100 Rupees
        if st.button("💳 Buy Pro (100 PKR)", use_container_width=True):
            st.info("Redirecting to payment gateway...")
            # Here you could add a link to JazzCash/EasyPaisa
    
    st.divider()
    
    app_mode = st.radio("Navigation", ["💬 Chatbot", "🎨 Pic Generate", "🖼️ See & Explain"])
    st.caption("🚀 Karachi Edition | 2026")

# --- 4. APP LOGIC ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# (Logic for Chatbot, Pic Generate, and See & Explain stays the same as before)
if app_mode == "💬 Chatbot":
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("Message TahaGpt..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                config=types.GenerateContentConfig(system_instruction=TAHA_IDENTITY),
                contents=prompt
            )
            with st.chat_message("assistant"): st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Error: {e}")

# ... rest of your Mode 2 and Mode 3 logic ...
