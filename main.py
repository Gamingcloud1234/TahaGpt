import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="TahaGpt Super App", page_icon="🚀", layout="wide")

# --- 2. API SETUP ---
if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ Please add GEMINI_API_KEY to your Streamlit Secrets!")
    st.stop()

# Initialize the new 2026 GenAI Client
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# --- 3. SIDEBAR UI (The Menu) ---
with st.sidebar:
    st.title("🤖 TahaGpt Pro")
    st.subheader("Karachi Home Edition")
    
    # THE "+" ICON / NEW CHAT BUTTON
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    
    # App Mode Selection
    app_mode = st.radio(
        "Select a Tool:",
        ["💬 Smart Chat", "🎨 Pic Generate", "🖼️ See & Explain"]
    )
    
    st.divider()
    st.caption("Powered by Gemini 3.1 Flash")

# --- 4. SESSION STATE FOR CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 5. APP MODES ---

# --- MODE 1: SMART CHAT ---
if app_mode == "💬 Smart Chat":
    st.header("💬 TahaGpt Conversation")
    
    # Display message history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User Input
    if prompt := st.chat_input("Ask TahaGpt anything..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate Response using the newest Flash model
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-preview", 
                contents=prompt
            )
            with st.chat_message("assistant"):
                st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Chat Error: {e}")

# --- MODE 2: PIC GENERATE ---
elif app_mode == "🎨 Pic Generate":
    st.header("🎨 AI Image Creator")
    st.write("Describe a picture, and I will draw it for you!")
    
    user_prompt = st.text_area("What should I draw?", placeholder="A futuristic Karachi city with flying cars...")
    
    if st.button("✨ Generate Picture"):
        if user_prompt:
            with st.spinner("TahaGpt is painting..."):
                try:
                    # Using the specialized 3.1 Image model (Nano Banana 2)
                    response = client.models.generate_content(
                        model='gemini-3.1-flash-image-preview',
                        contents=user_prompt,
                        config=types.GenerateContentConfig(response_modalities=["IMAGE"])
                    )
                    
                    # Display the generated image
                    for part in response.candidates[0].content.parts:
                        if part.inline_data:
                            img_data = io.BytesIO(part.inline_data.data)
                            img = Image.open(img_data)
                            st.image(img, caption=f"Result for: {user_prompt}", use_container_width=True)
                except Exception as e:
                    st.error(f"Image Generation Error: {e}")
        else:
            st.warning("Please type a description first!")

# --- MODE 3: SEE & EXPLAIN ---
elif app_mode == "🖼️ See & Explain":
    st.header("🖼️ Image Intelligence")
    st.write("Upload a photo and ask me questions about it.")
    
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="Your Upload", use_container_width=True)
        
        user_question = st.text_input("What do you want to know about this photo?", "What is in this image?")
        
        if st.button("🔍 Analyze"):
            with st.spinner("Analyzing..."):
                try:
                    response = client.models.generate_content(
                        model="gemini-3.1-flash-preview",
                        contents=[user_question, img]
                    )
                    st.write("### TahaGpt's Observation:")
                    st.write(response.text)
                except Exception as e:
                    st.error(f"Analysis Error: {e}")
