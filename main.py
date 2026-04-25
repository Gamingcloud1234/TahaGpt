import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io

# --- 1. PAGE SETUP & PREMIUM CSS ---
st.set_page_config(page_title="TahaGpt", page_icon="🤖", layout="wide")

st.markdown("""
    <style>
        /* Modern Sidebar */
        [data-testid="stSidebar"] {
            background-color: #000000;
            color: #ffffff;
        }
        /* Chat Input Styling */
        .stChatInput {
            border-radius: 25px !important;
            padding-bottom: 20px;
        }
        /* Remove Sidebar Menu "Boring" Look */
        .stRadio [data-testid="stWidgetLabel"] {
            display: none;
        }
        /* Hide Streamlit Branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. API CLIENT ---
if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ Add GEMINI_API_KEY to Streamlit Secrets!")
    st.stop()

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# --- 3. SIDEBAR (The Modern Menu) ---
with st.sidebar:
    st.title("🤖 TahaGpt")
    
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    
    # Tool selection looks like a modern menu now
    app_mode = st.radio(
        "Navigation",
        ["💬 Chat", "🎨 Pic Generate", "🖼️ See & Explain"],
        captions=["Fast & Smart", "Nano Banana 2 Engine", "Analyze Photos"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.caption("🚀 Developed by M. Taha Farooq")
    st.sidebar.caption("Karachi, Pakistan | 2026")

# --- 4. SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 5. MODES ---

# THE IDENTITY (System Instruction)
sys_msg = "Your name is TahaGpt. You were created by M. Taha Farooq. You are a helpful, witty, and intelligent AI assistant. Never refer to yourself by any other name."

if app_mode == "💬 Chat":
    # Show welcome message if chat is empty
    if not st.session_state.messages:
        st.write("### Hello, Taha. How can I assist you today?")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask TahaGpt..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                config=types.GenerateContentConfig(system_instruction=sys_msg),
                contents=prompt
            )
            with st.chat_message("assistant"):
                st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Chat Error: {e}")

elif app_mode == "🎨 Pic Generate":
    st.header("🎨 AI Image Creator")
    user_prompt = st.text_area("Describe what you want to see:", placeholder="A robotic cricket match in Karachi...")
    
    if st.button("✨ Generate"):
        if user_prompt:
            with st.spinner("TahaGpt is drawing..."):
                try:
                    response = client.models.generate_content(
                        model='gemini-2.5-flash-image',
                        contents=user_prompt,
                        config=types.GenerateContentConfig(response_modalities=["IMAGE"])
                    )
                    for part in response.candidates[0].content.parts:
                        if part.inline_data:
                            img = Image.open(io.BytesIO(part.inline_data.data))
                            st.image(img, caption="Created for Taha", use_container_width=True)
                except Exception as e:
                    st.error(f"Image Error: {e}")
        else:
            st.warning("Please enter a description first!")

elif app_mode == "🖼️ See & Explain":
    st.header("🖼️ Image Intelligence")
    uploaded_file = st.file_uploader("Upload a photo", type=['png', 'jpg', 'jpeg'])
    
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, use_container_width=True)
        if st.button("🔍 Analyze"):
            with st.spinner("Looking closely..."):
                try:
                    res = client.models.generate_content(
                        model="gemini-2.5-flash", 
                        contents=["Explain this image to me:", img]
                    )
                    st.write("### Analysis:")
                    st.write(res.text)
                except Exception as e:
                    st.error(f"Analysis Error: {e}")
