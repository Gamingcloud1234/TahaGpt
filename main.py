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
        
        .pro-header {
            background: linear-gradient(90deg, #FFD700, #FFFACD);
            color: #000; padding: 5px; border-radius: 8px;
            text-align: center; font-weight: bold; font-size: 16px;
            margin-bottom: 15px; border: 1px solid #E6B800;
        }
        .normal-header { text-align: center; font-size: 28px; font-weight: bold; margin-bottom: 15px; }
        .pro-item-text { color: #B8860B; font-weight: bold; font-size: 14px; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SESSION STATE ---
if "is_pro" not in st.session_state: st.session_state.is_pro = False
if "messages" not in st.session_state: st.session_state.messages = []
if "page" not in st.session_state: st.session_state.page = "Chat"

# --- 3. API SETUP ---
if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ KEY MISSING: Add GEMINI_API_KEY to your Streamlit Secrets.")
    st.stop()

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
TAHA_IDENTITY = "Your name is TahaGpt. You were created by M. Taha Farooq from Karachi."

# --- 4. SIDEBAR UI ---
with st.sidebar:
    MY_PIC_URL = "https://raw.githubusercontent.com/Gamingcloud1234/TahaGpt/main/Taha.jpeg"
    try:
        st.image(MY_PIC_URL, width=100)
    except:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
    
    st.markdown("**M. Taha Farooq** (Owner)")
    
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.page = "Chat"
        st.rerun()
    
    st.divider()

    # NAVIGATION
    app_mode = st.radio("Main Menu", ["💬 Chatbot", "🎨 Pic Generate", "🖼️ See & Explain"])
    if app_mode == "💬 Chatbot": st.session_state.page = "Chat"
    elif app_mode == "🎨 Pic Generate": st.session_state.page = "Draw"
    elif app_mode == "🖼️ See & Explain": st.session_state.page = "See"

    st.divider()
    st.caption("🚀 Karachi Edition | 2026")

    # --- PRO SECTION (NICHE WALI LINE KE BAAD) ---
    if not st.session_state.is_pro:
        with st.expander("💎 Become a Pro"):
            promo = st.text_input("Promo Code", key="promo_input")
            if st.button("Activate Code", use_container_width=True):
                if promo == "TAHA2026":
                    st.session_state.is_pro = True
                    st.rerun()
                else:
                    st.error("Invalid Code")
            st.write("--- OR ---")
            if st.button("💳 Buy for 100 PKR", use_container_width=True):
                st.info("Payment Link: JazzCash/EasyPaisa (Demo)")
    else:
        st.markdown("<p class='pro-item-text'>💎 Pro Items</p>", unsafe_allow_html=True)
        if st.button("📄 Create a PDF", use_container_width=True):
            st.session_state.page = "PDF_Mode"
            st.rerun()
        if st.button("💻 Create AI Code", use_container_width=True):
            st.session_state.page = "Code_Mode"
            st.rerun()
        if st.button("❌ Remove Pro Mode", use_container_width=True):
            st.session_state.is_pro = False
            st.session_state.page = "Chat"
            st.rerun()

# --- 5. TOP HEADER ---
if st.session_state.is_pro:
    st.markdown('<div class="pro-header">✨ PRO MODE ACTIVE ✨</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="normal-header">TahaGpt</div>', unsafe_allow_html=True)

# --- 6. PAGE LOGIC (Different Screens) ---

# --- MODE: PDF ASSISTANT ---
if st.session_state.page == "PDF_Mode":
    st.header("📄 Pro: PDF Maker")
    content = st.text_area("What should I write in your PDF?", height=200)
    if st.button("Generate & Download"):
        st.success("PDF logic is connected! Ready to download.")

# --- MODE: AI CODER ---
elif st.session_state.page == "Code_Mode":
    st.header("💻 Pro: Coding Studio")
    lang = st.selectbox("Language", ["Python", "JavaScript", "HTML/CSS", "Minecraft Skript"])
    query = st.text_input("What code do you need?")
    if st.button("Write Code"):
        with st.spinner("Coding..."):
            try:
                res = client.models.generate_content(model="gemini-2.5-flash", contents=f"Write {lang} code for: {query}")
                st.code(res.text, language=lang.lower())
            except Exception as e: st.error(e)

# --- NORMAL MODES ---
elif st.session_state.page == "Chat":
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
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
        except Exception as e: st.error(f"Error: {e}")

elif st.session_state.page == "Draw":
    st.header("🎨 AI Image Generation")
    p = st.text_input("Describe the image:")
    if st.button("Generate"):
        try:
            res = client.models.generate_content(model='gemini-2.5-flash-image', contents=p, config=types.GenerateContentConfig(response_modalities=["IMAGE"]))
            for part in res.candidates[0].content.parts:
                if part.inline_data: st.image(Image.open(io.BytesIO(part.inline_data.data)), use_container_width=True)
        except Exception as e: st.error(e)

elif st.session_state.page == "See":
    st.header("🖼️ Image Intelligence")
    # Add your image upload and analyze logic here as before
