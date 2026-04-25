import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- PAGE SETUP ---
st.set_page_config(page_title="TahaGpt Pro", page_icon="🤖", layout="wide")

# --- API CLIENT ---
if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ Add GEMINI_API_KEY to Secrets!")
    st.stop()

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# --- SIDEBAR UI ---
with st.sidebar:
    st.title("🤖 TahaGpt Menu")
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    app_mode = st.radio("Select Tool:", ["💬 Chatbot", "🎨 Pic Generate", "🖼️ Analyze Image"])
    st.info("Free Tier Mode | Karachi 2026")

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- MODE 1: CHATBOT ---
if app_mode == "💬 Chatbot":
    st.header("💬 Smart Chat")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask TahaGpt anything..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            # Using 1.5 Flash as it's more stable for Free Tier limits
            response = client.models.generate_content(
                model="gemini-1.5-flash", 
                contents=prompt
            )
            with st.chat_message("assistant"):
                st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            if "429" in str(e):
                st.warning("⏳ Karachi Server is busy (Quota Limit). Please wait 30 seconds and try again!")
            else:
                st.error(f"Error: {e}")

# --- MODE 2: PIC GENERATE ---
elif app_mode == "🎨 Pic Generate":
    st.header("🎨 AI Image Creator")
    user_prompt = st.text_area("Describe the image...")
    
    if st.button("✨ Generate"):
        with st.spinner("Drawing..."):
            try:
                response = client.models.generate_content(
                    model='imagen-3', 
                    contents=user_prompt,
                    config=types.GenerateContentConfig(response_modalities=["IMAGE"])
                )
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        st.image(Image.open(io.BytesIO(part.inline_data.data)))
            except Exception as e:
                st.error("Image generation is limited on Free Tier. Try again in a few minutes.")

# --- MODE 3: ANALYZE IMAGE ---
elif app_mode == "🖼️ Analyze Image":
    st.header("🖼️ Image Intelligence")
    uploaded_file = st.file_uploader("Upload photo", type=['png', 'jpg', 'jpeg'])
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, use_container_width=True)
        if st.button("Analyze"):
            try:
                res = client.models.generate_content(model="gemini-1.5-flash", contents=["Explain this image:", img])
                st.write(res.text)
            except Exception as e:
                st.error("Limit reached. Please wait.")
