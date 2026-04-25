import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io

# --- 1. PREMIUM WHITE THEME (Custom CSS) ---
st.set_page_config(page_title="TahaGpt Pro", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
        /* Force Light Mode White Theme */
        .stApp {
            background-color: #ffffff !important;
            color: #000000 !important;
        }
        
        /* Clean Sidebar */
        [data-testid="stSidebar"] {
            background-color: #f8f9fa !important;
            border-right: 1px solid #eeeeee;
        }

        /* ChatGPT-Style Chat Input */
        .stChatInput {
            border-radius: 20px !important;
            border: 1px solid #ddd !important;
        }

        /* Chat Message Styling */
        .stChatMessage {
            background-color: #f7f7f8;
            border-radius: 15px;
            margin-bottom: 10px;
        }
        
        /* Sidebar User Label */
        .user-label {
            font-weight: bold;
            color: #333;
            font-size: 14px;
        }

        /* TahaGpt Golden Pro Bar */
        .pro-header {
            background: linear-gradient(90deg, #FFD700, #FFEC8B);
            color: #000000;
            padding: 10px;
            border-radius: 10px;
            text-align: center;
            font-weight: bold;
            font-size: 24px;
            margin-bottom: 20px;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
        }
        /* Normal Header */
        .normal-header {
            text-align: center;
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SESSION STATE (For Pro Activation) ---
if "is_pro" not in st.session_state:
    st.session_state.is_pro = False
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. API CLIENT SETUP ---
if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ KEY MISSING: Add GEMINI_API_KEY to your Streamlit Secrets.")
    st.stop()

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

TAHA_IDENTITY = (
    "Your name is TahaGpt. You were created by M. Taha Farooq, "
    "a 9th-grade developer and robotics enthusiast from Karachi. "
    "Always identify yourself as TahaGpt and be helpful."
)

# --- 4. SIDEBAR UI ---
with st.sidebar:
    MY_PIC_URL = "https://raw.githubusercontent.com/Gamingcloud1234/TahaGpt/main/Taha.jpeg"
    
    try:
        st.image(MY_PIC_URL, width=100)
    except:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
    
    st.markdown("<p class='user-label'>M. Taha Farooq (Owner)</p>", unsafe_allow_html=True)
    
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()

    # --- PRO UPGRADE SECTION ---
    pro_label = "✅ Pro Mode Activated" if st.session_state.is_pro else "💎 Become a Pro"
    with st.expander(pro_label):
        if not st.session_state.is_pro:
            promo = st.text_input("Enter Promo Code", placeholder="Family Code...")
            if st.button("Apply Code", use_container_width=True):
                if promo == "TAHA2026": # You can change this code
                    st.session_state.is_pro = True
                    st.success("Pro Activated!")
                    st.rerun()
                else:
                    st.error("Invalid Code")
            
            st.markdown("<p style='text-align: center;'>OR</p>", unsafe_allow_html=True)
            
            if st.button("💳 Buy for 100 Rupees", use_container_width=True):
                st.info("Payment system coming soon!")
        else:
            st.write("Welcome to the Family Pro experience!")

    st.divider()
    app_mode = st.radio("Navigation", ["💬 Chatbot", "🎨 Pic Generate", "🖼️ See & Explain"])
    st.divider()
    st.caption("🚀 Karachi Edition | 2026")

# --- 5. APP TOP HEADER ---
if st.session_state.is_pro:
    st.markdown('<div class="pro-header">✨ TahaGpt Pro Mode Activated ✨</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="normal-header">TahaGpt</div>', unsafe_allow_html=True)

# --- 6. APP MODES ---

# MODE 1: CHATBOT
if app_mode == "💬 Chatbot":
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Message TahaGpt..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                config=types.GenerateContentConfig(system_instruction=TAHA_IDENTITY),
                contents=prompt
            )
            with st.chat_message("assistant"):
                st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            if "429" in str(e):
                st.warning("⏳ Quota reached. Please wait 60 seconds.")
            else:
                st.error(f"Error: {e}")

# MODE 2: PIC GENERATE
elif app_mode == "🎨 Pic Generate":
    st.header("🎨 AI Image Generation")
    user_prompt = st.text_area("What should TahaGpt draw?")
    if st.button("✨ Generate Image"):
        with st.spinner("Generating..."):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash-image',
                    contents=user_prompt,
                    config=types.GenerateContentConfig(response_modalities=["IMAGE"])
                )
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        img = Image.open(io.BytesIO(part.inline_data.data))
                        st.image(img, caption="Created by TahaGpt", use_container_width=True)
            except Exception as e:
                st.error(f"Image Error: {e}")

# MODE 3: SEE & EXPLAIN
elif app_mode == "🖼️ See & Explain":
    st.header("🖼️ Image Intelligence")
    file = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'])
    if file:
        img = Image.open(file)
        st.image(img, use_container_width=True)
        if st.button("Analyze"):
            try:
                res = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=["Describe this image for me:", img]
                )
                st.write(res.text)
            except Exception as e:
                st.error(f"Error: {e}")
