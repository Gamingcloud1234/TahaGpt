import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io

# --- 1. PREMIUM WHITE THEME & UI ---
st.set_page_config(page_title="TahaGpt Pro", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
        .stApp { background-color: #ffffff !important; color: #000000 !important; }
        [data-testid="stSidebar"] { background-color: #f8f9fa !important; border-right: 1px solid #eeeeee; }
        .stChatInput { border-radius: 20px !important; border: 1px solid #ddd !important; }
        .stChatMessage { background-color: #f7f7f8; border-radius: 15px; margin-bottom: 10px; }
        /* TahaGpt Header Styling */
        .chat-header {
            font-size: 32px;
            font-weight: bold;
            text-align: center;
            color: #333;
            margin-bottom: 20px;
            font-family: 'Arial', sans-serif;
        }
        .pro-badge {
            background-color: #FFD700;
            color: black;
            padding: 2px 8px;
            border-radius: 5px;
            font-size: 12px;
            font-weight: bold;
            margin-left: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API SETUP ---
if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ Add GEMINI_API_KEY to Streamlit Secrets!")
    st.stop()

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# --- 3. SESSION STATE (Memory) ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "is_pro" not in st.session_state:
    st.session_state.is_pro = False

# AI Identity
TAHA_IDENTITY = "Your name is TahaGpt. You were created by M. Taha Farooq."

# --- 4. SIDEBAR ---
with st.sidebar:
    # Profile Picture (Update your link here!)
    MY_PIC_URL = "https://raw.githubusercontent.com/YourUsername/TahaGpt/main/taha.jpg" 
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

    # --- DYNAMIC PRO SECTION ---
    pro_menu_label = "✅ Activated Pro" if st.session_state.is_pro else "💎 Become a Pro"
    
    with st.expander(pro_menu_label):
        if not st.session_state.is_pro:
            st.write("Unlock Family Features")
            promo = st.text_input("Promo Code")
            if st.button("Apply"):
                if promo == "TAHA2026":
                    st.session_state.is_pro = True
                    st.success("Pro Activated!")
                    st.rerun()
            st.write("--- OR ---")
            if st.button("💳 Buy for 100 PKR"):
                st.info("Payment feature coming soon!")
        else:
            st.success("You are a Pro Member!")
            st.write("🌟 No ads\n🌟 Priority Support\n🌟 HD Image Generation")

    st.divider()
    
    # Navigation
    app_mode = st.radio("Navigation", ["💬 Chat", "🎨 Draw", "🖼️ See"])
    st.caption("🚀 Karachi Edition | 2026")

# --- 5. MAIN CHAT AREA ---

# TOP HEADER
st.markdown('<div class="chat-header">TahaGpt</div>', unsafe_allow_html=True)

if app_mode == "💬 Chat":
    # Show badge if Pro
    if st.session_state.is_pro:
        st.markdown('<span class="pro-badge">PRO MODE ACTIVE</span>', unsafe_allow_html=True)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("Ask TahaGpt..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        try:
            # PRO FEATURE: Use a smarter model if Pro is active
            model_to_use = "gemini-2.0-pro-exp" if st.session_state.is_pro else "gemini-2.0-flash"
            
            response = client.models.generate_content(
                model=model_to_use,
                config=types.GenerateContentConfig(system_instruction=TAHA_IDENTITY),
                contents=prompt
            )
            with st.chat_message("assistant"): st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Error: {e}")

# MODE 2: DRAW (PRO FEATURE ADDED)
elif app_mode == "🎨 Draw":
    st.header("🎨 AI Image Generation")
    user_prompt = st.text_area("What should I draw?")
    
    # PRO FEATURE: HD Option
    quality = "High Definition" if st.session_state.is_pro else "Standard"
    st.caption(f"Current Quality: {quality}")

    if st.button("✨ Generate"):
        with st.spinner("Generating..."):
            try:
                response = client.models.generate_content(
                    model='gemini-2.0-flash-image',
                    contents=user_prompt,
                    config=types.GenerateContentConfig(response_modalities=["IMAGE"])
                )
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        st.image(Image.open(io.BytesIO(part.inline_data.data)), use_container_width=True)
            except Exception as e:
                st.error(f"Image Error: {e}")

# MODE 3: SEE
elif app_mode == "🖼️ See":
    st.header("🖼️ Image Intelligence")
    file = st.file_uploader("Upload", type=['png', 'jpg', 'jpeg'])
    if file:
        img = Image.open(file)
        st.image(img, use_container_width=True)
        if st.button("Analyze"):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=["Analyze:", img])
            st.write(res.text)
