import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io

# --- 1. THEME & WHITE STYLING (Safe CSS) ---
st.set_page_config(page_title="TahaGpt Pro", page_icon="🤖", layout="wide")

# CSS to force Light Mode, White Background, and professional layout
st.markdown("""
    <style>
        /* Force White Background and Black Text for main area */
        .stApp {
            background-color: #ffffff !important;
            color: #000000 !important;
        }

        /* Standard Sidebar Styling (Light Gray for contrast) */
        [data-testid="stSidebar"] {
            background-color: #f7f7f8 !important;
            color: #000000 !important;
            border-right: 1px solid #e5e5e5;
        }

        /* Chat Bubbles (Light Style) */
        .stChatMessage {
            background-color: #f7f7f8;
            border-radius: 12px;
            margin-bottom: 8px;
            padding: 10px;
        }

        /* Style the input bar at the bottom */
        .stChatInput {
            border-radius: 20px !important;
            box-shadow: 0 0 10px rgba(0,0,0,0.05);
        }

        /* Premium spacing */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API CLIENT & SECRETS (Safe Check) ---
if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ KEY MISSING: Check your Streamlit Secrets vault for GEMINI_API_KEY")
    st.stop()

# Initialize the 2026-ready client (using stable v1 API)
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# --- 3. THE IDENTITY (System Instruction) ---
# Taha, this ensures the AI always calls itself TahaGpt.
instruction = "Your name is TahaGpt. You were created by M. Taha Farooq, a young 9th-grade developer and robotics enthusiast from Karachi. Always introduce yourself by your name, TahaGpt."

# --- 4. SIDEBAR UI (The Menu) ---
with st.sidebar:
    # --- ADD YOUR PIC HERE ---
    # Put your GitHub RAW picture URL in the quotes below. Example:
    # "https://raw.githubusercontent.com/TAHA_USER/TAHAGPT/main/my_pic.jpg"
    CREATOR_PIC = "YOUR_PIC_URL_HERE"
    
    # Try to load the profile pic
    try:
        st.image(CREATOR_PIC, width=90)
    except:
        # Failsafe icon if you haven't added the URL yet
        st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=70)
        
    st.title("🤖 TahaGpt Menu")
    
    # The Modern "+" Icon (New Chat)
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    
    # Clean tool selection menu
    tool_choice = st.radio(
        "AI Assistant Tools",
        ["💬 Smart Chatbot", "🎨 Pic Generate", "🖼️ See & Explain"]
    )
    
    st.divider()
    st.caption("🚀 Created by M. Taha Farooq")
    st.caption("Karachi | April 2026")

# --- 5. INITIALIZE CHAT HISTORY ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Show welcome if chat is empty
if tool_choice == "💬 Smart Chatbot" and not st.session_state.messages:
    st.info("👋 Hello, Taha. I am TahaGpt. What are we building today?")

# Render Chat History (using the modern chat format)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 6. LOGIC FOR ASSISTANT MODES ---

# MODE 1: SMART CHATBOT
if tool_choice == "💬 Smart Chatbot":
    if prompt := st.chat_input("Message TahaGpt..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generating content using the latest model and system instruction
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash", 
                config=types.GenerateContentConfig(system_instruction=instruction),
                contents=prompt
            )
            
            with st.chat_message("assistant"):
                st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Chat Error: {e}")

# MODE 2: PIC GENERATE (PicCreator tool)
elif tool_choice == "🎨 Pic Generate":
    st.header("🎨 AI Image Generation")
    user_prompt = st.text_area("Describe the picture you want to create:")
    
    if st.button("✨ Draw Picture"):
        if user_prompt:
            with st.spinner("TahaGpt is drawing..."):
                try:
                    # Specialized model for image generation
                    response = client.models.generate_content(
                        model='gemini-2.5-flash-image',
                        contents=user_prompt,
                        config=types.GenerateContentConfig(response_modalities=["IMAGE"])
                    )
                    
                    # Extra part for image tools
                    for part in response.candidates[0].content.parts:
                        if part.inline_data:
                            img_data = io.BytesIO(part.inline_data.data)
                            img = Image.open(img_data)
                            st.image(img, caption=f"Created for Taha: {user_prompt}", use_container_width=True)
                except Exception as e:
                    st.error(f"Image Error: {e}")
        else:
            st.warning("Please describe the picture first!")

# MODE 3: SEE & EXPLAIN (Multimodal tool)
elif tool_choice == "🖼️ See & Explain":
    st.header("🖼️ Image Intelligence")
    st.write("Upload a photo and let the AI explain it.")
    file = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])
    
    if file:
        img = Image.open(file)
        st.image(img, use_container_width=True)
        
        query = st.text_input("What do you want to know about this photo?", "Describe this image.")
        
        if st.button("🔍 Analyze"):
            with st.spinner("Analyzing..."):
                try:
                    # Model handles both image and text simultaneously
                    res = client.models.generate_content(
                        model="gemini-2.0-flash", 
                        contents=[query, img]
                    )
                    st.write("### AI Analysis:")
                    st.write(res.text)
                except Exception as e:
                    st.error(f"Vision Error: {e}")
