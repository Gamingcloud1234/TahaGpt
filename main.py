import streamlit as st
import google.generativeai as genai
from PIL import Image

# --- PAGE CONFIG ---
st.set_page_config(page_title="TahaGpt Super App", page_icon="🚀")

# --- API SETUP ---
try:
    # Using the secret you just added
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    # Fix: Using the most stable model name for 2026
    model = genai.GenerativeModel('gemini-1.5-flash') 
except Exception as e:
    st.error("Check your API Key in Secrets!")
    st.stop()

# --- SIDEBAR (UI) ---
with st.sidebar:
    st.title("🚀 TahaGpt Pro")
    if st.button("➕ New Chat"):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    # Tool Selection
    choice = st.radio("Select Tool:", ["💬 Chat", "🖼️ Analyze Image", "📁 PDF Info"])

# --- CHAT LOGIC ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if choice == "💬 Chat":
    st.header("Chat with TahaGpt")
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("How can I help you?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate Response
        response = model.generate_content(prompt)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        with st.chat_message("assistant"):
            st.markdown(response.text)

elif choice == "🖼️ Analyze Image":
    st.header("Image AI")
    file = st.file_uploader("Upload an image", type=["jpg", "png", "jpeg"])
    if file:
        img = Image.open(file)
        st.image(img, use_container_width=True)
        if st.button("What is this?"):
            res = model.generate_content(["Describe this image in detail", img])
            st.write(res.text)

elif choice == "📁 PDF Info":
    st.header("PDF Tools")
    st.info("Upload your 9th grade notes here soon!")
