import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io

# --- 1. PREMIUM WHITE THEME (Custom CSS) ---
st.set_page_config(page_title="TahaGpt Pro", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
        .stApp { background-color: #ffffff !important; color: #000000 !important; }
        [data-testid="stSidebar"] { background-color: #f8f9fa !important; border-right: 1px solid #eeeeee; }
        .stChatInput { border-radius: 20px !important; border: 1px solid #ddd !important; }
        .stChatMessage { background-color: #f7f7f8; border-radius: 15px; margin-bottom: 10px; }
        
        /* SLEEK GOLDEN BAR (Reduced Size) */
        .pro-header {
            background: linear-gradient(90deg, #FFD700, #FFFACD);
            color: #000;
            padding: 5px;
            border-radius: 8px;
            text-align: center;
            font-weight: bold;
            font-size: 16px;
            margin-bottom: 15px;
            border: 1px solid #E6B800;
        }
        .normal-header {
            text-align: center;
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 15px;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SESSION STATE ---
if "is_pro" not in st.session_state:
    st.session_state.is_pro = False
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. API CLIENT SETUP ---
if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ KEY MISSING: Add GEMINI_API_KEY to your Streamlit Secrets.")
    st.stop()

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

TAHA_IDENTITY = "Your name is TahaGpt. You were created by M. Taha Farooq."

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
        st.rerun()
    
    st.divider()

    # --- PRO SECTION ---
    if not st.session_state.is_pro:
        with st.expander("💎 Become a Pro"):
            promo = st.text_input("Promo Code", placeholder="Enter code...")
            if st.button("Apply Code", use_container_width=True):
                if promo == "TAHA2026":
                    st.session_state.is_pro = True
                    st.rerun()
                else:
                    st.error("Wrong Code")
            st.divider()
            if st.button("💳 Buy Pro (100 PKR)", use_container_width=True):
                st.info("Payment feature coming soon!")
    else:
        # REMOVE PRO OPTION
        st.success("✅ Pro Active")
        if st.button("❌ Remove Pro Mode", use_container_width=True):
            st.session_state.is_pro = False
            st.rerun()

    st.divider()
    app_mode = st.radio("Navigation", ["💬 Chatbot", "🎨 Pic Generate", "🖼️ See & Explain"])
    st.caption("🚀 Karachi Edition | 2026")

# --- 5. TOP HEADER ---
if st.session_state.is_pro:
    st.markdown('<div class="pro-header">✨ PRO MODE ACTIVE ✨</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="normal-header">TahaGpt</div>', unsafe_allow_html=True)

# --- 6. APP MODES ---
if app_mode == "💬 Chatbot":
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
        except Exception as e:
            st.error(f"Error: {e}")

elif app_mode == "🎨 Pic Generate":
    st.header("🎨 AI Image Generation")
    user_prompt = st.text_area("What should I draw?")
    if st.button("✨ Generate"):
        with st.spinner("Drawing..."):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash-image',
                    contents=user_prompt,
                    config=types.GenerateContentConfig(response_modalities=["IMAGE"])
                )
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        st.image(Image.open(io.BytesIO(part.inline_data.data)), use_container_width=True)
            except Exception as e:
                st.error(f"Error: {e}")

elif app_mode == "🖼️ See & Explain":
    st.header("🖼️ Image Intelligence")
    file = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'])
    if file:
        img = Image.open(file)
        st.image(img, use_container_width=True)
        if st.button("Analyze"):
            try:
                res = client.models.generate_content(model="gemini-2.5-flash", contents=["Analyze this:", img])
                st.write(res.text)
            except Exception as e: st.error(f"Error: {e}")
