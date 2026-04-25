import streamlit as st
import google.generativeai as genai
from PIL import Image

# --- PAGE SETUP ---
st.set_page_config(page_title="TahaGpt Super App", page_icon="🚀", layout="wide")

# --- API SECRETS ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    # Using 1.5 Flash - it's fast and handles images + text perfectly
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error("Check your Streamlit Secrets for GEMINI_API_KEY!")
    st.stop()

# --- SIDEBAR & NEW CHAT (+) ---
with st.sidebar:
    st.title("⚙️ TahaGpt Menu")
    if st.button("➕ New Chat"):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    app_mode = st.radio("Select Tool:", ["💬 Chatbot", "🖼️ Analyze Image", "🎨 Imagine (Coming Soon)"])
    st.info("Home WiFi Version - Karachi")

# --- INITIALIZE CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- MODE: CHATBOT ---
if app_mode == "💬 Chatbot":
    st.header("💬 TahaGpt Conversation")
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask TahaGpt anything..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate Response
        response = model.generate_content(prompt)
        
        with st.chat_message("assistant"):
            st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})

# --- MODE: IMAGE ANALYSIS ---
elif app_mode == "🖼️ Analyze Image":
    st.header("🖼️ Image Intelligence")
    uploaded_file = st.file_uploader("Upload a photo", type=['png', 'jpg', 'jpeg'])
    
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="Uploaded Image", use_container_width=True)
        
        if st.button("Analyze this Photo"):
            with st.spinner("Looking at the image..."):
                response = model.generate_content(["Please describe this image in detail and tell me what you see.", img])
                st.write("### AI Analysis:")
                st.write(response.text)

# --- MODE: IMAGINE ---
elif app_mode == "🎨 Imagine (Coming Soon)":
    st.header("🎨 Image Generation")
    st.info("Taha, generating images requires a different API (like DALL-E). For now, use 'Analyze Image' to talk to your photos!")
